# ⬡ BharatChain — Universal Digital Identity Protocol

> A blockchain-based Universal ID system for India: combining Aadhaar biometrics, health records, financial identity (PAN+), land registry, and capital assets into one sovereign, citizen-controlled digital identity.

---

## 📁 Project Structure

```
bharatchain/
├── main.py                    ← Entry point — run this to start the server
├── config.py                  ← All settings loaded from .env
├── requirements.txt           ← Python dependencies
├── .env.example               ← Copy this to .env and fill in your values
├── .gitignore
│
├── core/                      ← Shared engine — used by all modules
│   ├── blockchain.py          ← Chain connection (simulation / Ethereum / Fabric)
│   ├── crypto.py              ← AES encryption, SHA-3 hashing, ZK-proof stubs
│   ├── identity.py            ← DID generation, biometric hashing
│   └── consent.py             ← Permission gate — every module goes through this
│
├── modules/                   ← Business logic for each data domain
│   ├── health.py              ← Health records (FHIR R4)
│   ├── financial.py           ← Financial ID / PAN+ replacement
│   ├── property.py            ← Land & property registry
│   └── assets.py              ← Capital assets & gains
│
├── api/                       ← HTTP endpoints (FastAPI routers)
│   ├── routes_identity.py     ← /identity/*
│   ├── routes_health.py       ← /health/*
│   ├── routes_financial.py    ← /financial/*
│   ├── routes_property.py     ← /property/*
│   ├── routes_assets.py       ← /assets/*
│   └── routes_consent.py      ← /consent/*
│
└── db/
    ├── session.py             ← PostgreSQL async connection
    └── models.py              ← All database table definitions
```

---

## 🔄 How the Files Connect

Every request flows through this exact chain:

```
HTTP Request
    ↓
main.py  (registers all routers)
    ↓
api/routes_*.py  (validates input, calls module)
    ↓
core/consent.py  ← SECURITY GATE (checks permission first)
    ↓
modules/*.py  (business logic)
    ↓
core/crypto.py  (encrypt / decrypt data)
    ↓
db/models.py  (save to PostgreSQL)
    ↓
core/blockchain.py  (write proof to chain)
    ↓
HTTP Response
```

**Key rule:** No module ever skips the consent check. `require_permission()` in `core/consent.py` is always called first.

---

## 🚀 Setup Guide

### Prerequisites

Before starting, you need these installed on your computer:

| Tool | Why | Install |
|------|-----|---------|
| Python 3.11+ | Runs the backend | [python.org](https://www.python.org/downloads/) |
| PostgreSQL 15+ | Stores encrypted data | [postgresql.org](https://www.postgresql.org/download/) |
| Git | Version control | [git-scm.com](https://git-scm.com/) |

> **Want to skip PostgreSQL?** Change `DATABASE_URL` in `.env` to use SQLite (easier for local dev): `sqlite+aiosqlite:///./bharatchain.db` and add `aiosqlite` to requirements.txt

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/bharatchain.git
cd bharatchain
```

---

### Step 2 — Create a Virtual Environment

A virtual environment keeps this project's dependencies separate from your system Python.

```bash
# Create the virtual environment
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# You should see (venv) in your terminal prompt now
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, cryptography libraries, web3, and all other packages.

> **Slow or failing?** Try: `pip install -r requirements.txt --timeout 60`

---

### Step 4 — Set Up the Database

#### Option A: PostgreSQL (recommended for production)

```bash
# Open PostgreSQL prompt
psql -U postgres

# Run these commands inside psql:
CREATE DATABASE bharatchain_db;
CREATE USER bharatchain WITH PASSWORD 'secret';
GRANT ALL PRIVILEGES ON DATABASE bharatchain_db TO bharatchain;
\q
```

#### Option B: SQLite (easiest for local dev, no installation needed)

In `.env`, change `DATABASE_URL` to:
```
DATABASE_URL=sqlite+aiosqlite:///./bharatchain.db
```
Then add to `requirements.txt`:
```
aiosqlite==0.20.0
```
And run `pip install aiosqlite`.

---

### Step 5 — Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Now open `.env` in any text editor and fill in these **required** values:

#### Generate ENCRYPTION_KEY:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output and paste it as `ENCRYPTION_KEY=` in `.env`.

#### Generate JWT_SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste it as `JWT_SECRET_KEY=` in `.env`.

Your `.env` should look like:
```env
APP_NAME=BharatChain
DEBUG=True
ENVIRONMENT=development
DATABASE_URL=postgresql://bharatchain:secret@localhost:5432/bharatchain_db
BLOCKCHAIN_BACKEND=simulation
ENCRYPTION_KEY=your-generated-key-here
JWT_SECRET_KEY=your-generated-secret-here
```

> ⚠️ **Never commit `.env` to GitHub.** It's already in `.gitignore` — keep it that way.

---

### Step 6 — Run the Server

```bash
python main.py
```

You should see:
```
INFO | Starting BharatChain v0.1.0
INFO | ✓ Database ready
INFO | ✓ Blockchain connected — backend: simulation
INFO | ✓ Crypto engine ready
INFO | ==================================================
INFO |   BharatChain is LIVE on port 8000
INFO | ==================================================
```

---

### Step 7 — Test It's Working

Open your browser and visit:

- **API Status:** http://localhost:8000
- **Swagger Docs (interactive):** http://localhost:8000/docs
- **ReDoc Docs:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health-check

The Swagger UI at `/docs` lets you test every endpoint directly in the browser — no extra tools needed.

---

## 🧪 Quick API Test

Once the server is running, try this sequence in Swagger at `/docs`:

#### 1. Register a Citizen
`POST /identity/register`
```json
{
  "uid": "123456789012",
  "full_name": "Rahul Sharma",
  "dob": "1990-08-15",
  "gender": "M",
  "address": "Mumbai, Maharashtra"
}
```
Save the `citizen_id` from the response.

#### 2. Grant Consent to a Hospital
`POST /consent/{citizen_id}/grant`
```json
{
  "citizen_uid": "123456789012",
  "requester_id": "APOLLO_HOSPITAL",
  "requester_name": "Apollo Hospitals",
  "modules": ["health"],
  "duration_days": 30
}
```

#### 3. Add a Health Record (as Apollo Hospital)
`POST /health/{citizen_id}/records`
```json
{
  "requester_id": "APOLLO_HOSPITAL",
  "record_type": "diagnosis",
  "provider_name": "Apollo Hospitals",
  "provider_id": "APOLLO_MUM_001",
  "record_data": {
    "diagnosis": "Hypertension",
    "medication": "Amlodipine 5mg",
    "notes": "Follow up in 3 months"
  }
}
```

#### 4. Read the Record Back
`GET /health/{citizen_id}/records?requester_id=APOLLO_HOSPITAL`

#### 5. View Audit Trail
`GET /consent/{citizen_id}/audit`

---

## 🔗 Pushing to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "feat: initial BharatChain implementation"

# Add your GitHub repo as remote
git remote add origin https://github.com/YOUR_USERNAME/bharatchain.git

# Push
git push -u origin main
```

> Make sure `.env` is NOT included. Run `git status` and verify it's not listed.

---

## ☁️ Deploying for Free (Demo)

### Option A — Render.com (easiest)
1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set environment variables (same as `.env`) in Render dashboard
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click Deploy — Render gives you a free HTTPS URL

### Option B — Railway.app
1. Go to [railway.app](https://railway.app) → New Project → GitHub Repo
2. Add a PostgreSQL plugin (free tier)
3. Set environment variables
4. Deploy automatically on every push

---

## 🔧 Switching Blockchain Backends

In `.env`, change `BLOCKCHAIN_BACKEND`:

| Value | Description | Requirements |
|-------|-------------|--------------|
| `simulation` | In-memory chain, zero setup | Nothing extra |
| `ethereum` | Real Ethereum node | Ganache/Hardhat + wallet key |
| `fabric` | Hyperledger Fabric | Full Fabric network running |

**Start with `simulation`** — it works immediately and logs every block to the terminal.

To use Ethereum locally:
```bash
# Install Ganache
npm install -g ganache

# Start local blockchain
ganache --chain.chainId 1337

# Update .env:
BLOCKCHAIN_BACKEND=ethereum
WEB3_PROVIDER_URL=http://127.0.0.1:8545
CHAIN_ID=1337
DEPLOYER_PRIVATE_KEY=<key from ganache output>
```

---

## 🛡️ Security Architecture

```
Citizen Data Flow:
Raw UID → SHA-3 Hash → stored in DB (UID never stored)
Raw Biometric → PBKDF2 Hash → stored in DB (biometric never stored)
Sensitive fields → AES-256 encrypted → stored in DB
All records → SHA-3 hash → written to blockchain (proof, not data)

Access Control:
Government tier  → full access, always audited
Regulated tier   → access only with active citizen consent
Commercial tier  → ZK-proofs only, never raw data
```

---

## 🗺️ Roadmap

- [x] Core identity + DID
- [x] Health, financial, property, assets modules
- [x] Consent engine
- [x] Simulation blockchain
- [x] Audit trail
- [ ] Real ZK-SNARK proofs (snarkjs integration)
- [ ] IPFS document storage
- [ ] Mobile app (React Native)
- [ ] Smart contract deployment (Solidity)
- [ ] Hyperledger Fabric full integration
- [ ] FHIR R4 full compliance
- [ ] Biometric SDK integration (OpenCV)

---

## 📞 Coming Back to This Project

When you return, just do:

```bash
cd bharatchain
source venv/bin/activate     # or venv\Scripts\activate on Windows
python main.py
```

Everything will start exactly where you left off.

---

*Built with FastAPI · SQLAlchemy · cryptography · web3.py · Hyperledger Fabric*
