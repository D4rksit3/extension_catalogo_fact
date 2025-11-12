from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://ventas.seguricloud.com"
LOGIN_URL = f"{BASE_URL}/login"
PRODUCTS_URL = f"{BASE_URL}/items/records"

EMAIL = "admin@ventas.com"
PASSWORD = "DyEo3mVn*"

session = requests.Session()

def login():
    """Obtiene el token CSRF y realiza el login."""
    try:
        resp = session.get(LOGIN_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if not token_input:
            raise ValueError("No se encontró el token CSRF.")
        csrf_token = token_input["value"]

        payload = {"_token": csrf_token, "email": EMAIL, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = session.post(LOGIN_URL, data=payload, headers=headers, allow_redirects=False)

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
        if resp.status_code == 401:
            print("🔄 Sesión caducada, relogueando...")
            if login():
                resp = session.get(PRODUCTS_URL, params=params, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        items = data.get("data", [])
        meta = data.get("meta", {})
        current_page = meta.get("current_page", int(page))
        last_page = meta.get("last_page", current_page)

        # Procesar productos
        for item in items:
            # Imagen de alta calidad (preferir second_name si es URL)
            image_hd = item.get("second_name", "")
            if image_hd and image_hd.startswith("http"):
                item["image"] = image_hd
            else:
                item["image"] = item.get("image_url") or "https://ventas.seguricloud.com/logo/imagen-no-disponible.jpg"

            # Precio limpio
            raw_price = item.get("sale_unit_price", "0").replace("\\", "").replace("S/", "").strip()
            try:
                item["price"] = float(raw_price)
            except:
                item["price"] = 0.0

            # 🛑 CAMBIO REALIZADO AQUÍ: Extrae solo la 'description' de cada unidad de tipo
            item["sizes"] = [s.get("description", "") for s in item.get("item_unit_types", [])]

            # Filtros
            item["brand"] = item.get("brand", "Sin marca") or "Sin marca"
            item["category"] = item.get("category_description", "Sin categoría") or "Sin categoría"

        return items, current_page, last_page

    except Exception as e:
        print("❌ Error obteniendo productos:", e)
        return [], 1, 1


@app.route("/")
def index():
    page = request.args.get("page", 1)
    marca = request.args.get("marca", "")
    categoria = request.args.get("categoria", "")

    items, current_page, last_page = obtener_productos(page)

    # Filtros dinámicos
    marcas = sorted(set(i["brand"] for i in items if i["brand"]))
    categorias = sorted(set(i["category"] for i in items if i["category"]))

    # Filtrado
    if marca:
        items = [i for i in items if i["brand"] == marca]
    if categoria:
        items = [i for i in items if i["category"] == categoria]

    numero_wtsp = "51926804683"

    return render_template(
        "index.html",
        items=items,
        current_page=current_page,
        last_page=last_page,
        marcas=marcas,
        categorias=categorias,
        marca_actual=marca,
        categoria_actual=categoria,
        numero=numero_wtsp
    )


@app.route("/api/productos")
def api_productos():
    """Devuelve los productos en formato JSON limpio para el frontend."""
    # Nota: Aquí se llama obtener_productos(1) para obtener todos los datos,
    # el frontend se encarga del filtrado y paginación si se usa el JSON completo.
    items, _, _ = obtener_productos(1) 
    
    # Se añade la clave 'sizes' a cada producto en el JSON devuelto
    return jsonify(items)

if __name__ == "__main__":
    print("🔐 Iniciando login automático...")
    if not login():
        print("⚠️ No se pudo loguear al iniciar.")
    app.run(debug=True, host="0.0.0.0", port=5000)