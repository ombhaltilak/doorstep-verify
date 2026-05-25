// ── Add Delivery form helpers ─────────────────────────────────────────────────

function initAddDelivery() {
  // Pre-fill driver ID from current login
  const driverEl = document.getElementById('add-driver');
  if (state.driverId) driverEl.value = state.driverId;

  // Clear previous entries
  document.getElementById('add-tracking').value = '';
  document.getElementById('add-customer').value = '';
  document.getElementById('add-address').value  = '';
  document.getElementById('add-lat').value       = '';
  document.getElementById('add-lng').value       = '';
  document.getElementById('add-w3w').value       = '';
  document.getElementById('add-result').style.display = 'none';
  document.getElementById('add-gps-status').style.display = 'none';
  document.getElementById('btn-add-submit').disabled = false;
}


// ── GPS auto-fill ─────────────────────────────────────────────────────────────

async function fillAddressFromGPS() {
  const btn    = document.getElementById('btn-gps-fill');
  const status = document.getElementById('add-gps-status');

  btn.disabled = true;
  btn.textContent = '⏳';
  status.style.display = 'block';
  status.className = 'add-gps-status loading';
  status.textContent = 'Getting GPS location…';

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      const acc = Math.round(pos.coords.accuracy);

      document.getElementById('add-lat').value = lat.toFixed(7);
      document.getElementById('add-lng').value = lng.toFixed(7);
      status.textContent = `GPS locked ±${acc}m — reverse-geocoding address…`;

      // Reverse geocode with Nominatim
      try {
        const r = await fetch(
          `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
          { headers: { 'User-Agent': 'DoorstepVerify/1.0 kalpandeparimal60@gmail.com' } }
        );
        const d = await r.json();
        if (d.display_name) {
          // Use a shorter form: road + suburb + city
          const a = d.address || {};
          const parts = [
            a.house_number,
            a.road || a.pedestrian || a.footway,
            a.suburb || a.neighbourhood || a.quarter,
            a.city || a.town || a.village || a.county,
            a.state,
          ].filter(Boolean);
          document.getElementById('add-address').value = parts.join(', ') || d.display_name;
          status.textContent = `Address filled from GPS (±${acc}m)`;
          status.className = 'add-gps-status success';
        } else {
          status.textContent = 'Geocoding returned no result — type address manually';
          status.className = 'add-gps-status warn';
        }
      } catch (e) {
        status.textContent = 'Geocoding failed — type address manually';
        status.className = 'add-gps-status warn';
        console.error('Reverse geocode error:', e);
      }

      // what3words auto-fill
      if (W3W_KEY && W3W_KEY !== 'YOUR_W3W_KEY') {
        try {
          const wr = await fetch(
            `https://api.what3words.com/v3/convert-to-3wa?coordinates=${lat},${lng}&language=en&key=${W3W_KEY}`
          );
          const wd = await wr.json();
          console.log('W3W add-form response:', wd);
          if (wd.words) {
            document.getElementById('add-w3w').value = wd.words;
          }
        } catch (e) {
          console.error('W3W error in add form:', e);
        }
      }

      btn.disabled = false;
      btn.textContent = '📍 GPS';
    },
    (err) => {
      status.style.display = 'block';
      status.className = 'add-gps-status warn';
      status.textContent = `GPS error: ${err.message} — type address manually`;
      btn.disabled = false;
      btn.textContent = '📍 GPS';
    },
    { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
  );
}


// ── Submit ────────────────────────────────────────────────────────────────────

async function submitAddDelivery() {
  const tracking  = document.getElementById('add-tracking').value.trim().toUpperCase();  // uppercase — barcode format
  const customer  = document.getElementById('add-customer').value.trim();
  const address   = document.getElementById('add-address').value.trim();
  const driver    = document.getElementById('add-driver').value.trim().toUpperCase();
  const latVal    = document.getElementById('add-lat').value.trim();
  const lngVal    = document.getElementById('add-lng').value.trim();
  const w3w       = document.getElementById('add-w3w').value.trim();

  if (!tracking)  { alert('Tracking ID is required'); return; }
  if (!customer)  { alert('Customer Name is required'); return; }
  if (!address)   { alert('Address is required'); return; }
  if (!driver)    { alert('Driver ID is required'); return; }

  const payload = {
    tracking_id:   tracking,
    customer_name: customer,
    address:       address,
    driver_id:     driver,
  };
  if (latVal && lngVal) {
    payload.expected_lat = parseFloat(latVal);
    payload.expected_lng = parseFloat(lngVal);
  }
  if (w3w) payload.front_door_w3w = w3w;

  const btn    = document.getElementById('btn-add-submit');
  const result = document.getElementById('add-result');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const r = await fetch(`${API_URL}/deliveries`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const d = await r.json();
    if (r.ok && d.ok) {
      result.style.display = 'block';
      result.className = 'add-result-box success';
      result.innerHTML = `
        <strong>✅ Saved!</strong><br>
        Tracking ID: <code>${d.tracking_id}</code><br>
        <small>GPS coords ${latVal ? 'stored' : 'not set — add later in Supabase'}</small>
      `;
      btn.textContent = '✅ Saved';
      // Go back to list after 1.5s
      setTimeout(() => {
        showScreen('screen-list');
        loadDeliveries();
      }, 1500);
    } else {
      throw new Error(d.detail || d.error || 'Unknown error');
    }
  } catch (e) {
    result.style.display = 'block';
    result.className = 'add-result-box fail';
    result.innerHTML = `<strong>❌ Error:</strong> ${e.message}`;
    btn.disabled = false;
    btn.textContent = '✅ Save Delivery';
  }
}
