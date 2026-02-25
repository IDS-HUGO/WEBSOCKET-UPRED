# 🔌 WebSocket RedUP - Guía Completa de Uso

Sistema de mensajería en tiempo real con WebSocket (Socket.IO) para la Red Social Universitaria, con persistencia en base de datos PostgreSQL.

## 📋 Índice

- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración](#️-configuración)
- [Iniciar el Servidor](#-iniciar-el-servidor)
- [Conectarse al WebSocket](#-conectarse-al-websocket)
- [Eventos Disponibles](#-eventos-disponibles)
- [Ejemplos de Uso](#-ejemplos-de-uso)
- [Estructura de Base de Datos](#-estructura-de-base-de-datos)
- [Solución de Problemas](#-solución-de-problemas)

---

## ✨ Características

- ✅ **Mensajería directa** (1 a 1) entre usuarios
- ✅ **Mensajería grupal** para grupos
- ✅ **Persistencia en PostgreSQL** - todos los mensajes se guardan en la base de datos
- ✅ **Salas de chat automáticas** - se crean automáticamente al enviar mensajes
- ✅ **Soporte para múltiples tipos de mensaje**: texto, imagen, archivo, audio
- ✅ **Confirmaciones de entrega** (ACK)
- ✅ **CORS configurable** para desarrollo y producción
- ✅ **Manejo de errores robusto** con fallback si falla la BD

---

## 📦 Requisitos

- **Python 3.8+**
- **PostgreSQL 15+**
- **Base de datos** upred_db con el esquema cargado (ver `database_schema.sql`)

---

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd WEBSOCKET_REDUP
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la base de datos

Asegúrate de que PostgreSQL esté corriendo y que hayas creado la base de datos:

```sql
-- En psql o pgAdmin
CREATE DATABASE upred_db;

-- Cargar el esquema
\i database_schema.sql
```

---

## ⚙️ Configuración

### Editar el archivo `.env`

Abre el archivo `.env` y configura tus credenciales:

```dotenv
# Configuración de desarrollo local
SECRET_KEY=dev-secret-key-local-only
FLASK_ENV=development
CORS_ALLOWED_ORIGINS=*
PORT=5000
HOST=0.0.0.0
SSL_CERT_FILE=
SSL_KEY_FILE=

# Base de datos PostgreSQL
# ⚠️ IMPORTANTE: Cambia estos valores con tus credenciales reales
DATABASE_URL=postgresql://postgres:tu_password_aqui@localhost:5432/upred_db
```

**Formato de DATABASE_URL:**
```
postgresql://[usuario]:[contraseña]@[host]:[puerto]/[nombre_bd]
```

**Ejemplo real:**
```
DATABASE_URL=postgresql://postgres:mipassword123@localhost:5432/upred_db
```

---

## ▶️ Iniciar el Servidor

```bash
python app.py
```

**Salida esperada:**
```
✓ [DB] Conexión a base de datos configurada
✓ [DB] Conexión exitosa: PostgreSQL
[INICIO] Servidor corriendo en http://0.0.0.0:5000
[CORS] Orígenes permitidos: *
[ENV] Entorno: development
```

El servidor estará disponible en: `http://localhost:5000`

---

## 🔌 Conectarse al WebSocket

### URL de Conexión

```
ws://localhost:5000?user_id=TU_USER_ID
```

⚠️ **IMPORTANTE**: El parámetro `user_id` es **obligatorio** en la conexión.

### Ejemplos por Cliente

#### **JavaScript (Socket.IO Client)**

```bash
npm install socket.io-client
```

```javascript
import { io } from 'socket.io-client';

// Conectar al WebSocket
const socket = io('http://localhost:5000', {
  query: {
    user_id: '123'  // ⚠️ OBLIGATORIO: ID del usuario actual
  },
  transports: ['websocket', 'polling']
});

// Eventos de conexión
socket.on('connect', () => {
  console.log('✓ Conectado al WebSocket:', socket.id);
});

socket.on('connected', (data) => {
  console.log('✓ Confirmación del servidor:', data);
  // { status: 'connected', user_id: '123', sid: 'abc123...' }
});

socket.on('disconnect', () => {
  console.log('✗ Desconectado del WebSocket');
});

socket.on('error', (error) => {
  console.error('✗ Error:', error);
});
```

#### **Python (Socket.IO Client)**

```bash
pip install python-socketio[client]
```

```python
import socketio

# Crear cliente
sio = socketio.Client()

# Eventos de conexión
@sio.event
def connect():
    print('✓ Conectado al WebSocket')

@sio.on('connected')
def on_connected(data):
    print('✓ Confirmación del servidor:', data)

@sio.event
def disconnect():
    print('✗ Desconectado del WebSocket')

# Conectar con user_id
sio.connect('http://localhost:5000?user_id=123')
sio.wait()
```

#### **React Native / Expo**

```bash
npm install socket.io-client
```

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5000', {
  query: { user_id: '123' },
  transports: ['websocket']
});

socket.on('connect', () => {
  console.log('✓ Conectado');
});

socket.on('connected', (data) => {
  console.log('Datos:', data);
});
```

#### **Flutter**

```yaml
# pubspec.yaml
dependencies:
  socket_io_client: ^2.0.3+1
```

```dart
import 'package:socket_io_client/socket_io_client.dart' as IO;

IO.Socket socket = IO.io('http://localhost:5000', 
  IO.OptionBuilder()
    .setQuery({'user_id': '123'})
    .setTransports(['websocket'])
    .build()
);

socket.onConnect((_) {
  print('✓ Conectado al WebSocket');
});

socket.on('connected', (data) {
  print('Datos: $data');
});

socket.connect();
```

---

## 🎯 Eventos Disponibles

### 1. **connect** (Automático)

Se ejecuta al establecer conexión. El servidor te une automáticamente a tu "room" personal (tu `user_id`).

**Respuesta del servidor:**
```javascript
{
  "status": "connected",
  "user_id": "123",
  "sid": "abc123xyz..."
}
```

---

### 2. **join_group**

Únete a un grupo para recibir mensajes grupales.

**Enviar:**
```javascript
socket.emit('join_group', {
  group_id: '456'
});
```

**Respuesta:**
```javascript
{
  "status": "ok",
  "group_id": "456",
  "user_id": "123"
}
```

---

### 3. **send_message** (Principal)

Envía un mensaje directo o grupal. El mensaje se guarda automáticamente en la base de datos.

#### **Mensaje Directo (1 a 1)**

```javascript
socket.emit('send_message', {
  to: '789',                              // user_id del destinatario
  message: 'Hola, ¿cómo estás?',         // Contenido del mensaje
  sender_id: '123',                       // Tu user_id
  timestamp: new Date().toISOString(),    // ISO 8601
  type: 'directo',                        // Tipo de chat
  message_type: 'texto'                   // Tipo de mensaje (opcional, default: 'texto')
});
```

#### **Mensaje Grupal**

```javascript
socket.emit('send_message', {
  to: '456',                              // group_id del grupo
  message: 'Hola a todos!',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'grupal',
  message_type: 'texto'
});
```

#### **Mensaje con Archivo/Imagen**

```javascript
socket.emit('send_message', {
  to: '789',
  message: 'Te envío esta imagen',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'directo',
  message_type: 'imagen',                 // 'imagen', 'archivo', 'audio'
  url_archivo: 'https://cloudinary.com/mi-imagen.jpg'
});
```

#### **Valores válidos para `message_type`:**
- `texto` (default)
- `imagen`
- `archivo`
- `audio`
- `sistema`

**Respuesta (ACK):**
```javascript
{
  "status": "sent",
  "to": "789",
  "sender_id": "123",
  "timestamp": "2024-01-15T10:30:00Z",
  "type": "directo",
  "message_type": "texto",
  "saved_to_db": true,
  "mensaje_id": "12345",                  // ID del mensaje en la BD
  "sala_chat_id": "67890",                 // ID de la sala de chat
  "message": "Mensaje enviado y guardado en BD"
}
```

---

### 4. **receive_message**

Evento que RECIBES cuando alguien te envía un mensaje.

**Escuchar:**
```javascript
socket.on('receive_message', (data) => {
  console.log('📩 Nuevo mensaje:', data);
  
  // Mostrar el mensaje en tu UI
  displayMessage(data);
});
```

**Datos recibidos:**
```javascript
{
  "from": "789",                          // user_id del remitente
  "to": "123",                            // Tu user_id o group_id
  "message": "Hola, ¿cómo estás?",
  "type": "directo",
  "message_type": "texto",
  "timestamp": "2024-01-15T10:30:00Z",
  "mensaje_id": "12345",                  // ID en BD (si se guardó)
  "mensaje_uuid": "uuid-abc-123",         // UUID único del mensaje
  "enviado_en": "2024-01-15T10:30:00.123456+00:00",
  "sala_chat_id": "67890",
  "url_archivo": null                     // URL si es imagen/archivo
}
```

---

### 5. **mark_delivered**

Marca un mensaje como entregado.

**Enviar:**
```javascript
socket.emit('mark_delivered', {
  mensaje_id: '12345',
  user_id: '123'
});
```

**Respuesta:**
```javascript
{
  "status": "ok",
  "mensaje_id": "12345",
  "user_id": "123"
}
```

---

### 6. **disconnect** (Automático)

Se ejecuta al desconectarse del servidor.

**Escuchar:**
```javascript
socket.on('disconnect', () => {
  console.log('✗ Desconectado del servidor');
});
```

---

## 💡 Ejemplos de Uso

### Ejemplo Completo: Chat 1 a 1

```javascript
import { io } from 'socket.io-client';

// Usuario 1 (ID: 123)
const socket1 = io('http://localhost:5000', {
  query: { user_id: '123' }
});

socket1.on('connected', (data) => {
  console.log('Usuario 123 conectado:', data);
  
  // Enviar mensaje al usuario 789
  socket1.emit('send_message', {
    to: '789',
    message: 'Hola, ¿cómo estás?',
    sender_id: '123',
    timestamp: new Date().toISOString(),
    type: 'directo',
    message_type: 'texto'
  });
});

socket1.on('ack', (data) => {
  console.log('✓ Mensaje enviado:', data);
  // { status: 'sent', saved_to_db: true, mensaje_id: '12345', ... }
});

socket1.on('receive_message', (data) => {
  console.log('📩 Mensaje recibido:', data);
  
  // Marcar como entregado
  socket1.emit('mark_delivered', {
    mensaje_id: data.mensaje_id,
    user_id: '123'
  });
});
```

```javascript
// Usuario 2 (ID: 789)
const socket2 = io('http://localhost:5000', {
  query: { user_id: '789' }
});

socket2.on('connected', (data) => {
  console.log('Usuario 789 conectado:', data);
});

socket2.on('receive_message', (data) => {
  console.log('📩 Mensaje recibido de', data.from, ':', data.message);
  // 📩 Mensaje recibido de 123 : Hola, ¿cómo estás?
  
  // Responder
  socket2.emit('send_message', {
    to: data.from,
    message: '¡Hola! Todo bien, ¿y tú?',
    sender_id: '789',
    timestamp: new Date().toISOString(),
    type: 'directo',
    message_type: 'texto'
  });
});
```

---

### Ejemplo Completo: Chat Grupal

```javascript
import { io } from 'socket.io-client';

// Usuario 1 se une al grupo 456
const socket1 = io('http://localhost:5000', {
  query: { user_id: '123' }
});

socket1.on('connected', () => {
  // Unirse al grupo
  socket1.emit('join_group', {
    group_id: '456'
  });
});

socket1.on('group_joined', (data) => {
  console.log('✓ Unido al grupo:', data);
  
  // Enviar mensaje al grupo
  socket1.emit('send_message', {
    to: '456',                    // group_id
    message: 'Hola a todos!',
    sender_id: '123',
    timestamp: new Date().toISOString(),
    type: 'grupal',
    message_type: 'texto'
  });
});

socket1.on('receive_message', (data) => {
  console.log('📩 Mensaje grupal de', data.from, ':', data.message);
});
```

```javascript
// Usuario 2 también se une al grupo 456
const socket2 = io('http://localhost:5000', {
  query: { user_id: '789' }
});

socket2.on('connected', () => {
  socket2.emit('join_group', {
    group_id: '456'
  });
});

socket2.on('group_joined', (data) => {
  console.log('✓ Unido al grupo:', data);
});

socket2.on('receive_message', (data) => {
  console.log('📩 Mensaje grupal de', data.from, ':', data.message);
  // 📩 Mensaje grupal de 123 : Hola a todos!
});
```

---

### Ejemplo: Enviar Imagen

```javascript
socket.emit('send_message', {
  to: '789',
  message: 'Te envío esta foto de la clase',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'directo',
  message_type: 'imagen',
  url_archivo: 'https://res.cloudinary.com/mycloud/image/upload/v123/clase.jpg'
});
```

---

### Ejemplo: React Hook Personalizado

```javascript
// useWebSocket.js
import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

export const useWebSocket = (userId) => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const newSocket = io('http://localhost:5000', {
      query: { user_id: userId }
    });

    newSocket.on('connect', () => {
      setConnected(true);
    });

    newSocket.on('connected', (data) => {
      console.log('Conectado:', data);
    });

    newSocket.on('disconnect', () => {
      setConnected(false);
    });

    newSocket.on('receive_message', (data) => {
      setMessages((prev) => [...prev, data]);
      
      // Marcar como entregado
      newSocket.emit('mark_delivered', {
        mensaje_id: data.mensaje_id,
        user_id: userId
      });
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [userId]);

  const sendMessage = (to, message, type = 'directo', messageType = 'texto') => {
    if (socket && connected) {
      socket.emit('send_message', {
        to,
        message,
        sender_id: userId,
        timestamp: new Date().toISOString(),
        type,
        message_type: messageType
      });
    }
  };

  const joinGroup = (groupId) => {
    if (socket && connected) {
      socket.emit('join_group', {
        group_id: groupId
      });
    }
  };

  return { socket, connected, messages, sendMessage, joinGroup };
};
```

**Uso:**

```javascript
function ChatScreen() {
  const { connected, messages, sendMessage, joinGroup } = useWebSocket('123');

  useEffect(() => {
    if (connected) {
      // Unirse al grupo al conectar
      joinGroup('456');
    }
  }, [connected]);

  const handleSendMessage = () => {
    sendMessage('789', 'Hola!', 'directo', 'texto');
  };

  return (
    <div>
      <div>Estado: {connected ? '🟢 Conectado' : '🔴 Desconectado'}</div>
      <div>
        {messages.map((msg, idx) => (
          <div key={idx}>
            <strong>{msg.from}:</strong> {msg.message}
          </div>
        ))}
      </div>
      <button onClick={handleSendMessage}>Enviar Mensaje</button>
    </div>
  );
}
```

---

## 🗄️ Estructura de Base de Datos

### Tablas Principales

#### **salas_chat**
Almacena las salas de chat (directas y grupales).

```sql
CREATE TABLE salas_chat (
    id                      BIGSERIAL PRIMARY KEY,
    sala_uuid               UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tipo_sala               tipo_sala_chat_enum NOT NULL,  -- 'directo' o 'grupal'
    usuario_a_id            BIGINT REFERENCES usuarios(id),
    usuario_b_id            BIGINT REFERENCES usuarios(id),
    grupo_id                BIGINT REFERENCES grupos(id),
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Cómo funciona:**
- Para chats **directos**: se usan `usuario_a_id` y `usuario_b_id`
- Para chats **grupales**: se usa `grupo_id`
- La sala se crea automáticamente al enviar el primer mensaje

---

#### **mensajes**
Almacena todos los mensajes.

```sql
CREATE TABLE mensajes (
    id                      BIGSERIAL PRIMARY KEY,
    mensaje_uuid            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    sala_chat_id            BIGINT NOT NULL REFERENCES salas_chat(id),
    remitente_id            BIGINT NOT NULL REFERENCES usuarios(id),
    tipo_mensaje            tipo_mensaje_enum NOT NULL DEFAULT 'texto',
    contenido               TEXT,
    url_archivo             TEXT,
    metadatos               JSONB NOT NULL DEFAULT '{}'::jsonb,
    enviado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    editado_en              TIMESTAMPTZ,
    eliminado_en            TIMESTAMPTZ
);
```

---

#### **destinatarios_mensaje**
Almacena el estado de entrega de mensajes.

```sql
CREATE TABLE destinatarios_mensaje (
    mensaje_id              BIGINT NOT NULL REFERENCES mensajes(id),
    destinatario_id         BIGINT NOT NULL REFERENCES usuarios(id),
    entregado_en            TIMESTAMPTZ,
    leido_en                TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (mensaje_id, destinatario_id)
);
```

---

### Flujo de Datos

1. **Enviar mensaje**
   - Cliente emite `send_message`
   - Servidor verifica si existe sala de chat:
     - Chat directo: busca `salas_chat` con `usuario_a_id` y `usuario_b_id`
     - Chat grupal: busca `salas_chat` con `grupo_id`
   - Si no existe, crea nueva sala
   - Guarda mensaje en tabla `mensajes`
   - Envía mensaje al destinatario via `receive_message`
   - Responde con ACK al remitente

2. **Marcar como entregado**
   - Cliente recibe mensaje y emite `mark_delivered`
   - Servidor actualiza `destinatarios_mensaje.entregado_en`

---

## 🔧 Solución de Problemas

### ❌ Error: "user_id es requerido"

**Problema:** No se proporcionó el `user_id` al conectar.

**Solución:**
```javascript
// ✗ Incorrecto
const socket = io('http://localhost:5000');

// ✓ Correcto
const socket = io('http://localhost:5000', {
  query: { user_id: '123' }
});
```

---

### ❌ Error: "DATABASE_URL no configurada"

**Problema:** No has configurado la conexión a la base de datos.

**Solución:** Edita `.env`:
```dotenv
DATABASE_URL=postgresql://postgres:tu_password@localhost:5432/upred_db
```

---

### ❌ Error: "No se pudo conectar a la base de datos"

**Problema:** La base de datos no está corriendo o las credenciales son incorrectas.

**Solución:**
1. Verifica que PostgreSQL esté corriendo:
   ```bash
   # Windows (PowerShell)
   Get-Service postgresql*
   
   # Linux
   sudo systemctl status postgresql
   ```

2. Verifica las credenciales en `.env`
3. Verifica que la base de datos `upred_db` exista:
   ```sql
   psql -U postgres -l
   ```

---

### ❌ Error: CORS

**Problema:** Error de CORS al conectar desde el frontend.

**Solución:**

Para desarrollo, en `.env`:
```dotenv
CORS_ALLOWED_ORIGINS=*
```

Para producción, especifica tus dominios:
```dotenv
CORS_ALLOWED_ORIGINS=https://tuapp.com,https://www.tuapp.com
```

---

### ❌ No recibo mensajes

**Problema:** El destinatario no está recibiendo mensajes.

**Solución:**
1. Verifica que el destinatario esté conectado
2. Para mensajes grupales, verifica que el destinatario se haya unido al grupo con `join_group`
3. Verifica que el `to` sea correcto (user_id para directo, group_id para grupal)

---

### ❌ Los mensajes no se guardan en BD

**Problema:** Los mensajes se envían pero no aparecen en la base de datos.

**Solución:**
1. Verifica que `DATABASE_URL` esté configurada en `.env`
2. Verifica que el esquema de BD esté cargado (`database_schema.sql`)
3. Revisa los logs del servidor para ver errores de BD
4. El sistema tiene fallback: los mensajes se entregan aunque falle la BD

---

## 📊 Monitoreo y Logs

El servidor imprime logs detallados:

```
[CONNECT] user_id=123 | sid=abc123... | unido a room='123'
[JOIN_GROUP] user_id=123 | sid=abc123... | group_id=456
[SEND_MESSAGE] from=123 to=789 type=directo message_type=texto timestamp=2024-01-15T10:30:00Z
[MARK_DELIVERED] mensaje_id=12345 | user_id=789
[DISCONNECT] sid=abc123...
[DB-ERROR] descripción del error si hay alguno
```

---

## 🎯 Resumen Rápido

### Conectar
```javascript
const socket = io('http://localhost:5000', {
  query: { user_id: '123' }
});
```

### Unirse a Grupo
```javascript
socket.emit('join_group', { group_id: '456' });
```

### Enviar Mensaje Directo
```javascript
socket.emit('send_message', {
  to: '789',
  message: 'Hola!',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'directo',
  message_type: 'texto'
});
```

### Recibir Mensajes
```javascript
socket.on('receive_message', (data) => {
  console.log('Mensaje:', data);
});
```

---

## 📞 Soporte

Si tienes problemas:
1. Verifica los logs del servidor
2. Revisa que todos los parámetros requeridos estén presentes
3. Verifica la conexión a la base de datos
4. Revisa CORS si hay problemas de conexión

---

**¡Listo! 🎉** Ahora tu WebSocket está completamente funcional con persistencia en base de datos.
