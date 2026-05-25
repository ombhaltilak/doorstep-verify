// ══════════════════════════════════════════════════════════════════════════════
// APPROACH A — GEOTAGGED PHOTO
// ══════════════════════════════════════════════════════════════════════════════

async function startPhotoMode() {
  state.mediaType = 'photo';
  showScreen('screen-photo');

  // Reset preview
  document.getElementById('photo-preview-wrap').style.display = 'none';

  state.photoStream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: 'environment',
      width:  { ideal: 1920 },
      height: { ideal: 1080 },
    }
  });
  document.getElementById('photo-video').srcObject = state.photoStream;

  // Show current GPS once — no interval needed, GPS was locked on previous screen
  if (state.gps) {
    document.getElementById('photo-gps-badge').textContent =
      `GPS: ${state.gps.lat.toFixed(5)}, ${state.gps.lng.toFixed(5)}  ±${state.gps.accuracy.toFixed(0)}m`;
  }
}

function captureGeotaggedPhoto() {
  // Refresh GPS at exact moment of capture
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const filtered = kf.update(
        pos.coords.latitude, pos.coords.longitude,
        pos.coords.accuracy, pos.timestamp
      );
      state.gps = {
        lat:       filtered.lat,
        lng:       filtered.lng,
        accuracy:  filtered.accuracy,
        timestamp: new Date(pos.timestamp).toISOString(),
      };

      const video  = document.getElementById('photo-video');
      const canvas = document.getElementById('photo-canvas');
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      const jpegBase64 = canvas.toDataURL('image/jpeg', 0.95);

      // Inject GPS into JPEG EXIF using piexifjs
      const exifObj = {
        'GPS': {
          [piexif.GPSIFD.GPSLatitudeRef]:  state.gps.lat >= 0 ? 'N' : 'S',
          [piexif.GPSIFD.GPSLatitude]:
            piexif.GPSHelper.degToDmsRational(Math.abs(state.gps.lat)),
          [piexif.GPSIFD.GPSLongitudeRef]: state.gps.lng >= 0 ? 'E' : 'W',
          [piexif.GPSIFD.GPSLongitude]:
            piexif.GPSHelper.degToDmsRational(Math.abs(state.gps.lng)),
          [piexif.GPSIFD.GPSDateStamp]:    state.gps.timestamp.split('T')[0],
          [piexif.GPSIFD.GPSTimeStamp]:
            state.gps.timestamp.split('T')[1].split('Z')[0]
              .split(':').map(v => [parseInt(v), 1]),
        },
        'Exif': {
          [piexif.ExifIFD.DateTimeOriginal]: state.gps.timestamp,
        },
      };
      const exifBytes     = piexif.dump(exifObj);
      state.photoBase64   = piexif.insert(exifBytes, jpegBase64);

      // Show preview
      document.getElementById('photo-preview').src = state.photoBase64;
      document.getElementById('photo-preview-wrap').style.display = 'flex';
      document.getElementById('photo-preview-wrap').style.flexDirection = 'column';
      document.getElementById('photo-preview-wrap').style.gap = '10px';
    },
    (err) => { alert('Could not get GPS — try again outdoors'); },
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

function retakePhoto() {
  document.getElementById('photo-preview-wrap').style.display = 'none';
  state.photoBase64 = null;
}

function photoGoBack() {
  stopStream(state.photoStream);
  state.photoStream = null;
  state.photoBase64 = null;
  document.getElementById('photo-preview-wrap').style.display = 'none';
  showScreen('screen-choose');
}

async function submitPhoto() {
  stopStream(state.photoStream);
  showScreen('screen-uploading');
  setUploadStep('Uploading geotagged photo...');

  try {
    const res = await fetch(`${API_URL}/verify`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        tracking_id: state.trackingId,
        barcode:     state.scannedBarcode,
        gps:         state.gps,
        driver_id:   state.driverId,
        media_type:  'photo',
        file_base64: state.photoBase64.split(',')[1],
      }),
    });
    const result = await res.json();
    showResult(result);
  } catch (e) {
    showResult({ verified: false, error: e.message, checks: {} });
  }
}
