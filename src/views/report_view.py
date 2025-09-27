"""
Report view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from views.template_view import get_template, get_param
from queries.read_order import get_highest_spending_users, get_most_sold_products
def show_highest_spending_users():
    try:
        rows = get_highest_spending_users()
    except Exception as e:
        print(e)
        rows = []

    items_html = "".join(
        f"<li>{user} — {total:.2f}$</li>" for user, total in rows
    )
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
            <h2>Les plus gros acheteurs</h2>
            {ul_html}
        </body>
    </html>
    """

def show_best_sellers():
    try:
        rows = get_most_sold_products()
    except Exception as e:
        print(e)
        rows = []

    items_html = "".join(
        f"<li>{product} — {qty} vendus</li>" for product, qty in rows
    )
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