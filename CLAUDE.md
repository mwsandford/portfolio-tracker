# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Portfolio Tracker is a Flask web app for tracking live algorithmic trading performance across portfolios, accounts, and strategies. It's a single-user local tool (not deployed to production) running on Windows, backed by SQLite.

## Running the App

```bash
# Development (with auto-reload)
python app.py

# Production (Waitress WSGI server, port 5000)
python run_server.py

# Windows background service (no console window)
wscript start_hidden.vbs

# Service management (start/stop/restart/startup)
service_manager.bat
```

The app runs on `http://localhost:5000`. The database file is `PortfolioTracker.db` in the project root.

## Architecture

**Single-file Flask app** — all models, routes, and helpers are in `app.py`. There is no separate models file, no blueprints, no API versioning.

**Data model hierarchy:** Portfolio → Account → Strategy → Trade. Strategies also store backtest data (JSON blob), equity charts, and pseudo code imported from StrategyQuant X dashboard exports.

**Key models (all in `app.py`):**
- `Portfolio` — groups of trading accounts
- `Account` — broker accounts identified by login number
- `Strategy` — trading strategies with both live metrics (`Live*` columns) and backtest data (`BacktestData` JSON column)
- `Trade` — individual closed trades, imported via CSV from MT5
- `MarginData` — instrument margin requirements imported from MT5
- `Note` — rich-text notes using Quill editor
- `UserSettings` — key-value store for persistent UI settings

**Strategy matching:** Trades are matched to strategies by Magic Number first, then by normalised comment string (see `normalise_comment()`). Strategy names follow the pattern `SQ <SYMBOL> <TIMEFRAME> <version>` (e.g., `SQ XAUUSD H1 1.1.178_1_`).

**Live metrics recalculation:** On trade import (`_update_live_metrics()`), all `Live*` fields on Strategy are recalculated from trades — win rate, profit factor, Ret/DD, max consecutive losses, etc.

**Retire health system:** `_calc_retire_health()` compares live metrics against backtest data with configurable tolerance thresholds (stored in UserSettings). Status: grey (insufficient trades) → green → amber → red.

**Frontend:** Server-rendered Jinja2 templates with vanilla JS (`static/js/app.js`). Charts use Chart.js. Notes use the Quill rich-text editor. No build step, no npm, no bundler.

**Templates:** `base.html` provides the sidebar layout. All pages extend it. Pagination uses `pagination.html` include.

## Database

SQLite with Flask-SQLAlchemy. Schema migrations are manual `ALTER TABLE` statements in `init_db()`. All datetime columns are stored as text strings (`'%Y-%m-%d %H:%M:%S'`). There is no migration framework (no Alembic).

When adding new columns to existing tables, add a migration block in `init_db()` following the existing pattern (try SELECT, catch exception, ALTER TABLE).

## Conventions

- Column names use PascalCase (e.g., `StrategyName`, `LiveNetProfit`)
- Route functions use snake_case
- All monetary values are floats (AUD by default)
- Strategy status values: `'Demo'`, `'Running'`, `'Retired'`
- Market type values: `'Forex'`, `'Index'`, `'Commodity'`, `'Crypto'`
- The `BacktestData` column stores a JSON string containing `ranking`, `overview`, `strategy_profile`, `portfolio`, and `sqx_metadata` sub-objects