# QXAI — Advanced Trading Analysis (8 Agents)

Analysis-only trading system. **No automatic trade execution.**
No profit is promised; every signal is a rule-based score.

## Phases
- Phase 1 (this): repo skeleton, config, market-data adapter (Agent 1), tests.
- Phase 2: Agents 2-5 (trend, indicators, price action, structure).
- Phase 3: Agents 6-8 (risk, backtesting, validator) + orchestrator.
- Phase 4: mobile frontend (GitHub Pages) + cloudflared tunnel.
- Phase 5: Telegram notifications + SQLite history/performance.

## Android-only workflow
1. Create this repo on GitHub (web), add files with full paths.
2. Termux: `pkg install git -y && cd ~ && git clone https://github.com/rahulmondaljr-creator/qxai.git && cd qxai`
3. `pip install -r requirements.txt`
4. `cp .env.example .env` then `nano .env` (fill QX_EMAIL / QX_PASSWORD)
5. Stop your old bot first: `pkill -9 -f quotex` (only ONE Quotex connection at a time)
6. Test: `python -m pytest backend/tests -q`
7. Run: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
8. Expose HTTPS (new Termux session): `pkg install cloudflared -y` then `cloudflared tunnel --url http://localhost:8000` → copy the https://xxx.trycloudflare.com URL (changes each restart).
