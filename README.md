# Arcus Market Maker

Legitimate two-sided market making bot for Arcus (https://docs.arcus.xyz) + professional dark trading dashboard.

**No wash trading, no self-trading, no fake volume.** Profit via spread capture with inventory/adverse-selection/fee/funding risk controls.

> **Phase 2 scaffold** — full implementation in Phases 3-41. Default mode is `PAPER` (simulated). `LIVE` requires explicit confirmation.

## Project Structure

```
arcus-market-maker/
  backend/
    api/               # FastAPI routes
    arcus/             # Arcus REST + WS client (official docs only)
    authentication/    # HMAC signing, no seed/privkey
    market_data/       # WS engine, BBO/L2, stale detection
    strategy/          # fair value, quoting, dynamic spread
    execution/         # order mgmt, reconciliation
    risk/              # pre-trade checks, emergency stop, DMS
    profitability/     # expected P&L engine + filter
    paper_trading/     # simulated fills/fees/inventory/PnL
    database/          # SQLAlchemy + SQLite
    models/            # Pydantic/SQLAlchemy models
    services/          # shared services
    config/            # settings (TRADING_MODE etc.)
    monitoring/        # logs, metrics
    tests/             # pytest
  frontend/
    src/
      components/ pages/ charts/ services/ hooks/ types/ layouts/
  .env.example
  .gitignore
```

## Quick Start (Linux Mint 22.3)

### Prerequisites
- Python 3.12 (`python3 --version`)
- Node 18 + npm 9 (`node --version`, `npm --version` — if npm missing: `sudo apt install npm` or manual install via `~/.local/bin/npm` wrapper)
- `~/.local/bin` in PATH (`export PATH="$HOME/.local/bin:$PATH"`)

### 1. Clone / enter
```bash
cd ~/arcus-market-maker
```

### 2. Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt  # (added in Phase 3)
cp .env.example .env  # edit TRADING_MODE etc.
uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install          # (after Phase 3 adds package.json)
npm run dev          # Vite on http://localhost:5173
```

### 4. Modes
- `TRADING_MODE=PAPER` (default, simulated)
- `TRADING_MODE=TESTNET` (real testnet, needs Arcus testnet creds)
- `TRADING_MODE=LIVE` (requires explicit confirmation + risk limits + DMS)

## Security
- Never commit `.env`; never log `ARCUS_API_SECRET`; no seed/mnemonic/private key handling; no withdrawals.
- Auth per https://docs.arcus.xyz/api-reference/authentication.md

## Docs
Official Arcus docs: https://docs.arcus.xyz/llms.txt

## License
Private — do not distribute.
