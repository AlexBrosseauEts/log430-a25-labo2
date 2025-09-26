"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql
from db import get_sqlalchemy_session, get_redis_conn
from models import SessionLocal

def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    try:
        product_ids = []
        for item in items:
            product_ids.append(int(item['product_id']))
    except Exception as e:
        print(e)
        raise ValueError(f"L'ID Article n'est pas valide: {item['product_id']}")
    session = get_sqlalchemy_session()

    try:
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}
        total_amount = 0
        order_items_data = []
        
        for item in items:
            pid = int(item["product_id"])
            qty = float(item["quantity"])

            if not qty or qty <= 0:
                raise ValueError(f"Vous devez indiquer une quantité superieure à zéro.")

            if pid not in price_map:
                raise ValueError(f"Article ID {pid} n'est pas dans la base de données.")

            unit_price = price_map[pid]
            total_amount += unit_price * qty
            order_items_data.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': unit_price
            })
        
        new_order = Order(user_id=user_id, total_amount=total_amount)
        session.add(new_order)
        session.flush() 
        
        order_id = new_order.id

        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            session.add(order_item)

        session.commit()

        # TODO: ajouter la commande à Redis
        add_order_to_redis(order_id, user_id, total_amount, items)

        return order_id

    except Exception as e:
        session.rollback()
        raise e
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

            # TODO: supprimer la commande à Redis
            delete_order_from_redis(order_id)
            return 1  
        else:
            return 0  
            
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def add_order_to_redis(order_id, user_id, total_amount, items):
    self.db.add(order)
    self.db.commit()
    self.db.refresh(order)

    payload = {
        "id": order.id,
        "user_id": order.user_id,
        "total": float(order.total),
        "created_at": order.created_at.isoformat()
    }
    self.r.hset("orders:index", order.id, json.dumps(payload))

def delete_order_from_redis(order_id):
    order = self.db.get(Order,order_id)
    if not order:
        return
    self.db.delete(order)
    self.db.commit()
    self.r.hdel("orders:index",order_id)

def sync_all_orders_to_redis():
    """ Sync orders from MySQL to Redis """
    # redis
    r = get_redis_conn()
    orders_in_redis = r.keys(f"order:*")
    rows_added = 0

    try:
        if len(orders_in_redis) == 0:
            # mysql
            orders_from_mysql = (
                .options(joinedload(Order.items))
                .all()
            )
            for o in orders_from_mysql:
                order_id = o.id
                key = f"order:{order_id}"
                mapping = {
                    "id": str(o.id),
                    "user_id": str(o.user_id) if o.user_id is not None else "",
                    "total": str(float(o.total)) if o.total is not None else "",
                    "created_at": str(o.created_at) if getattr(o, "created_at", None) else "",
                }
                r.hset(key, mapping=mapping)
                r.sadd("orders", o.id)
                print(f"Inserted {key} -> {mapping}")
            rows_added = len(orders_from_mysql)
        else:
            print("Redis already contains orders, no need to sync!")
    except Exception as e:
        print(e)
        return 0
    finally:
        return len(orders_in_redis) + rows_added