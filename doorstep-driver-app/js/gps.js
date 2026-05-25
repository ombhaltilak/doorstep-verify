// ── Kalman Filter ─────────────────────────────────────────────────────────────
function GPSKalmanFilter() {
  this.lat = null; this.lng = null; this.variance = -1; this.Q = 3; this.lastTs = null;
  this.update = function(lat, lng, accuracy, ts) {
    if (this.variance < 0) {
      this.lat = lat; this.lng = lng;
      this.variance = accuracy * accuracy;
      this.lastTs = ts;
      return { lat, lng, accuracy };
    }
    const dt = (ts - this.lastTs) / 1000;
    this.lastTs = ts;
    this.variance += dt * this.Q * this.Q;
    const K = this.variance / (this.variance + accuracy * accuracy);
    this.lat     += K * (lat - this.lat);
    this.lng     += K * (lng - this.lng);
    this.variance = (1 - K) * this.variance;
    return { lat: this.lat, lng: this.lng, accuracy: Math.sqrt(this.variance) };
  };
}

// Assign to the global kf declared in config.js
kf = new GPSKalmanFilter();

// ── GPS Watch ─────────────────────────────────────────────────────────────────
function startGPSWatch() {
  const statusEl   = document.getElementById('gps-status');
  const fillEl     = document.getElementById('gps-accuracy-fill');
  const labelEl    = document.getElementById('gps-accuracy-label');
  const coordsEl   = document.getElementById('gps-coords');
  const proceedBtn = document.getElementById('btn-to-capture');
  const iconEl     = document.getElementById('gps-icon');

  // Reset GPS screen DOM to fresh state
  statusEl.textContent          = 'Acquiring location — hold the phone steady...';
  fillEl.style.width            = '0%';
  fillEl.style.background       = '#C03020';
  labelEl.textContent           = 'Signal strength: acquiring...';
  coordsEl.textContent          = '';
  iconEl.textContent            = '📡';
  proceedBtn.disabled           = true;
  document.getElementById('gps-w3w').style.display = 'none';
  document.getElementById('w3w-words').textContent = '';

  let sampleCount = 0;
  let bestAccuracy = Infinity;

  gpsWatcher = navigator.geolocation.watchPosition(
    (pos) => {
      sampleCount++;
      const filtered = kf.update(
        pos.coords.latitude,
        pos.coords.longitude,
        pos.coords.accuracy,
        pos.timestamp
      );
      const acc = filtered.accuracy;

      // Always keep the best (most accurate) reading seen
      if (acc < bestAccuracy) {
        bestAccuracy = acc;
        state.gps = {
          lat:       filtered.lat,
          lng:       filtered.lng,
          accuracy:  acc,
          timestamp: new Date().toISOString(),
        };
        coordsEl.textContent = `${filtered.lat.toFixed(6)}, ${filtered.lng.toFixed(6)}`;
      }

      const display = bestAccuracy;
      const quality = Math.max(5, Math.min(100, 100 - display));
      fillEl.style.width = quality + '%';

      const sampleNote = sampleCount < 5 ? ` (${sampleCount} samples…)` : '';

      if (display <= 8) {
        fillEl.style.background = '#10A050';
        labelEl.textContent = `Excellent ±${display.toFixed(0)}m${sampleNote}`;
        iconEl.textContent  = '📍';
        statusEl.textContent = 'Location locked — excellent accuracy ✓';
        proceedBtn.disabled = false;
      } else if (display <= 15) {
        fillEl.style.background = '#50C030';
        labelEl.textContent = `Strong ±${display.toFixed(0)}m${sampleNote}`;
        iconEl.textContent  = '📍';
        statusEl.textContent = 'Location locked — strong accuracy ✓';
        proceedBtn.disabled = false;
      } else if (display <= 25) {
        fillEl.style.background = '#80C000';
        labelEl.textContent = `Good ±${display.toFixed(0)}m${sampleNote}`;
        iconEl.textContent  = '📍';
        statusEl.textContent = sampleCount < 6
          ? 'Refining accuracy — stay still for a moment...'
          : 'Location ready — good enough to proceed ✓';
        proceedBtn.disabled = false;
      } else if (display <= 40) {
        fillEl.style.background = '#F0A000';
        labelEl.textContent = `Moderate ±${display.toFixed(0)}m${sampleNote}`;
        statusEl.textContent = 'Moderate accuracy — stand in an open area and hold still...';
        proceedBtn.disabled = false;
      } else {
        fillEl.style.background = '#C03020';
        labelEl.textContent = `Weak ±${display.toFixed(0)}m — acquiring${sampleNote}`;
        statusEl.textContent = 'Low accuracy — step into open sky area, away from tall buildings...';
        iconEl.textContent  = '📡';
        proceedBtn.disabled = true;
      }
    },
    (err) => {
      statusEl.textContent = 'Location unavailable — check GPS is enabled in device settings';
    },
    { enableHighAccuracy: true, maximumAge: 3000, timeout: 30000 }
  );
}

function gpsGoBack() {
  if (gpsWatcher) {
    navigator.geolocation.clearWatch(gpsWatcher);
    gpsWatcher = null;
  }
  showScreen('screen-barcode');
  startBarcodeScanner();   // restart scanner, keep previous barcode state
}

function chooseGoBack() {
  // Go back to GPS screen and resume watching
  showScreen('screen-gps');
  startGPSWatch();
}

async function goToCapture() {
  navigator.geolocation.clearWatch(gpsWatcher);
  gpsWatcher = null;

  // Try to get what3words address (optional — skip if no key)
  if (W3W_KEY && W3W_KEY !== 'YOUR_W3W_KEY' && state.gps) {
    try {
      const r = await fetch(
        `https://api.what3words.com/v3/convert-to-3wa` +
        `?coordinates=${state.gps.lat},${state.gps.lng}&language=en&key=${W3W_KEY}`
      );
      const d = await r.json();
      console.log('W3W response:', d);
      if (d.words) {
        state.gps.w3w_words = d.words;
        document.getElementById('w3w-words').textContent = d.words;
        document.getElementById('gps-w3w').style.display = 'flex';
      }
    } catch (e) {
      console.error('W3W fetch failed:', e);
    }
  }

  showScreen('screen-choose');
}
