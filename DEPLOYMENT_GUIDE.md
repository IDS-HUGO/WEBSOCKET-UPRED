# WebSocket REDUP - Guía de Deployment Independiente

## ✓ Arquitectura

El servidor WebSocket (`WEBSOCKET_REDUP`) funciona **completamente independiente** de la API (`API_UPRed`):

```
┌─────────────────────────────────────────────────────────┐
│                    RED-UP Mobile (Android)              │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    Socket.IO (Real-time)        HTTP REST (Data)
    (Puerto 5000)                (Puerto 8000)
         │                              │
         ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│  WEBSOCKET_REDUP     │      │    API_UPRed         │
│  (Flask-SocketIO)    │      │    (FastAPI)         │
│  - Chat Messaging    │      │ - Auth               │
│  - Room Management   │      │ - Publicaciones      │
│  - Real-time Events  │      │ - Grupos             │
└──────────────────────┘      │ - Usuarios           │
         │                      │ - Comentarios       │
         ▼                      ▼
    ┌─────────────────────────────┐
    │      MySQL Database         │
    │      (Shared Schema)        │
    └─────────────────────────────┘
```

## 📋 Requisitos

### Sistema:
- Python 3.8+
- MySQL 5.7+ (servidor ejecutándose)
- Puerto 5000 disponible (configurable en `.env`)

### Dependencias Python:
```bash
pip install -r requirements.txt
```

Dependencias incluidas:
- `Flask` - Framework web
- `Flask-SocketIO` - WebSocket en Flask
- `Flask-CORS` - Soporte CORS
- `python-dotenv` - Gestión de variables .env
- `PyMySQL` - Driver de MySQL
- `cloudinary` - Almacenamiento de imágenes
- `eventlet` - WSGI async server

## 🚀 Instalación y Setup

### 1. Clonar repositorio
```bash
git clone https://github.com/IDS-HUGO/WEBSOCKET_REDUP.git
cd WEBSOCKET_REDUP
```

### 2. Crear entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Copiar template
cp .env.example .env

# Editar .env con tu configuración
nano .env  # o usa tu editor favorito
```

#### Variables necesarias en `.env`:
```bash
# Server Config
SECRET_KEY=tu-secret-key-segura-aqui
FLASK_ENV=development  # o "production"
HOST=0.0.0.0          # Para aceptar conexiones remotas
PORT=5000
CORS_ALLOWED_ORIGINS=*  # O especifica: http://localhost:3000,http://192.168.x.x

# Database (MySQL) - Misma DB que la API
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu-contraseña
DB_NAME=upred_db

# Cloudinary (Opcional - para subida de imágenes)
CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret

# SSL (Opcional - para HTTPS/WSS)
SSL_CERT_FILE=
SSL_KEY_FILE=
```

### 5. Validar instalación
```bash
python validate_standalone.py
```

Debe mostrar:
```
✓ VALIDACIÓN EXITOSA: WebSocket está listo para deploy
```

### 6. Ejecutar servidor

**Desarrollo:**
```bash
python app.py
```

Salida esperada:
```
 * Running on http://0.0.0.0:5000
 * SocketIO server started
```

**Producción (con SSL):**
```bash
FLASK_ENV=production \
SSL_CERT_FILE=/path/to/cert.pem \
SSL_KEY_FILE=/path/to/key.pem \
python app.py
```

## 🧪 Testing

### Verificar conectividad WebSocket
```bash
# Desde otra terminal, usa un cliente WebSocket:
# Python
pip install python-socketio
python -c "
import socketio
sio = socketio.Client()
@sio.connect
def on_connect():
    print('Conectado al WebSocket')
@sio.on('receive_message')
def on_message(data):
    print('Mensaje:', data)
sio.connect('http://localhost:5000')
"

# O usa un cliente web: https://socket.io/socket.io-client-demo/
```

### Verificar eventos disponibles
```bash
# Los eventos del servidor están documentados en app.py:
# - on_connect: Usuario conecta
# - on_disconnect: Usuario desconecta
# - on_join_direct_chat: Unirse a sala de chat directo
# - on_send_message: Enviar mensaje
# - on_mark_delivered: Marcar mensaje entregado
# - on_mark_read: Marcar mensaje leído
```

## 📱 Integración con Android

### En la app móvil (RED-UP):
1. Obtener IP de la máquina WebSocket:
   ```bash
   # En Linux/Mac:
   hostname -I
   
   # En Windows:
   ipconfig | findstr IPv4
   ```

2. Configurar URL en Android (SocketIoRepository):
   ```kotlin
   val socketUrl = "http://192.168.x.x:5000"  // Usa la IP actual
   ```

3. Conectar:
   ```kotlin
   socketRepository.connect(userId)
   ```

## 🔧 Troubleshooting

### Puerto ya en uso
```bash
# Cambiar puerto en .env
PORT=5001

# O liberar puerto 5000:
# Windows: netstat -ano | findstr :5000
# Linux: lsof -i :5000 | kill -9 <PID>
```

### Conexión a BD falla
```
Error: 2003 - Can't connect to MySQL server on 'localhost'
```
Soluciones:
- Verificar MySQL está ejecutándose: `mysql -u root -p`
- Cambiar `DB_HOST=127.0.0.1` si localhost no funciona
- Verificar credenciales en `.env`
- Crear BD: `mysql -u root -p < database_schema.sql`

### Clientes no reciben mensajes
- Verificar `CORS_ALLOWED_ORIGINS` en `.env`
- Verificar IP del cliente en logs
- Revisar conexión Socket.IO en browser console

### SSL certificate errors
```
SSL: CERTIFICATE_VERIFY_FAILED
```
Si usas certificados auto-firmados:
```python
# En cliente Python:
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

## 📊 Monitoreo de Conexiones

Ver usuarios conectados actualmente:
```bash
# En Python, conectar a servidor Socket.IO y usar eventos disponibles
python app.py  # con FLASK_ENV=development para ver logs detallados
```

Logs mostrarán:
```
[2026-03-11 09:30:15] Usuario 123 conectado (SID: abc123)
[2026-03-11 09:30:20] Usuario 123 unido a sala: direct_chat_uuid
[2026-03-11 09:30:25] Mensaje enviado en sala: direct_chat_uuid
```

## 🚢 Deployment en Producción

### Opción 1: Systemd (Linux)
```bash
# /etc/systemd/system/websocket-redup.service
[Unit]
Description=WebSocket REDUP
After=network.target

[Service]
Type=simple
User=websocket
WorkingDirectory=/home/websocket/WEBSOCKET_REDUP
ExecStart=/home/websocket/WEBSOCKET_REDUP/venv/bin/python app.py
Restart=always
Environment="FLASK_ENV=production"

[Install]
WantedBy=multi-user.target
```

Ejecutar:
```bash
sudo systemctl start websocket-redup
sudo systemctl enable websocket-redup
```

### Opción 2: Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
```

Build y run:
```bash
docker build -t websocket-redup .
docker run -d \
  -e FLASK_ENV=production \
  -e DB_HOST=mysql-container \
  -e SECRET_KEY=tu-secret \
  -p 5000:5000 \
  websocket-redup
```

### Opción 3: Nginx + Gunicorn (Linux)
```bash
# Instalar Gunicorn
pip install gunicorn

# Ejecutar con Gunicorn
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 app:app
```

Config Nginx reverseproxy:
```nginx
upstream websocket {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## ✓ Verificación de Independencia

El WebSocket es completamente independiente:
- ✓ No tiene referencias hardcodeadas a la API
- ✓ Conecta directamente a MySQL (sin pasar por API)
- ✓ Tiene su propio SECRET_KEY y configuración
- ✓ Puede ejecutarse en máquina diferente a la API
- ✓ Solo comparte el schema de BD con la API

Verificar: `python validate_standalone.py`

## 📚 Variables de Entorno Completas

```bash
# Core
SECRET_KEY=change-me-in-production
FLASK_ENV=development                    # development | production
HOST=0.0.0.0                            # 0.0.0.0 para aceptar externo
PORT=5000                               # Puerto Socket.IO

# CORS
CORS_ALLOWED_ORIGINS=*                  # * para desarrollo | especificar en prod

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=upred_db

# Cloudinary (Opcional)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# SSL (Opcional)
SSL_CERT_FILE=
SSL_KEY_FILE=
```

## 🔒 Seguridad en Deployment

1. ✓ Cambiar `SECRET_KEY` en producción
2. ✓ Usar `FLASK_ENV=production`
3. ✓ Restringir `CORS_ALLOWED_ORIGINS` a dominios conocidos
4. ✓ Usar SSL/TLS (WSS en lugar de WS)
5. ✓ Configurar firewall (solo puerto 5000 desde app)
6. ✓ Usar credenciales de BD seguras
7. ✓ Mantener actualizado Python y dependencias

## 📞 Soporte

Para problemas o preguntas:
- Ver logs: `FLASK_ENV=development python app.py`
- Revisar `.env` está correctamente configurado
- Ejecutar: `python validate_standalone.py`
- Consultar troubleshooting arriba

---

**Última actualización:** March 11, 2026
