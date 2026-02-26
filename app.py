import os
from contextlib import contextmanager
from datetime import datetime
import uuid as uuid_pkg
import json

from dotenv import load_dotenv
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import pymysql

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

# Configuración de MySQL (misma que la API)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "upred_db")

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

# Diccionario para rastrear usuarios conectados y sus rooms
# Formato: {user_id: {"sid": session_id, "rooms": [room1, room2, ...]}}
connected_users = {}

# =====================================================================
# CONEXIÓN A BASE DE DATOS MYSQL
# =====================================================================

@contextmanager
def get_db_connection():
    """Context manager para conexiones a MySQL"""
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
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
                return sala
            
            # Crear nueva sala con UUID
            nuevo_uuid = str(uuid_pkg.uuid4())
            cursor.execute("""
                INSERT INTO salas_chat (sala_uuid, tipo_sala, usuario_a_id, usuario_b_id)
                VALUES (%s, 'directo', %s, %s)
            """, (nuevo_uuid, menor_id, mayor_id))
            
            # Obtener ID insertado
            sala_id = cursor.lastrowid
            return {"id": sala_id, "sala_uuid": nuevo_uuid}
            
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
                return sala
            
            # Crear nueva sala con UUID
            nuevo_uuid = str(uuid_pkg.uuid4())
            cursor.execute("""
                INSERT INTO salas_chat (sala_uuid, tipo_sala, grupo_id)
                VALUES (%s, 'grupal', %s)
            """, (nuevo_uuid, int(group_id)))
            
            # Obtener ID insertado
            sala_id = cursor.lastrowid
            return {"id": sala_id, "sala_uuid": nuevo_uuid}
            
    except Exception as e:
        print(f"[DB-ERROR] get_or_create_group_chat: {e}")
        return None


def save_message(sala_chat_id, sender_id, message_type, content, url_archivo=None, metadatos=None):
    """Guarda un mensaje en la base de datos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Crear UUID para el mensaje
            nuevo_uuid = str(uuid_pkg.uuid4())
            metadatos_json = json.dumps(metadatos) if metadatos else None
            
            # Insertar mensaje
            cursor.execute("""
                INSERT INTO mensajes (
                    mensaje_uuid, sala_chat_id, remitente_id, 
                    tipo_mensaje, contenido, url_archivo, metadatos
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                nuevo_uuid,
                int(sala_chat_id),
                int(sender_id),
                message_type,
                content,
                url_archivo,
                metadatos_json
            ))
            
            # Obtener ID insertado
            mensaje_id = cursor.lastrowid
            
            # Obtener el mensaje completo con timestamp
            cursor.execute("""
                SELECT id, mensaje_uuid, enviado_en
                FROM mensajes
                WHERE id = %s
            """, (mensaje_id,))
            
            mensaje = cursor.fetchone()
            return mensaje
            
    except Exception as e:
        print(f"[DB-ERROR] save_message: {e}")
        return None


def mark_message_delivered(mensaje_id, destinatario_id):
    """Marca un mensaje como entregado a un destinatario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe el registro
            cursor.execute("""
                SELECT mensaje_id FROM destinatarios_mensaje
                WHERE mensaje_id = %s AND destinatario_id = %s
            """, (int(mensaje_id), int(destinatario_id)))
            
            if cursor.fetchone():
                # Actualizar
                cursor.execute("""
                    UPDATE destinatarios_mensaje
                    SET entregado_en = NOW()
                    WHERE mensaje_id = %s AND destinatario_id = %s
                """, (int(mensaje_id), int(destinatario_id)))
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO destinatarios_mensaje (mensaje_id, destinatario_id, entregado_en)
                    VALUES (%s, %s, NOW())
                """, (int(mensaje_id), int(destinatario_id)))
            
            return True
            
    except Exception as e:
        print(f"[DB-ERROR] mark_message_delivered: {e}")
        return False


def mark_message_read(mensaje_id, destinatario_id):
    """Marca un mensaje como leído por un destinatario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe el registro
            cursor.execute("""
                SELECT mensaje_id FROM destinatarios_mensaje
                WHERE mensaje_id = %s AND destinatario_id = %s
            """, (int(mensaje_id), int(destinatario_id)))
            
            if cursor.fetchone():
                # Actualizar
                cursor.execute("""
                    UPDATE destinatarios_mensaje
                    SET leido_en = NOW()
                    WHERE mensaje_id = %s AND destinatario_id = %s
                """, (int(mensaje_id), int(destinatario_id)))
            else:
                # Insertar con leído (y entregado automáticamente)
                cursor.execute("""
                    INSERT INTO destinatarios_mensaje (mensaje_id, destinatario_id, entregado_en, leido_en)
                    VALUES (%s, %s, NOW(), NOW())
                """, (int(mensaje_id), int(destinatario_id)))
            
            return True
            
    except Exception as e:
        print(f"[DB-ERROR] mark_message_read: {e}")
        return False


def get_group_members(group_id):
    """Obtiene los IDs de los miembros activos de un grupo"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT usuario_id
                FROM miembros_grupo
                WHERE grupo_id = %s 
                AND estado_membresia = 'activo'
            """, (int(group_id),))
            
            miembros = cursor.fetchall()
            return [str(m["usuario_id"]) for m in miembros]
            
    except Exception as e:
        print(f"[DB-ERROR] get_group_members: {e}")
        return []


def verify_user_in_group(user_id, group_id):
    """Verifica si un usuario es miembro activo de un grupo"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT usuario_id
                FROM miembros_grupo
                WHERE grupo_id = %s 
                AND usuario_id = %s
                AND estado_membresia = 'activo'
            """, (int(group_id), int(user_id)))
            
            return cursor.fetchone() is not None
            
    except Exception as e:
        print(f"[DB-ERROR] verify_user_in_group: {e}")
        return False


# =====================================================================
# WEBSOCKET HANDLERS
# =====================================================================

@app.route("/")
def health_check():
    return {
        "status": "ok",
        "service": "websocket_upred",
        "database": "MySQL",
        "connected_users": len(connected_users)
    }, 200


@socketio.on("connect")
def on_connect(auth=None):
    """Maneja nuevas conexiones de usuarios"""
    user_id = request.args.get("user_id")

    if not user_id:
        print("[CONNECT-ERROR] Conexión rechazada: falta user_id en query params")
        return False
    
    # Validación básica del user_id
    user_id = str(user_id).strip()
    if len(user_id) == 0 or len(user_id) > 100:
        print(f"[CONNECT-ERROR] user_id inválido: longitud={len(user_id)}")
        return False

    # Unir al usuario a su room personal
    join_room(user_id)
    
    # Registrar usuario conectado
    connected_users[user_id] = {
        "sid": request.sid,
        "rooms": [user_id]
    }
    
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
    """Maneja desconexión de usuarios"""
    # Buscar y eliminar usuario de connected_users
    user_id = None
    for uid, data in list(connected_users.items()):
        if data["sid"] == request.sid:
            user_id = uid
            del connected_users[uid]
            break
    
    print(f"[DISCONNECT] user_id={user_id} | sid={request.sid}")


@socketio.on("join_direct_chat")
def on_join_direct_chat(data):
    """
    Une al usuario a una sala de chat directo
    
    Formato esperado:
    {
        "other_user_id": "123"
    }
    """
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para join_direct_chat"})
        return

    user_id = request.args.get("user_id", "unknown")
    other_user_id = data.get("other_user_id")

    if not other_user_id:
        emit("error", {"message": "other_user_id es requerido"})
        return

    other_user_id = str(other_user_id)
    
    # Obtener o crear sala de chat
    sala_chat = get_or_create_direct_chat(user_id, other_user_id)
    
    if not sala_chat:
        emit("error", {"message": "No se pudo crear/obtener sala de chat"})
        return
    
    # Unirse a la room usando el UUID de la sala
    room_name = f"chat_{sala_chat['sala_uuid']}"
    join_room(room_name)
    
    # Actualizar rooms del usuario
    if user_id in connected_users:
        if room_name not in connected_users[user_id]["rooms"]:
            connected_users[user_id]["rooms"].append(room_name)

    print(f"[JOIN_DIRECT_CHAT] user_id={user_id} | other_user_id={other_user_id} | room={room_name}")

    emit(
        "direct_chat_joined",
        {
            "status": "ok",
            "other_user_id": other_user_id,
            "sala_chat_id": sala_chat["id"],
            "sala_uuid": sala_chat["sala_uuid"],
            "room": room_name
        },
    )


@socketio.on("join_group")
def on_join_group(data):
    """
    Une al usuario a un chat grupal
    
    Formato esperado:
    {
        "group_id": "456"
    }
    """
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para join_group"})
        return

    user_id = request.args.get("user_id", "unknown")
    group_id = data.get("group_id")

    if not group_id:
        emit("error", {"message": "group_id es requerido"})
        return

    group_id = str(group_id)
    
    # Verificar que el usuario es miembro del grupo
    if not verify_user_in_group(user_id, group_id):
        emit("error", {"message": "No eres miembro de este grupo"})
        return
    
    # Obtener o crear sala de chat grupal
    sala_chat = get_or_create_group_chat(group_id)
    
    if not sala_chat:
        emit("error", {"message": "No se pudo crear/obtener sala de chat grupal"})
        return
    
    # Unirse a la room usando el UUID de la sala
    room_name = f"group_{sala_chat['sala_uuid']}"
    join_room(room_name)
    
    # Actualizar rooms del usuario
    if user_id in connected_users:
        if room_name not in connected_users[user_id]["rooms"]:
            connected_users[user_id]["rooms"].append(room_name)

    print(f"[JOIN_GROUP] user_id={user_id} | group_id={group_id} | room={room_name}")

    # Notificar al grupo que un usuario se unió
    emit(
        "user_joined_group",
        {
            "user_id": user_id,
            "group_id": group_id,
            "sala_uuid": sala_chat["sala_uuid"]
        },
        room=room_name,
        include_self=False
    )

    emit(
        "group_joined",
        {
            "status": "ok",
            "group_id": group_id,
            "sala_chat_id": sala_chat["id"],
            "sala_uuid": sala_chat["sala_uuid"],
            "room": room_name
        },
    )


@socketio.on("leave_group")
def on_leave_group(data):
    """
    Saca al usuario de un chat grupal
    
    Formato esperado:
    {
        "group_id": "456"
    }
    """
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para leave_group"})
        return

    user_id = request.args.get("user_id", "unknown")
    group_id = data.get("group_id")

    if not group_id:
        emit("error", {"message": "group_id es requerido"})
        return

    group_id = str(group_id)
    
    # Obtener sala de chat grupal
    sala_chat = get_or_create_group_chat(group_id)
    
    if sala_chat:
        room_name = f"group_{sala_chat['sala_uuid']}"
        leave_room(room_name)
        
        # Actualizar rooms del usuario
        if user_id in connected_users and room_name in connected_users[user_id]["rooms"]:
            connected_users[user_id]["rooms"].remove(room_name)
        
        # Notificar al grupo que un usuario salió
        emit(
            "user_left_group",
            {
                "user_id": user_id,
                "group_id": group_id
            },
            room=room_name
        )
    
    print(f"[LEAVE_GROUP] user_id={user_id} | group_id={group_id}")

    emit(
        "group_left",
        {
            "status": "ok",
            "group_id": group_id
        },
    )


@socketio.on("send_message")
def on_send_message(data):
    """
    Maneja el envío de mensajes (directo o grupal) y los guarda en la BD
    
    Formato esperado:
    {
        "sala_uuid": "uuid-de-la-sala",
        "message": "Texto del mensaje",
        "sender_id": "123",
        "timestamp": "2024-01-15T10:30:00Z",
        "type": "directo" o "grupal",
        "message_type": "texto" (opcional, default: "texto")
        "url_archivo": "https://..." (opcional)
    }
    """
    required_fields = ["sala_uuid", "message", "sender_id", "timestamp", "type"]

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
    sala_uuid = str(data["sala_uuid"])
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

    # Validar tipo de chat
    if chat_type not in ["directo", "grupal"]:
        emit("ack", {
            "status": "error",
            "message": "type debe ser 'directo' o 'grupal'"
        })
        return

    print(
        "[SEND_MESSAGE] "
        f"from={sender_id} "
        f"sala_uuid={sala_uuid} "
        f"type={chat_type} "
        f"message_type={message_type} "
        f"timestamp={timestamp}"
    )

    # Intentar guardar en base de datos
    mensaje_guardado = None
    sala_chat_id = None
    
    try:
        # Obtener info de la sala desde BD
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tipo_sala, usuario_a_id, usuario_b_id, grupo_id
                FROM salas_chat
                WHERE sala_uuid = %s
            """, (sala_uuid,))
            sala_info = cursor.fetchone()
        
        if not sala_info:
            emit("ack", {
                "status": "error",
                "message": "Sala de chat no encontrada"
            })
            return
        
        sala_chat_id = sala_info["id"]
        
        # Guardar mensaje
        metadatos = {
            "client_timestamp": timestamp,
            "type": chat_type
        }
        
        mensaje_guardado = save_message(
            sala_chat_id,
            sender_id,
            message_type,
            message_content,
            url_archivo,
            metadatos
        )
        
    except Exception as e:
        print(f"[ERROR] Error al guardar mensaje: {e}")
        emit("ack", {
            "status": "error",
            "message": f"Error al guardar mensaje: {str(e)}"
        })
        return
    
    if not mensaje_guardado:
        emit("ack", {
            "status": "error",
            "message": "No se pudo guardar el mensaje"
        })
        return
    
    # Preparar datos para emitir
    message_data = {
        "from": sender_id,
        "message": message_content,
        "type": chat_type,
        "message_type": message_type,
        "timestamp": timestamp,
        "url_archivo": url_archivo,
        "mensaje_id": str(mensaje_guardado["id"]),
        "mensaje_uuid": str(mensaje_guardado["mensaje_uuid"]),
        "enviado_en": mensaje_guardado["enviado_en"].isoformat() if isinstance(mensaje_guardado["enviado_en"], datetime) else str(mensaje_guardado["enviado_en"]),
        "sala_uuid": sala_uuid
    }

    # Determinar el nombre de la room
    room_name = f"{chat_type[0:5]}_{sala_uuid}" if chat_type == "directo" else f"group_{sala_uuid}"
    
    # Emitir mensaje a la room (todos los conectados en esa sala)
    emit("receive_message", message_data, room=room_name)

    print(f"[MESSAGE_SENT] mensaje_id={mensaje_guardado['id']} | room={room_name}")

    # Enviar confirmación al remitente
    emit(
        "ack",
        {
            "status": "sent",
            "sender_id": sender_id,
            "timestamp": timestamp,
            "type": chat_type,
            "message_type": message_type,
            "mensaje_id": str(mensaje_guardado["id"]),
            "mensaje_uuid": str(mensaje_guardado["mensaje_uuid"]),
            "sala_uuid": sala_uuid,
            "message": "Mensaje enviado y guardado en BD"
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


@socketio.on("mark_read")
def on_mark_read(data):
    """
    Marca un mensaje como leído
    
    Formato esperado:
    {
        "mensaje_id": "123",
        "user_id": "456"
    }
    """
    if not isinstance(data, dict):
        emit("error", {"message": "Payload inválido para mark_read"})
        return
    
    mensaje_id = data.get("mensaje_id")
    user_id = data.get("user_id")
    
    if not mensaje_id or not user_id:
        emit("error", {"message": "mensaje_id y user_id son requeridos"})
        return
    
    try:
        success = mark_message_read(mensaje_id, user_id)
        if success:
            print(f"[MARK_READ] mensaje_id={mensaje_id} | user_id={user_id}")
            emit("read_confirmed", {
                "status": "ok",
                "mensaje_id": mensaje_id,
                "user_id": user_id
            })
        else:
            emit("error", {"message": "No se pudo marcar el mensaje como leído"})
    except Exception as e:
        print(f"[ERROR] mark_read: {e}")
        emit("error", {"message": "Error al marcar mensaje como leído"})


if __name__ == "__main__":
    # Advertencia de seguridad
    if app.config["SECRET_KEY"] == "super-secret-key-change-me-in-production":
        print("⚠️  [ADVERTENCIA] Usando SECRET_KEY por defecto. Cámbiala en .env para producción!")
    
    # Verificar configuración de base de datos
    if not DB_HOST or not DB_NAME:
        print("⚠️  [ADVERTENCIA] Base de datos no configurada. Los mensajes NO se guardarán en BD.")
        print("    Configura DB_HOST, DB_NAME, DB_USER y DB_PASSWORD en .env")
    else:
        print(f"✓ [DB] Configuración de base de datos: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        # Probar conexión
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"✓ [DB] Conexión exitosa: MySQL {version['VERSION()'] if version else 'desconocida'}")
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
    
    print(f"[INICIO] Servidor WebSocket corriendo en {protocol}://{HOST}:{PORT}")
    print(f"[CORS] Orígenes permitidos: {CORS_ORIGINS}")
    print(f"[ENV] Entorno: {FLASK_ENV}")
    print(f"[INFO] Para conectar usa: {protocol}://{HOST}:{PORT}?user_id=TU_USER_ID")
    
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=(FLASK_ENV == "development"),
        allow_unsafe_werkzeug=(FLASK_ENV == "development"),
        **ssl_args,
    )
