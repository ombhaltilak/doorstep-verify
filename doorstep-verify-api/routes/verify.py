import os
import json
import base64
import uuid
import hashlib

from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import supabase
from models import VerifyRequest, AddDeliveryRequest
from services.ai import analyze_photo, analyze_best_frame
from services.location import check_location_three_signals
from services.geotag import verify_photo_exif, verify_video_geotag

router = APIRouter()


@router.get("/")
async def root():
    return {"status": "Doorstep Verify API running"}


@router.get("/verify")
async def list_deliveries(action: str = "", driverId: str = ""):
    if action == "ping":
        return JSONResponse({"status": "awake"})
    rows = (
        supabase.table("deliveries")
        .select("*")
        .ilike("driver_id", driverId.strip())
        .eq("status", "pending")
        .execute()
    )
    return JSONResponse(rows.data)


@router.get("/deliveries")
async def list_all_deliveries(status: str = "", driver_id: str = ""):
    query = supabase.table("deliveries").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if driver_id:
        query = query.eq("driver_id", driver_id.strip().lower())
    rows = query.execute()
    return JSONResponse(rows.data)


@router.post("/deliveries/{tracking_id}/reset")
async def reset_delivery(tracking_id: str):
    supabase.table("deliveries").update({
        "status": "pending", "verified": None, "checks": None,
        "file_url": None, "proof_hash": None, "timestamp": None,
    }).ilike("tracking_id", tracking_id.strip()).execute()
    return JSONResponse({"ok": True})


@router.post("/deliveries")
async def add_delivery(req: AddDeliveryRequest):
    row = {
        "tracking_id":    req.tracking_id.strip().upper(),  # uppercase — barcode format
        "customer_name":  req.customer_name.strip(),
        "address":        req.address.strip(),
        "driver_id":      req.driver_id.strip().lower(),
        "status":         "pending",
        "verified":       None,
        "checks":         None,
        "file_url":       None,
        "proof_hash":     None,
        "timestamp":      None,
    }
    if req.expected_lat is not None:
        row["expected_lat"] = req.expected_lat
    if req.expected_lng is not None:
        row["expected_lng"] = req.expected_lng
    if req.front_door_w3w:
        row["front_door_w3w"] = req.front_door_w3w.strip()

    supabase.table("deliveries").upsert(row, on_conflict="tracking_id").execute()
    return JSONResponse({"ok": True, "tracking_id": row["tracking_id"]})


@router.post("/verify")
async def verify(req: VerifyRequest):
    file_bytes  = base64.b64decode(req.file_base64)
    timestamp   = datetime.now(timezone.utc).isoformat()
    tracking_id = req.tracking_id.strip().upper()
    barcode_raw = req.barcode.strip().split('|')[0].strip().upper()

    # Look up delivery record in Supabase
    record = get_record(tracking_id)
    if not record:
        return JSONResponse({"error": "Tracking ID not found"}, status_code=404)

    # ── Check 1: Barcode ─────────────────────────────────────────────────────
    barcode_ok    = barcode_raw == tracking_id
    barcode_check = {
        "pass":   barcode_ok,
        "detail": "Barcode matches order" if barcode_ok
                  else f"Barcode '{barcode_raw}' does not match order '{tracking_id}'"
    }

    # ── Check 2: Geotag (GPS baked into the file) ────────────────────────────
    if req.media_type == "photo":
        geotag_check = verify_photo_exif(file_bytes, req.gps)
        ai_result    = analyze_photo(req.file_base64, record)
    else:
        geotag_check, analysis_frames = verify_video_geotag(file_bytes, req.gps, req.frame_base64)
        if not analysis_frames:
            analysis_frames = [req.frame_base64] if req.frame_base64 else []
        ai_result = analyze_best_frame(analysis_frames, record) if analysis_frames else {
            "visible_address_text": None, "address_confirmed": None,
            "door_check":    {"pass": False, "detail": "No frames extracted from video"},
            "address_check": {"pass": None,  "detail": "No frames extracted from video"},
        }

    # ── Checks 3+4+5: AI scene + three-signal location ───────────────────────
    visible_text = ai_result.get("visible_address_text")       # OCR text from photo
    location_check = check_location_three_signals(req.gps, record, visible_text)
    door_check       = ai_result["door_check"]

    # geotag None = unreadable due to compression (skip, not fail)
    # address_check is informational only — not required for verified=true
    geotag_pass = geotag_check["pass"] is not False   # True or None both pass
    all_pass = all([
        barcode_check["pass"],
        geotag_pass,
        location_check["pass"],
        door_check["pass"],
    ])

    # ── Upload proof file to Supabase Storage ────────────────────────────────
    ext       = "jpg" if req.media_type == "photo" else "webm"
    filename  = f"{tracking_id}_{uuid.uuid4().hex[:8]}.{ext}"
    try:
        supabase.storage.from_("proof-files").upload(
            filename, file_bytes,
            file_options={"content-type": "image/jpeg" if ext == "jpg" else "video/webm"}
        )
        file_url = (
            f"{os.environ['SUPABASE_URL']}/storage/v1/object/public/proof-files/{filename}"
        )
    except Exception as e:
        file_url = f"upload_failed: {str(e)}"

    # ── SHA-256 tamper-evident hash ───────────────────────────────────────────
    hash_input = (
        file_bytes
        + str(req.gps["lat"]).encode()
        + str(req.gps["lng"]).encode()
        + timestamp.encode()
        + tracking_id.encode()
    )
    proof_hash = hashlib.sha256(hash_input).hexdigest()

    # ── Save result to Supabase DB ────────────────────────────────────────────
    checks_dict = {
        "barcode_match":  barcode_check,
        "geotag_verify":  geotag_check,
        "location":       location_check,
        "front_door":     door_check,
        "address_check":  ai_result["address_check"],
    }
    result_row = {
        "tracking_id":  tracking_id,
        "driver_id":    req.driver_id.strip().lower(),
        "verified":     all_pass,
        "media_type":   req.media_type,
        "file_url":     file_url,
        "proof_hash":   proof_hash,
        "gps_lat":      req.gps["lat"],
        "gps_lng":      req.gps["lng"],
        "gps_accuracy": req.gps.get("accuracy"),
        "timestamp":    timestamp,
        "checks":       json.dumps(checks_dict),
        "status":       "completed",
    }
    supabase.table("deliveries").upsert(result_row, on_conflict="tracking_id").execute()

    return JSONResponse({
        "verified":   all_pass,
        "checks":     checks_dict,
        "file_url":   file_url,
        "proof_hash": proof_hash,
    })


# ── DB helpers ───────────────────────────────────────────────────────────────

def get_record(tracking_id: str):
    tid = tracking_id.strip().upper()
    # ilike = case-insensitive exact match — handles old lowercase data in DB
    res = (
        supabase.table("deliveries")
        .select("*")
        .ilike("tracking_id", tid)
        .execute()
    )
    return res.data[0] if res.data else None
