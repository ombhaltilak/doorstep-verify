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

## End-to-End Delivery Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DRIVER SMARTPHONE (PWA)                          │
│                                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│  │  Sign In │──▶│  Select  │──▶│  Barcode │──▶│  GPS     │             │
│  │          │   │Delivery  │   │  Scan    │   │  Lock    │             │
│  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘             │
│                                                     │                   │
│                                               ┌─────▼──────┐           │
│                                               │  Capture   │           │
│                                               │  Photo or  │           │
│                                               │  Video     │           │
│                                               └─────┬──────┘           │
└─────────────────────────────────────────────────────┼────────────────────┘
                                                      │ HTTPS upload
                                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        VERIFICATION API  (FastAPI)                       │
│                                                                          │
│   Proof file received → 5 checks run in sequence                        │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  CHECK 1 — Package ID                                           │   │
│   │  Scanned barcode  ==  assigned tracking ID ?   ──▶  PASS / FAIL │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  CHECK 2 — Location Stamp                                       │   │
│   │  GPS in file EXIF  ==  GPS submitted by app ?  ──▶  PASS / SKIP │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  CHECK 3 — Delivery Location  (3-signal)                        │   │
│   │  ① GPS Geofence   — within 50 m of stored door coords          │   │
│   │  ② What3Words     — exact 3 m × 3 m door square (if set)       │   │
│   │  ③ LLM Address    — GPT-4o-mini semantic match                  │   │
│   │                                             ──▶  PASS / FAIL    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  CHECK 4 — Door Confirmed  (AI Vision)                          │   │
│   │  Gemini Flash / GPT-4o                                          │   │
│   │  Door panel + frame + package visible in proof?  ──▶ PASS / FAIL│   │
│   └─────────────────────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  CHECK 5 — Address Match  (Informational)                       │   │
│   │  AI reads nameplate / house number vs stored address            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   All checks pass ──▶ SHA-256 proof hash generated ──▶ verified: true   │
└──────────────────────────────────────────────────────────────────────────┘
                         │                        │
                         ▼                        ▼
              ┌─────────────────┐      ┌─────────────────────┐
              │   Supabase DB   │      │  Supabase Storage   │
              │  Delivery record│      │  Proof file + hash  │
              │  verified flag  │      │  (permanent record) │
              └────────┬────────┘      └─────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Admin Portal   │
              │  Dispatch team  │
              │  monitors live  │
              └─────────────────┘
```

---

## How It Works — Driver Steps

**Step 1 — Sign In & Select Delivery**
Driver logs in with their ID. Only deliveries assigned to that driver are visible.

**Step 2 — Barcode Scan**
Driver scans the package barcode with the phone camera. The system blocks progress if the barcode does not match the assigned delivery — wrong package cannot proceed.

**Step 3 — GPS Lock**
GPS is acquired using a Kalman filter for noise reduction. Accuracy is displayed in real time. The driver cannot proceed until signal quality is acceptable.

**Step 4 — Proof Capture**
Driver chooses Photo or Video. Both modes permanently embed GPS coordinates:
- **Photo** — GPS injected into JPEG EXIF metadata (tamper-evident, industry standard)
- **Video** — GPS injected into a canvas reference frame via EXIF; 3 frames extracted for AI analysis

**Step 5 — AI Verification**
The proof file is uploaded and all 5 checks run automatically. Result displayed within seconds.

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
                    ┌───────────────────────────────┐
                    │   3-Signal Location Check      │
                    └───────────────┬───────────────┘
                                    │
          ┌─────────────────────────┼──────────────────────────┐
          ▼                         ▼                          ▼
  ┌───────────────┐        ┌────────────────┐        ┌──────────────────┐
  │  GPS Geofence │        │  What3Words    │        │  LLM Address     │
  │               │        │                │        │  Match           │
  │  Driver within│        │  Driver in     │        │  GPT-4o-mini     │
  │  50m of stored│        │  exact 3m×3m   │        │  semantic check  │
  │  door coords  │        │  door square   │        │  of GPS address  │
  │               │        │  (if set up)   │        │  vs stored addr  │
  └───────┬───────┘        └───────┬────────┘        └────────┬─────────┘
          │                        │                           │
          └────────────────────────┼───────────────────────────┘
                                   ▼
                          ┌────────────────┐
                          │  LOCATION PASS │
                          │  (1 of 3 min)  │
                          └────────────────┘
```

GPS geofence alone is sufficient to confirm location. What3Words provides 3-metre precision when configured per delivery. LLM handles address variations — abbreviations, local landmark names, alternate spellings.

### Door Confirmed — AI Vision Logic

```
  Proof image / video frames
           │
           ▼
  ┌─────────────────────────────────────────────────────┐
  │              Gemini Flash  (primary)                │
  │                                                     │
  │  Is there a door panel / frame / handle / doorbell  │
  │  clearly visible in the image?          ──▶  YES/NO │
  │                                                     │
  │  Is a package present in the image?     ──▶  YES/NO │
  └────────────────────┬────────────────────────────────┘
                       │  if Gemini unavailable
                       ▼
  ┌─────────────────────────────────────────────────────┐
  │              GPT-4o  (fallback)                     │
  │  Same door + package checks                         │
  └─────────────────────────────────────────────────────┘
           │
           ▼
  Both door AND package visible ──▶  PASS
  Gate / fence / wall / garage    ──▶  FAIL  (even if GPS is correct)
  Package missing from frame      ──▶  FAIL
```

For video: 3 frames extracted at 25%, 50%, and 75% of the clip. Best result across all frames is used — maximising the chance of catching door and package in frame.

---

## Tamper-Evident Proof Chain

```
  ┌────────────┐  ┌─────────┐  ┌───────────┐  ┌─────────────┐
  │ Proof file │  │ GPS lat │  │ GPS long  │  │  Timestamp  │
  │ (photo/vid)│  │         │  │           │  │             │
  └──────┬─────┘  └────┬────┘  └─────┬─────┘  └──────┬──────┘
         │             │             │                │
         └─────────────┴──────┬──────┴────────────────┘
                              │  +  tracking_id
                              ▼
                     ┌─────────────────┐
                     │  SHA-256 hash   │
                     │  (stored in DB) │
                     └────────┬────────┘
                              │
                    Any field modified?
                              │
                    Different hash ──▶ Tamper detected
```

Any modification to the file, coordinates, or timestamp after submission produces a different hash — making post-submission tampering immediately detectable.

---

## System Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                   │
│                                                                           │
│  ┌──────────────────────────┐      ┌──────────────────────────────────┐  │
│  │   Driver App  (PWA)      │      │   Admin / Dispatch Portal        │  │
│  │   Any smartphone browser │      │   Static web app                 │  │
│  │   No install required    │      │   Add deliveries, monitor status │  │
│  │   Offline-resilient      │      │   GPS auto-fill for door coords  │  │
│  └────────────┬─────────────┘      └─────────────────┬────────────────┘  │
└───────────────┼─────────────────────────────────────┼────────────────────┘
                │  HTTPS                               │  HTTPS
                ▼                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           API LAYER  (Render)                             │
│                                                                           │
│                    FastAPI — Python 3.11                                  │
│                                                                           │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│   │  Barcode Check   │    │  Location Check  │    │  AI Vision       │  │
│   │  Exact match     │    │  GPS + W3W + LLM │    │  Door + Package  │  │
│   └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                           │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    AI Services                                   │   │
│   │   Google Gemini Flash  ──  Vision (primary)                      │   │
│   │   OpenAI GPT-4o        ──  Vision (fallback)                     │   │
│   │   OpenAI GPT-4o-mini   ──  Address text matching                 │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER  (Supabase)                            │
│                                                                           │
│   ┌─────────────────────────┐      ┌──────────────────────────────┐     │
│   │  PostgreSQL             │      │  Object Storage              │     │
│   │  Delivery records       │      │  Proof files (photo / video) │     │
│   │  Verification results   │      │  Permanent, timestamped      │     │
│   │  SHA-256 proof hashes   │      │  Publicly accessible via URL │     │
│   └─────────────────────────┘      └──────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────────┘
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
| Location Precision | What3Words (3 m × 3 m) |

### Deployment

- **Zero hardware cost** — runs on driver's existing smartphone
- **No app store** — opens in browser, installs as PWA with one tap
- **Fully cloud-hosted** — API and both portals on Render
- **Offline-resilient** — service worker caches app shell for unreliable connectivity

---

## Admin / Dispatch Portal

Dispatch teams manage deliveries through a dedicated web portal:

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                  Admin / Dispatch Portal                         │
  │                                                                  │
  │  Add Delivery                                                    │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
  │  │ Tracking ID  │  │ Customer     │  │ Delivery Address     │  │
  │  │ PKGXXXXXXXX  │  │ Name         │  │ + GPS auto-fill  📍  │  │
  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │
  │                                                                  │
  │  Live Dashboard                                                  │
  │  ┌──────────────────────────────────────────────────────────┐  │
  │  │ ID         │ Customer  │ Status    │ Verified │ Proof    │  │
  │  │ PKG001     │ J. Carter │ delivered │   ✅     │  📎 link │  │
  │  │ PKG002     │ S. Holmes │ pending   │    —     │    —     │  │
  │  │ PKG003     │ R. Hayes  │ delivered │   ❌     │  📎 link │  │
  │  └──────────────────────────────────────────────────────────┘  │
  │                                                                  │
  │  Actions: Reset to Pending · Search · Filter by status/driver   │
  └──────────────────────────────────────────────────────────────────┘
```

- Add new deliveries with customer name, address, driver ID
- **GPS auto-fill** — one tap captures exact front door coordinates and What3Words address
- Live delivery dashboard — status, verified flag, GPS indicator, proof file link
- Reset any delivery to pending for re-attempt
- Search and filter by status, driver, or tracking ID

---

## Prototype Status

| Feature | Status |
|---|---|
| Barcode scan (camera + manual) | Complete |
| GPS lock with Kalman filter | Complete |
| Geotagged photo (EXIF) | Complete |
| Geotagged video (3-frame AI) | Complete |
| AI door + package detection | Complete |
| 3-signal location verification | Complete |
| LLM address matching | Complete |
| Local language address support | Complete |
| SHA-256 tamper-evident hash | Complete |
| Admin / dispatch portal | Complete |
| Cloud deployment | Complete |
| What3Words integration | Complete |

---

## Integration Path

DoorStep is designed as a **drop-in enhancement** to an existing POD workflow:

```
  Existing Logistics Platform
           │
           │  1. Dispatch adds delivery via Admin Portal
           │     (or direct API call — standard JSON)
           ▼
  ┌─────────────────────┐
  │  DoorStep Database  │
  │  Delivery record    │
  │  status: pending    │
  └──────────┬──────────┘
             │
             │  2. Driver opens web app on phone
             │     No install, no training beyond 2-min walkthrough
             ▼
  ┌─────────────────────┐
  │  Driver completes   │
  │  verified delivery  │
  │  verified: true     │
  │  proof hash stored  │
  └──────────┬──────────┘
             │
             │  3. Existing platform queries API
             │     GET /delivery/{tracking_id}
             │     → verified: true/false + proof_hash + file_url
             ▼
  Existing platform marks delivery complete with verified POD
```

The API accepts standard JSON and returns structured results. Integration with any existing system requires only a few API calls with no dependency on DoorStep's front-end.

---

## Live Demo

**Driver App:** `https://doorstep-driver.onrender.com`
**Admin Portal:** `https://doorstep-admin.onrender.com`

*Note: First load after inactivity may take 30-60 seconds on the free tier as the API wakes up.*

---

*Prototype built with open-source stack. Production deployment would include SLA-backed hosting, dedicated AI API quotas, and integration with existing driver mobile infrastructure.*
