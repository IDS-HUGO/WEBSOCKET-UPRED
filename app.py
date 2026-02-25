import os
from contextlib import contextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Cargar variables desde .env si existe
load_dotenv()

# Configuración desde variables de entorno
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-production")
FLASK_ENV = os.getenv("FLASK_ENV", "development")
CORS_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
SSL_CERT = os.getenv("SSL_CERT_FILE", "")
SSL_KEY = os.getenv("SSL_KEY_FILE", "")

# Soporta DATABASE_URL directo o los mismos DB_* que usa la API
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "5432") or "5432")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL and DB_HOST and DB_USER and DB_NAME:
    password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    auth = f"{DB_USER}:{password}" if DB_PASSWORD else DB_USER
    DATABASE_URL = f"postgresql://{auth}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# CORS para REST endpoints
CORS(app, origins=CORS_ORIGINS if CORS_ORIGINS != "*" else "*", supports_credentials=True)

# SocketIO con CORS configurable
socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode="eventlet",
    logger=FLASK_ENV == "development",
    engineio_logger=FLASK_ENV == "development",
)


# =====================================================================
# CONEXIÓN A BASE DE DATOS
# =====================================================================

@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos"""
    conn = None
    try:
        if not DATABASE_URL:
            raise Exception("DATABASE_URL no configurada")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB-ERROR] {e}")
        raise
    finally:
        if conn:
            conn.close()


# =====================================================================
# FUNCIONES DE BASE DE DATOS
# =====================================================================

def get_or_create_direct_chat(user_a_id, user_b_id):
    """Obtiene o crea una sala de chat directa entre dos usuarios"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Ordenar IDs para búsqueda consistente
            menor_id = min(int(user_a_id), int(user_b_id))
            mayor_id = max(int(user_a_id), int(user_b_id))
            
            # Intentar obtener sala existente
            cursor.execute("""
                SELECT id, sala_uuid
                FROM salas_chat
                WHERE tipo_sala = 'directo'
                AND LEAST(usuario_a_id, usuario_b_id) = %s
                AND GREATEST(usuario_a_id, usuario_b_id) = %s
            """, (menor_id, mayor_id))
            
            sala = cursor.fetchone()
            
            if sala:
                return dict(sala)
            
            # Crear nueva sala
            cursor.execute("""
                INSERT INTO salas_chat (tipo_sala, usuario_a_id, usuario_b_id)
                VALUES ('directo', %s, %s)
                RETURNING id, sala_uuid
            """, (menor_id, mayor_id))
            
            nueva_sala = cursor.fetchone()
            return dict(nueva_sala)
            
    except Exception as e:
        print(f"[DB-ERROR] get_or_create_direct_chat: {e}")
        return None


def get_or_create_group_chat(group_id):
    """Obtiene o crea una sala de chat grupal"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Intentar obtener sala existente
            cursor.execute("""
                SELECT id, sala_uuid
                FROM salas_chat
                WHERE tipo_sala = 'grupal' AND grupo_id = %s
            """, (int(group_id),))
            
            sala = cursor.fetchone()
            
            if sala:
                return dict(sala)
            
            # Crear nueva sala
            cursor.execute("""
                INSERT INTO salas_chat (tipo_sala, grupo_id)
                VALUES ('grupal', %s)
                RETURNING id, sala_uuid
            """, (int(group_id),))
            
            nueva_sala = cursor.fetchone()
            return dict(nueva_sala)
            
    except Exception as e:
        print(f"[DB-ERROR] get_or_create_group_chat: {e}")
        return None


def save_message(sala_chat_id, sender_id, message_type, content, url_archivo=None, metadatos=None):
    """Guarda un mensaje en la base de datos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insertar mensaje
            cursor.execute("""
                INSERT INTO mensajes (sala_chat_id, remitente_id, tipo_mensaje, contenido, url_archivo, metadatos)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, mensaje_uuid, enviado_en
            """, (
                int(sala_chat_id),
                int(sender_id),
                message_type,
                content,
                url_archivo,
                metadatos or {}
            ))
            
            mensaje = cursor.fetchone()
            return dict(mensaje)
            
    except Exception as e:
        print(f"[DB-ERROR] save_message: {e}")
        return None


def mark_message_delivered(mensaje_id, destinatario_id):
    """Marca un mensaje como entregado a un destinatario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO destinatarios_mensaje (mensaje_id, destinatario_id, entregado_en)
                VALUES (%s, %s, NOW())
                ON CONFLICT (mensaje_id, destinatario_id)
                DO UPDATE SET entregado_en = NOW()
            """, (int(mensaje_id), int(destinatario_id)))
            
            return True
            
    except Exception as e:
        print(f"[DB-ERROR] mark_message_delivered: {e}")
        return False


# =====================================================================
# WEBSOCKET HANDLERS
# =====================================================================



@app.route("/")
def health_check():
    return {
        "status": "ok",
        "service": "websocket_redUP",
    }, 200


@socketio.on("connect")
def on_connect(auth=None):
    user_id = request.args.get("user_id")

    if not user_id:
        print("[CONNECT-ERROR] Conexión rechazada: falta user_id en query params")
        return False
    
    # Validación básica del user_id
    user_id = str(user_id).strip()
    if len(user_id) == 0 or len(user_id) > 100:
        print(f"[CONNECT-ERROR] user_id inválido: longitud={len(user_id)}")
        return False

    join_room(user_id)
    print(f"[CONNECT] user_id={user_id} | sid={request.sid} | unido a room='{user_id}'")

    emit(
        "connected",
        {
            "status": "connected",
            "user_id": user_id,
            "sid": request.sid,
        },
    )


@socketio.on("disconnect")
def on_disconnect():
    print(f"[DISCONNECT] sid={request.sid}")


@socketio.on("join_group")
def on_join_group(data):
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para join_group"})
        return

    user_id = request.args.get("user_id", "unknown")
    group_id = data.get("group_id")

    if not group_id:
        emit("error", {"message": "group_id es requerido"})
        return

    group_id = str(group_id)
    join_room(group_id)

    print(f"[JOIN_GROUP] user_id={user_id} | sid={request.sid} | group_id={group_id}")

    emit(
        "group_joined",
        {
            "status": "ok",
            "group_id": group_id,
            "user_id": user_id,
        },
    )


@socketio.on("send_message")
def on_send_message(data):
    """
    Maneja el envío de mensajes (directo o grupal) y los guarda en la BD
    
    Formato esperado:
    {
        "to": "user_123" o "group_456",
        "message": "Texto del mensaje",
        "sender_id": "123",
        "timestamp": "2024-01-15T10:30:00Z",
        "type": "directo" o "grupal",
        "message_type": "texto" (opcional, default: "texto")
        "url_archivo": "https://..." (opcional)
    }
    """
    required_fields = ["to", "message", "sender_id", "timestamp", "type"]

    if not isinstance(data, dict):
        emit("ack", {"status": "error", "message": "Payload inválido"})
        return

    missing = [field for field in required_fields if field not in data]
    if missing:
        emit(
            "ack",
            {
                "status": "error",
                "message": f"Faltan campos: {', '.join(missing)}",
            },
        )
        return

    # Normalizar datos
    to = str(data["to"])
    sender_id = str(data["sender_id"])
    chat_type = str(data["type"]).lower()
    message_type = str(data.get("message_type", "texto")).lower()
    message_content = data["message"]
    url_archivo = data.get("url_archivo")
    timestamp = data["timestamp"]

    # Validar tipo de mensaje
    valid_message_types = ["texto", "imagen", "archivo", "audio", "sistema"]
    if message_type not in valid_message_types:
        emit("ack", {
            "status": "error",
            "message": f"message_type debe ser uno de: {', '.join(valid_message_types)}"
        })
        return

    print(
        "[SEND_MESSAGE] "
        f"from={sender_id} "
        f"to={to} "
        f"type={chat_type} "
        f"message_type={message_type} "
        f"timestamp={timestamp}"
    )

    # Intentar guardar en base de datos
    mensaje_guardado = None
    sala_chat = None
    
    try:
        # Crear/obtener sala de chat según el tipo
        if chat_type == "directo":
            # Para chat directo, 'to' debe ser el user_id del destinatario
            sala_chat = get_or_create_direct_chat(sender_id, to)
        elif chat_type == "grupal":
            # Para chat grupal, 'to' debe ser el group_id
            sala_chat = get_or_create_group_chat(to)
        else:
            emit("ack", {
                "status": "error",
                "message": "type debe ser 'directo' o 'grupal'"
            })
            return
        
        if not sala_chat:
            emit("ack", {
                "status": "error",
                "message": "No se pudo crear/obtener sala de chat"
            })
            return
        
        # Guardar mensaje
        metadatos = {
            "client_timestamp": timestamp,
            "original_to": to
        }
        
        mensaje_guardado = save_message(
            sala_chat["id"],
            sender_id,
            message_type,
            message_content,
            url_archivo,
            metadatos
        )
        
    except Exception as e:
        print(f"[ERROR] Error al guardar mensaje: {e}")
        # Continuar con entrega aunque falle BD (modo fallback)
    
    # Preparar datos para emitir
    message_data = {
        "from": sender_id,
        "to": to,
        "message": message_content,
        "type": chat_type,
        "message_type": message_type,
        "timestamp": timestamp,
        "url_archivo": url_archivo
    }
    
    # Si se guardó en BD, agregar info adicional
    if mensaje_guardado:
        message_data["mensaje_id"] = str(mensaje_guardado["id"])
        message_data["mensaje_uuid"] = str(mensaje_guardado["mensaje_uuid"])
        message_data["enviado_en"] = mensaje_guardado["enviado_en"].isoformat()
        message_data["sala_chat_id"] = str(sala_chat["id"])

    # Emitir mensaje al destinatario (room)
    emit("receive_message", message_data, room=to)

    # Enviar confirmación al remitente
    emit(
        "ack",
        {
            "status": "sent",
            "to": to,
            "sender_id": sender_id,
            "timestamp": timestamp,
            "type": chat_type,
            "message_type": message_type,
            "saved_to_db": mensaje_guardado is not None,
            "mensaje_id": str(mensaje_guardado["id"]) if mensaje_guardado else None,
            "sala_chat_id": str(sala_chat["id"]) if sala_chat else None,
            "message": "Mensaje enviado" + (" y guardado en BD" if mensaje_guardado else "")
        },
    )



@socketio.on("mark_delivered")
def on_mark_delivered(data):
    """
    Marca un mensaje como entregado
    
    Formato esperado:
    {
        "mensaje_id": "123",
        "user_id": "456"
    }
    """
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para mark_delivered"})
        return
    
    mensaje_id = data.get("mensaje_id")
    user_id = data.get("user_id")
    
    if not mensaje_id or not user_id:
        emit("error", {"message": "mensaje_id y user_id son requeridos"})
        return
    
    try:
        success = mark_message_delivered(mensaje_id, user_id)
        if success:
            print(f"[MARK_DELIVERED] mensaje_id={mensaje_id} | user_id={user_id}")
            emit("delivery_confirmed", {
                "status": "ok",
                "mensaje_id": mensaje_id,
                "user_id": user_id
            })
        else:
            emit("error", {"message": "No se pudo marcar el mensaje como entregado"})
    except Exception as e:
        print(f"[ERROR] mark_delivered: {e}")
        emit("error", {"message": "Error al marcar mensaje como entregado"})


if __name__ == "__main__":
    # Advertencia de seguridad
    if app.config["SECRET_KEY"] == "super-secret-key-change-me-in-production":
        print("⚠️  [ADVERTENCIA] Usando SECRET_KEY por defecto. Cámbiala en .env para producción!")
    
    # Verificar configuración de base de datos
    if not DATABASE_URL:
        print("⚠️  [ADVERTENCIA] DATABASE_URL no configurada. Los mensajes NO se guardarán en BD.")
        print("    Configura DATABASE_URL en .env para persistencia de mensajes.")
    else:
        print("✓ [DB] Conexión a base de datos configurada")
        # Probar conexión
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()
                print(f"✓ [DB] Conexión exitosa: PostgreSQL")
        except Exception as e:
            print(f"✗ [DB-ERROR] No se pudo conectar a la base de datos: {e}")
            print("    Los mensajes NO se guardarán en BD.")
    
    # Configurar SSL si se proporcionan certificados
    ssl_args = {}
    if SSL_CERT and SSL_KEY and os.path.exists(SSL_CERT) and os.path.exists(SSL_KEY):
        ssl_args = {
            "certfile": SSL_CERT,
            "keyfile": SSL_KEY,
        }
        print(f"🔒 [SSL] HTTPS habilitado con certificados")
        protocol = "https"
    else:
        protocol = "http"
        if FLASK_ENV == "production" and not SSL_CERT:
            print("ℹ️  [INFO] Sin SSL directo. Asegúrate de usar Nginx/proxy con HTTPS")
    
    print(f"[INICIO] Servidor corriendo en {protocol}://{HOST}:{PORT}")
    print(f"[CORS] Orígenes permitidos: {CORS_ORIGINS}")
    print(f"[ENV] Entorno: {FLASK_ENV}")
    
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=(FLASK_ENV == "development"),
        allow_unsafe_werkzeug=(FLASK_ENV == "development"),
        **ssl_args,
    )
