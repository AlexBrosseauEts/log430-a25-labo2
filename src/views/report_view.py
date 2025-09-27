"""
Report view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from views.template_view import get_template, get_param
from queries.read_order import get_highest_spending_users, get_most_sold_products
from sqlalchemy import text
from db import engine
def _render_page(title: str, heading: str, ul_html: str) -> str:
    return f"""<!DOCTYPE html>
    <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="/assets/light.css">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <header>
                <img id="logo" src="/assets/logo.svg" />
                <h1>Le Magasin du Coin</h1>
            </header>
            <div id="breadcrumbs">
                <a href="/">← Retourner à la page d'accueil</a>
            </div>
            <hr>
            <h2>{heading}</h2>
            {ul_html}
        </body>
    </html>
    """
def show_highest_spending_users():
    try:
        rows = get_highest_spending_users()
    except Exception as e:
        print(e)
        rows = []
    if not rows:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("""
                    SELECT u.name AS user_name,
                           COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS spent
                    FROM orders o
                    JOIN users u ON u.id = o.user_id
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    GROUP BY u.id, u.name
                    ORDER BY spent DESC
                    LIMIT 10
                """))
                rows = [(r["user_name"], float(r["spent"])) for r in res.mappings()]
        except Exception as e:
            print(e)
            rows = []
    items = []
    for row in rows:
        if isinstance(row, dict):
            user = row.get("user_name") or row.get("name")
            total = row.get("spent") or row.get("total") or 0
        else:
            try:
                user, total = row
            except Exception:
                continue
        if user is None:
            continue
        try:
            total = float(total or 0)
        except Exception:
            total = 0.0
        items.append(f"<li>{user} — {total:.2f}$</li>")

    if not items:
        items_html = "<li>Aucun résultat</li>"
    else:
        items_html = "".join(items)

    ul_html = f"<ul>{items_html}</ul>"
    return _render_page("Les plus gros acheteurs", "Les plus gros acheteurs", ul_html)


def show_best_sellers():
    try:
        rows = get_most_sold_products()
    except Exception as e:
        print(e)
        rows = []

    items_html = "".join(
        f"<li>{product} — {int(qty or 0)} vendus</li>"
        for product, qty in rows
        if product is not None
    )

    if not items_html:
        items_html = "<li>Aucun résultat</li>"

    ul_html = f"<ul>{items_html}</ul>"

    return f"""<!DOCTYPE html>
    <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="/assets/light.css">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <header>
                <img id="logo" src="/assets/logo.svg" />
                <h1>Le Magasin du Coin</h1>
            </header>
            <div id="breadcrumbs">
                <a href="/">← Retourner à la page d'accueil</a>
            </div>
            <hr>
            <h2>Les articles les plus vendus</h2>
            {ul_html}
        </body>
    </html>
    """
