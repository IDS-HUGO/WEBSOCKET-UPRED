# Lista de Verificación - Seguridad y Producción

## ✅ CAMBIOS REALIZADOS

### 1. CORS Configurable
- ✅ CORS ahora se configura por variable de entorno `CORS_ALLOWED_ORIGINS`
- ✅ En desarrollo: `*` (permite todos los orígenes)
- ✅ En producción: lista específica de dominios
- ✅ Agregado `Flask-Cors` para endpoints REST

### 2. Variables de Entorno
- ✅ `SECRET_KEY` ya no está hardcodeada
- ✅ `FLASK_ENV` para separar dev/producción
- ✅ `HOST` y `PORT` configurables
- ✅ Archivo `.env.example` como plantilla
- ✅ `.env` incluido en `.gitignore` (no se sube a Git)

### 3. Seguridad Git
- ✅ Desactivada firma GPG de commits
- ✅ `.gitignore` completo para Python
- ✅ Excluye archivos sensibles (.env, venv, __pycache__)

### 4. Código subido a GitHub
- ✅ Repositorio: https://github.com/IDS-HUGO/WEBSOCKET_REDUP
- ✅ Commits con mensajes descriptivos
- ✅ README actualizado con instrucciones completas

---

## 🔒 RECOMENDACIONES DE SEGURIDAD ADICIONALES

### Antes de ir a producción

#### 1. SECRET_KEY
Genera una clave aleatoria fuerte:

```python
import secrets
print(secrets.token_urlsafe(32))
```

Cópiala en `.env`:

```env
SECRET_KEY=TuClaveGeneradaAqui_gFx9m2kL8pQ3vR7w
```

#### 2. Validación de user_id
Actualmente el servidor confía en el `user_id` del cliente. Para producción:

```python
# app.py - MEJORA DE SEGURIDAD
from functools import wraps
import jwt

def verificar_token(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return False
        
        try:
            datos = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = datos['user_id']
            return f(*args, **kwargs)
        except:
            return False
    return decorador

@socketio.on("connect")
@verificar_token
def on_connect(auth=None):
    user_id = request.user_id  # Ya verificado por JWT
    join_room(user_id)
    # ...
```

#### 3. Rate Limiting
Prevenir abuso de endpoints:

```bash
pip install Flask-Limiter
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/registro", methods=["POST"])
@limiter.limit("5 per hour")
def registro():
    # ...
```

#### 4. HTTPS Obligatorio
En producción, fuerza HTTPS:

```python
from flask_talisman import Talisman

if FLASK_ENV == "production":
    Talisman(app, force_https=True)
```

#### 5. Sanitización de Inputs
Valida y limpia todos los datos de entrada:

```python
from bleach import clean

@socketio.on("send_message")
def on_send_message(data):
    # Sanitizar contenido
    data['message'] = clean(data['message'], strip=True)
    
    # Validar longitud
    if len(data['message']) > 5000:
        emit("error", {"message": "Mensaje muy largo"})
        return
    
    # ...
```

#### 6. Logging en Producción
No uses `print()`, usa `logging`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('websocket.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@socketio.on("connect")
def on_connect():
    logger.info(f"Usuario conectado: user_id={user_id}, ip={request.remote_addr}")
    # ...
```

#### 7. Base de Datos - Conexión Segura
Usa SSL para PostgreSQL en producción:

```python
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(
    DATABASE_URL,
    sslmode='require'  # Fuerza SSL
)
```

#### 8. Headers de Seguridad
Agrega headers de seguridad HTTP:

```python
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

#### 9. Protección contra SQL Injection
Las funciones PL/pgSQL ya están parametrizadas, pero al llamarlas desde Python:

```python
# ✅ BIEN - Usar parámetros
cursor.execute(
    "SELECT fn_registrar_estudiante(%s, %s, %s, %s, %s, %s)",
    (correo, hash_password, nombre, apellido_p, apellido_m, fecha_nac)
)

# ❌ MAL - Concatenar strings
cursor.execute(
    f"SELECT fn_registrar_estudiante('{correo}', ...)"  # VULNERABLE
)
```

#### 10. Manejo de Sesiones
Usa Redis para almacenar sesiones de Socket.IO:

```bash
pip install redis
```

```python
from redis import Redis

redis_client = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=6379,
    decode_responses=True
)

socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode='eventlet',
    message_queue='redis://localhost:6379'  # Para múltiples workers
)
```

---

## 📋 CHECKLIST PRE-PRODUCCIÓN

Antes de lanzar:

- [ ] `SECRET_KEY` generada aleatoriamente
- [ ] `CORS_ALLOWED_ORIGINS` con dominios específicos
- [ ] HTTPS activado (Let's Encrypt + Nginx/Caddy)
- [ ] JWT para autenticación de WebSocket
- [ ] Rate limiting en endpoints críticos
- [ ] Logs en archivos (no `print`)
- [ ] Monitoreo de errores (Sentry / Rollbar)
- [ ] Backups automáticos de PostgreSQL
- [ ] Variables de entorno en secretos (no en `.env` en servidor)
- [ ] Firewall configurado (solo puertos 80, 443, 22)
- [ ] PostgreSQL con SSL/TLS
- [ ] Sanitización de inputs
- [ ] Headers de seguridad HTTP
- [ ] Documentación de API actualizada
- [ ] Tests de carga (Locust / Artillery)

---

## 🚀 DESPLIEGUE RECOMENDADO

### Opción 1: VPS (DigitalOcean, Linode, etc.)

```bash
# Ubuntu 22.04 LTS
sudo apt update
sudo apt install -y python3.11 python3.11-venv postgresql nginx certbot

# Crear usuario
sudo adduser websocket
sudo usermod -aG sudo websocket

# Clonar repo
cd /home/websocket
git clone https://github.com/IDS-HUGO/WEBSOCKET_REDUP.git
cd WEBSOCKET_REDUP

# Configurar
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
nano .env  # Editar con valores de producción

# Systemd service
sudo nano /etc/systemd/system/websocket.service
```

```ini
[Unit]
Description=WebSocket RedUP
After=network.target

[Service]
Type=notify
User=websocket
WorkingDirectory=/home/websocket/WEBSOCKET_REDUP
Environment="PATH=/home/websocket/WEBSOCKET_REDUP/.venv/bin"
ExecStart=/home/websocket/WEBSOCKET_REDUP/.venv/bin/gunicorn \
    --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    app:app

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable websocket
sudo systemctl start websocket
sudo systemctl status websocket
```

### Opción 2: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
      - DATABASE_URL=postgresql://postgres:password@db:5432/red_social_uni
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=red_social_uni
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database_schema.sql:/docker-entrypoint-initdb.d/schema.sql
  
  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

### Opción 3: Plataformas Cloud

- **Heroku**: `git push heroku main`
- **Railway**: Auto-deploy desde GitHub
- **Render**: Docker deploy
- **AWS Elastic Beanstalk**
- **Google Cloud Run**

---

## 📊 MONITOREO

```bash
pip install prometheus-flask-exporter

# app.py
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'WebSocket RedUP', version='1.0.0')
```

Visualizar con Grafana + Prometheus.

---

## 🧪 TESTING

```bash
pip install pytest pytest-flask pytest-socketio

# tests/test_websocket.py
def test_connect(socketio_client):
    received = socketio_client.get_received()
    assert len(received) > 0
    assert received[0]['name'] == 'connected'
```

---

¿Alguna pregunta sobre seguridad o despliegue?
