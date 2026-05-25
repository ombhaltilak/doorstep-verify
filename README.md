# 📦 DoorStep - Delivery Verification System

DoorStep is an intelligent proof-of-delivery tracking system that prevents misdeliveries using AI visual verification and strict GPS matching. It ensures that packages are delivered to the correct doorstep by validating the delivery photo against the expected address and coordinates.

## ✨ Key Features

- **🤖 AI Visual Verification:** Uses Google Gemini Vision API to extract text (house numbers, nameplates) from delivery photos and matches it against the delivery address.
- **📍 Strict Geofencing & EXIF Matching:** Validates the GPS coordinates where the photo was taken (EXIF data) against the expected delivery location.
- **📷 Driver App:** A mobile-friendly PWA (Progressive Web App) for drivers with built-in barcode scanning, GPS capture, and camera support.
- **💻 Admin Dashboard:** A dispatch dashboard to create parcels, assign drivers, auto-fill expected GPS coordinates via what3words/Nominatim, and monitor delivery status in real-time.
- **☁️ Cloud Database:** Powered by Supabase (PostgreSQL) for real-time tracking and data storage.

---

## 🏗️ Architecture

The project is divided into three main components:

### 1. `doorstep-admin-app/` (Dispatcher/Admin Portal)
A web interface for warehouse managers to create and dispatch parcels.
- Auto-generates GPS coordinates from written addresses using Nominatim (OpenStreetMap).
- Optionally integrates with what3words for high-precision door locations.
- Displays the real-time status of all deliveries (Pending, Verified ✅, Failed ❌).

### 2. `doorstep-driver-app/` (Driver PWA)
A mobile web application for delivery drivers on the road.
- Uses the device camera to scan package barcodes.
- Captures delivery photos with embedded EXIF GPS tags.
- Securely submits proof of delivery over HTTPS.

### 3. `doorstep-verify-api/` (Python Verification API)
The core backend processing engine built with FastAPI.
- Handles image uploads and extracts EXIF metadata.
- Compares driver coordinates with expected coordinates.
- Sends the image and address to Google Gemini to verify visual proof (e.g., verifying that a "123" nameplate matches "123 Main St").
- Updates the Supabase database with the final verification result.

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9+
- A [Supabase](https://supabase.com/) account
- A [Google Gemini](https://ai.google.dev/) API Key

### 1. Database Setup
1. Create a new Supabase project.
2. Go to the SQL Editor and run the script located in `doorstep-verify-api/supabase_setup.sql`.
3. (Optional) Run `doorstep-verify-api/supabase_sample_data.sql` to populate the database with dummy test parcels.

### 2. API Backend Setup
Navigate to the API folder:
```bash
cd doorstep-verify-api
```
Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Configure environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and add your `SUPABASE_URL`, `SUPABASE_KEY`, and `GEMINI_API_KEY`.

Start the API server:
```bash
python3 main.py
```

### 3. Driver App Setup
The driver app requires an HTTPS context to access the mobile camera and barcode scanner.
Navigate to the driver app folder:
```bash
cd doorstep-driver-app
```
*Note: Make sure your `config.js` is pointing to your running API URL.*
Run the secure local server:
```bash
python3 https_server.py
```
Access the app at `https://localhost:4443` (accept the self-signed certificate warning for local testing).

### 4. Admin App Setup
Navigate to the admin app folder:
```bash
cd doorstep-admin-app
```
Run a simple HTTP server:
```bash
python3 -m http.server 4000
```
Access the dashboard at `http://localhost:4000`.

---

## 🛡️ Security Note
This project uses `.env` files to manage secrets. Ensure that you never commit your real API keys or `.pem` SSL certificates to version control. They have been properly added to `.gitignore`.
