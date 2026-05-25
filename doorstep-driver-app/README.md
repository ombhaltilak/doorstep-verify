# Doorstep Verify — Driver PWA

Progressive Web App for delivery drivers. Runs in any phone browser — no app install needed.

## Stack
- **Hosting**: Vercel (free)
- **Barcode scan**: ZXing.js (live camera stream, auto-detects)
- **GPS EXIF injection**: piexifjs (bakes GPS into JPEG metadata)
- **Geotagged video**: Canvas + MediaRecorder (GPS burned into every frame)

## Setup

### 1. Update API URL
Open `app.js` and replace line 3:
```js
const API_URL = 'https://YOUR_RENDER_URL.onrender.com';
```
With your actual Render.com backend URL.

### 2. what3words (optional)
Get a free key at developer.what3words.com and replace line 4:
```js
const W3W_KEY = 'YOUR_W3W_KEY';
```

### 3. Icons
Add `icons/icon-192.png` and `icons/icon-512.png` (any PNG images).
You can generate them at realfavicongenerator.net.

### 4. Deploy to Vercel
- Push this folder to GitHub
- Import repo on vercel.com → Deploy
- Open HTTPS URL on phone

## Driver Flow
1. Login with Driver ID
2. Tap a delivery from list
3. Scan package barcode (or type manually)
4. Wait for GPS lock (need < 30m accuracy)
5. Choose: Geotagged Photo or Video
6. Capture proof (door + package in frame)
7. Submit → AI verification runs → result shown
