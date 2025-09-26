"""
Store manager application
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import os
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from views.template_view import show_main_menu, show_404_page
from views.user_view import show_user_form, register_user, remove_user
from views.product_view import show_product_form, register_product, remove_product
from views.order_view import show_order_form, register_order, remove_order
from views.report_view import show_highest_spending_users, show_best_sellers
from commands.write_order import sync_all_orders_to_redis
from database import db_session, redis_client   

class StoreManager(BaseHTTPRequestHandler):
    def do_GET(self):
        """ Handle GET requests received by the http.server """
        id = self.path.split("/")[-1]
        if self.path == "/" or self.path == "/home":
            self._send_html(show_main_menu())
            return
        if self.path == "/users":
            self._send_html(show_user_form())
        elif self.path.startswith("/users/remove/"):
            response = remove_user(id)
            self._send_html(response)
        elif self.path == "/products":
            self._send_html(show_product_form())
        elif self.path.startswith("/products/remove/"):
            response = remove_product(id)
            self._send_html(response)
        elif self.path == "/orders":
            self._send_html(show_order_form())
        elif self.path.startswith("/orders/remove/"):
            response = remove_order(id)
            self._send_html(response)
        elif self.path == "/orders/reports/highest_spenders":
            self._send_html(show_highest_spending_users())
        elif self.path == "/orders/reports/best_sellers":
            self._send_html(show_best_sellers())
        elif "/assets" in self.path: # load assets such as images, CSS, etc.
            self.load_asset()      
        else:
            self._send_html(show_404_page(), status=404)

    def do_POST(self):
        """ Handle POST requests received by the http.server """
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)
        if self.path == "/users/add":
            response = register_user(params)
            self._send_html(response)
        elif self.path == "/products/add":
            response = register_product(params)
            self._send_html(response)
        elif self.path == "/orders/add":
            response = register_order(params)
            self._send_html(response)
        else:
            self._send_html(show_404_page(), status=404)

    def load_asset(self):
        """ Load assets from disk based on requested path, then send file contents as a response to the client """
        path_parts = self.path.split(".")
        extension = path_parts[1] if len(path_parts) >= 2 else None
        base_directory = os.path.dirname(__file__)
        with open(base_directory + self.path, "r") as file:
            css = "".join(file.readlines())
            self.send_response(200)
            self.send_header("Content-type", self.get_mimetype(extension))
            self.end_headers()
            self.wfile.write(css.encode("utf-8"))

    def get_mimetype(self, extension):
        """ Get mimetype (https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types/Common_types) """
        if (extension == "html"):
            return "text/html"
        elif (extension == "css"):
            return "text/css"
        elif (extension == "js"):
            return "text/javascript"
        elif (extension == "svg"):
            return "image/svg+xml"
        else:
            return "application/octet-stream"

    def _send_html(self, html, status=200):
        """ Send given HTML string as a response to the client """
        self.send_response(status)
        self.send_header("Content-type", self.get_mimetype("html"))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

if __name__ == "__main__":
    """ Init des données db + redis"""
    added = sync_all_orders_to_redis()

    server = HTTPServer(("0.0.0.0", 5000), StoreManager)
    print("Server running on http://0.0.0.0:5000")
    server.serve_forever()
