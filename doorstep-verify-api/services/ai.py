import json
import base64
import io
import re
import requests

from typing import Optional
from PIL import Image
from config import gemini_client, openai_client, HF_TOKEN


def transliterate_to_latin(text: str) -> str:
    """Convert any script (Devanagari, Arabic, Chinese, etc.) to Latin/Roman characters.
    Phonetic only — names stay as names. 'माणिक नगर' → 'Manik Nagar', never 'Pearl Town'."""
    if not text:
        return text
    # Skip if already fully Latin/ASCII
    if not re.search(r'[^\x00-\x7F]', text):
        return text

    prompt = (
        "Transliterate the address below to Latin/Roman script (English alphabet).\n"
        "STRICT RULES — read carefully:\n"
        "1. Do NOT translate meanings. Keep every name phonetically as it sounds.\n"
        "2. 'माणिक नगर' → 'Manik Nagar'   NOT 'Pearl Town'\n"
        "3. 'सोमवार पेठ' → 'Somwar Peth'   NOT 'Monday Market'\n"
        "4. Local-script digits: '१२३' → '123'\n"
        "5. Return ONLY the transliterated address — no explanation, no quotes.\n\n"
        f"Address: {text}"
    )
    try:
        resp = gemini_client.models.generate_content(
            model="gemini-flash-latest",
            contents=[prompt],
        )
        result = resp.text.strip()
        # Safety: if LLM returned something longer than expected, log and fallback
        if len(result) > len(text) * 4:
            return text
        return result
    except Exception:
        return text  # fallback: return original unchanged


LLM_ADDRESS_PROMPT = """You are verifying a delivery location for a logistics company.

Customer's delivery address (entered when ordering): "{stored}"
Address at driver's GPS location right now (reverse geocoded): "{gps}"
Text visible in the delivery photo (nameplate/sign/house number): "{ocr}"

Question: Is the driver at the correct delivery location?

Rules:
- Customers often use landmarks like "near McDonald's" or "opposite the park"
- The GPS address and stored address may use different landmark names for the same area — that is OK
- Minor spelling differences, abbreviations, local language names are OK
- Only say false if they are clearly in different streets, areas, or cities
- If GPS address is unavailable, use OCR text and stored address only

Respond ONLY in valid JSON with no markdown:
{{"match": true or false, "confidence": 0.0 to 1.0, "reason": "one line explanation"}}"""


def llm_address_match(
    stored_address: str,
    gps_address: Optional[str],
    ocr_text: Optional[str],
) -> dict:
    prompt = LLM_ADDRESS_PROMPT.format(
        stored = stored_address or "unknown",
        gps    = gps_address   or "unavailable",
        ocr    = ocr_text      or "none visible",
    )

    # Tier 1: GPT-4o-mini — Gemini is busy with image analysis, keep them separate
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"LLM address match (GPT) failed: {e}")

    # Tier 2: Gemini fallback (text-only, no image)
    try:
        response = gemini_client.models.generate_content(
            model="gemini-flash-latest",
            contents=[prompt],
        )
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"LLM address match (Gemini fallback) failed: {e}")

    # Tier 3: word overlap fallback (no LLM)
    stored_words = set((stored_address or "").lower().split())
    gps_words    = set((gps_address    or "").lower().split())
    common       = stored_words & gps_words - {"the", "a", "of", "and", "in", "at", "near", "road", "street", "st"}
    match        = len(common) >= 2
    return {
        "match":      match,
        "confidence": 0.5,
        "reason":     f"Fallback word overlap: {len(common)} common words ({', '.join(list(common)[:3])})",
    }


AI_PROMPT = (
    "You are verifying a delivery photo for a logistics company.\n"
    "Delivery address: {address}\n\n"
    "STRICT RULES:\n"
    "- location_type is 'front_door' ONLY if you can clearly see: a door panel, door frame, door handle, or doorbell\n"
    "- A plain wall, fence, gate pillar, or building exterior WITHOUT a visible door = 'unknown', NOT 'front_door'\n"
    "- package_at_door is true ONLY if location_type is front_door or porch AND package is visible\n"
    "- If the photo is blurry, dark, or unclear set confidence below 0.7\n\n"
    "Respond ONLY in valid JSON with no markdown, no code blocks:\n"
    "{{\n"
    "  \"location_type\": \"front_door or porch or yard or garden or side_door or garage or interior_door or wall or unknown\",\n"
    "  \"package_at_door\": true or false,\n"
    "  \"visible_address_text\": \"any house number, building name or nameplate text visible in photo\" or null,\n"
    "  \"address_confirmed\": true or false,\n"
    "  \"confidence\": 0.0 to 1.0,\n"
    "  \"rejection_reason\": null or \"reason string\"\n"
    "}}"
)


def compress_for_ai(image_b64: str, max_size: int = 1024) -> str:
    img = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
    ratio = min(max_size / img.width, max_size / img.height, 1.0)
    if ratio < 1.0:
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.LANCZOS
        )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()


def analyze_photo(image_b64: str, record: dict) -> dict:
    compressed = compress_for_ai(image_b64)
    address    = transliterate_to_latin(record.get("address", "unknown address"))
    prompt     = AI_PROMPT.format(address=address)

    # Tier 1: Gemini Flash (free — 1,500/day)
    try:
        result = run_gemini(compressed, prompt)
        if result.get("confidence", 0) >= 0.75:
            return build_ai_result(result)
    except Exception as e:
        print(f"Gemini failed: {e}")

    # Tier 2: OpenAI GPT-4o (your $5 — fallback)
    try:
        result = run_openai(compressed, prompt)
        return build_ai_result(result)
    except Exception as e:
        print(f"OpenAI failed: {e}")

    # Tier 3: Hugging Face BLIP (free — last resort)
    return run_huggingface_fallback(compressed)


def run_gemini(compressed_b64: str, prompt: str) -> dict:
    from google.genai import types as genai_types
    response = gemini_client.models.generate_content(
        model="gemini-flash-latest",
        contents=[
            genai_types.Part.from_bytes(
                data=base64.b64decode(compressed_b64),
                mime_type="image/jpeg",
            ),
            prompt,
        ],
    )
    text = response.text.strip()
    # Strip markdown code blocks if present
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def run_openai(compressed_b64: str, prompt: str) -> dict:
    resp = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{compressed_b64}",
                "detail": "low"
            }}
        ]}],
        max_tokens=300,
    )
    return json.loads(resp.choices[0].message.content)


def run_huggingface_fallback(compressed_b64: str) -> dict:
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            data=base64.b64decode(compressed_b64),
            timeout=30,
        ).json()
        caption = resp[0]["generated_text"].lower() if isinstance(resp, list) else ""
        at_door = any(w in caption for w in ["door", "porch", "entrance", "step", "front"])
    except Exception:
        at_door = False
        caption = ""
    return build_ai_result({
        "location_type":       "front_door" if at_door else "unknown",
        "package_at_door":     at_door,
        "visible_address_text": None,
        "address_confirmed":   False,
        "confidence":          0.6 if at_door else 0.4,
        "rejection_reason":    None if at_door else "Could not confirm front door from image",
    })


def analyze_best_frame(frames: list, record: dict) -> dict:
    """Run analyze_photo on each frame, return the best result.
    Prefers a passing door check; among passes prefers visible address text."""
    best = None
    for frame_b64 in frames:
        try:
            result = analyze_photo(frame_b64, record)
        except Exception:
            continue
        if best is None:
            best = result
            continue
        best_pass = best["door_check"].get("pass")
        this_pass = result["door_check"].get("pass")
        if this_pass is True and best_pass is not True:
            best = result
        elif this_pass is True and best_pass is True:
            if result.get("visible_address_text") and not best.get("visible_address_text"):
                best = result
    return best or analyze_photo(frames[0], record)


def build_ai_result(ai: dict) -> dict:
    door_pass    = ai["location_type"] in ["front_door", "porch"] and ai.get("package_at_door") is True
    visible_text = ai.get("visible_address_text")

    # None = no text visible (skip), True = confirmed, False = text visible but wrong
    if visible_text:
        address_confirmed = ai.get("address_confirmed") is True
    else:
        address_confirmed = None  # no nameplate — neither confirm nor contradict

    if address_confirmed is True:
        addr_detail = f"Address text '{visible_text}' confirmed in photo"
    elif address_confirmed is False:
        addr_detail = f"Visible text '{visible_text}' — does not match delivery address"
    else:
        addr_detail = "No address text visible in photo — check skipped"

    return {
        "visible_address_text": visible_text,
        "address_confirmed":    address_confirmed,
        "door_check": {
            "pass":   door_pass,
            "detail": ai.get("rejection_reason") or
                      f"{ai['location_type']} — package at door: {ai['package_at_door']}",
        },
        "address_check": {
            "pass":   address_confirmed,
            "detail": addr_detail,
        },
    }
