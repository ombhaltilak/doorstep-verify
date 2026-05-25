import base64
from typing import Optional

import cv2
import piexif


def verify_photo_exif(file_bytes: bytes, gps_browser: dict) -> dict:
    try:
        exif_data = piexif.load(file_bytes)
        gps_ifd   = exif_data.get("GPS", {})
        if not gps_ifd:
            return {"pass": False, "detail": "No GPS EXIF found in photo — piexifjs may not have injected it"}

        def dms_to_deg(dms):
            d, m, s = dms
            return d[0] / d[1] + m[0] / m[1] / 60 + s[0] / s[1] / 3600

        exif_lat = dms_to_deg(gps_ifd[piexif.GPSIFD.GPSLatitude])
        exif_lng = dms_to_deg(gps_ifd[piexif.GPSIFD.GPSLongitude])
        if gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)  == b"S": exif_lat *= -1
        if gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef) == b"W": exif_lng *= -1

        ok = (
            abs(exif_lat - gps_browser["lat"]) < 0.001
            and abs(exif_lng - gps_browser["lng"]) < 0.001
        )
        return {
            "pass":   ok,
            "detail": "EXIF GPS matches submitted GPS" if ok
                      else f"EXIF GPS mismatch: file has ({exif_lat:.5f},{exif_lng:.5f}), submitted ({gps_browser['lat']:.5f},{gps_browser['lng']:.5f})",
        }
    except Exception as e:
        return {"pass": False, "detail": f"EXIF read error: {e}"}


def verify_video_geotag(file_bytes: bytes, gps_browser: dict, frame_b64: Optional[str] = None):
    # Geotag: read GPS EXIF from canvas reference frame if available
    if frame_b64:
        frame_bytes = base64.b64decode(frame_b64)
        geotag = verify_photo_exif(frame_bytes, gps_browser)
        if geotag["pass"] is True:
            geotag["detail"] = "Video frame GPS (EXIF) matches submitted GPS"
        elif geotag["pass"] is False and "No GPS EXIF" in geotag.get("detail", ""):
            geotag = {"pass": None, "detail": "Video frame has no GPS EXIF — location check used instead"}
    else:
        geotag = {"pass": None, "detail": "No reference frame received — location check used instead"}

    # Extract 3 frames from the video for AI scene analysis
    analysis_frames = _extract_video_frames(file_bytes)
    if not analysis_frames and frame_b64:
        analysis_frames = [frame_b64]  # fallback to canvas frame

    return geotag, analysis_frames


def _extract_video_frames(file_bytes: bytes, count: int = 3) -> list:
    """Extract `count` evenly-spaced frames from the video as base64 JPEGs."""
    try:
        tmp = "/tmp/proof_video.webm"
        with open(tmp, "wb") as f:
            f.write(file_bytes)
        cap   = cv2.VideoCapture(tmp)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total == 0:
            cap.release()
            return []
        frames = []
        positions = [int(total * (i + 1) / (count + 1)) for i in range(count)]
        for pos in positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if ret:
                _, buf = cv2.imencode(".jpg", frame)
                frames.append(base64.b64encode(buf).decode())
        cap.release()
        return frames
    except Exception:
        return []
