"""
Orders (read-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from db import get_sqlalchemy_session, get_redis_conn
from sqlalchemy import desc
from models.order import Order

def get_order_by_id(order_id):
    """Get order by ID from Redis"""
    r = get_redis_conn()
    return r.hgetall(order_id)

def get_orders_from_mysql(limit=9999):
    """Get last X orders"""
    session = get_sqlalchemy_session()
    return session.query(Order).order_by(desc(Order.id)).limit(limit).all()

def get_orders_from_redis(limit=9999):
    all_fields = self.r.hgetall("orders:index")
    orders = []
    for _, raw in all_fields.items():
        orders.append(json.loads(raw.decode("utf-8")))
    return orders

def get_highest_spenders(limit=10):
    """Get report of highest spending users from Redis"""
    r = get_redis_conn()
    orders_keys = r.keys("order:*")
    expenses_by_user = defaultdict(float)

    for key in orders_keys:
        order = r.hgetall(key)
        if not order:
            continue
        user_id = order.get(b"user_id")
        total = order.get(b"total")
        if user_id and total:
            expenses_by_user[user_id.decode()] += float(total.decode())

    top = sorted(expenses_by_user.items(), key=lambda kv: kv[1], reverse=True)
    return top[:limit]


def get_best_sellers(top=10):
    """Get report of best selling products from Redis"""
    r = get_redis_conn()
    product_ids = r.smembers("products:ids")
    sales = []

    for pid_b in product_ids:
        pid = pid_b.decode()
        count = int(r.get(f"product:{pid}:sold") or 0)
        sales.append((pid, count))

    sales.sort(key=lambda x: x[1], reverse=True)
    return sales[:top]
    