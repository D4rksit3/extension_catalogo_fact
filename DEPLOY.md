# 🚀 Despliegue a producción — extension_catalogo_fact (storedemo)

Pequeña aplicación **Flask** que actúa de puente/extensión sobre el catálogo de `ventas.seguricloud.com`: hace login automático contra ese sistema, descarga los productos y los expone en una vista/API de catálogo (con enlace a WhatsApp). Servicio systemd: `storedemo`.

## 1. Stack (componentes y puertos)

| Componente | Ruta | Tecnología | Puerto interno | Servicio systemd |
|---|---|---|---|---|
| App web | `/home/ubuntu/extension_catalogo_fact/app.py` | Flask + requests + BeautifulSoup | `0.0.0.0:5000` | `storedemo` |

- Renderiza `templates/index.html` y expone `GET /api/productos` (JSON de productos).
- Consume `https://ventas.seguricloud.com` (login + listado de productos) como backend de datos.
- No hay vhost Apache asociado en la configuración revisada → se accede directo por el puerto **5000** (verificar exposición/proxy).

## 2. Requisitos

- **Python 3** del sistema (la unidad ejecuta `/usr/bin/python3` directamente, **sin venv**).
- Paquetes Python: `flask`, `requests`, `beautifulsoup4` (deben estar instalados a nivel de sistema, ya que no hay entorno virtual ni `requirements.txt` en el repo).
- Salida de red hacia `ventas.seguricloud.com`.

## 3. Base de datos

- No usa base de datos propia. Los datos provienen en vivo del sistema remoto `ventas.seguricloud.com` mediante scraping/API autenticada.

## 4. Variables de entorno requeridas

- La unidad solo define `Environment="PATH=/usr/bin"`. No usa `EnvironmentFile`.
- **Gotcha de seguridad:** las credenciales de acceso al catálogo remoto están **hardcodeadas en `app.py`** (constantes `EMAIL`/`PASSWORD`). Recomendado externalizarlas a variables de entorno/secret y rotarlas; no se reproducen aquí.

| NOMBRE | Descripción |
|---|---|
| (ninguna requerida por la unidad) | Config embebida en el código; ver nota de seguridad |

## 5. Instalación y build

```bash
# Dependencias a nivel de sistema (no hay venv)
sudo pip3 install flask requests beautifulsoup4
```
No hay paso de build.

## 6. Puesta en marcha en producción

**`storedemo.service`**:
```
Description=Storedemo Flask App
User=www-data
WorkingDirectory=/home/ubuntu
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/python3 /home/ubuntu/extension_catalogo_fact/app.py
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now storedemo
```

## 7. Reverse proxy

- No hay vhost Apache dedicado en la config revisada. `app.run(host="0.0.0.0", port=5000)` deja el servicio escuchando en el puerto **5000** en todas las interfaces. (verificar) Si debe publicarse, añadir un vhost con `ProxyPass / http://127.0.0.1:5000/` y cambiar el bind a `127.0.0.1`.

## 8. Comandos útiles

```bash
sudo systemctl restart storedemo
journalctl -u storedemo -f
sudo systemctl status storedemo
curl -s http://127.0.0.1:5000/api/productos | head
```

## 9. Notas / gotchas

- Corre con `app.run(debug=True, ...)`: **modo debug de Flask en producción** (reloader + traceback interactivo Werkzeug). Riesgo de RCE si se expone; conviene desactivar `debug` y usar gunicorn/waitress.
- Escucha en `0.0.0.0:5000` (todas las interfaces) sin proxy: exposición directa a la red. Restringir a `127.0.0.1` + Apache o firewall.
- Depende por completo de que `ventas.seguricloud.com` esté arriba y el login siga siendo válido; si cambian el formulario/CSRF o las credenciales, deja de traer productos.
- Corre como `User=www-data` pero con `WorkingDirectory=/home/ubuntu`.
