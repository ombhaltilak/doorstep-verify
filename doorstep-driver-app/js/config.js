// ── Config ──────────────────────────────────────────────────────────────────
// Production: https://doorstep-verify-api.onrender.com
// Local dev:  http://<your-local-ip>:8000
const API_URL = 'https://doorstep-verify-api.onrender.com';
const W3W_KEY = 'SGU2U9NM';

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  driverId:      null,
  trackingId:    null,
  scannedBarcode:null,
  gps:           null,   // { lat, lng, accuracy, timestamp, w3w_words? }
  mediaType:     null,   // 'photo' or 'video'
  photoBase64:   null,
  videoBlob:     null,
  photoStream:   null,
  videoStream:   null,
};

let barcodeReader    = null;
let mediaRecorder    = null;
let recordedChunks   = [];
let recTimerInterval = null;
let gpsWatcher       = null;
let canvasAnimFrame  = null;
// kf is declared here and assigned in gps.js after GPSKalmanFilter is defined
let kf = null;
