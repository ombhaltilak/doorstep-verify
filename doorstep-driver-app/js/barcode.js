// ── Barcode Scan ──────────────────────────────────────────────────────────────
function startDelivery(trackingId) {
  // New delivery — full reset
  state.trackingId     = trackingId;
  state.scannedBarcode = null;
  state.photoBase64    = null;
  state.videoBlob      = null;
  state.gps            = null;

  const resEl = document.getElementById('barcode-result');
  resEl.style.display    = 'none';
  resEl.textContent      = '';
  resEl.style.background = '';
  resEl.style.color      = '';
  document.getElementById('manual-barcode').value = '';

  showScreen('screen-barcode');
  startBarcodeScanner();
}

function startBarcodeScanner() {
  // Restart scanner only — does NOT clear DOM (used for back navigation too)
  if (barcodeReader) barcodeReader.reset();

  barcodeReader = new ZXing.BrowserMultiFormatReader();
  barcodeReader.decodeFromConstraints(
    { video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } } },
    document.getElementById('barcode-video'),
    (result, err) => {
      if (result) {
        const scanned = result.getText().split('|')[0].trim().toUpperCase();
        const resEl   = document.getElementById('barcode-result');

        if (scanned !== state.trackingId.toUpperCase()) {
          resEl.textContent   = `❌ Incorrect barcode — please scan the package for this delivery`;
          resEl.style.display = 'block';
          resEl.style.background = 'var(--red-bg)';
          resEl.style.color      = 'var(--red)';
          barcodeReader.reset();
          setTimeout(() => startBarcodeScanner(), 2000);
          return;
        }

        state.scannedBarcode = scanned;
        barcodeReader.reset();
        resEl.textContent   = '✅ Package verified: ' + scanned;
        resEl.style.display = 'block';
        resEl.style.background = '';
        resEl.style.color      = '';

        setTimeout(() => {
          showScreen('screen-gps');
          startGPSWatch();
        }, 1200);
      }
    }
  );
}

let torchOn = false;
async function toggleTorch() {
  try {
    const video = document.getElementById('barcode-video');
    const track = video.srcObject && video.srcObject.getVideoTracks()[0];
    if (!track) return;
    torchOn = !torchOn;
    await track.applyConstraints({ advanced: [{ torch: torchOn }] });
    document.getElementById('torch-btn').textContent = torchOn ? '🔦 Torch ON' : '🔦 Torch OFF';
  } catch(e) {
    alert('Torch not supported on this device');
  }
}

function useManualBarcode() {
  const val    = document.getElementById('manual-barcode').value.trim().toUpperCase();
  const resEl  = document.getElementById('barcode-result');
  if (!val) { alert('Please enter the tracking number to continue.'); return; }

  if (val !== state.trackingId.toUpperCase()) {
    resEl.textContent   = `❌ Incorrect tracking number — please check and try again`;
    resEl.style.display = 'block';
    resEl.style.background = 'var(--red-bg)';
    resEl.style.color      = 'var(--red)';
    return;
  }

  state.scannedBarcode   = val;
  resEl.style.background = '';
  resEl.style.color      = '';
  if (barcodeReader) barcodeReader.reset();
  showScreen('screen-gps');
  startGPSWatch();
}
