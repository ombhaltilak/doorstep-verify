// ── Utility ──────────────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function stopStream(stream) {
  if (stream) stream.getTracks().forEach(t => t.stop());
}

function setUploadStep(text) {
  const el = document.getElementById('upload-steps');
  if (el) el.textContent = text;
}

// ── Login ────────────────────────────────────────────────────────────────────
function login() {
  const id = document.getElementById('driver-id').value.trim().toLowerCase();
  if (!id) { alert('Please enter your Driver ID to continue.'); return; }
  state.driverId = id;
  document.getElementById('topbar-driver').textContent = id;
  loadDeliveries();
  showScreen('screen-list');
}

async function loadDeliveries() {
  const listEl = document.getElementById('delivery-list');
  listEl.innerHTML = '<div class="loading">Loading your deliveries...</div>';
  try {
    const res  = await fetch(`${API_URL}/verify?action=list&driverId=${state.driverId}`);
    const list = await res.json();
    if (!list.length) {
      listEl.innerHTML = '<div class="loading">No deliveries assigned.</div>';
      return;
    }
    listEl.innerHTML = list.map(d => `
      <div class="delivery-card" onclick="startDelivery('${d.tracking_id}')">
        <div class="track">${d.tracking_id}</div>
        <div class="cust">${d.customer_name || ''}</div>
        <div class="addr">${d.address || ''}</div>
      </div>
    `).join('');
  } catch (e) {
    listEl.innerHTML = `<div class="loading">Unable to load deliveries. Please check your connection.</div>`;
  }
}

// ── Result screen ─────────────────────────────────────────────────────────────
function showResult(result) {
  showScreen('screen-result');

  const icon  = document.getElementById('result-icon');
  const title = document.getElementById('result-title');
  const checksEl = document.getElementById('result-checks');
  const hashEl   = document.getElementById('result-hash');

  if (result.error && !result.checks) {
    icon.textContent  = '❌';
    title.textContent = 'Submission Failed';
    checksEl.innerHTML = `<div class="check-row fail">
      <span class="check-badge">ERR</span>
      <div><div class="check-label">Connection Error</div>
      <div class="check-detail">${result.error}</div></div></div>`;
    hashEl.textContent = '';
    return;
  }

  icon.textContent  = result.verified ? '✅' : '❌';
  title.textContent = result.verified ? 'Delivery Confirmed' : 'Verification Failed';
  title.style.color = result.verified ? 'var(--green)' : 'var(--red)';

  const checks = result.checks || {};
  const rows = [
    { key: 'barcode_match', label: 'Package ID' },
    { key: 'geotag_verify', label: 'Location Stamp' },
    { key: 'location',      label: 'Delivery Location' },
    { key: 'front_door',    label: 'Door Confirmed' },
  ];

  checksEl.innerHTML = rows.map(({ key, label }) => {
    const chk = checks[key];
    if (!chk) return '';
    const pass   = chk.pass;
    const detail = chk.detail || '';
    const rowClass   = pass === true ? 'pass' : pass === false ? 'fail' : 'skip';
    const badgeText  = pass === true ? 'PASS' : pass === false ? 'FAIL' : 'SKIP';
    return `
      <div class="check-row ${rowClass}">
        <span class="check-badge">${badgeText}</span>
        <div>
          <div class="check-label">${label}</div>
          <div class="check-detail">${detail}</div>
        </div>
      </div>`;
  }).join('');

  // Location sub-signals
  if (checks.location && checks.location.gps) {
    const loc = checks.location;
    const subs = [
      { label: 'GPS Range',      s: loc.gps },
      { label: 'Precise Address', s: loc.w3w },
      { label: 'Address Match',   s: loc.ocr_loc },
    ].filter(x => x.s && x.s.pass !== undefined);

    if (subs.length) {
      checksEl.innerHTML += subs.map(({ label, s }) => `
        <div class="check-row ${s.pass === true ? 'pass' : s.pass === null ? '' : 'fail'}"
             style="margin-left:20px; border-radius:8px;">
          <span class="check-badge">${s.pass === true ? 'PASS' : s.pass === null ? 'SKIP' : 'FAIL'}</span>
          <div>
            <div class="check-label" style="font-size:12px">${label}</div>
            <div class="check-detail">${s.detail || ''}</div>
          </div>
        </div>`).join('');
    }
  }

  if (result.proof_hash) {
    hashEl.textContent = `Tamper-Proof Hash: ${result.proof_hash}`;
  } else {
    hashEl.textContent = '';
  }
}

function nextDelivery() {
  // Full state reset
  state.trackingId     = null;
  state.scannedBarcode = null;
  state.photoBase64    = null;
  state.videoBlob      = null;
  state.videoFrameB64  = null;
  state.gps            = null;
  state.mediaType      = null;

  // Stop any active streams
  stopStream(state.photoStream);
  stopStream(state.videoStream);
  state.photoStream = null;
  state.videoStream = null;

  // Stop GPS watcher if still running
  if (gpsWatcher) {
    navigator.geolocation.clearWatch(gpsWatcher);
    gpsWatcher = null;
  }

  // Reset result screen for next use
  document.getElementById('result-icon').textContent  = '';
  document.getElementById('result-title').textContent = '';
  document.getElementById('result-checks').innerHTML  = '';
  document.getElementById('result-hash').textContent  = '';

  showScreen('screen-list');
  loadDeliveries();
}

// ── Service Worker (offline support) ─────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('service-worker.js').catch(() => {});
}
