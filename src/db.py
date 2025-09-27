"""
Database connections
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

import mysql.connector
import redis
import config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_mysql_conn():
    """Get a MySQL connection using env variables (auth plugin forced)."""
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASS,              
        database=config.DB_NAME,
        auth_plugin="caching_sha2_password",   
    )


def get_redis_conn():
    """Get a Redis connection using env variables."""
    return redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        decode_responses=True,
    )
_CONNECTION_STRING = (
    f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASS}"
    f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
)
engine = create_engine(
    _CONNECTION_STRING,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={"auth_plugin": "caching_sha2_password"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_sqlalchemy_session():
    """Return a new SQLAlchemy ORM session bound to the shared engine."""
    return SessionLocal()

db_session = SessionLocal()
