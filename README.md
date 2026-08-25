# Arcus Market Maker — Legit Two-Sided Liquidity (PAPER Default)

Professional dark trading dashboard + Rust-inspired Python market-making bot for [Arcus](https://docs.arcus.xyz). **Never** does wash/self/circular/fake volume. Profit via legitimate spread capture with inventory, adverse-selection, fee, funding, volatility controls.

> Default `TRADING_MODE=PAPER` (simulated). `LIVE` requires explicit `confirm_live=true` + credentials + risk limits + dead man's switch.

## What You Get
- **Bot**: fair value (mid/microprice/imbalance/vol), dynamic spread, inventory skew, adaptive sizing, profitability filter (`expected_net_profit`), maker-fee aware, stale-data → cancel quotes, rate-limit scheduler, 14 risk checks, emergency stop + DMS, paper-testnet-live modes.
- **Dashboard**: bot status, $1M volume progress, PnL (gross/fees/funding/net), 7 charts (volume/PnL/inventory/spread/fees...), order/fill tables, risk bars, START/PAUSE/STOP/EMERGENCY, settings, WS live updates.
- **Stack**: Python 3.12 FastAPI + Pydantic + SQLAlchemy (aiosqlite) + httpx/websockets; React 18 TS + Vite 6 + Tailwind 3 + Recharts 2; SQLite; pytest.

## Project Map
```
arcus-market-maker/
  backend/
    api/routes.py          # /api/health, /bot/*, /analytics/*, /orders, /fills, /config, /ws/dashboard
    arcus/client.py        # Official REST only (no guessed endpoints), Ed25519 Scheme1/2
    authentication/signer.py # build_place/cancel/modify payloads, ticks/quantums, never logs secrets
    market_data/engine.py  # WS + BBO/L2 + stale(5s)+sequence+REST fallback
    strategy/fair_value.py # mid/microprice/imbalance/vol → fair_value()
    strategy/market_maker.py # two-sided quotes + dynamic spread + skew + adaptive size
    profitability/engine.py # expected_gross/fees/funding/adverse → net + profitability_check()
    risk/engine.py         # 14 pre-trade checks
    risk/rate_limiter.py   # 8 RPS scheduler, throttling
    risk/emergency.py      # EmergencyManager + DMS
    paper_trading/engine.py # fills/partial/cancel/fees/inventory/PnL
    services/bot.py        # orchestrator + quote loop
    config/settings.py     # TRADING_MODE PAPER|TESTNET|LIVE
    database/db.py + models/tables.py # sessions/orders/fills/positions/market_data/pnl_records/risk_events/bot_events/daily_statistics
    monitoring/logger.py   # sanitize(), no API_SECRET in logs
  frontend/src/
    components/StatusCard, TradingModeBadge, VolumeCard, PnLCards, RiskDashboard, OrderTable, FillTable, BotControls
    charts/DashboardCharts (Recharts), pages/Dashboard, pages/Settings
  .env.example  .gitignore  pytest.ini
```

## Linux Mint 22.3 Install (beginner, step-by-step)

### 0) Check versions
```bash
python3 --version   # 3.12.3
node --version      # v18.19.1
~/.local/bin/npm --version  # 9.2.0 (if missing, see fix below)
```

**If `npm` missing** (Mint's `nodejs` package doesn't bundle it):
```bash
# already fixed via ~/.local/share/nodejs wrapper; else:
sudo apt install npm  # needs password, or use the wrapper at ~/.local/bin/npm
export PATH="$HOME/.local/bin:$PATH"
```

### 1) Enter project
```bash
cd ~/arcus-market-maker
```

### 2) Backend
```bash
python3 -m venv .venv  # already created at ./.venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # edit if needed; default PAPER is safe
# .env never committed (see .gitignore)
```

**No secrets needed for PAPER.** For TESTNET/LIVE, fill:
```
ARCUS_API_KEY=your 64-hex public key
ARCUS_API_SECRET=your 64-hex Ed25519 private (32 bytes hex) - NEVER share
ARCUS_ACCOUNT_ADDRESS=0x...
ARCUS_ACCOUNT_INDEX=0
```

### 3) Frontend
```bash
cd frontend
npm install
npm run build   # or npm run dev for Vite dev server
cd ..
```

### 4) Run backend + frontend
```bash
# Terminal 1: backend (port 8000)
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
# -> http://127.0.0.1:8000/api/health

# Terminal 2: frontend (port 5173)
cd frontend && npm run dev
# -> http://127.0.0.1:5173
```

### 5) Use PAPER mode (default)
- Open `http://127.0.0.1:5173`
- `TradingModeBadge` shows `PAPER · SAFE` (green)
- Click `START` → bot quotes synthetically, paper engine simulates fills (30% touch → no fake volume)
- Watch: Volume $1M card, PnL cards, charts, risk bars, order/fill tables update via `ws://127.0.0.1:8000/api/ws/dashboard` (2s push)
- `EMERGENCY STOP` → cancels all paper quotes, shows red `EMERGENCY`, requires `RESET EMERGENCY` to restart.

### 6) TESTNET (after PAPER works)
1) Get testnet key per https://docs.arcus.xyz/guides/rest-trading.md (Ed25519 gen + `POST /v1/createApiKey` EIP-712)
2) Fund via Arcus testnet app → **Testnet Deposit** (~$1k) or on-chain per https://docs.arcus.xyz/guides/fund-testnet-account.md
3) Set `.env`: `TRADING_MODE=TESTNET` + `ARCUS_TESTNET_REST_URL` + credentials
4) Restart backend, verify: `curl http://127.0.0.1:8000/api/analytics/risk`, place small `TESTNET` order via API, cancel, check fills/positions.

### 7) LIVE (only after PAPER+TESTNET ok)
1) Set `.env` `TRADING_MODE=LIVE` + mainnet creds, **conservative** `ORDER_SIZE=0.001`, `MAX_INVENTORY` low, `DMS=30s`
2) Start backend; dashboard `LIVE · CONFIRM REQUIRED` (red)
3) `START` → browser `confirm()` → backend requires `confirm_live=true` or 400. Never auto-starts.
4) Verify DMS refresh logs, rate-limit throttling, stale-data cancels.

### 8) Tests
```bash
source .venv/bin/activate
pytest -q                         # backend 17 tests
# new: fair value, spread, skew, profitability, paper, signer, trading_mode, health
npm --prefix frontend run build   # Vite prod build (~556kB → 159kB gzip)
```

### 9) Stop safely
```bash
# Dashboard: STOP or EMERGENCY STOP (cancels quotes)
# Or Ctrl+C backend; WS reconnects gracefully.
```

## Security
- `.env` is gitignored; never commit. `logger.sanitize()` redacts `api_secret/signature/private_key`.
- No wallet seed/mnemonic/private key requested. No withdrawals/transfers. Minimum trading permission only.
- Auth per https://docs.arcus.xyz/api-reference/authentication.md — `X-API-Key` (public), `X-Timestamp` (ns), `X-Signature` (128 hex Ed25519 over canonical payload). Scheme 1 for orders, Scheme 2 (`timestamp+action+canonical_json`) for cancelAll/DMS.

## API (backend → frontend)
`GET /api/health`, `GET /api/bot/status`, `POST /api/bot/{start,pause,stop,emergency-stop,reset-emergency}`, `GET /api/config/mode`, `GET /api/market/snapshot`, `GET /api/analytics/{status,volume,pnl,risk}`, `GET /api/{orders,fills}`, `GET|POST /api/config/settings`, `WS /api/ws/dashboard` (2s push).

## Volume & PnL
- Target `$1,000,000` notional, tracked **only** from actual fills (`sum(fill.notional)`), separated `paper/testnet/live`. Progress bar + daily/session. **Never** mix simulated with live.
- PnL: `gross - fees - funding - inventory_cost - adverse_selection` → `net`; metrics per $1k/$10k/$100k/$1M.

## Troubleshooting
- `npm: command not found` → `export PATH="$HOME/.local/bin:$PATH"` (wrapper at `~/.local/bin/npm`)
- Backend 400 on LIVE start → need `confirm_live=true` + `confirm()` dialog.
- `401` on Arcus → check `ARCUS_API_SECRET` is 64-hex Ed25519, `X-Timestamp` ns within ±30s, address lowercased.
- WS stale → check `ARCUS_WS_URL`, backend logs `MARKET_DATA_STALE`, frontend shows `STALE`.

## License
Private. Do not distribute secrets. See https://docs.arcus.xyz/llms.txt for Arcus source of truth.
