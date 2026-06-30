# TNG CRM 2.0

A production-style starter CRM for TNG Boxing sales reps, members, commissions, referral links, QR codes, and future Clover automation.

## What this version includes

- FastAPI backend
- SQLite database
- Admin login
- Sales rep login
- Role-based dashboard data
- Sales reps with Clover links
- Referral slugs like `/join/mike`
- Automatic commission tiers
- Membership products:
  - Pre-Sale Monthly: $155
  - Month-to-Month: $150
  - 3 Months Special: $300
  - Full Year: $900
- Clover settings placeholder
- Clover webhook endpoint placeholder
- React frontend starter

## Run backend locally

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

Backend opens at:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Default admin:

```text
Email: admin@tngboxinggym.com
Password: admin123
```

## Run frontend locally

Open a new PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Frontend opens at:

```text
http://127.0.0.1:5173
```

## Clover webhook URL after deployment

```text
https://crm.tngboxinggym.com/api/clover/webhook
```

Clover cannot send webhooks to local `127.0.0.1`. The app must be deployed online first.
