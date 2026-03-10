"""
Portfolio Tracker - Flask Application
Tracks live trading performance across portfolios, accounts, and strategies.
"""

import os
import json
import re
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy

# ── App Configuration ──────────────────────────────────────────────────────────

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pt-dev-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "PortfolioTracker.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

db = SQLAlchemy(app)


# ── Context Processor: Sidebar Counts ──────────────────────────────────────────

@app.context_processor
def inject_sidebar_counts():
    """Inject entity counts into all templates for sidebar badges."""
    try:
        return {
            'portfolio_count': Portfolio.query.count(),
            'account_count': Account.query.count(),
            'strategy_count': Strategy.query.filter_by(Status='Running').count(),
            'retired_count': Strategy.query.filter_by(Status='Retired').count(),
            'trade_count': Trade.query.count(),
            'margin_count': MarginData.query.count(),
            'note_count': Note.query.count(),
            'today': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        }
    except Exception:
        return {
            'portfolio_count': 0,
            'account_count': 0,
            'strategy_count': 0,
            'retired_count': 0,
            'trade_count': 0,
            'margin_count': 0,
            'note_count': 0,
        }


@app.template_filter('strategy_profile')
def strategy_profile_filter(backtest_data_json):
    """Extract strategy_profile from BacktestData JSON string for use in templates."""
    if not backtest_data_json:
        return {}
    try:
        data = json.loads(backtest_data_json)
        return data.get('strategy_profile', {})
    except (json.JSONDecodeError, TypeError):
        return {}


@app.template_filter('days_active')
def days_active_filter(strategy):
    """Calculate days active from StartDate to today for Running strategies."""
    if strategy.Status != 'Running' or not strategy.StartDate:
        return 0
    try:
        start = datetime.strptime(strategy.StartDate, '%Y-%m-%d')
        delta = datetime.now(timezone.utc) - start
        return max(0, delta.days)
    except (ValueError, TypeError):
        return 0

# ── Models ─────────────────────────────────────────────────────────────────────

class Portfolio(db.Model):
    __tablename__ = 'Portfolios'

    PortfolioID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PortfolioName = db.Column(db.Text, nullable=False)
    Description = db.Column(db.Text)
    CreatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))

    accounts = db.relationship('Account', backref='portfolio', lazy=True)


class Account(db.Model):
    __tablename__ = 'Accounts'

    AccountID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AccountLogin = db.Column(db.Integer, nullable=False, unique=True)
    AccountName = db.Column(db.Text)
    Broker = db.Column(db.Text)
    Currency = db.Column(db.Text, default='AUD')
    InitialBalance = db.Column(db.Float, default=0)
    PortfolioID = db.Column(db.Integer, db.ForeignKey('Portfolios.PortfolioID'))
    CreatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))

    strategies = db.relationship('Strategy', backref='account', lazy=True)


class Strategy(db.Model):
    __tablename__ = 'Strategies'

    StrategyID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StrategyName = db.Column(db.Text, nullable=False)
    DisplayName = db.Column(db.Text)
    Symbol = db.Column(db.Text)
    Timeframe = db.Column(db.Text)
    Direction = db.Column(db.Text)
    Style = db.Column(db.Text)
    MagicNumber = db.Column(db.Integer)
    AccountID = db.Column(db.Integer, db.ForeignKey('Accounts.AccountID'))
    Status = db.Column(db.Text, default='Demo')
    StartDate = db.Column(db.Text)
    Complexity = db.Column(db.Integer)
    Market = db.Column(db.Text)
    Notes = db.Column(db.Text)

    # Live performance metrics
    LiveNetProfit = db.Column(db.Float, default=0)
    LiveTotalTrades = db.Column(db.Integer, default=0)
    LiveWinRate = db.Column(db.Float, default=0)
    LiveProfitFactor = db.Column(db.Float, default=0)
    LiveSharpe = db.Column(db.Float, default=0)
    LiveRetDD = db.Column(db.Float, default=0)
    LiveWLRatio = db.Column(db.Float, default=0)
    LiveRecovery = db.Column(db.Float, default=0)
    LiveLRCorrelation = db.Column(db.Float, default=0)
    LiveMaxDDDollars = db.Column(db.Float, default=0)
    LiveMaxDDPct = db.Column(db.Float, default=0)
    LiveExpectedPayoff = db.Column(db.Float, default=0)
    LiveAvgWin = db.Column(db.Float, default=0)
    LiveAvgLoss = db.Column(db.Float, default=0)
    LiveLongTrades = db.Column(db.Integer, default=0)
    LiveShortTrades = db.Column(db.Integer, default=0)
    LiveMaxConsecLosses = db.Column(db.Integer, default=0)
    LiveLastTradeDate = db.Column(db.Text)
    LiveDaysTrading = db.Column(db.Integer, default=0)
    LiveMetricsUpdatedAt = db.Column(db.Text)

    # Backtest data from dashboard export
    BacktestData = db.Column(db.Text)
    BacktestEquityChart = db.Column(db.Text)
    PseudoCode = db.Column(db.Text)
    BacktestImportedAt = db.Column(db.Text)

    RetiredReason = db.Column(db.Text)

    CreatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
    UpdatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))

    trades = db.relationship('Trade', backref='strategy', lazy=True)


class Trade(db.Model):
    __tablename__ = 'Trades'

    TradeID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Ticket = db.Column(db.Integer, nullable=False, unique=True)
    StrategyID = db.Column(db.Integer, db.ForeignKey('Strategies.StrategyID'))
    Symbol = db.Column(db.Text)
    Type = db.Column(db.Text)
    Lots = db.Column(db.Float)
    OpenPrice = db.Column(db.Float)
    ClosePrice = db.Column(db.Float)
    OpenTime = db.Column(db.Text)
    CloseTime = db.Column(db.Text)
    Profit = db.Column(db.Float)
    Swap = db.Column(db.Float)
    Commission = db.Column(db.Float)
    NetProfit = db.Column(db.Float)
    TP = db.Column(db.Float)
    SL = db.Column(db.Float)
    Pips = db.Column(db.Float)
    MagicNumber = db.Column(db.Integer)
    Comment = db.Column(db.Text)
    BalanceAfter = db.Column(db.Float)
    ImportedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


class UserSettings(db.Model):
    __tablename__ = 'UserSettings'

    SettingKey = db.Column(db.Text, primary_key=True)
    SettingValue = db.Column(db.Text)
    UpdatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


class MarginData(db.Model):
    __tablename__ = 'MarginData'

    MarginID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Symbol = db.Column(db.Text, nullable=False)
    SymbolClean = db.Column(db.Text)            # Symbol without broker suffix (e.g. USDJPY)
    Type = db.Column(db.Text)                   # Forex, CFD/Index, Commodity, Crypto, Other
    Bid = db.Column(db.Float)
    Ask = db.Column(db.Float)
    ContractSize = db.Column(db.Float)
    LotSize = db.Column(db.Float)
    MinLot = db.Column(db.Float)
    MaxLot = db.Column(db.Float)
    LotStep = db.Column(db.Float)
    AccountLeverage = db.Column(db.Integer)
    MarginRequired = db.Column(db.Float)        # In account currency (AUD)
    MarginCurrency = db.Column(db.Text)
    BaseCurrency = db.Column(db.Text)
    ProfitCurrency = db.Column(db.Text)
    AccountCurrency = db.Column(db.Text)
    AccountLogin = db.Column(db.Integer)
    Spread = db.Column(db.Float)
    SpreadPoints = db.Column(db.Integer)
    TickSize = db.Column(db.Float)
    TickValue = db.Column(db.Float)
    ExportTime = db.Column(db.Text)
    ImportedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


class Note(db.Model):
    __tablename__ = 'Notes'

    NoteID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.Text, nullable=False)
    Content = db.Column(db.Text)           # Rich HTML content from Quill editor
    CreatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
    UpdatedAt = db.Column(db.Text, default=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


# ── Helper Functions ───────────────────────────────────────────────────────────

PER_PAGE = 25


def paginate_query(query, page=None):
    """Paginate a SQLAlchemy query. Returns (items, pagination_info) dict."""
    if page is None:
        page = request.args.get('page', 1, type=int)
    page = max(1, page)

    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, pages)

    items = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    pagination = {
        'page': page,
        'per_page': PER_PAGE,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
    }

    class PaginationObj:
        pass
    obj = PaginationObj()
    for k, v in pagination.items():
        setattr(obj, k, v)

    return items, obj


def paginate_list(items_list, page=None):
    """Paginate a plain Python list. Returns (page_items, pagination_info)."""
    if page is None:
        page = request.args.get('page', 1, type=int)
    page = max(1, page)

    total = len(items_list)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, pages)

    start = (page - 1) * PER_PAGE
    page_items = items_list[start:start + PER_PAGE]

    class PaginationObj:
        pass
    obj = PaginationObj()
    obj.page = page
    obj.per_page = PER_PAGE
    obj.total = total
    obj.pages = pages
    obj.has_prev = page > 1
    obj.has_next = page < pages

    return page_items, obj

def get_setting(key, default=None):
    """Get a user setting value by key."""
    setting = UserSettings.query.get(key)
    return setting.SettingValue if setting else default


def set_setting(key, value):
    """Set a user setting value."""
    setting = UserSettings.query.get(key)
    if setting:
        setting.SettingValue = value
        setting.UpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    else:
        setting = UserSettings(SettingKey=key, SettingValue=value)
        db.session.add(setting)
    db.session.commit()


def normalise_comment(name):
    """
    Normalise a strategy name or MT5 comment to a canonical form for matching.
    Handles both formats:
        Strategy name: 'SQ XAUUSD H1 1.1.178_1_'  -> 'SQ_XAUUSD_H1_1_1_178_1'
        MT5 comment:   'SQ_XAUUSD_H1_1_1_178_1'   -> 'SQ_XAUUSD_H1_1_1_178_1'
    """
    return name.replace(' ', '_').replace('.', '_').strip('_')


def parse_strategy_name(name):
    """
    Parse a StrategyQuant strategy name like 'SQ NAS100 H1 2.2.128'
    into its component parts: symbol, timeframe, and magic number.

    Also handles suffixed names like 'SQ NAS100 H1 2.1.148_1_' where
    the suffix is appended to the magic number: 2.1.148_1_ -> 211481
    """
    result = {'symbol': None, 'timeframe': None, 'magic_number': None}

    # Pattern: SQ <SYMBOL> <TIMEFRAME> <version>[_suffix]
    match = re.match(r'^SQ\s+(\S+)\s+(M\d+|H\d+|D\d+|W\d+)\s+([\d.]+(?:_\d+)?_?)$', name)
    if match:
        result['symbol'] = match.group(1)
        result['timeframe'] = match.group(2)

        # Derive magic number from version: 2.2.128 -> 22128, 2.1.148_1_ -> 211481
        version = match.group(3)
        magic = version.replace('.', '').replace('_', '')
        if magic.isdigit():
            result['magic_number'] = int(magic)

    return result


def clean_pseudo_code(text):
    """
    Remove HTML artifacts that may bleed into pseudo code when exported
    from the dashboard. The dashboard uses inline styles like:
      <span style="font-weight:600;">  and  <span style="font-weight:700; font-size:13px;">
    which can leave behind fragments like '600;">' or '700; font-size:13px;">'
    """
    if not text:
        return text

    # Remove patterns: 600;"> or 700; font-size:13px;"> (CSS weight artifacts)
    text = re.sub(r'[67]00;(?:\s*font-size:\d+px;)?\s*">', '', text)
    # Clean up any double spaces left behind
    text = re.sub(r'  +', ' ', text)

    return text


def parse_export_json(data):
    """
    Parse the dashboard export JSON and extract fields for the Strategy record.
    Returns a dict of fields ready to populate the Strategy model.
    """
    pseudo_code = data.get('pseudo_code')
    pseudo_code = clean_pseudo_code(pseudo_code)

    fields = {
        'StrategyName': data.get('strategy_name', ''),
        'BacktestData': json.dumps(data.get('backtest_data')) if data.get('backtest_data') else None,
        'BacktestEquityChart': data.get('backtest_equitychart'),
        'PseudoCode': pseudo_code,
        'BacktestImportedAt': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
    }

    # Parse symbol, timeframe, magic number from strategy name
    parsed = parse_strategy_name(fields['StrategyName'])
    fields['Symbol'] = parsed['symbol']
    fields['Timeframe'] = parsed['timeframe']
    fields['MagicNumber'] = parsed['magic_number']

    # Extract direction and style from strategy profile
    backtest = data.get('backtest_data', {})
    profile = backtest.get('strategy_profile') if backtest else None
    if profile:
        fields['Direction'] = profile.get('direction')
        fields['Style'] = profile.get('style')

    # Extract complexity from SQX metadata
    sqx_meta = backtest.get('sqx_metadata') if backtest else None
    if sqx_meta and sqx_meta.get('complexity') is not None:
        fields['Complexity'] = sqx_meta.get('complexity')

    return fields


# ── Routes: Dashboard ──────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    """Main dashboard with summary stats and portfolio equity chart.
    Always includes all strategies (Running + Retired) to reflect true account performance."""
    portfolios = Portfolio.query.all()

    all_strategies = Strategy.query.filter(
        Strategy.Status.in_(['Running', 'Retired'])
    ).all()

    total_pnl = sum(s.LiveNetProfit or 0 for s in all_strategies)
    total_trades = sum(s.LiveTotalTrades or 0 for s in all_strategies)

    total_wins = 0
    total_counted = 0
    for s in all_strategies:
        if s.LiveTotalTrades and s.LiveTotalTrades > 0 and s.LiveWinRate is not None:
            wins = round(s.LiveWinRate / 100 * s.LiveTotalTrades)
            total_wins += wins
            total_counted += s.LiveTotalTrades
    overall_win_rate = (total_wins / total_counted * 100) if total_counted > 0 else 0

    return render_template('dashboard.html',
        portfolios=portfolios,
        dashboard_strategy_count=len(all_strategies),
        total_pnl=total_pnl,
        total_trades=total_trades,
        overall_win_rate=overall_win_rate,
    )


# ── Routes: Portfolios ────────────────────────────────────────────────────────

@app.route('/portfolios')
def portfolios():
    """List all portfolios. Always includes all strategies to reflect true account performance."""
    all_portfolios = Portfolio.query.order_by(Portfolio.CreatedAt.desc()).all()

    # Enrich with counts and P&L
    portfolio_data = []
    for p in all_portfolios:
        accts = Account.query.filter_by(PortfolioID=p.PortfolioID).all()
        acct_ids = [a.AccountID for a in accts]
        if acct_ids:
            strats = Strategy.query.filter(Strategy.AccountID.in_(acct_ids)).all()
        else:
            strats = []
        pnl = sum(s.LiveNetProfit or 0 for s in strats)

        # Also include unassigned strategies (e.g. retired with no account)
        unassigned = Strategy.query.filter(
            Strategy.AccountID.is_(None)
        ).all()
        pnl += sum(s.LiveNetProfit or 0 for s in unassigned)

        portfolio_data.append({
            'portfolio': p,
            'account_count': len(accts),
            'strategy_count': len(strats),
            'total_pnl': pnl,
        })

    return render_template('portfolios.html',
        portfolio_data=portfolio_data,
    )


@app.route('/portfolios/add', methods=['POST'])
def add_portfolio():
    """Create a new portfolio."""
    name = request.form.get('portfolio_name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Portfolio name is required.', 'error')
        return redirect(url_for('portfolios'))

    # Check for duplicate name
    existing = Portfolio.query.filter_by(PortfolioName=name).first()
    if existing:
        flash(f'Portfolio "{name}" already exists.', 'error')
        return redirect(url_for('portfolios'))

    portfolio = Portfolio(PortfolioName=name, Description=description or None)
    db.session.add(portfolio)
    db.session.commit()
    flash(f'Portfolio "{name}" created successfully.', 'success')
    return redirect(url_for('portfolios'))


@app.route('/portfolios/<int:portfolio_id>/edit', methods=['POST'])
def edit_portfolio(portfolio_id):
    """Update an existing portfolio."""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    portfolio.PortfolioName = request.form.get('portfolio_name', portfolio.PortfolioName).strip()
    portfolio.Description = request.form.get('description', '').strip() or None
    db.session.commit()
    flash(f'Portfolio "{portfolio.PortfolioName}" updated.', 'success')
    return redirect(url_for('portfolios'))


@app.route('/portfolios/<int:portfolio_id>/delete', methods=['POST'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio (only if no accounts are linked)."""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    linked_accounts = Account.query.filter_by(PortfolioID=portfolio_id).count()
    if linked_accounts > 0:
        flash(f'Cannot delete "{portfolio.PortfolioName}" — it has {linked_accounts} linked account(s).', 'error')
        return redirect(url_for('portfolios'))

    name = portfolio.PortfolioName
    db.session.delete(portfolio)
    db.session.commit()
    flash(f'Portfolio "{name}" deleted.', 'success')
    return redirect(url_for('portfolios'))


# ── Routes: Accounts ──────────────────────────────────────────────────────────

@app.route('/accounts')
def accounts():
    """List all accounts."""
    all_accounts = Account.query.order_by(Account.CreatedAt.desc()).all()
    all_portfolios = Portfolio.query.order_by(Portfolio.PortfolioName).all()

    account_data = []
    for a in all_accounts:
        strat_count = Strategy.query.filter_by(AccountID=a.AccountID).count()
        account_data.append({
            'account': a,
            'strategy_count': strat_count,
        })

    return render_template('accounts.html',
        account_data=account_data,
        portfolios=all_portfolios,
    )


@app.route('/accounts/add', methods=['POST'])
def add_account():
    """Create a new account."""
    login = request.form.get('account_login', '').strip()
    name = request.form.get('account_name', '').strip()
    broker = request.form.get('broker', '').strip()
    currency = request.form.get('currency', 'AUD').strip()
    initial_balance = request.form.get('initial_balance', 0)
    portfolio_id = request.form.get('portfolio_id')

    if not login:
        flash('Account login is required.', 'error')
        return redirect(url_for('accounts'))

    try:
        login_int = int(login)
    except ValueError:
        flash('Account login must be a number.', 'error')
        return redirect(url_for('accounts'))

    # Check for duplicate login
    existing = Account.query.filter_by(AccountLogin=login_int).first()
    if existing:
        flash(f'Account with login {login_int} already exists.', 'error')
        return redirect(url_for('accounts'))

    account = Account(
        AccountLogin=login_int,
        AccountName=name or None,
        Broker=broker or None,
        Currency=currency,
        InitialBalance=float(initial_balance) if initial_balance else 0,
        PortfolioID=int(portfolio_id) if portfolio_id else None,
    )
    db.session.add(account)
    db.session.commit()
    flash(f'Account "{name or login}" added successfully.', 'success')
    return redirect(url_for('accounts'))


@app.route('/accounts/<int:account_id>/edit', methods=['POST'])
def edit_account(account_id):
    """Update an existing account."""
    account = Account.query.get_or_404(account_id)
    account.AccountName = request.form.get('account_name', '').strip() or None
    account.Broker = request.form.get('broker', '').strip() or None
    account.Currency = request.form.get('currency', 'AUD').strip()
    account.InitialBalance = float(request.form.get('initial_balance', 0) or 0)
    portfolio_id = request.form.get('portfolio_id')
    account.PortfolioID = int(portfolio_id) if portfolio_id else None
    db.session.commit()
    flash(f'Account "{account.AccountName or account.AccountLogin}" updated.', 'success')
    return redirect(url_for('accounts'))


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """Delete an account (only if no strategies are linked)."""
    account = Account.query.get_or_404(account_id)
    linked_strategies = Strategy.query.filter_by(AccountID=account_id).count()
    if linked_strategies > 0:
        flash(f'Cannot delete "{account.AccountName or account.AccountLogin}" — it has {linked_strategies} linked strategy(ies).', 'error')
        return redirect(url_for('accounts'))

    name = account.AccountName or str(account.AccountLogin)
    db.session.delete(account)
    db.session.commit()
    flash(f'Account "{name}" deleted.', 'success')
    return redirect(url_for('accounts'))


# ── Routes: Strategies ────────────────────────────────────────────────────────

@app.route('/strategies')
def strategies():
    """List all running strategies, optionally filtered by account, market, and symbol."""
    # Get account filter from query param, or fall back to saved setting
    account_filter = request.args.get('account')
    if account_filter is not None:
        # User explicitly changed the filter — save it
        set_setting('strategies_account_filter', account_filter)
    else:
        # No param — use saved setting
        account_filter = get_setting('strategies_account_filter', 'all')

    market_filter = request.args.get('market', 'all')
    symbol_filter = request.args.get('symbol', 'all')
    sort_by = request.args.get('sort', 'CreatedAt')
    sort_dir = request.args.get('dir', 'desc')
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    # Whitelist sortable columns
    sort_columns = {
        'Strategy': Strategy.StrategyName,
        'Account': Account.AccountName,
        'Market': Strategy.Market,
        'StartDate': Strategy.StartDate,
        'Complexity': Strategy.Complexity,
        'NetPL': Strategy.LiveNetProfit,
        'Trades': Strategy.LiveTotalTrades,
        'WinPct': Strategy.LiveWinRate,
        'PF': Strategy.LiveProfitFactor,
        'RetDD': Strategy.LiveRetDD,
        'Sharpe': Strategy.LiveSharpe,
        'CreatedAt': Strategy.CreatedAt,
    }

    query = Strategy.query.filter_by(Status='Running')
    if account_filter != 'all':
        try:
            query = query.filter_by(AccountID=int(account_filter))
        except (ValueError, TypeError):
            account_filter = 'all'

    if market_filter != 'all':
        query = query.filter_by(Market=market_filter)

    if symbol_filter != 'all':
        query = query.filter(Strategy.Symbol == symbol_filter)

    # Apply sort — join Account if sorting by account name
    sort_col = sort_columns.get(sort_by, Strategy.CreatedAt)
    if sort_by == 'Account':
        query = query.outerjoin(Account)
    order = sort_col.asc() if sort_dir == 'asc' else sort_col.desc()
    all_strategies = query.order_by(order)
    strategies, pagination = paginate_query(all_strategies)
    all_accounts = Account.query.order_by(Account.AccountName).all()

    # Build account counts for the dropdown
    account_counts = {'all': Strategy.query.filter_by(Status='Running').count()}
    for a in all_accounts:
        account_counts[str(a.AccountID)] = Strategy.query.filter_by(Status='Running', AccountID=a.AccountID).count()

    # Get distinct market types for filter buttons
    market_types = [r[0] for r in db.session.query(Strategy.Market).filter(
        Strategy.Status == 'Running', Strategy.Market.isnot(None)
    ).distinct().order_by(Strategy.Market).all()]

    # Get distinct symbols for dropdown (filtered by market if active)
    symbol_query = Strategy.query.filter(Strategy.Status == 'Running', Strategy.Symbol.isnot(None))
    if market_filter != 'all':
        symbol_query = symbol_query.filter_by(Market=market_filter)
    symbols = [r[0] for r in symbol_query.with_entities(Strategy.Symbol).distinct().order_by(Strategy.Symbol).all()]

    # Calculate retire health for each strategy
    health_map = {}
    for s in strategies:
        health_map[s.StrategyID] = _calc_retire_health(s)

    # Calculate filtered net profit from LiveNetProfit on strategies
    profit_query = db.session.query(db.func.coalesce(db.func.sum(Strategy.LiveNetProfit), 0)).filter(Strategy.Status == 'Running')
    if account_filter != 'all':
        try:
            profit_query = profit_query.filter(Strategy.AccountID == int(account_filter))
        except (ValueError, TypeError):
            pass
    if market_filter != 'all':
        profit_query = profit_query.filter(Strategy.Market == market_filter)
    if symbol_filter != 'all':
        profit_query = profit_query.filter(Strategy.Symbol == symbol_filter)
    filtered_net_profit = profit_query.scalar() or 0

    return render_template('strategies.html',
        strategies=strategies,
        accounts=all_accounts,
        account_filter=account_filter,
        account_counts=account_counts,
        pagination=pagination,
        health_map=health_map,
        market_filter=market_filter,
        market_types=market_types,
        symbol_filter=symbol_filter,
        symbols=symbols,
        filtered_net_profit=filtered_net_profit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@app.route('/complexity')
def complexity_analysis():
    """Complexity analysis page: NET P&L grouped by Complexity value per account."""
    account_filter = request.args.get('account', 'all')

    all_accounts = Account.query.order_by(Account.AccountName).all()

    # Query all Running + Retired strategies that have a Complexity value
    query = Strategy.query.filter(
        Strategy.Status.in_(['Running', 'Retired']),
        Strategy.Complexity.isnot(None)
    )
    if account_filter != 'all':
        try:
            query = query.filter_by(AccountID=int(account_filter))
        except (ValueError, TypeError):
            account_filter = 'all'

    strategies = query.all()

    # Group by Complexity and aggregate NET P&L
    complexity_map = {}
    for s in strategies:
        c = s.Complexity
        acct_name = s.account.AccountName if s.account else 'Unassigned'
        key = (c, acct_name)
        if key not in complexity_map:
            complexity_map[key] = {'complexity': c, 'account': acct_name, 'net_pnl': 0, 'strategy_count': 0}
        complexity_map[key]['net_pnl'] += (s.LiveNetProfit or 0)
        complexity_map[key]['strategy_count'] += 1

    rows = sorted(complexity_map.values(), key=lambda r: r['complexity'])

    return render_template('complexity.html',
        rows=rows,
        accounts=all_accounts,
        account_filter=account_filter,
    )


# ── Notes ─────────────────────────────────────────────────────────────────────

@app.route('/notes')
def notes_page():
    """Notes page with master/detail layout."""
    notes = Note.query.order_by(Note.UpdatedAt.desc()).all()
    selected_id = request.args.get('id', type=int)

    selected_note = None
    if selected_id:
        selected_note = Note.query.get(selected_id)
    elif notes:
        selected_note = notes[0]

    return render_template('notes.html',
        notes=notes,
        selected_note=selected_note,
    )


@app.route('/notes/add', methods=['POST'])
def add_note():
    """Create a new note."""
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if not title:
        flash('Note title is required.', 'error')
        return redirect(url_for('notes_page'))

    note = Note(Title=title, Content=content)
    db.session.add(note)
    db.session.commit()

    flash(f'Note "{title}" created.', 'success')
    return redirect(url_for('notes_page', id=note.NoteID))


@app.route('/notes/<int:note_id>/edit', methods=['POST'])
def edit_note(note_id):
    """Update an existing note."""
    note = Note.query.get_or_404(note_id)
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if title:
        note.Title = title
    note.Content = content
    note.UpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db.session.commit()

    flash(f'Note "{note.Title}" updated.', 'success')
    return redirect(url_for('notes_page', id=note.NoteID))


@app.route('/notes/<int:note_id>/delete', methods=['POST'])
def delete_note(note_id):
    """Delete a note."""
    note = Note.query.get_or_404(note_id)
    title = note.Title
    db.session.delete(note)
    db.session.commit()

    flash(f'Note "{title}" deleted.', 'success')
    return redirect(url_for('notes_page'))


@app.route('/retired')
def retired():
    """List all retired strategies."""
    sort_by = request.args.get('sort', 'UpdatedAt')
    sort_dir = request.args.get('dir', 'desc')
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    sort_columns = {
        'Strategy': Strategy.StrategyName,
        'Account': Account.AccountName,
        'StartDate': Strategy.StartDate,
        'FinalPL': Strategy.LiveNetProfit,
        'Trades': Strategy.LiveTotalTrades,
        'WinPct': Strategy.LiveWinRate,
        'PF': Strategy.LiveProfitFactor,
        'Reason': Strategy.RetiredReason,
        'UpdatedAt': Strategy.UpdatedAt,
    }

    query = Strategy.query.filter_by(Status='Retired')

    sort_col = sort_columns.get(sort_by, Strategy.UpdatedAt)
    if sort_by == 'Account':
        query = query.outerjoin(Account)
    order = sort_col.asc() if sort_dir == 'asc' else sort_col.desc()
    query = query.order_by(order)

    strategies, pagination = paginate_query(query)
    all_accounts = Account.query.order_by(Account.AccountName).all()

    return render_template('retired.html',
        strategies=strategies,
        accounts=all_accounts,
        pagination=pagination,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@app.route('/retired/<int:strategy_id>/reactivate', methods=['POST'])
def reactivate_strategy(strategy_id):
    """Reactivate a retired strategy back to Running."""
    strategy = Strategy.query.get_or_404(strategy_id)
    strategy.Status = 'Running'
    strategy.RetiredReason = None
    strategy.UpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db.session.commit()
    flash(f'Strategy "{strategy.StrategyName}" reactivated.', 'success')
    return redirect(url_for('retired'))


@app.route('/retired/<int:strategy_id>/edit', methods=['POST'])
def edit_retired(strategy_id):
    """Update the retired reason for a strategy."""
    strategy = Strategy.query.get_or_404(strategy_id)
    strategy.RetiredReason = request.form.get('retired_reason', '').strip() or None
    strategy.UpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db.session.commit()
    flash(f'Strategy "{strategy.StrategyName}" updated.', 'success')
    return redirect(url_for('retired'))


@app.route('/strategies/symbols')
def strategy_symbols():
    """Return distinct symbols for running strategies, optionally filtered by market."""
    market = request.args.get('market', 'all')
    q = Strategy.query.filter(Strategy.Status == 'Running', Strategy.Symbol.isnot(None))
    if market != 'all':
        q = q.filter_by(Market=market)
    symbols = [r[0] for r in q.with_entities(Strategy.Symbol).distinct().order_by(Strategy.Symbol).all()]
    return {'symbols': symbols}


@app.route('/strategies/add', methods=['POST'])
def add_strategy():
    """Add a strategy from a dashboard export JSON file."""
    file = request.files.get('export_file')

    if not file or not file.filename:
        flash('Please upload a dashboard export JSON file.', 'error')
        return redirect(url_for('strategies'))

    try:
        data = json.loads(file.read().decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        flash(f'Invalid JSON file: {e}', 'error')
        return redirect(url_for('strategies'))

    # Parse the export JSON
    fields = parse_export_json(data)

    # Check for duplicate strategy name
    existing = Strategy.query.filter_by(StrategyName=fields['StrategyName']).first()
    if existing:
        flash(f'Strategy "{fields["StrategyName"]}" already exists.', 'error')
        return redirect(url_for('strategies'))

    # Get form fields
    display_name = request.form.get('display_name', '').strip()
    account_id = request.form.get('account_id')
    status = request.form.get('status', 'Running')
    start_date = request.form.get('start_date', '')
    notes = request.form.get('notes', '').strip()
    market = request.form.get('market', '').strip() or None

    strategy = Strategy(
        StrategyName=fields['StrategyName'],
        DisplayName=display_name or None,
        Symbol=fields.get('Symbol'),
        Timeframe=fields.get('Timeframe'),
        Direction=fields.get('Direction'),
        Style=fields.get('Style'),
        MagicNumber=fields.get('MagicNumber'),
        AccountID=int(account_id) if account_id else None,
        Status=status,
        StartDate=start_date or None,
        Complexity=fields.get('Complexity'),
        Market=market,
        Notes=notes or None,
        BacktestData=fields.get('BacktestData'),
        BacktestEquityChart=fields.get('BacktestEquityChart'),
        PseudoCode=fields.get('PseudoCode'),
        BacktestImportedAt=fields.get('BacktestImportedAt'),
    )
    db.session.add(strategy)
    db.session.commit()
    flash(f'Strategy "{fields["StrategyName"]}" imported successfully.', 'success')
    return redirect(url_for('strategies'))


@app.route('/strategies/parse-export', methods=['POST'])
def parse_export():
    """
    AJAX endpoint: parse a dashboard export JSON and return the extracted fields.
    Used by the Add Strategy modal to auto-populate fields before submission.
    """
    file = request.files.get('export_file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    try:
        data = json.loads(file.read().decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return jsonify({'error': f'Invalid JSON: {e}'}), 400

    fields = parse_export_json(data)

    # Also extract composite score for display
    backtest = data.get('backtest_data', {})
    ranking = backtest.get('ranking') if backtest else None
    composite_score = ranking.get('composite_score') if ranking else None

    return jsonify({
        'strategy_name': fields.get('StrategyName', ''),
        'symbol': fields.get('Symbol', ''),
        'timeframe': fields.get('Timeframe', ''),
        'direction': fields.get('Direction', ''),
        'style': fields.get('Style', ''),
        'magic_number': fields.get('MagicNumber', ''),
        'composite_score': composite_score,
        'complexity': fields.get('Complexity'),
        'market': _lookup_market_for_symbol(fields.get('Symbol', '')),
        'has_backtest_data': fields.get('BacktestData') is not None,
        'has_equity_chart': fields.get('BacktestEquityChart') is not None,
        'has_pseudo_code': fields.get('PseudoCode') is not None,
    })


@app.route('/strategies/<int:strategy_id>/edit', methods=['POST'])
def edit_strategy(strategy_id):
    """Update an existing strategy."""
    strategy = Strategy.query.get_or_404(strategy_id)
    strategy.DisplayName = request.form.get('display_name', '').strip() or None
    strategy.Status = request.form.get('status', strategy.Status)
    strategy.Notes = request.form.get('notes', '').strip() or None

    # Save retired reason if retiring
    retired_reason = request.form.get('retired_reason')
    if retired_reason is not None:
        strategy.RetiredReason = retired_reason.strip() or None

    account_id = request.form.get('account_id')
    strategy.AccountID = int(account_id) if account_id else None

    start_date = request.form.get('start_date', '')
    strategy.StartDate = start_date or strategy.StartDate

    strategy.UpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db.session.commit()

    if strategy.Status == 'Retired':
        flash(f'Strategy "{strategy.StrategyName}" retired.', 'success')
        return redirect(url_for('retired'))
    else:
        flash(f'Strategy "{strategy.StrategyName}" updated.', 'success')
        return redirect(url_for('strategies'))


@app.route('/strategies/<int:strategy_id>/delete', methods=['POST'])
def delete_strategy(strategy_id):
    """Delete a strategy (only if no trades are linked)."""
    strategy = Strategy.query.get_or_404(strategy_id)
    linked_trades = Trade.query.filter_by(StrategyID=strategy_id).count()
    if linked_trades > 0:
        flash(f'Cannot delete "{strategy.StrategyName}" — it has {linked_trades} linked trade(s).', 'error')
        return redirect(url_for('strategies'))

    name = strategy.StrategyName
    db.session.delete(strategy)
    db.session.commit()
    flash(f'Strategy "{name}" deleted.', 'success')
    return redirect(url_for('strategies'))


@app.route('/strategies/<int:strategy_id>/backtest')
def strategy_backtest(strategy_id):
    """View backtest data for a strategy (JSON API)."""
    strategy = Strategy.query.get_or_404(strategy_id)
    backtest = json.loads(strategy.BacktestData) if strategy.BacktestData else {}
    return jsonify({
        'strategy_name': strategy.StrategyName,
        'ranking': backtest.get('ranking'),
        'overview': backtest.get('overview'),
        'strategy_profile': backtest.get('strategy_profile'),
        'portfolio': backtest.get('portfolio'),
        'equity_chart': strategy.BacktestEquityChart,
        'imported_at': strategy.BacktestImportedAt,
    })


@app.route('/strategies/<int:strategy_id>/pseudocode')
def strategy_pseudocode(strategy_id):
    """Return the pseudo code text for a strategy (JSON API)."""
    strategy = Strategy.query.get_or_404(strategy_id)
    return jsonify({
        'strategy_name': strategy.StrategyName,
        'pseudo_code': clean_pseudo_code(strategy.PseudoCode),
    })


@app.route('/strategies/backtest-correlation')
def backtest_correlation():
    """Compute pairwise monthly correlation from backtest data for running strategies."""
    account_filter = request.args.get('account', 'all')

    query = Strategy.query.filter_by(Status='Running').filter(Strategy.BacktestData.isnot(None))
    if account_filter != 'all':
        try:
            query = query.filter_by(AccountID=int(account_filter))
        except (ValueError, TypeError):
            pass

    strategies = query.order_by(Strategy.StrategyName).all()

    if len(strategies) < 2:
        return jsonify({'error': 'Need at least 2 strategies with backtest data', 'strategies': len(strategies)})

    # Build monthly PnL series from stored backtest data
    names = []
    full_names = {}  # short_name -> full StrategyName
    monthly_series = {}

    for s in strategies:
        data = json.loads(s.BacktestData)
        monthly_pnl = data.get('overview', {}).get('monthly_pnl', {})
        if not monthly_pnl:
            continue

        name = s.StrategyName
        # Strip common prefix for shorter display names
        short = name.split(' ')
        short_name = '.'.join(short[-1].split('.')) if len(short) > 3 else name
        names.append(short_name)
        full_names[short_name] = name

        # Flatten year/month dict into a time series
        series = {}
        for year_str, months in sorted(monthly_pnl.items()):
            for month_str, value in months.items():
                if month_str == 'ytd':
                    continue
                key = f"{year_str}-{int(month_str):02d}"
                series[key] = value if value != 0 else None  # treat 0 as no activity

        monthly_series[short_name] = series

    if len(names) < 2:
        return jsonify({'error': 'Need at least 2 strategies with monthly PnL data', 'strategies': len(names)})

    # Build DataFrame — all months across all strategies
    all_months = sorted(set().union(*[s.keys() for s in monthly_series.values()]))
    import pandas as pd
    df = pd.DataFrame(index=all_months)
    for name in names:
        df[name] = pd.Series(monthly_series[name])

    # Compute pairwise correlation excluding mutual-NaN months
    n = len(names)
    matrix = []
    min_obs = 6

    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            else:
                s1 = df[names[i]]
                s2 = df[names[j]]
                # Include months where at least one strategy had activity
                active_mask = s1.notna() | s2.notna()
                s1_active = s1[active_mask].fillna(0)
                s2_active = s2[active_mask].fillna(0)

                if len(s1_active) >= min_obs:
                    corr_val = s1_active.corr(s2_active)
                    corr_val = 0.0 if pd.isna(corr_val) else round(float(corr_val), 3)
                else:
                    corr_val = 0.0
                row.append(corr_val)
        matrix.append(row)

    # Identify clusters (same logic as correlation analysis script)
    threshold = 0.5
    clusters = []
    assigned = set()
    for i, name in enumerate(names):
        if name in assigned:
            continue
        cluster = [name]
        assigned.add(name)
        for j, other in enumerate(names):
            if other in assigned:
                continue
            if abs(matrix[i][j]) >= threshold:
                cluster.append(other)
                assigned.add(other)
        clusters.append(cluster)

    return jsonify({
        'names': names,
        'full_names': full_names,
        'matrix': matrix,
        'clusters': [{'id': i + 1, 'members': c} for i, c in enumerate(clusters)],
        'strategy_count': len(names),
        'months_covered': len(all_months),
    })


# ── Routes: Retire Metrics ────────────────────────────────────────────────────

@app.route('/strategies/retire-metrics/settings', methods=['GET', 'POST'])
def retire_metrics_settings():
    """Get or save retire metrics threshold settings."""
    if request.method == 'POST':
        data = request.get_json()
        set_setting('rm_min_trades', str(data.get('min_trades', 30)))
        set_setting('rm_retdd_tolerance', str(data.get('retdd_tolerance', 60)))
        set_setting('rm_pf_tolerance', str(data.get('pf_tolerance', 60)))
        set_setting('rm_consec_tolerance', str(data.get('consec_tolerance', 100)))
        return jsonify({'ok': True})

    return jsonify({
        'min_trades': int(get_setting('rm_min_trades', '30')),
        'retdd_tolerance': int(get_setting('rm_retdd_tolerance', '60')),
        'pf_tolerance': int(get_setting('rm_pf_tolerance', '60')),
        'consec_tolerance': int(get_setting('rm_consec_tolerance', '100')),
    })


@app.route('/strategies/<int:strategy_id>/retire-health')
def retire_health(strategy_id):
    """Calculate retire health metrics for a single strategy."""
    s = Strategy.query.get_or_404(strategy_id)
    return jsonify(_calc_retire_health(s))


@app.route('/strategies/<int:strategy_id>/trades-json')
def strategy_trades_json(strategy_id):
    """Return all trades for a strategy as JSON."""
    trades = Trade.query.filter_by(StrategyID=strategy_id).order_by(Trade.CloseTime.desc()).all()
    return jsonify([{
        'ticket': t.Ticket,
        'symbol': t.Symbol,
        'type': t.Type,
        'lots': t.Lots,
        'open_time': t.OpenTime,
        'close_time': t.CloseTime,
        'profit': t.Profit,
        'swap': t.Swap,
        'commission': t.Commission,
        'net_profit': t.NetProfit,
        'pips': t.Pips,
    } for t in trades])


@app.route('/strategies/<int:strategy_id>/equity-json')
def strategy_equity_json(strategy_id):
    """Return equity curve and drawdown data for charting."""
    s = Strategy.query.get_or_404(strategy_id)
    trades = Trade.query.filter_by(StrategyID=strategy_id).order_by(Trade.CloseTime.asc()).all()

    if not trades:
        return jsonify({'labels': [], 'equity': [], 'drawdown': [], 'trade_count': 0})

    labels = []
    equity_series = []
    drawdown_series = []

    equity = 0
    peak = 0

    for t in trades:
        equity += t.NetProfit or 0
        if equity > peak:
            peak = equity
        dd = peak - equity

        labels.append(t.CloseTime or '')
        equity_series.append(round(equity, 2))
        drawdown_series.append(round(-dd, 2))  # negative for display below zero

    return jsonify({
        'labels': labels,
        'equity': equity_series,
        'drawdown': drawdown_series,
        'trade_count': len(trades),
        'strategy_name': s.DisplayName or s.StrategyName,
        'net_profit': round(equity, 2),
        'max_dd': round(min(drawdown_series), 2) if drawdown_series else 0,
    })


def _lookup_market_for_symbol(symbol):
    """Look up the Market type for a symbol by checking existing strategies."""
    if not symbol:
        return None
    existing = Strategy.query.filter(
        Strategy.Symbol == symbol,
        Strategy.Market.isnot(None)
    ).first()
    return existing.Market if existing else None


def _calc_retire_health(strategy):
    """Calculate retirement health status for a strategy.
    Returns dict with status (grey/green/amber/red), metrics breakdown, and breach count.
    
    Metrics:
    1. Ret/DD vs Backtest Ret/DD — strategy degradation signal
    2. Ret/DD vs MC95 Ret/DD — statistical worst-case floor
    3. Profit Factor — profitability vs backtest
    4. Max Consecutive Losses — unusual losing streaks
    """
    min_trades = int(get_setting('rm_min_trades', '30'))
    retdd_tolerance = int(get_setting('rm_retdd_tolerance', '60'))
    pf_tolerance = int(get_setting('rm_pf_tolerance', '60'))
    consec_tolerance = int(get_setting('rm_consec_tolerance', '100'))

    live_trades = strategy.LiveTotalTrades or 0
    result = {
        'strategy_id': strategy.StrategyID,
        'strategy_name': strategy.StrategyName,
        'live_trades': live_trades,
        'min_trades': min_trades,
        'status': 'grey',
        'breaches': 0,
        'metrics': [],
    }

    # Not enough trades — grey status
    if live_trades < min_trades:
        result['reason'] = f'Needs {min_trades - live_trades} more trades (minimum {min_trades})'
        return result

    # No backtest data — can't compare
    if not strategy.BacktestData:
        result['reason'] = 'No backtest data available'
        return result

    try:
        bt = json.loads(strategy.BacktestData)
    except (json.JSONDecodeError, TypeError):
        result['reason'] = 'Invalid backtest data'
        return result

    overview = bt.get('overview', {})
    ranking = bt.get('ranking', {})
    breaches = 0

    live_retdd = strategy.LiveRetDD or 0

    # Metric 1: Ret/DD vs Backtest Ret/DD — degradation signal
    bt_retdd = ranking.get('ret_dd') or overview.get('ret_dd', 0) or 0
    if bt_retdd > 0:
        retdd_threshold = bt_retdd * (retdd_tolerance / 100)
        retdd_breached = live_retdd < retdd_threshold
        if retdd_breached:
            breaches += 1
        result['metrics'].append({
            'name': 'Ret/DD vs Backtest',
            'live_value': f'{live_retdd:.2f}',
            'bt_value': f'{bt_retdd:.2f}',
            'threshold': f'≥ {retdd_threshold:.2f} ({retdd_tolerance}% of backtest)',
            'breached': retdd_breached,
        })

    # Metric 2: Ret/DD vs MC95 Ret/DD — statistical floor
    mc95_retdd = ranking.get('mc95_ret_dd', 0) or 0
    if mc95_retdd > 0:
        mc95_breached = live_retdd < mc95_retdd
        if mc95_breached:
            breaches += 1
        result['metrics'].append({
            'name': 'Ret/DD vs MC95',
            'live_value': f'{live_retdd:.2f}',
            'bt_value': f'{mc95_retdd:.2f}',
            'threshold': f'≥ {mc95_retdd:.2f} (MC 95% floor)',
            'breached': mc95_breached,
        })

    # Metric 3: Profit Factor — live PF vs backtest PF * tolerance
    bt_pf = overview.get('profit_factor', 0) or 0
    live_pf = strategy.LiveProfitFactor or 0
    if bt_pf > 0:
        pf_threshold = bt_pf * (pf_tolerance / 100)
        pf_breached = live_pf < pf_threshold
        if pf_breached:
            breaches += 1
        result['metrics'].append({
            'name': 'Profit Factor',
            'live_value': f'{live_pf:.2f}',
            'bt_value': f'{bt_pf:.2f}',
            'threshold': f'≥ {pf_threshold:.2f} ({pf_tolerance}% of backtest)',
            'breached': pf_breached,
        })

    # Metric 4: Max Consecutive Losses — live vs backtest * tolerance
    bt_consec = overview.get('max_consec_losses', 0) or 0
    live_consec = strategy.LiveMaxConsecLosses or 0
    if bt_consec > 0:
        consec_threshold = bt_consec * (consec_tolerance / 100)
        consec_breached = live_consec > consec_threshold
        if consec_breached:
            breaches += 1
        result['metrics'].append({
            'name': 'Max Consec. Losses',
            'live_value': str(live_consec),
            'bt_value': str(bt_consec),
            'threshold': f'≤ {consec_threshold:.0f} ({consec_tolerance}% of backtest)',
            'breached': consec_breached,
        })

    result['breaches'] = breaches
    if breaches == 0:
        result['status'] = 'green'
    elif breaches == 1:
        result['status'] = 'amber'
    else:
        result['status'] = 'red'

    return result


@app.route('/equity/combined')
def equity_combined():
    """Return combined equity curve across multiple strategies.
    Query params:
      - scope: 'all' (default), 'account'
      - account_id: required when scope=account
      - include_retired: '1' to include retired strategies
    """
    scope = request.args.get('scope', 'all')
    include_retired = request.args.get('include_retired', '0') == '1'
    account_id = request.args.get('account_id', type=int)

    # Build strategy filter
    if scope == 'account' and account_id:
        query = Strategy.query.filter_by(AccountID=account_id)
    else:
        query = Strategy.query

    if include_retired:
        query = query.filter(Strategy.Status.in_(['Running', 'Retired']))
    else:
        query = query.filter_by(Status='Running')

    strategy_ids = [s.StrategyID for s in query.all()]

    if not strategy_ids:
        return jsonify({'labels': [], 'equity': [], 'drawdown': [], 'trade_count': 0})

    # Get all trades across these strategies, sorted by close time
    trades = Trade.query.filter(
        Trade.StrategyID.in_(strategy_ids)
    ).order_by(Trade.CloseTime.asc()).all()

    if not trades:
        return jsonify({'labels': [], 'equity': [], 'drawdown': [], 'trade_count': 0})

    labels = []
    equity_series = []
    drawdown_series = []

    equity = 0
    peak = 0

    for t in trades:
        equity += t.NetProfit or 0
        if equity > peak:
            peak = equity
        dd = peak - equity

        labels.append(t.CloseTime or '')
        equity_series.append(round(equity, 2))
        drawdown_series.append(round(-dd, 2))

    return jsonify({
        'labels': labels,
        'equity': equity_series,
        'drawdown': drawdown_series,
        'trade_count': len(trades),
        'net_profit': round(equity, 2),
        'max_dd': round(min(drawdown_series), 2) if drawdown_series else 0,
    })


@app.route('/equity/weekly-wl')
def equity_weekly_wl():
    """Return win/loss counts grouped by ISO week number."""
    query = Strategy.query.filter(Strategy.Status.in_(['Running', 'Retired']))
    strategy_ids = [s.StrategyID for s in query.all()]

    if not strategy_ids:
        return jsonify({'weeks': [], 'wins': [], 'losses': []})

    trades = Trade.query.filter(
        Trade.StrategyID.in_(strategy_ids)
    ).all()

    if not trades:
        return jsonify({'weeks': [], 'wins': [], 'losses': []})

    wins_by_week = {}
    losses_by_week = {}
    win_pnl_by_week = {}
    loss_pnl_by_week = {}

    for t in trades:
        try:
            dt = datetime.strptime(t.CloseTime, '%Y.%m.%d %H:%M')
        except (ValueError, TypeError):
            try:
                dt = datetime.strptime(t.CloseTime, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                continue
        week = dt.isocalendar()[1]
        profit = t.NetProfit or 0
        if t.NetProfit is not None and t.NetProfit > 0:
            wins_by_week[week] = wins_by_week.get(week, 0) + 1
            win_pnl_by_week[week] = round(win_pnl_by_week.get(week, 0) + profit, 2)
        else:
            losses_by_week[week] = losses_by_week.get(week, 0) + 1
            loss_pnl_by_week[week] = round(loss_pnl_by_week.get(week, 0) + profit, 2)

    max_week = max(
        max(wins_by_week.keys(), default=0),
        max(losses_by_week.keys(), default=0),
        52
    )
    weeks = list(range(1, max_week + 1))
    wins = [wins_by_week.get(w, 0) for w in weeks]
    losses = [-losses_by_week.get(w, 0) for w in weeks]
    win_pnl = [win_pnl_by_week.get(w, 0) for w in weeks]
    loss_pnl = [loss_pnl_by_week.get(w, 0) for w in weeks]

    return jsonify({'weeks': weeks, 'wins': wins, 'losses': losses,
                    'win_pnl': win_pnl, 'loss_pnl': loss_pnl})


# ── Routes: Trades & Import (placeholder for now) ────────────────────────────

@app.route('/trades')
def trades():
    """List all trades, optionally filtered by market and symbol."""
    market_filter = request.args.get('market', 'all')
    symbol_filter = request.args.get('symbol', 'all')
    sort_by = request.args.get('sort', 'CloseTime')
    sort_dir = request.args.get('dir', 'desc')
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    # Whitelist sortable columns
    sort_columns = {
        'Ticket': Trade.Ticket,
        'Strategy': Strategy.StrategyName,
        'Symbol': Trade.Symbol,
        'Type': Trade.Type,
        'Lots': Trade.Lots,
        'OpenTime': Trade.OpenTime,
        'CloseTime': Trade.CloseTime,
        'Profit': Trade.Profit,
        'NetProfit': Trade.NetProfit,
    }

    query = Trade.query

    if market_filter != 'all':
        query = query.join(Strategy).filter(Strategy.Market == market_filter)

    if symbol_filter != 'all':
        query = query.filter(Trade.Symbol == symbol_filter)

    # Apply sort — join Strategy if sorting by strategy name and not already joined
    sort_col = sort_columns.get(sort_by, Trade.CloseTime)
    if sort_by == 'Strategy' and market_filter == 'all':
        query = query.join(Strategy)
    order = sort_col.asc() if sort_dir == 'asc' else sort_col.desc()
    query = query.order_by(order)
    all_trades, pagination = paginate_query(query)
    all_accounts = Account.query.order_by(Account.AccountName).all()

    # Get distinct market types from strategies that have trades
    market_types = [r[0] for r in db.session.query(Strategy.Market).join(Trade).filter(
        Strategy.Market.isnot(None)
    ).distinct().order_by(Strategy.Market).all()]

    # Get distinct symbols for dropdown (filtered by market if active)
    symbol_query = db.session.query(Trade.Symbol).filter(Trade.Symbol.isnot(None))
    if market_filter != 'all':
        symbol_query = symbol_query.join(Strategy).filter(Strategy.Market == market_filter)
    symbols = [r[0] for r in symbol_query.distinct().order_by(Trade.Symbol).all()]

    # Calculate filtered net profit
    profit_query = db.session.query(db.func.coalesce(db.func.sum(Trade.NetProfit), 0))
    if market_filter != 'all':
        profit_query = profit_query.join(Strategy).filter(Strategy.Market == market_filter)
    if symbol_filter != 'all':
        profit_query = profit_query.filter(Trade.Symbol == symbol_filter)
    filtered_net_profit = profit_query.scalar() or 0

    return render_template('trades.html',
        trades=all_trades,
        pagination=pagination,
        accounts=all_accounts,
        market_filter=market_filter,
        market_types=market_types,
        symbol_filter=symbol_filter,
        symbols=symbols,
        filtered_net_profit=filtered_net_profit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@app.route('/import')
def import_page():
    """Redirect to trades page (import is now on the trades page)."""
    return redirect(url_for('trades'))


@app.route('/import/upload', methods=['POST'])
def import_upload():
    """Handle CSV upload: parse, match trades to strategies, and import."""
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a .csv file.', 'error')
        return redirect(url_for('trades'))

    account_id = request.form.get('account_id')
    if not account_id:
        flash('Please select an account.', 'error')
        return redirect(url_for('trades'))

    account = Account.query.get(int(account_id))
    if not account:
        flash('Account not found.', 'error')
        return redirect(url_for('trades'))

    import csv
    import io

    content = file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    # Build strategy lookup - include strategies assigned to this account
    # AND unassigned strategies (AccountID is NULL) so retired/orphaned strategies still match
    strategies = Strategy.query.filter(
        db.or_(Strategy.AccountID == int(account_id), Strategy.AccountID.is_(None))
    ).all()
    strategy_by_magic = {}
    strategy_by_comment = {}

    for s in strategies:
        if s.MagicNumber:
            strategy_by_magic[s.MagicNumber] = s
        # Normalise: "SQ NAS100 H1 2.2.128" -> "SQ_NAS100_H1_2_2_128"
        # Also handles "SQ XAUUSD H1 1.1.178_1_" -> "SQ_XAUUSD_H1_1_1_178_1"
        strategy_by_comment[normalise_comment(s.StrategyName)] = s

    imported = 0
    skipped_dup = 0
    unmatched = []
    errors = 0
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    for row in reader:
        try:
            ticket = int(row['Ticket'])

            # Skip if already imported
            if Trade.query.filter_by(Ticket=ticket).first():
                skipped_dup += 1
                continue

            comment = row.get('Comment', '').strip()
            magic = int(row.get('Magic', 0))

            # Match to strategy: try Magic Number first, then Comment
            strategy = None

            if magic:
                strategy = strategy_by_magic.get(magic)

            if not strategy and comment:
                strategy = strategy_by_comment.get(normalise_comment(comment))

            trade = Trade(
                Ticket=ticket,
                StrategyID=strategy.StrategyID if strategy else None,
                Symbol=row.get('Symbol', '').strip(),
                Type=row.get('Type', '').strip(),
                Lots=float(row.get('Lots', 0)),
                OpenPrice=float(row.get('OpenPrice', 0)),
                ClosePrice=float(row.get('ClosePrice', 0)),
                OpenTime=row.get('OpenTime', '').strip(),
                CloseTime=row.get('CloseTime', '').strip(),
                Profit=float(row.get('Profit', 0)),
                Swap=float(row.get('Swap', 0)),
                Commission=float(row.get('Commission', 0)),
                NetProfit=float(row.get('NetProfit', 0)),
                TP=float(row.get('TP', 0)),
                SL=float(row.get('SL', 0)),
                Pips=float(row.get('Pips', 0)),
                MagicNumber=magic,
                Comment=comment,
                BalanceAfter=float(row.get('BalanceAfter', 0)),
                ImportedAt=now,
            )
            db.session.add(trade)
            imported += 1

            if not strategy:
                unmatched.append(f"Ticket {ticket}: magic={magic}, comment={comment}")

        except Exception as e:
            errors += 1

    db.session.commit()

    # Re-link any orphaned trades (previously imported but unmatched)
    relinked = _relink_orphaned_trades(int(account_id))

    # Always recalculate live metrics (covers relinks, new imports, and previous failed updates)
    _update_live_metrics(int(account_id))

    # Build result message
    parts = [f'{imported} trades imported']
    if skipped_dup:
        parts.append(f'{skipped_dup} duplicates skipped')
    if relinked:
        parts.append(f'{relinked} previously unmatched trades linked')
    if errors:
        parts.append(f'{errors} errors')
    if unmatched:
        parts.append(f'{len(unmatched)} unmatched (no strategy found)')

    flash('. '.join(parts) + '.', 'success' if imported > 0 else 'warning')

    if unmatched and len(unmatched) <= 10:
        flash('Unmatched: ' + '; '.join(unmatched[:10]), 'warning')

    return redirect(url_for('trades'))


def _relink_orphaned_trades(account_id):
    """Re-match trades with no StrategyID to strategies by magic number or comment."""
    orphans = Trade.query.filter_by(StrategyID=None).all()
    if not orphans:
        return 0

    strategies = Strategy.query.filter(
        db.or_(Strategy.AccountID == account_id, Strategy.AccountID.is_(None))
    ).all()

    strategy_by_magic = {}
    strategy_by_comment = {}
    for s in strategies:
        if s.MagicNumber:
            strategy_by_magic[s.MagicNumber] = s
        norm = normalise_comment(s.StrategyName)
        if norm:
            strategy_by_comment[norm] = s

    relinked = 0
    for t in orphans:
        strategy = None
        if t.MagicNumber and t.MagicNumber in strategy_by_magic:
            strategy = strategy_by_magic[t.MagicNumber]
        elif t.Comment:
            norm = normalise_comment(t.Comment)
            if norm in strategy_by_comment:
                strategy = strategy_by_comment[norm]

        if strategy:
            t.StrategyID = strategy.StrategyID
            relinked += 1

    if relinked:
        db.session.commit()

    return relinked


def _update_live_metrics(account_id):
    """Recalculate live performance metrics for all strategies that have trades.
    Includes strategies on the given account, unassigned strategies, and any
    strategy that has trades linked to it (e.g. from relinking orphans)."""
    # Find all strategies that might need updating:
    # 1. On this account
    # 2. Unassigned (AccountID is NULL)
    # 3. Any strategy that has at least one trade (covers cross-account relinks)
    strategies_with_trades = db.session.query(Strategy).join(
        Trade, Trade.StrategyID == Strategy.StrategyID
    ).distinct().all()

    account_strategies = Strategy.query.filter(
        db.or_(Strategy.AccountID == account_id, Strategy.AccountID.is_(None))
    ).all()

    # Merge both sets by StrategyID
    seen = set()
    strategies = []
    for s in strategies_with_trades + account_strategies:
        if s.StrategyID not in seen:
            seen.add(s.StrategyID)
            strategies.append(s)

    for s in strategies:
        trades = Trade.query.filter_by(StrategyID=s.StrategyID).order_by(Trade.CloseTime).all()
        if not trades:
            continue

        profits = [t.NetProfit for t in trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]

        total = len(profits)
        num_wins = len(wins)
        num_losses = len(losses)

        s.LiveTotalTrades = total
        s.LiveNetProfit = round(sum(profits), 2)
        s.LiveWinRate = round(num_wins / total * 100, 1) if total > 0 else 0

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        s.LiveProfitFactor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

        s.LiveAvgWin = round(sum(wins) / num_wins, 2) if num_wins > 0 else 0
        s.LiveAvgLoss = round(sum(losses) / num_losses, 2) if num_losses > 0 else 0

        avg_win = s.LiveAvgWin
        avg_loss = abs(s.LiveAvgLoss) if s.LiveAvgLoss else 0
        s.LiveWLRatio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0

        s.LiveExpectedPayoff = round(sum(profits) / total, 2) if total > 0 else 0

        # Long/Short counts
        s.LiveLongTrades = sum(1 for t in trades if t.Type in ('Buy', 'BuyStop', 'BuyLimit'))
        s.LiveShortTrades = sum(1 for t in trades if t.Type in ('Sell', 'SellStop', 'SellLimit'))

        # Max consecutive losses
        max_consec = 0
        current_consec = 0
        for t in trades:
            if t.NetProfit < 0:
                current_consec += 1
                if current_consec > max_consec:
                    max_consec = current_consec
            else:
                current_consec = 0
        s.LiveMaxConsecLosses = max_consec

        # Max drawdown from equity curve
        equity = 0
        peak = 0
        max_dd = 0
        for t in trades:
            equity += t.NetProfit
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        s.LiveMaxDDDollars = round(max_dd, 2)

        # Return / Drawdown ratio
        net_profit = sum(profits)
        s.LiveRetDD = round(net_profit / max_dd, 2) if max_dd > 0 else 0

        # Last trade date
        s.LiveLastTradeDate = trades[-1].CloseTime

        s.LiveMetricsUpdatedAt = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    db.session.commit()


@app.route('/import/preview', methods=['POST'])
def import_preview():
    """Preview CSV import: check duplicates and strategy matching."""
    import csv
    import io

    file = request.files.get('csv_file')
    if not file:
        return jsonify({'error': 'No file'})

    account_id = request.form.get('account_id', '')
    content = file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    # Build strategy lookup - include unassigned strategies (AccountID is NULL)
    strategy_by_magic = {}
    strategy_by_comment = {}
    if account_id:
        strategies = Strategy.query.filter(
            db.or_(Strategy.AccountID == int(account_id), Strategy.AccountID.is_(None))
        ).all()
    else:
        strategies = Strategy.query.all()

    for s in strategies:
        if s.MagicNumber:
            strategy_by_magic[s.MagicNumber] = s
        strategy_by_comment[normalise_comment(s.StrategyName)] = s

    total = 0
    duplicates = 0
    unmatched = []
    strategy_trades = {}  # strategy_name -> {count, net_profit}

    for row in reader:
        total += 1
        ticket = int(row.get('Ticket', 0))
        comment = row.get('Comment', '').strip()
        magic = int(row.get('Magic', 0))
        net_profit = float(row.get('NetProfit', 0))

        if Trade.query.filter_by(Ticket=ticket).first():
            duplicates += 1
            continue

        # Match strategy: Magic Number first, Comment fallback
        strategy = None
        if magic:
            strategy = strategy_by_magic.get(magic)
        if not strategy and comment:
            strategy = strategy_by_comment.get(normalise_comment(comment))

        if strategy:
            name = strategy.DisplayName or strategy.StrategyName
            if name not in strategy_trades:
                strategy_trades[name] = {'count': 0, 'net_profit': 0}
            strategy_trades[name]['count'] += 1
            strategy_trades[name]['net_profit'] += net_profit
        else:
            unmatched.append({'ticket': ticket, 'magic': magic, 'comment': comment})

    breakdown = [
        {'name': k, 'count': v['count'], 'net_profit': round(v['net_profit'], 2)}
        for k, v in sorted(strategy_trades.items())
    ]

    return jsonify({
        'total': total,
        'new_trades': total - duplicates,
        'duplicates': duplicates,
        'unmatched_count': len(unmatched),
        'unmatched': unmatched[:20],
        'strategy_breakdown': breakdown,
    })


# ── Margins ────────────────────────────────────────────────────────────────────

# Symbol classification rules (applied on PT import side)
FOREX_PAIRS = {
    'AUDUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'NZDUSD', 'USDCAD', 'USDCHF',
    'AUDNZD', 'EURNZD', 'GBPNZD', 'NZDJPY', 'NZDCAD', 'NZDCHF',
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'EURAUD', 'EURCHF', 'EURGBP',
    'GBPAUD', 'GBPCHF', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURCAD',
    'EURJPY', 'GBPCAD', 'GBPJPY', 'AUDCNH', 'CNHJPY',
}

COMMODITIES = {'XAUUSD', 'XAGUSD', 'SpotCrude', 'NatGas', 'XBRUSD', 'XTIUSD', 'XNGUSD'}
CRYPTO = {'BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD'}


def classify_symbol(symbol_raw):
    """Classify a broker symbol (e.g. 'USDJPY.a') into a type category."""
    clean = re.sub(r'\.[a-zA-Z]+$', '', symbol_raw)  # Strip broker suffix
    if clean.upper() in {s.upper() for s in FOREX_PAIRS}:
        return 'Forex', clean
    if clean in COMMODITIES or clean.upper() in {s.upper() for s in COMMODITIES}:
        return 'Commodity', clean
    if clean.upper() in {s.upper() for s in CRYPTO}:
        return 'Crypto', clean
    # If contract size is 1 and it's not forex/commodity, likely an index
    return 'Index', clean


@app.route('/margins')
def margins():
    """Margins page — show margin requirements for all instruments."""
    type_filter = request.args.get('type', 'all')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', '')
    sort_dir = request.args.get('dir', 'asc')
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'asc'

    sort_columns = {
        'Symbol': MarginData.SymbolClean,
        'Type': MarginData.Type,
        'Bid': MarginData.Bid,
        'Ask': MarginData.Ask,
        'Spread': MarginData.SpreadPoints,
        'ContractSize': MarginData.ContractSize,
        'MinLot': MarginData.MinLot,
        'Margin': MarginData.MarginRequired,
        'MarginCCY': MarginData.MarginCurrency,
        'TickValue': MarginData.TickValue,
    }

    query = MarginData.query

    if type_filter != 'all':
        query = query.filter_by(Type=type_filter)

    if search:
        query = query.filter(
            db.or_(
                MarginData.Symbol.ilike(f'%{search}%'),
                MarginData.SymbolClean.ilike(f'%{search}%'),
            )
        )

    if sort_by in sort_columns:
        sort_col = sort_columns[sort_by]
        order = sort_col.asc() if sort_dir == 'asc' else sort_col.desc()
        query = query.order_by(order)
    else:
        query = query.order_by(MarginData.Type, MarginData.SymbolClean)

    # Get types for filter dropdown (from full unfiltered dataset)
    all_types = db.session.query(MarginData.Type).distinct().order_by(MarginData.Type).all()
    types = [t[0] for t in all_types if t[0]]

    # Summary stats need the full filtered count (before pagination)
    total_instruments = query.count()
    first_inst = query.first()
    last_import = first_inst.ImportedAt if first_inst else None

    # Cross-reference with active strategies to show which instruments are in use
    active_strategies = Strategy.query.filter_by(Status='Running').all()
    active_symbols = {s.Symbol.upper() for s in active_strategies if s.Symbol}

    # Calculate total margin for active strategies at MinLot (from full dataset)
    all_instruments = query.all()
    total_active_margin = 0
    for inst in all_instruments:
        if inst.SymbolClean and inst.SymbolClean.upper() in active_symbols:
            total_active_margin += inst.MarginRequired or 0

    # Paginate the results for display
    instruments, pagination = paginate_list(all_instruments)

    return render_template('margins.html',
        active_page='margins',
        instruments=instruments,
        types=types,
        type_filter=type_filter,
        search=search,
        total_instruments=total_instruments,
        last_import=last_import,
        active_symbols=active_symbols,
        total_active_margin=total_active_margin,
        pagination=pagination,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@app.route('/margins/import', methods=['POST'])
def margins_import():
    """Import margin data from MT5 MarginExport.csv."""
    import csv
    import io

    file = request.files.get('margin_csv')
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('margins'))

    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file.', 'error')
        return redirect(url_for('margins'))

    try:
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            flash('CSV file is empty.', 'error')
            return redirect(url_for('margins'))

        # Clear existing margin data (full replace on each import)
        MarginData.query.delete()

        imported = 0
        for row in rows:
            symbol_raw = row.get('Symbol', '').strip()
            if not symbol_raw:
                continue

            instrument_type, symbol_clean = classify_symbol(symbol_raw)

            # Override type if MT5 reported it correctly
            mt5_type = row.get('Type', '').strip()
            if mt5_type == 'CFD/Index' and instrument_type not in ('Commodity', 'Crypto'):
                instrument_type = 'Index'

            margin = MarginData(
                Symbol=symbol_raw,
                SymbolClean=symbol_clean,
                Type=instrument_type,
                Bid=float(row.get('Bid', 0)),
                Ask=float(row.get('Ask', 0)),
                ContractSize=float(row.get('ContractSize', 0)),
                LotSize=float(row.get('LotSize', 0)),
                MinLot=float(row.get('MinLot', 0)),
                MaxLot=float(row.get('MaxLot', 0)),
                LotStep=float(row.get('LotStep', 0)),
                AccountLeverage=int(row.get('AccountLeverage', 0)),
                MarginRequired=float(row.get('MarginRequired', 0)),
                MarginCurrency=row.get('MarginCurrency', ''),
                BaseCurrency=row.get('BaseCurrency', ''),
                ProfitCurrency=row.get('ProfitCurrency', ''),
                AccountCurrency=row.get('AccountCurrency', ''),
                AccountLogin=int(row.get('AccountLogin', 0)),
                Spread=float(row.get('Spread', 0)),
                SpreadPoints=int(row.get('SpreadPoints', 0)),
                TickSize=float(row.get('TickSize', 0)),
                TickValue=float(row.get('TickValue', 0)),
                ExportTime=row.get('ExportTime', ''),
            )
            db.session.add(margin)
            imported += 1

        db.session.commit()
        flash(f'Imported margin data for {imported} instruments.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Import error: {str(e)}', 'error')

    return redirect(url_for('margins'))


# ── Database Initialisation ───────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist, and run migrations."""
    with app.app_context():
        db.create_all()

        # Migration: Add LiveMaxConsecLosses column if not present
        try:
            db.session.execute(db.text("SELECT LiveMaxConsecLosses FROM Strategies LIMIT 1"))
        except Exception:
            db.session.rollback()
            db.session.execute(db.text("ALTER TABLE Strategies ADD COLUMN LiveMaxConsecLosses INTEGER DEFAULT 0"))
            db.session.commit()

        # Migration: Add Complexity column if not present
        try:
            db.session.execute(db.text("SELECT Complexity FROM Strategies LIMIT 1"))
        except Exception:
            db.session.rollback()
            db.session.execute(db.text("ALTER TABLE Strategies ADD COLUMN Complexity INTEGER"))
            db.session.commit()

        # Migration: Add Market column if not present
        try:
            db.session.execute(db.text("SELECT Market FROM Strategies LIMIT 1"))
        except Exception:
            db.session.rollback()
            db.session.execute(db.text("ALTER TABLE Strategies ADD COLUMN Market TEXT"))
            db.session.commit()


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
