# Doorstep Verify — Backend API

FastAPI backend for AI-powered doorstep delivery verification.

## Stack
- **Hosting**: Render.com (free tier)
- **Database + Storage**: Supabase (free tier)
- **AI Tier 1**: Google Gemini 1.5 Flash (free, 1,500/day)
- **AI Tier 2**: OpenAI GPT-4o (fallback, your $5 credits)
- **AI Tier 3**: Hugging Face BLIP (free fallback)
- **Geocoding**: Nominatim / OpenStreetMap (free, no key)

## Setup

### 1. Supabase
- Create project at supabase.com
- Run `supabase_setup.sql` in SQL Editor
- Create storage bucket: `proof-files` (private)
- Copy Project URL and service_role key

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...service_role_key...
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-...
HF_TOKEN=hf_...
W3W_API_KEY=...  (optional)
```

### 3. Local Development
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
API docs: http://localhost:8000/docs

### 4. Deploy to Render.com
- Push this folder to GitHub
- New Web Service on render.com → connect repo
- Add all environment variables in Render dashboard
- Deploy

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/verify?driverId=X` | List pending deliveries for driver |
| GET | `/verify?action=ping` | Keep-alive ping |
| POST | `/verify` | Submit delivery for verification |

## POST /verify Body
```json
{
  "tracking_id": "TEST001",
  "barcode": "TEST001",
  "gps": { "lat": 41.882700, "lng": -87.623300, "accuracy": 12.0 },
  "driver_id": "DRIVER1",
  "media_type": "photo",
  "file_base64": "..."
}
```
