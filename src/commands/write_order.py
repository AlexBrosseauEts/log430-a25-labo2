"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import json
from datetime import datetime

from sqlalchemy import text

from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql  # (ok si utilisé ailleurs)
from db import get_sqlalchemy_session, get_redis_conn, engine


def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    # Valider et collecter les IDs produits
    try:
        product_ids = [int(item["product_id"]) for item in items]
    except Exception:
        raise ValueError("L'ID Article n'est pas valide dans la liste des items.")

    session = get_sqlalchemy_session()

    try:
        # Récupérer les prix par produit
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}

        total_amount = 0.0
        order_items_data = []

        for item in items:
            pid = int(item["product_id"])
            try:
                qty = float(item["quantity"])
            except Exception:
                raise ValueError("La quantité doit être un nombre.")

            if qty <= 0:
                raise ValueError("Vous devez indiquer une quantité superieure à zéro.")

            if pid not in price_map:
                raise ValueError(f"Article ID {pid} n'est pas dans la base de données.")

            unit_price = float(price_map[pid])
            total_amount += unit_price * qty
            order_items_data.append({
                "product_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
            })

        # Créer la commande (en supposant que Order a un champ total_amount)
        new_order = Order(user_id=user_id, total_amount=total_amount)
        session.add(new_order)
        session.flush()  # pour obtenir new_order.id

        order_id = int(new_order.id)

        # Insérer les items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            session.add(order_item)

        session.commit()

        # Garder Redis en sync
        add_order_to_redis(order_id, user_id, total_amount, items)

        return order_id

    except Exception as e:
        session.rollback()
        print(e)
        return "Une erreur s'est produite lors de la création de l'enregistrement. Veuillez consulter les logs pour plus d'informations."
    finally:
        session.close()


def delete_order(order_id: int):
    """Delete order in MySQL, keep Redis in sync"""
    session = get_sqlalchemy_session()
    try:
        order = session.query(Order).filter(Order.id == order_id).first()
        if order:
            session.delete(order)
            session.commit()

            # Supprimer aussi dans Redis
            delete_order_from_redis(order_id)
            return 1
        else:
            return 0
    except Exception as e:
        session.rollback()
        print(e)
        raise
    finally:
        session.close()


def add_order_to_redis(order_id, user_id, total_amount, items):
    r = get_redis_conn()
    mapping = {
        "id": str(order_id),
        "user_id": "" if user_id is None else str(user_id),
        "total": "" if total_amount is None else str(float(total_amount)),
        "created_at": datetime.utcnow().isoformat(),
    }
    r.hset(f"order:{order_id}", mapping=mapping)
    r.sadd("orders", order_id)

    if items:
        r.set(f"order:{order_id}:items", json.dumps(items))
        # facultatif : maintenir un compteur de ventes par produit
        for it in items:
            pid = int(it["product_id"])
            qty = int(it["quantity"])
            r.hincrby("product:sold_qty", pid, qty)

    return True


def delete_order_from_redis(order_id):
    r = get_redis_conn()
    deleted = r.delete(f"order:{order_id}")
    r.srem("orders", order_id)
    r.delete(f"order:{order_id}:items")
    return deleted > 0


def sync_all_orders_to_redis():
    """Sync orders from MySQL to Redis (utilise l'engine partagé, pas d'engine local)."""
    r = get_redis_conn()
    existing = r.keys("order:*")
    if existing:
        print("Redis already contains orders, no need to sync!")
        return len(existing)

    rows_added = 0
    try:
        # Ta table 'orders' peut avoir total_amount ; sinon on le calcule via order_items
        # On prend COALESCE(total_amount, SUM(...)) pour supporter les deux cas.
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    o.id,
                    o.user_id,
                    o.created_at,
                    COALESCE(o.total_amount, SUM(oi.quantity * oi.unit_price)) AS total
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                GROUP BY o.id, o.user_id, o.created_at, o.total_amount
            """))

            for row in result.mappings():
                order_id = row["id"]
                key = f"order:{order_id}"
                mapping = {
                    "id": str(row["id"]),
                    "user_id": "" if row["user_id"] is None else str(row["user_id"]),
                    "total": "" if row["total"] is None else str(float(row["total"])),
                    "created_at": "" if row["created_at"] is None else str(row["created_at"]),
                }
                r.hset(key, mapping=mapping)
                r.sadd("orders", order_id)
                rows_added += 1
                print(f"Inserted {key} -> {mapping}")

        return rows_added

    except Exception as e:
        print(e)
        return 0
