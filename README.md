# Servidor de Mensajería en Tiempo Real (Flask-SocketIO)

Backend en Python para chat estilo WhatsApp con Android Studio + Red Social Universitaria.

## Funcionalidades implementadas

### WebSocket (Flask-SocketIO)
- Conexión con `user_id` desde `request.args`.
- Unión automática a room personal (`room = user_id`).
- Evento `join_group` para entrar a rooms grupales (`group_id`).
- Evento `send_message` universal (usuario o grupo).
- Ruteo inteligente: `emit('receive_message', data, room=data['to'])`.
- Confirmación de envío al emisor con evento `ack`.
- Logs de conexión, unión a grupos y envío de mensajes.
- CORS configurable por variable de entorno.

### Base de datos PostgreSQL
- Esquema normalizado completo en español.
- Catálogo de correos institucionales (whitelist de registro).
- Estudiantes con datos completos (nombre, apellidos, edad, carrera, cuatrimestre).
- Publicaciones por carrera/general con multimedia, comentarios y reacciones.
- Grupos con membresía y roles.
- Mensajería 1:1 y grupal con estados de entrega/lectura.
- Funciones SQL listas para registro, publicaciones y mensajes.

## Estructura

- `app.py`: servidor Socket.IO con configuración por `.env`
- `database_schema.sql`: esquema PostgreSQL normalizado completo
- `requirements.txt`: dependencias Python
- `.env.example`: plantilla de configuración
- `.gitignore`: archivos excluidos de Git

## Requisitos

- Python 3.10+ (recomendado 3.11)
- PostgreSQL 15+
- Windows CMD / PowerShell

## 1) Clonar repositorio

```bash
git clone https://github.com/IDS-HUGO/WEBSOCKET_REDUP.git
cd WEBSOCKET_REDUP
```

## 2) Crear y activar entorno virtual (Windows)

En CMD:

```bat
python -m venv .venv
.venv\Scripts\activate
```

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Configurar variables de entorno

Copia `.env.example` a `.env` y ajusta:

```bash
copy .env.example .env
```

### Para DESARROLLO:

```env
SECRET_KEY=dev-secret-key-local-only
FLASK_ENV=development
CORS_ALLOWED_ORIGINS=*
PORT=5000
HOST=0.0.0.0
SSL_CERT_FILE=
SSL_KEY_FILE=
```

### Para PRODUCCIÓN:

```env
SECRET_KEY=TuClaveGeneradaAleatoriaSegura123xyz
FLASK_ENV=production
CORS_ALLOWED_ORIGINS=https://tuapp.com,https://www.tuapp.com
PORT=5000
HOST=0.0.0.0
SSL_CERT_FILE=
SSL_KEY_FILE=
```

> ⚠️ **Importante**: Genera un `SECRET_KEY` aleatorio con:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

## 4) Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 5) Crear base de datos PostgreSQL

```bash
createdb red_social_uni
psql -d red_social_uni -f database_schema.sql
```

## 6) Ejecutar servidor

```bash
python app.py
```

Verás logs como:

```
[INICIO] Servidor corriendo en 0.0.0.0:5000
[CORS] Orígenes permitidos: *
[ENV] Entorno: development
[CONNECT] user_id=123 ...
[JOIN_GROUP] user_id=123 ... group_id=grupo_1
[SEND_MESSAGE] from=123 to=grupo_1 ...
```

## 4) Cómo conectar desde Android (Socket.IO client)

URL base local:

- Emulador Android Studio hacia host local: `http://10.0.2.2:5000`
- Teléfono en misma red WiFi: `http://IP_DE_TU_PC:5000`

Conexión con query param `user_id`:

- `http://10.0.2.2:5000?user_id=123`
- `http://192.168.1.50:5000?user_id=123`

## 5) Payload esperado para `send_message`

```json
{
  "to": "456_o_grupo_1",
  "message": "Hola",
  "sender_id": "123",
  "timestamp": "2026-02-21T20:15:00Z",
  "type": "text"
}
```

`type` puede ser `text` o `image`.

## 6) Evento para grupos

Enviar a `join_group`:

```json
{
  "group_id": "grupo_1"
}
```

## 7) Conectar “desde cualquier lugar” (internet)

Para acceso externo real necesitas exponer tu servidor:

- Opción rápida: usar `ngrok` (recomendado para pruebas)
- Opción permanente: VPS/Cloud + dominio + HTTPS + reverse proxy

### ngrok rápido (solo pruebas)

1. Instala ngrok y autentica tu cuenta.
2. Con el server corriendo en `5000`, ejecuta:

```bash
ngrok http 5000
```

3. Usa la URL pública `https://xxxx.ngrok-free.app` en Android.

---

## 8) Despliegue en producción con HTTPS

### ✅ Opción 1: Nginx como Proxy Inverso (RECOMENDADO)

Esta es la forma más segura y eficiente. Nginx maneja SSL/TLS y redirige al servidor Flask.

**En tu servidor EC2/VPS (Ubuntu/Debian):**

```bash
# 1. Instalar Nginx y Certbot
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y

# 2. Configurar Nginx
sudo nano /etc/nginx/sites-available/default
```

**Configuración Nginx:**

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
# 3. Obtener certificado SSL gratuito
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com

# 4. Reiniciar Nginx
sudo systemctl restart nginx
```

**Actualizar `.env` en el servidor:**

```env
FLASK_ENV=production
CORS_ALLOWED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
HOST=127.0.0.1
PORT=5000
SSL_CERT_FILE=
SSL_KEY_FILE=
```

**Conectar desde tu app:**

```javascript
const socket = io('https://tu-dominio.com', {
  query: { user_id: 'usuario123' }
});
```

---

### Opción 2: SSL Directo en Flask (solo si NO usas Nginx)

Si por alguna razón no puedes usar Nginx, puedes configurar SSL directamente:

**1. Obtener certificados SSL:**

```bash
# Usando certbot standalone
sudo certbot certonly --standalone -d tu-dominio.com
```

**2. Configurar `.env`:**

```env
SSL_CERT_FILE=/etc/letsencrypt/live/tu-dominio.com/fullchain.pem
SSL_KEY_FILE=/etc/letsencrypt/live/tu-dominio.com/privkey.pem
FLASK_ENV=production
PORT=443
HOST=0.0.0.0
```

**3. Ejecutar con permisos (puerto 443 requiere root):**

```bash
sudo python app.py
```

> ⚠️ **No recomendado**: Flask no está optimizado para servir SSL directamente. Usa Nginx en producción.

---

## 9) Crear servicio systemd (auto-inicio en servidor)

```bash
sudo nano /etc/systemd/system/websocket-app.service
```

```ini
[Unit]
Description=WebSocket RedUP Server
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/WEBSOCKET_REDUP
Environment="PATH=/home/ubuntu/WEBSOCKET_REDUP/.venv/bin"
EnvironmentFile=/home/ubuntu/WEBSOCKET_REDUP/.env
ExecStart=/home/ubuntu/WEBSOCKET_REDUP/.venv/bin/python app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable websocket-app
sudo systemctl start websocket-app
sudo systemctl status websocket-app
```

**Ver logs:**

```bash
sudo journalctl -u websocket-app -f
```

---

## 10) Checklist de seguridad para producción

- [ ] `SECRET_KEY` generado aleatoriamente (no usar el de ejemplo)
- [ ] `FLASK_ENV=production` en `.env`
- [ ] `CORS_ALLOWED_ORIGINS` con dominios específicos (no `*`)
- [ ] HTTPS habilitado (Nginx + Let's Encrypt)
- [ ] Firewall configurado (solo puertos 80, 443, 22)
- [ ] Autenticación JWT implementada (recomendado)
- [ ] Rate limiting para prevenir abuso
- [ ] Variables sensibles en `.env` (nunca en código)
- [ ] Certificados SSL renovados automáticamente

> Nota: Este servidor acepta cualquier `user_id` sin validación. Para producción, implementa autenticación JWT o similar.
