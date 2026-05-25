# DoorStep — AI-Powered Proof of Delivery
### Prototype Presentation

---

## The Problem

Last-mile delivery faces three recurring fraud and dispute scenarios that cost logistics companies significantly:

| Scenario | Impact |
|---|---|
| Driver marks delivered but package left at wrong address | Customer disputes, re-delivery cost |
| Package left at gate / yard instead of front door | Theft, liability claims |
| Proof photo is faked or recycled from a previous delivery | Fraud, no legal standing |

Existing POD (Proof of Delivery) systems capture a photo — but do not **verify** it. A photo of a random door taken anywhere passes the check.

---

## The Solution

**DoorStep** is a browser-based PWA that runs on any smartphone. No app store, no hardware beyond the driver's phone. Every delivery generates a tamper-proof proof file that is automatically verified across five independent checks before the delivery is marked complete.

---

## How It Works — Driver Flow

```
Sign In → Select Delivery → Scan Package Barcode → GPS Lock → Capture Proof → Verified ✅
```

**Step 1 — Barcode Scan**
Driver scans the package barcode with the phone camera. The system blocks progress if the scanned barcode does not match the assigned delivery. Wrong package = cannot proceed.

**Step 2 — GPS Lock**
The system acquires GPS using a Kalman filter for noise reduction. Accuracy is displayed in real time. The driver cannot proceed until signal quality is acceptable.

**Step 3 — Proof Capture**
Driver chooses Photo or Video. Both modes embed GPS coordinates permanently:
- **Photo** — GPS injected into JPEG EXIF metadata (tamper-evident, industry standard)
- **Video** — GPS injected into a canvas reference frame via EXIF; 3 frames extracted for AI analysis

**Step 4 — AI Verification**
The proof file is uploaded and run through 5 automated checks instantly.

---

## The 5 Verification Checks

| # | Check | Method | Must Pass? |
|---|---|---|---|
| 1 | **Package ID** | Barcode scan vs assigned tracking ID — exact match | Yes |
| 2 | **Location Stamp** | GPS EXIF in proof file matches submitted coordinates | Yes (SKIP = pass) |
| 3 | **Delivery Location** | 3-signal GPS verification (see below) | Yes |
| 4 | **Door Confirmed** | AI vision — door panel/handle/frame + package visible | Yes |
| 5 | **Address Match** | AI reads nameplate/house number vs delivery address | Informational |

### Location — 3-Signal Verification

```
Signal 1: GPS Geofence     → Driver within 50m of stored delivery coordinates
Signal 2: What3Words        → Driver in exact 3m × 3m door square (if configured)
Signal 3: LLM Address Match → GPT-4o-mini semantic match of GPS address vs stored address
```

GPS geofence alone (with stored coordinates) is sufficient to confirm location. W3W provides 3-metre precision when configured. LLM handles address variations — abbreviations, local landmark names, alternate spellings.

### Door Confirmed — AI Vision Rules

Gemini Flash (primary) and GPT-4o (fallback) analyse the proof image. The check passes **only** if a door panel, door frame, door handle, or doorbell is clearly visible AND a package is present.

A wall, gate, fence, garage, or building exterior without a visible door always **fails** — regardless of GPS.

For video, 3 frames are extracted at 25%, 50%, and 75% of the clip. The best result across all 3 frames is used, maximising the chance of catching the door in frame.

---

## Tamper-Evident Proof Chain

Every verified delivery generates a **SHA-256 proof hash** computed from:

```
hash = SHA256(proof_file + GPS_lat + GPS_lng + timestamp + tracking_id)
```

This hash is stored in the database and displayed to the driver. Any modification to the file, coordinates, or timestamp after submission produces a different hash — making tampering detectable.

---

## Technical Architecture

```
┌─────────────────────────────┐     HTTPS      ┌──────────────────────────────┐
│   Driver App (PWA)          │ ─────────────► │   Verification API           │
│   Any smartphone browser    │                │   FastAPI on Render           │
│   No install required       │                │                              │
└─────────────────────────────┘                │  ┌─────────────────────────┐ │
                                               │  │ Gemini Flash (vision)   │ │
┌─────────────────────────────┐                │  │ GPT-4o (fallback)       │ │
│   Admin / Dispatch Portal   │ ─────────────► │  │ GPT-4o-mini (address)   │ │
│   Add parcels, monitor      │                │  └─────────────────────────┘ │
│   deliveries, reset status  │                │                              │
└─────────────────────────────┘                │  ┌─────────────────────────┐ │
                                               │  │ Supabase (PostgreSQL)   │ │
                                               │  │ Delivery records        │ │
                                               │  │ Proof file storage      │ │
                                               │  └─────────────────────────┘ │
                                               └──────────────────────────────┘
```

### Stack

| Layer | Technology |
|---|---|
| Driver App | Vanilla JS PWA — works on any phone browser, no install |
| Admin Portal | Vanilla JS static site |
| API | Python FastAPI, deployed on Render |
| Database | Supabase (PostgreSQL) |
| Proof Storage | Supabase Storage |
| Primary AI | Google Gemini Flash (vision + address) |
| Fallback AI | OpenAI GPT-4o (vision), GPT-4o-mini (text) |
| GPS | Browser Geolocation API + Kalman filter |
| Barcode | ZXing multi-format scanner |

### Deployment

- **Zero hardware cost** — runs on driver's existing smartphone
- **No app store** — opens in browser, installs as PWA with one tap
- **Fully cloud-hosted** — API and both portals on Render free tier
- **Offline-resilient** — service worker caches app shell for unreliable connectivity

---

## Admin / Dispatch Portal

Dispatch teams manage deliveries through a dedicated portal:

- Add new deliveries with customer name, address, driver ID
- **GPS auto-fill** — one tap captures exact front door coordinates and what3words address
- Live delivery dashboard — status, verified flag, GPS indicator, proof file link
- Reset any delivery to pending for re-attempt
- Search and filter by status, driver, or tracking ID

---

## Prototype Status

| Feature | Status |
|---|---|
| Barcode scan (camera + manual) | ✅ Complete |
| GPS lock with Kalman filter | ✅ Complete |
| Geotagged photo (EXIF) | ✅ Complete |
| Geotagged video (3-frame AI) | ✅ Complete |
| AI door + package detection | ✅ Complete |
| 3-signal location verification | ✅ Complete |
| LLM address matching | ✅ Complete |
| Local language address support | ✅ Complete |
| SHA-256 tamper-evident hash | ✅ Complete |
| Admin / dispatch portal | ✅ Complete |
| Cloud deployment (Render) | ✅ Complete |
| What3Words integration | ✅ Complete |

---

## Integration Path

DoorStep is designed as a **drop-in enhancement** to an existing POD workflow:

1. Dispatch adds deliveries via the admin portal (or API integration)
2. Driver opens the web app — no install, no training beyond a 2-minute walkthrough
3. Verification results are stored in the database and accessible via API
4. Existing logistics platform queries the API for `verified: true/false` and the proof hash

The API is fully documented and accepts standard JSON — integration with any existing system requires only a few API calls.

---

## Live Demo

**Driver App:** `https://doorstep-driver.onrender.com`
**Admin Portal:** `https://doorstep-admin.onrender.com`

*Note: First load after inactivity may take 20–30 seconds on the free tier as the API wakes up.*

---

*Prototype built with open-source stack. Production deployment would include SLA-backed hosting, dedicated AI API quotas, and integration with existing driver mobile infrastructure.*
