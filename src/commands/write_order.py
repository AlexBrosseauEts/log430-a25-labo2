"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import json
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker, joinedload
from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql
from db import get_sqlalchemy_session, get_redis_conn, engine
from sqlalchemy import text,create_engine


def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    # Valider et collecter les IDs produits
    try:
        product_ids = [int(item["product_id"]) for item in items]
    except Exception:
        # NOTE: item peut ne pas être défini si l'erreur survient au début; on reste générique
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
        # Conserver l'exception ou renvoyer un message, selon tes tests :
        # raise
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
    """ Sync orders from MySQL to Redis """
    r = get_redis_conn()
    orders_in_redis = r.keys("order:*")
    rows_added = 0
    try:
        if len(orders_in_redis) == 0:
            user = os.getenv("MYSQL_USER", "user")
            password = os.getenv("MYSQL_PASSWORD", "pass")
            host = os.getenv("MYSQL_HOST", "mysql")
            db = os.getenv("MYSQL_DATABASE", "labo02_db")

            url = f"mysql+mysqlconnector://{user}:{password}@{host}/{db}"
            engine = create_engine(url)
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                orders_from_mysql = session.query(Order).all()
            finally:
                session.close()

            for order in orders_from_mysql:
                order_id = order.id
                key = f"order:{order_id}"
                mapping = {
                    "id": str(order.id),
                    "user_id": str(order.user_id) if order.user_id is not None else "",
                    # Ton schéma SQL utilise total_amount
                    "total": str(float(order.total_amount))
                             if getattr(order, "total_amount", None) is not None else "",
                    "created_at": str(order.created_at)
                                  if getattr(order, "created_at", None) else "",
                }
                r.hset(key, mapping=mapping)
                r.sadd("orders", order_id)
                print(f"Inserted {key} -> {mapping}")
            rows_added = len(orders_from_mysql)
        else:
            print("Redis already contains orders, no need to sync!")
    except Exception as e:
        print(e)
        return 0
    finally:
        return len(orders_in_redis) + rows_added
