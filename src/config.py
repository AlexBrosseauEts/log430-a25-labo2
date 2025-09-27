"""
Load configurations
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
# Accepte DB_PASSWORD ou DB_PASS, priorité à DB_PASSWORD (compose)
DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS") or ""
DB_NAME = os.getenv("DB_NAME", "test")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))