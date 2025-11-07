from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://rj.seguricloud.com"
LOGIN_URL = f"{BASE_URL}/login"
PRODUCTS_URL = f"{BASE_URL}/items/records"

EMAIL = "jroque@rj.com"
PASSWORD = "10738003751"

session = requests.Session()

def login():
    """Obtiene el token CSRF y realiza el login."""
    try:
        # Paso 1: obtener el token CSRF
        resp = session.get(LOGIN_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if not token_input:
            raise ValueError("No se encontró el token CSRF en el formulario.")
        csrf_token = token_input["value"]

        # Paso 2: hacer login
        payload = {
            "_token": csrf_token,
            "email": EMAIL,
            "password": PASSWORD
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = session.post(LOGIN_URL, data=payload, headers=headers, timeout=10, allow_redirects=False)

        # Laravel redirige si el login fue exitoso (302)
        if resp.status_code in (302, 303):
            print("✅ Login exitoso")
            return True
        else:
            print("❌ Login falló:", resp.status_code)
            return False
    except Exception as e:
        print("⚠️ Error en login:", e)
        return False


def obtener_productos(page=1):
    """Descarga la lista de productos (requiere sesión activa)."""
    params = {
        "column": "description",
        "isEcommerce": "false",
        "isPharmacy": "false",
        "isRestaurant": "false",
        "list_value": "all",
        "page": page,
        "sort_direction": "desc",
        "sort_field": "id",
        "type": "PRODUCTS",
        "value": ""
    }

    try:
        resp = session.get(PRODUCTS_URL, params=params, timeout=10)
        if resp.status_code == 401:  # sesión caducada
            print("🔄 Sesión caducada, relogueando...")
            if login():
                resp = session.get(PRODUCTS_URL, params=params, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        items = data.get('data') or data.get('items') or []
        meta = data.get('meta', {})
        current_page = meta.get('current_page', int(page))
        last_page = meta.get('last_page', current_page)

        # Ajustar formato
        for item in items:
            item['image'] = (
                item.get('image_url_small') or
                item.get('image_url_medium') or
                item.get('image_url') or
                "https://rj.seguricloud.com/logo/imagen-no-disponible.jpg"
            )
            item['id'] = item.get('id', '')
            raw_price = str(item.get('sale_unit_price', '0')).replace('\\', '')
            try:
                item['price'] = int(float(raw_price))
            except:
                item['price'] = 0
            item['stock'] = int(float(item.get('stock', 0)))

        return items, current_page, last_page

    except Exception as e:
        print("❌ Error obteniendo productos:", e)
        return [], 1, 1


@app.route('/')
def index():
    page = request.args.get('page', 1)
    items, current_page, last_page = obtener_productos(page)
    numero_wtsp = "51987654321"  # WhatsApp destino
    return render_template(
        'index.html',
        items=items,
        current_page=current_page,
        last_page=last_page,
        numero=numero_wtsp
    )


if __name__ == '__main__':
    print("🔐 Iniciando login automático...")
    if not login():
        print("⚠️ No se pudo loguear al iniciar (pero el sistema intentará en el primer fetch).")
    app.run(debug=True, host='0.0.0.0', port=5000)
