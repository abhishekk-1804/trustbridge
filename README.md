# TrustBridge — AI-Powered Financial Trust & Fraud Intelligence Platform

> **Trust Score ≠ Fraud Risk.** A high-trust user can still have a high-risk transaction. TrustBridge makes this distinction explicit.

---

## Overview

TrustBridge is a fintech risk intelligence platform that converts real-world financial behaviour into a portable trust identity. It combines:

- **Trust Score (0–100)** — Long-term behavioural reliability across Payment Reliability, Transaction Consistency, and Account Behaviour
- **Rule-Based Fraud Detection** — Deterministic amount-spike detection with configurable multipliers
- **Isolation Forest Anomaly Detection** — Unsupervised ML on 24 leakage-aware behavioural features
- **Unified Risk Assessment** — Combines Trust Score + Fraud Rules + ML Anomaly → Risk Decision (PROCEED / FLAG / REJECT)
- **Simulated Payment Processing** — Idempotent, atomic, double-entry ledger with balance validation
- **AI Risk Analyst Copilot** — Server-side LLM integration that explains risk decisions using real TrustBridge context

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TrustBridge Platform                     │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite + TanStack Query + Tailwind)           │
│  ─────────────────────────────────────────────────────────────  │
│  Command Center | Trust Profiles | Risk Intelligence |          │
│  Payments | Model Lab | AI Copilot | Verifications | Devs      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy + SQLite/PostgreSQL)            │
│  ─────────────────────────────────────────────────────────────  │
│  /api/dashboard   /api/users   /api/risk   /api/payments       │
│  /api/ledger      /api/copilot /api/health                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Trust Score     │ │ Fraud Rules     │ │ Isolation Forest│
│ Engine          │ │ Engine          │ │ ML Engine       │
│                 │ │                 │ │                 │
│ • Payment       │ │ • Amount Spike  │ │ • 24 Features   │
│   Reliability   │ │   Detection     │ │ • Leakage-Aware │
│ • Transaction   │ │ • Rolling Avg   │ │ • Unsupervised  │
│   Consistency   │ │ • Configurable  │ │ • Isolation     │
│ • Account       │ │   Multiplier    │ │   Forest        │
│   Behaviour     │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
              ┌─────────────────────────┐
              │ Unified Risk Assessment │
              │  Trust Score + Rules    │
              │  + ML Anomaly → Decision│
              │  PROCEED / FLAG / REJECT│
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Payment Processing      │
              │ • Idempotency Keys      │
              │ • Atomic Transactions   │
              │ • Double-Entry Ledger   │
              │ • Balance Validation    │
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ AI Risk Analyst Copilot │
              │ (Server-side LLM only)  │
              │ Explains decisions      │
              │ using real context      │
              └─────────────────────────┘
```

---

## Core Features

### Trust Score (0–100)
Three weighted components:
| Component | Weight | Description |
|-----------|--------|-------------|
| Payment Reliability | 40% | Success rate of transactions |
| Transaction Consistency | 35% | Coefficient of variation of debit amounts |
| Account Behaviour | 25% | Activity frequency + recency |

**Key Principle:** Trust Score reflects *long-term behavioural reliability*, not individual transaction risk.

### Rule-Based Fraud Detection
- **Amount Spike Detection**: Compares transaction amount against historical average and rolling 20-transaction average
- **Configurable Multiplier**: Default 3× threshold
- **Deterministic**: Same input → same output

### Isolation Forest Anomaly Detection
- **24 Leakage-Aware Features**: Amount ratios, rolling statistics, temporal patterns, categorical encodings
- **Strict Temporal Ordering**: Features computed only from prior transactions (no look-ahead)
- **Unsupervised**: Learns normal behaviour patterns, flags deviations
- **Evaluation**: Precision/Recall/F1 on injected synthetic anomalies

### Payment Processing
- **Idempotency**: Client-provided keys prevent duplicate payments (HTTP 409 on replay)
- **Atomicity**: Balance updates + ledger entries in single transaction
- **Double-Entry Ledger**: Every payment creates DEBIT (sender) + CREDIT (receiver) entries
- **Balance Validation**: Rejects payments exceeding available balance
- **Risk Integration**: Trust Score + Fraud Rules + ML Anomaly → PROCEED / FLAG / REJECT

### AI Risk Analyst Copilot
- **Server-Side Only**: LLM credentials never leave backend
- **Structured Context**: Sends only relevant TrustBridge data (Trust Score, transactions, risk events, ML explanations)
- **Prompt Injection Protection**: Input sanitization blocks override attempts
- **Graceful Degradation**: Clear message when AI provider not configured
- **Read-Only**: Explains data, never executes financial actions

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL for production

### Backend Setup
```bash
cd D:\TrustBridge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Generate synthetic data (3 users, 399 transactions, 2 injected anomalies)
python -m data.generator

# Train Isolation Forest model
python -c "from engine.ml_fraud import train_isolation_forest; print(train_isolation_forest())"

# Start API server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd D:\TrustBridge\frontend
npm install
npm run dev
```

Open http://localhost:5173

### Environment Configuration
Copy `.env.example` to `.env` and configure:
```bash
# Required for AI Copilot
AI_PROVIDER=openai
AI_API_KEY=your_actual_api_key_here
AI_MODEL=gpt-4o-mini

# Production CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Production database
DATABASE_URL=postgresql://user:pass@host:5432/trustbridge
```

---

## API Endpoints

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/` | Service info |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/summary` | System metrics, trust distribution |
| GET | `/api/dashboard/live-risk-feed` | Recent risk events |
| GET | `/api/dashboard/recent-transactions` | Latest transactions |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List users (paginated) |
| GET | `/api/users/{id}` | Get user profile |
| GET | `/api/users/{id}/trust` | Trust Score + components |
| GET | `/api/users/{id}/transactions` | User transactions |
| GET | `/api/users/{id}/payments` | Sent/received payments |

### Risk Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/risk/assess` | Assess payment risk |
| GET | `/api/risk/events` | List risk events (filterable) |
| GET | `/api/risk/events/{id}` | Risk event detail |
| GET | `/api/risk/evaluation` | ML model metrics |
| GET | `/api/risk/comparison` | Rule vs ML comparison |
| GET | `/api/risk/explain/{id}` | ML anomaly indicators |

### Payments & Ledger
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/simulate` | Simulate payment |
| GET | `/api/payments` | List payments |
| GET | `/api/payments/{id}` | Payment detail |
| GET | `/api/payments/by-idempotency/{key}` | Lookup by idempotency key |
| GET | `/api/payments/by-reference/{ref}` | Lookup by reference ID |
| GET | `/api/ledger/{payment_id}` | Ledger entries |
| GET | `/api/ledger/{payment_id}/verify` | Verify ledger balance |

### AI Copilot
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/copilot/ask` | Ask question with context |
| GET | `/api/copilot/status` | AI availability |
| GET | `/api/copilot/examples` | Example queries |

---

## Example: Simulate Payment

```bash
curl -X POST http://localhost:8000/api/payments/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "sender_account_id": 1,
    "receiver_account_id": 2,
    "amount": 5000,
    "payment_method": "upi_simulated",
    "idempotency_key": "idem_1234567890_abcdef"
  }'
```

Response:
```json
{
  "payment_id": 1,
  "reference_id": "TB20241219143022A1B2C3D4",
  "status": "completed",
  "amount": 5000.0,
  "trust_score": 76.4,
  "fraud_rule_flagged": false,
  "ml_anomaly_score": -0.0123,
  "ml_is_anomaly": false,
  "risk_policy_decision": "proceed"
}
```

---

## AI Copilot Example Queries

- `"Why was transaction 121 flagged?"`
- `"Why is Raj's Trust Score 76.4?"`
- `"What indicators contributed to this anomaly?"`
- `"Summarize this user's recent behaviour."`
- `"Why did this payment receive HIGH risk?"`
- `"Explain the difference between Trust Score and Fraud Risk."`
- `"Show me the recent suspicious activity."`

**Context**: Provide `user_id`, `transaction_id`, or `payment_id` for grounded answers.

---

## Testing

```bash
# Full test suite (108 tests)
cd D:\TrustBridge
$env:PYTHONPATH="D:\TrustBridge"
.venv\Scripts\python -m pytest tests/ -v --tb=short

# API tests only
.venv\Scripts\python -m pytest tests/test_api.py -v

# Frontend build
cd frontend && npm run build
```

**Results**: 108 tests pass (76 core + 32 API)

---

## Security

- **No Hardcoded Secrets**: All credentials via environment variables
- **AI Keys Server-Side Only**: Never exposed to frontend
- **CORS**: Production restricts to configured origins
- **Rate Limiting**: 200 req/min per IP (configurable)
- **Request Size Limit**: 1MB default
- **Input Validation**: Pydantic schemas on all endpoints
- **Safe Errors**: No stack traces in production responses
- **Prompt Injection Protection**: Input sanitization on Copilot
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

### Security Checklist
- [x] `.env` not tracked (in `.gitignore`)
- [x] Model artifacts not tracked (`models/` in `.gitignore`)
- [x] Database files not tracked (`*.db` in `.gitignore`)
- [x] Virtual environment not tracked (`.venv/` in `.gitignore`)
- [x] No hardcoded API keys in source
- [x] No secrets in frontend build output
- [x] AI credentials only in backend environment

---

## Security & Production Architecture Boundaries

TrustBridge is engineered as a high-fidelity internal risk and fraud
intelligence platform. The architecture emphasizes financial accounting
invariants, machine-learning auditability, grounded advisory AI, and
human-controlled investigation workflows.

For controlled demonstration and architectural clarity, the current build
deliberately defines the following boundaries:

### 1. Authentication & Identity Isolation

- The demonstration API does not currently implement JWT, OAuth/OIDC,
  session-based authentication, or application-level user authentication.
- API endpoints therefore operate in a controlled/demo context rather than
  as an unrestricted public financial service.
- `InvestigationCase.analyst_id` remains nullable in the current build because
  authenticated analyst identity is not implemented.
- Production deployment would require an authenticated identity boundary,
  such as an API gateway validating OIDC/JWT credentials and propagating
  verified identity claims to the application.

### 2. Authorization & Role Isolation

- Role-based authorization is not implemented in the current demonstration
  build.
- Investigation and payment operations should therefore be considered
  controlled-demo capabilities rather than production-grade multi-tenant
  authorization boundaries.
- A production deployment would require explicit roles/permissions,
  user isolation, and authorization checks on protected resources.

### 3. Polymorphic Risk References

- `InvestigationCase` references the underlying risk event through the
  application-level compound key `(risk_event_id, risk_event_type)`.
- The current implementation supports risk events originating from the
  supported transaction/payment domains without introducing an artificial
  database foreign key across multiple entity types.
- Referential existence is validated at the application layer.
- The compound uniqueness constraint prevents duplicate investigation cases
  for the same risk-event/type pair.
- Production schema evolution could replace or further formalize this
  relationship depending on the persistence architecture.

### 4. Strict AI Advisory Perimeter

- The AI Copilot is an advisory explanation layer.
- It receives grounded TrustBridge context and produces explanatory text.
- It has no tool/function-calling capability that can mutate TrustBridge
  state.
- It cannot approve, reject, escalate, dismiss, resolve, block, or otherwise
  execute financial or investigation actions.
- Human-controlled investigation disposition remains separate from AI output.
- Trust Score and transaction-level Fraud Risk remain separate concepts;
  the AI does not replace either underlying deterministic/model-based
  decision process.

### 5. Deterministic Payment & Accounting Controls

- Payment simulation uses idempotency controls and atomic database
  transactions.
- Ledger entries follow the application's double-entry accounting model.
- Monetary amounts are represented internally in minor currency units
  (paise) and converted at the API/display boundary.
- Ledger verification is separate from AI-generated explanations.
- AI output cannot mutate payment or ledger state.

### 6. Auditability

- Investigation cases maintain persistent workflow state.
- Meaningful case creation and state changes are recorded through the
  append-only audit-log mechanism.
- The audit trail is separate from AI-generated explanations and risk
  detection output.

### 7. Production Hardening Requirements

The current build is intended for controlled demonstration and evaluation,
not unrestricted production financial use.

A production deployment would additionally require, at minimum:

- authenticated identity and authorization/RBAC
- user/tenant isolation
- production-specific CORS configuration
- managed secret storage and deployment configuration
- database migration management
- stronger operational monitoring and alerting
- production infrastructure, network, and deployment controls
- security testing appropriate to the deployment environment

These are deliberate production-boundary requirements, not claims that those
capabilities are implemented in the current demonstration build.

---

### CORS & Debug Configuration Boundary

- Debug now defaults to `False` in application settings.
- CORS origins are configurable through application settings/environment.
- Development defaults include the local frontend origins
  (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).
- Production deployments must explicitly configure trusted origins via
  the `CORS_ORIGINS` environment variable (comma-separated or JSON list).
- Debug mode defaults to `False` and should remain `False` in production.
- CORS `allow_headers` is restricted to a minimal explicit set
  (`Content-Type`, `Authorization`, `Accept`, `X-Requested-With`,
  `X-Idempotency-Key`) rather than the wildcard `["*"]`.

---

## Deployment

### Backend (Render / Railway / Fly.io)
```bash
# Build command
pip install -r requirements.txt

# Start command
uvicorn backend.main:app --host 0.0.0.0 --port $PORT

# Environment variables (set in platform dashboard)
APP_ENV=production
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://yourdomain.com
AI_PROVIDER=openai
AI_API_KEY=sk-...
```

### Frontend (Vercel / Netlify)
```bash
# Build command
npm run build

# Output directory
dist

# Environment variables
VITE_API_BASE_URL=https://api.yourdomain.com/api
```

---

## Limitations & Known Issues

| Area | Limitation |
|------|------------|
| **Data** | Synthetic dataset (399 transactions, 3 users, 2 injected anomalies) |
| **ML Model** | Isolation Forest unsupervised; evaluation on injected anomalies only |
| **Payments** | Simulated only (UPI_SIMULATED, BANK_TRANSFER_SIMULATED, WALLET_SIMULATED) |
| **AI Copilot** | Requires external LLM provider; falls back gracefully if unavailable |
| **Scale** | SQLite for dev; PostgreSQL recommended for production |
| **Auth** | Not implemented (add JWT/OAuth2 for production) |
| **Real-time** | Polling-based (add WebSockets for live updates) |

---

## Project Structure

```
TrustBridge/
├── app.py                 # Legacy Streamlit app (deprecated)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .gitignore
├── backend/
│   ├── main.py           # FastAPI app + middleware
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # SQLAlchemy engine/session
│   ├── ai_copilot.py     # AI Copilot logic
│   └── api/              # REST endpoints
│       ├── users.py
│       ├── risk.py
│       ├── payments.py
│       ├── dashboard.py
│       └── copilot.py
├── database/
│   ├── models.py         # SQLAlchemy models
│   └── db.py             # DB connection
├── engine/
│   ├── trust_score.py    # Trust Score calculation
│   ├── fraud_rules.py    # Rule-based detection
│   ├── ml_features.py    # Leakage-aware feature engineering
│   ├── ml_fraud.py       # Isolation Forest training/inference
│   └── payment_service.py # Payment + ledger logic
├── data/
│   └── generator.py      # Synthetic data generator
├── models/               # Trained ML artifacts (gitignored)
├── tests/                # 108 tests
│   ├── test_api.py       # 32 API integration tests
│   └── ...               # 76 core engine tests
└── frontend/             # React + Vite + TanStack Query
    ├── src/
    │   ├── pages/        # 9 pages
    │   ├── components/   # Reusable UI
    │   ├── api/          # Axios + TanStack Query hooks
    │   └── types/        # TypeScript interfaces
    └── package.json
```

---

## License

MIT License — See LICENSE file for details.

---

## Acknowledgments

Built for Hackathon 2026 by Team StratNova.

**Core Technologies**: FastAPI, React, SQLAlchemy, scikit-learn, TanStack Query, Tailwind CSS, Vite.

---

*TrustBridge — Because Trust Score ≠ Fraud Risk.*