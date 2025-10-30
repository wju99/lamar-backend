# Backend

Backend API for the Lamar Health care plan intake app. Implements patient/order creation with confirmation flows, provider upsert by NPI, PDF records text extraction, and care plan generation via OpenAI.

## Tech
- Django 5
- Django Ninja (Fast API layer)
- Postgres
- OpenAI SDK (care plan generation)
- pypdf (PDF → text extraction)

## Quick Start
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Environment Variables
Set in `.env` or your hosting provider:

- DATABASE_URL  Postgres connection URL
- OPENAI_API_KEY  API key for LLM care plan generation

## Endpoints (mounted at /api)
- POST /providers  Create/update provider by NPI
- GET /providers  List providers
- POST /patients  Create patient + order (with confirmation flows)
- GET /patients  List patients
- POST /orders  Create order
- GET /orders  List orders
- POST /records/extract  Upload PDF → { extracted_text }
- GET /patients/{patient_id}/orders/{order_id}/care-plan  Download care-plan .txt

## CORS / CSRF
Allowed origins are configured in `lamar_backend/settings.py` (Vercel domains + localhost). Update `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` when adding new frontends.

## Tests
```bash
cd lamar-backend
source venv/bin/activate
python manage.py test patients
```

## Deployment Notes
- Production server: gunicorn lamar_backend.wsgi:application
- Static files served via WhiteNoise
- Ensure ALLOWED_HOSTS, DATABASE_URL, OPENAI_API_KEY, and CORS/CSRF origins are set

## Project Structure (key paths)
```
lamar-backend/
  lamar_backend/         # Django project
  patients/              # App: models, schemas, api, tests
  requirements.txt
  README.md
```
