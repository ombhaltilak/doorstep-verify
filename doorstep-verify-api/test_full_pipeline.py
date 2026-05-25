"""
Full end-to-end pipeline test.
Creates a synthetic door image, injects real GPS EXIF, and sends to /verify.
Run: venv/bin/python test_full_pipeline.py
"""

import base64
import io
import json
import os
import time
import requests
import piexif
from dotenv import load_dotenv
from supabase import create_client
from PIL import Image, ImageDraw

load_dotenv()
API = "http://localhost:8000"
supa = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ── Geocode address using Nominatim (free, no key) ───────────────────────────
def geocode(address: str):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "DoorstepVerify-Test/1.0 kalpandeparimal60@gmail.com"},
            timeout=10,
        ).json()
        if resp:
            return float(resp[0]["lat"]), float(resp[0]["lon"])
    except Exception:
        pass
    return None, None


# ── Build a synthetic door image with given house number ─────────────────────
def make_door_jpeg(house_num: str) -> bytes:
    img  = Image.new("RGB", (600, 800), (180, 140, 100))
    draw = ImageDraw.Draw(img)
    draw.rectangle([150, 200, 450, 720], outline=(80, 50, 30), width=12, fill=(120, 70, 40))
    draw.rectangle([180, 230, 420, 700], outline=(60, 40, 20), width=4)
    draw.ellipse([390, 460, 415, 490], fill=(200, 170, 50))
    draw.text((250, 130), house_num, fill=(255, 255, 255))
    draw.rectangle([100, 720, 500, 760], fill=(160, 150, 140))
    draw.rectangle([220, 620, 370, 720], outline=(139, 90, 43), width=3, fill=(210, 180, 140))
    draw.line([220, 665, 370, 665], fill=(139, 90, 43), width=2)
    draw.line([295, 620, 295, 720], fill=(139, 90, 43), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ── Inject GPS EXIF into JPEG bytes ──────────────────────────────────────────
def inject_gps_exif(jpeg_bytes: bytes, lat: float, lng: float) -> bytes:
    def to_rational(value: float):
        # convert decimal degrees to (deg, min, sec) as piexif rationals
        d = int(abs(value))
        m = int((abs(value) - d) * 60)
        s = round(((abs(value) - d) * 60 - m) * 60 * 1000)
        return ((d, 1), (m, 1), (s, 1000))

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef:  b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude:     to_rational(lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lng >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude:    to_rational(abs(lng)),
    }
    exif_dict  = {"GPS": gps_ifd}
    exif_bytes = piexif.dump(exif_dict)

    # Use Pillow to re-save with EXIF injected (piexif.insert needs a file path)
    img = Image.open(io.BytesIO(jpeg_bytes))
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif_bytes, quality=92)
    return out.getvalue()


# ── Main test ─────────────────────────────────────────────────────────────────
def run():
    print("=== Door-Step Delivery Verification — Full Pipeline Test ===\n")

    # 0. Reset test records to pending so every run is fresh
    supa.table("deliveries").update({"status": "pending"}).in_(
        "tracking_id", ["TEST001", "TEST002", "TEST003"]
    ).execute()
    print("[0] ✓ Reset TEST001/002/003 to pending")

    # 1. Ping
    r = requests.get(f"{API}/verify?action=ping")
    assert r.ok, f"Ping failed: {r.text}"
    print("[1] ✓ API is awake")

    # 2. Confirm a pending delivery is in DB
    r = requests.get(f"{API}/verify?driverId=DRIVER1")
    deliveries = r.json()
    tracking_ids = [d["tracking_id"] for d in deliveries]
    assert len(tracking_ids) > 0, "No pending deliveries — run supabase_fix_rls.sql to reset test data"
    test_id  = tracking_ids[0]
    delivery = next(d for d in deliveries if d["tracking_id"] == test_id)
    address  = delivery.get("address", "")
    print(f"[2] ✓ Using {test_id} — address: {address}")

    # 3. Geocode address to get real GPS coordinates
    lat, lng = geocode(address)
    if lat is None:
        print("    ⚠ Geocoding failed — using fallback coords (location check may fail)")
        lat, lng = 41.8788, -87.6359
    else:
        print(f"[3] ✓ Geocoded to ({lat:.5f}, {lng:.5f})")

    # 4. Build geotagged photo with matching house number
    house_num = address.split()[0] if address else "000"
    door_jpeg = make_door_jpeg(house_num)
    geotagged = inject_gps_exif(door_jpeg, lat, lng)
    file_b64  = base64.b64encode(geotagged).decode()
    print(f"[4] ✓ Created geotagged JPEG ({len(geotagged):,} bytes) — house #{house_num}")

    # 5. Submit verification request
    payload = {
        "tracking_id": test_id,
        "barcode":     test_id,             # exact match → pass
        "driver_id":   "DRIVER1",
        "media_type":  "photo",
        "gps":         {"lat": lat, "lng": lng, "accuracy": 12.0},
        "file_base64": file_b64,
    }

    print("[5] Waiting 2s for Nominatim rate-limit window …")
    time.sleep(2)
    print("[5] Submitting to /verify …")
    r = requests.post(f"{API}/verify", json=payload, timeout=60)
    assert r.ok, f"HTTP {r.status_code}: {r.text}"
    result = r.json()

    # 6. Print results
    print("\n── Verification Result ─────────────────────────────────")
    print(f"   VERIFIED:    {result['verified']}")
    checks = result["checks"]
    for key, val in checks.items():
        icon = "✓" if val.get("pass") else ("~" if val.get("pass") is None else "✗")
        print(f"   {icon} {key:20s}: {val.get('detail','')}")
    print(f"   proof_hash:  {result['proof_hash'][:24]}…")
    print(f"   file_url:    {result['file_url'][:60]}…")
    print("────────────────────────────────────────────────────────")

    passed = sum(1 for v in checks.values() if v.get("pass") is True)
    print(f"\n{passed}/4 checks passed.")
    if result["verified"]:
        print("ALL CHECKS PASSED — pipeline is fully operational.")
    else:
        print("Some checks failed — see details above.")
        print("(Expected: geotag=✓, barcode=✓, location=✓, front_door=✓)")

if __name__ == "__main__":
    run()
