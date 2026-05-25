import math
import requests

from typing import Optional
from config import W3W_KEY


def reverse_geocode(lat: float, lng: float) -> Optional[str]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json"},
            headers={"User-Agent": "DoorstepVerify/1.0 kalpandeparimal60@gmail.com"},
            timeout=10,
        ).json()
        return resp.get("display_name")
    except Exception:
        return None


def haversine_metres(gps1: dict, gps2: dict) -> float:
    R    = 6371000
    dlat = math.radians(gps1["lat"] - gps2["lat"])
    dlng = math.radians(gps1["lng"] - gps2["lng"])
    a    = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(gps2["lat"]))
        * math.cos(math.radians(gps1["lat"]))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def geocode_address(address: str) -> Optional[dict]:
    from services.ai import transliterate_to_latin
    # Transliterate non-Latin scripts before sending to Nominatim
    latin_address = transliterate_to_latin(address)
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": latin_address, "format": "json", "limit": 1},
            headers={"User-Agent": "DoorstepVerify/1.0 kalpandeparimal60@gmail.com"},
            timeout=10,
        ).json()
        if not resp:
            return None
        return {"lat": float(resp[0]["lat"]), "lng": float(resp[0]["lon"])}
    except Exception:
        return None


def w3w_to_coords(words: str) -> Optional[dict]:
    if not W3W_KEY or not words:
        return None
    try:
        res = requests.get(
            "https://api.what3words.com/v3/convert-to-coordinates",
            params={"words": words, "key": W3W_KEY},
            timeout=10,
        ).json()
        if "error" in res:
            return None
        return {"lat": res["coordinates"]["lat"], "lng": res["coordinates"]["lng"]}
    except Exception:
        return None


def check_w3w(driver_words: Optional[str], expected_words: Optional[str]) -> dict:
    if not expected_words:
        return {"pass": None, "detail": "W3W not tagged for this address — check skipped"}
    if not driver_words:
        return {"pass": None, "detail": "W3W unavailable from driver — GPS + OCR used"}
    if driver_words.strip() == expected_words.strip():
        return {"pass": True, "detail": f"Exact door square: ///{driver_words}"}
    driver_c   = w3w_to_coords(driver_words)
    expected_c = w3w_to_coords(expected_words)
    if not driver_c or not expected_c:
        return {"pass": None, "detail": "W3W lookup failed — GPS used"}
    dist = haversine_metres(driver_c, expected_c)
    ok   = dist <= 9
    return {
        "pass":   ok,
        "detail": f"///{driver_words} is {int(dist)}m from ///{expected_words}"
                  + ("" if ok else " — outside front door zone"),
    }


def check_location_three_signals(gps: dict, record: dict, visible_text: Optional[str]) -> dict:
    # Signal 1: GPS geofence
    # Use stored expected_lat/lng if available (precise) — else fall back to geocoding (imprecise)
    exp_lat = record.get("expected_lat")
    exp_lng = record.get("expected_lng")

    if exp_lat and exp_lng:
        # Stored coordinates: 50m floor accounts for GPS error in both the stored coord
        # and the driver's current reading (two different devices, recorded at different times)
        dist      = haversine_metres(gps, {"lat": exp_lat, "lng": exp_lng})
        threshold = max(gps.get("accuracy", 15) * 3, 50)
        sig_gps   = {
            "pass":   dist <= threshold,
            "detail": f"{int(dist)}m from delivery address (limit {int(threshold)}m, GPS ±{int(gps.get('accuracy', 0))}m)",
        }
    else:
        # Fallback: geocode the address text
        addr_coords = geocode_address(record.get("address", ""))
        if addr_coords:
            dist      = haversine_metres(gps, addr_coords)
            threshold = max(gps.get("accuracy", 30) * 3, 250)
            sig_gps   = {
                "pass":   dist <= threshold,
                "detail": f"{int(dist)}m from geocoded address (limit {int(threshold)}m, GPS ±{int(gps.get('accuracy', 0))}m)",
            }
        else:
            sig_gps = {"pass": None, "detail": "Location could not be verified — no coordinates on record"}

    # Signal 2: what3words (3m precision)
    sig_w3w = check_w3w(
        gps.get("w3w_words"),
        record.get("front_door_w3w"),
    )

    # Signal 3: LLM semantic address match
    # Transliterate stored address so LLM/Nominatim can read any script
    from services.ai import llm_address_match, transliterate_to_latin
    stored_addr = transliterate_to_latin(record.get("address", ""))
    gps_address = reverse_geocode(gps["lat"], gps["lng"])
    llm         = llm_address_match(
        stored_address = stored_addr,
        gps_address    = gps_address,
        ocr_text       = visible_text,
    )
    if llm["confidence"] >= 0.6:
        sig_llm = {
            "pass":   llm["match"],
            "detail": f"LLM: {llm['reason']} (confidence {llm['confidence']:.0%})",
        }
    else:
        sig_llm = {
            "pass":   None,
            "detail": f"LLM confidence too low ({llm['confidence']:.0%}) — skipped",
        }

    passed  = sum(1 for s in [sig_gps, sig_w3w, sig_llm] if s["pass"] is True)
    counted = sum(1 for s in [sig_gps, sig_w3w, sig_llm] if s["pass"] is not None)

    # PRIMARY: Stored precise GPS coords + GPS passes = strong proof, location confirmed
    if exp_lat and exp_lng and sig_gps["pass"]:
        ok = True
    # MODERATE: W3W passes (3m square precision) = very strong proof
    elif sig_w3w.get("pass") is True:
        ok = True
    # FALLBACK: need any 2 signals, or 1 if only 1 available
    else:
        ok = passed >= 2 or (counted <= 1 and passed >= 1)

    return {
        "pass":    ok,
        "detail":  f"{passed}/{counted} location signals confirmed",
        "gps":     sig_gps,
        "w3w":     sig_w3w,
        "ocr_loc": sig_llm,
    }
