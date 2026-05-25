// ══════════════════════════════════════════════════════════════════════════════
// APPROACH B — GEOTAGGED VIDEO
// ══════════════════════════════════════════════════════════════════════════════

async function startVideoMode() {
  state.mediaType = 'video';
  showScreen('screen-video');

  // Reset video screen DOM
  document.getElementById('rec-timer').style.display  = 'none';
  document.getElementById('rec-timer').textContent    = '⏺ Recording: 0s';
  document.getElementById('btn-record').style.display = 'block';
  document.getElementById('btn-stop').style.display   = 'none';
  document.getElementById('video-gps-status').textContent = 'GPS: loading...';

  state.videoStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
    audio: false,
  });

  const videoSrc = document.getElementById('video-source');
  const canvas   = document.getElementById('video-canvas');
  const ctx      = canvas.getContext('2d');
  canvas.width   = 854;
  canvas.height  = 480;
  videoSrc.srcObject = state.videoStream;

  // Refresh GPS every 4 seconds
  let liveGPS = state.gps;
  const gpsRefreshId = setInterval(() => {
    navigator.geolocation.getCurrentPosition(
      pos => {
        const f = kf.update(
          pos.coords.latitude, pos.coords.longitude,
          pos.coords.accuracy, pos.timestamp
        );
        liveGPS = { lat: f.lat, lng: f.lng, accuracy: f.accuracy,
                    timestamp: new Date().toISOString() };
        state.gps = liveGPS;
        document.getElementById('video-gps-status').textContent =
          `GPS: ${f.lat.toFixed(6)}, ${f.lng.toFixed(6)}  ±${f.accuracy.toFixed(0)}m`;
      },
      null,
      { enableHighAccuracy: true }
    );
  }, 4000);

  // Draw camera frame + GPS overlay at 15fps (enough for video, saves CPU on mobile)
  const FRAME_MS = 1000 / 15;
  let lastDrawTs = 0;
  function drawFrame(ts) {
    canvasAnimFrame = requestAnimationFrame(drawFrame);
    if (ts - lastDrawTs < FRAME_MS) return;
    lastDrawTs = ts;

    ctx.drawImage(videoSrc, 0, 0, canvas.width, canvas.height);

    if (liveGPS) {
      const now = new Date().toISOString();
      ctx.fillStyle = 'rgba(0, 0, 0, 0.80)';
      ctx.fillRect(0, canvas.height - 80, canvas.width, 80);
      ctx.fillStyle = '#00FF00';
      ctx.font      = 'bold 22px monospace';
      ctx.fillText(
        `LAT:${liveGPS.lat.toFixed(6)} LNG:${liveGPS.lng.toFixed(6)} ACC:${liveGPS.accuracy.toFixed(0)}m`,
        10, canvas.height - 48
      );
      ctx.fillStyle = '#FFFFFF';
      ctx.font      = 'bold 17px monospace';
      ctx.fillText(
        `ORDER:${state.trackingId} DRV:${state.driverId} ${now}`,
        10, canvas.height - 16
      );
    }
  }
  requestAnimationFrame(drawFrame);

  // Store cleanup ref
  canvas._gpsRefreshId = gpsRefreshId;
}

function startRecording() {
  recordedChunks = [];
  const canvas       = document.getElementById('video-canvas');
  const canvasStream = canvas.captureStream(30);

  const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
    ? 'video/webm;codecs=vp9'
    : 'video/webm';

  mediaRecorder = new MediaRecorder(canvasStream, {
    mimeType,
    videoBitsPerSecond: 3000000,
  });

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    cancelAnimationFrame(canvasAnimFrame);
    clearInterval(document.getElementById('video-canvas')._gpsRefreshId);
    state.videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
    submitVideo();
  };

  mediaRecorder.start(200);

  document.getElementById('btn-record').style.display    = 'none';
  document.getElementById('btn-stop').style.display      = 'block';
  document.getElementById('rec-timer').style.display     = 'block';
  document.getElementById('btn-video-back').style.display = 'none';

  let secs = 0;
  recTimerInterval = setInterval(() => {
    secs++;
    document.getElementById('rec-timer').textContent = `⏺ Recording: ${secs}s`;
    if (secs >= 30) stopRecording();  // max 30 seconds
  }, 1000);
}

function stopRecording() {
  clearInterval(recTimerInterval);

  // Capture canvas JPEG and inject GPS as EXIF — same mechanism as photo mode.
  // This avoids OCR entirely: backend reads binary EXIF, not text from a compressed frame.
  const canvas     = document.getElementById('video-canvas');
  const jpegDataUrl = canvas.toDataURL('image/jpeg', 0.92);

  if (state.gps) {
    try {
      const exifObj = {
        GPS: {
          [piexif.GPSIFD.GPSLatitudeRef]:  state.gps.lat >= 0 ? 'N' : 'S',
          [piexif.GPSIFD.GPSLatitude]:     piexif.GPSHelper.degToDmsRational(Math.abs(state.gps.lat)),
          [piexif.GPSIFD.GPSLongitudeRef]: state.gps.lng >= 0 ? 'E' : 'W',
          [piexif.GPSIFD.GPSLongitude]:    piexif.GPSHelper.degToDmsRational(Math.abs(state.gps.lng)),
          [piexif.GPSIFD.GPSDateStamp]:    state.gps.timestamp ? state.gps.timestamp.split('T')[0] : '',
        }
      };
      const exifBytes = piexif.dump(exifObj);
      state.videoFrameB64 = piexif.insert(exifBytes, jpegDataUrl).split(',')[1];
    } catch (_) {
      state.videoFrameB64 = jpegDataUrl.split(',')[1];
    }
  } else {
    state.videoFrameB64 = jpegDataUrl.split(',')[1];
  }

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  stopStream(state.videoStream);
  showScreen('screen-uploading');
}

function videoGoBack() {
  // Stop recording if active
  clearInterval(recTimerInterval);
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  cancelAnimationFrame(canvasAnimFrame);
  const canvas = document.getElementById('video-canvas');
  if (canvas._gpsRefreshId) {
    clearInterval(canvas._gpsRefreshId);
    canvas._gpsRefreshId = null;
  }
  stopStream(state.videoStream);
  state.videoStream = null;
  state.videoBlob   = null;
  recordedChunks    = [];
  // Reset video screen UI
  document.getElementById('rec-timer').style.display  = 'none';
  document.getElementById('btn-record').style.display = 'block';
  document.getElementById('btn-stop').style.display   = 'none';
  showScreen('screen-choose');
}

async function submitVideo() {
  setUploadStep('Encoding video...');
  const reader = new FileReader();
  reader.onload = async (e) => {
    setUploadStep('Uploading geotagged video...');
    try {
      const res = await fetch(`${API_URL}/verify`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          tracking_id:  state.trackingId,
          barcode:      state.scannedBarcode,
          gps:          state.gps,
          driver_id:    state.driverId,
          media_type:   'video',
          file_base64:  e.target.result.split(',')[1],
          frame_base64: state.videoFrameB64 || null,
        }),
      });
      const result = await res.json();
      showResult(result);
    } catch (err) {
      showResult({ verified: false, error: err.message, checks: {} });
    }
  };
  reader.readAsDataURL(state.videoBlob);
}
