"""
Portfolio Tracker — Waitress Server
=====================================
Production WSGI server for Portfolio Tracker.

Run directly:
    python run_server.py

Or install as a Windows Service using NSSM (see install_service.bat).
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Ensure we're in the right directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from waitress import serve
from app import app, init_db


def setup_logging():
    """Set up file logging."""
    log_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # App log
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'server.log'),
        maxBytes=5*1024*1024, backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    return logger


if __name__ == '__main__':
    logger = setup_logging()

    init_db()

    host = '0.0.0.0'
    port = 5000

    logger.info(f'Portfolio Tracker starting on http://{host}:{port}')
    logger.info(f'Directory: {BASE_DIR}')
    print(f'Portfolio Tracker running on http://localhost:{port}')
    print(f'Also accessible on your network via http://{os.environ.get("COMPUTERNAME", "tradepc").lower()}:{port}')
    print(f'Press Ctrl+C to stop')

    serve(app, host=host, port=port)
