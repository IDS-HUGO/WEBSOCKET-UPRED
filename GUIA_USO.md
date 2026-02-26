# 📡 WebSocket UPRed - Guía de Uso

## 🔧 Configuración

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Copia `.env.example` a `.env` y configura tus credenciales:

```bash
cp .env.example .env
```

Edita `.env` con la configuración de tu base de datos MySQL (la misma que usa tu API):

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=upred_db
```

### 3. Ejecutar el servidor
```bash
python app.py
```

El servidor WebSocket estará disponible en: `http://localhost:5000`

---

## 🔌 Conexión al WebSocket

### Conectarse desde el cliente

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5000', {
  query: { user_id: '123' }  // ID del usuario logueado
});

socket.on('connected', (data) => {
  console.log('Conectado:', data);
  // { status: 'connected', user_id: '123', sid: '...' }
});
```

---

## 📨 Eventos del WebSocket

### 1. **Chat Directo (1 a 1)**

#### a) Unirse a un chat directo
```javascript
socket.emit('join_direct_chat', {
  other_user_id: '456'  // ID del otro usuario
});

socket.on('direct_chat_joined', (data) => {
  console.log('Unido al chat directo:', data);
  // {
  //   status: 'ok',
  //   other_user_id: '456',
  //   sala_chat_id: 789,
  //   sala_uuid: 'uuid-de-la-sala',
  //   room: 'chat_uuid-de-la-sala'
  // }
});
```

#### b) Enviar mensaje en chat directo
```javascript
socket.emit('send_message', {
  sala_uuid: 'uuid-de-la-sala',  // De la respuesta anterior
  message: 'Hola!',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'directo',
  message_type: 'texto'  // 'texto', 'imagen', 'archivo', 'audio', 'sistema'
});

// Confirmación del envío
socket.on('ack', (data) => {
  console.log('ACK:', data);
  // {
  //   status: 'sent',
  //   mensaje_id: '999',
  //   mensaje_uuid: 'uuid-del-mensaje',
  //   ...
  // }
});
```

#### c) Recibir mensajes en chat directo
```javascript
socket.on('receive_message', (data) => {
  console.log('Mensaje recibido:', data);
  // {
  //   from: '456',
  //   message: 'Hola!',
  //   type: 'directo',
  //   message_type: 'texto',
  //   timestamp: '...',
  //   mensaje_id: '999',
  //   mensaje_uuid: 'uuid-del-mensaje',
  //   sala_uuid: 'uuid-de-la-sala'
  // }
});
```

---

### 2. **Chat Grupal**

#### a) Unirse a un grupo
```javascript
socket.emit('join_group', {
  group_id: '789'  // ID del grupo
});

socket.on('group_joined', (data) => {
  console.log('Unido al grupo:', data);
  // {
  //   status: 'ok',
  //   group_id: '789',
  //   sala_chat_id: 123,
  //   sala_uuid: 'uuid-de-la-sala-grupal',
  //   room: 'group_uuid-de-la-sala-grupal'
  // }
});

// Notificación cuando otro usuario se une
socket.on('user_joined_group', (data) => {
  console.log('Usuario se unió al grupo:', data);
  // { user_id: '456', group_id: '789', sala_uuid: '...' }
});
```

#### b) Enviar mensaje en grupo
```javascript
socket.emit('send_message', {
  sala_uuid: 'uuid-de-la-sala-grupal',
  message: 'Hola grupo!',
  sender_id: '123',
  timestamp: new Date().toISOString(),
  type: 'grupal',
  message_type: 'texto'
});
```

#### c) Salir de un grupo
```javascript
socket.emit('leave_group', {
  group_id: '789'
});

socket.on('group_left', (data) => {
  console.log('Saliste del grupo:', data);
});

// Notificación cuando otro usuario sale
socket.on('user_left_group', (data) => {
  console.log('Usuario salió del grupo:', data);
});
```

---

### 3. **Estado de Mensajes**

#### a) Marcar mensaje como entregado
```javascript
socket.emit('mark_delivered', {
  mensaje_id: '999',
  user_id: '123'
});

socket.on('delivery_confirmed', (data) => {
  console.log('Mensaje marcado como entregado:', data);
});
```

#### b) Marcar mensaje como leído
```javascript
socket.emit('mark_read', {
  mensaje_id: '999',
  user_id: '123'
});

socket.on('read_confirmed', (data) => {
  console.log('Mensaje marcado como leído:', data);
});
```

---

### 4. **Errores**

```javascript
socket.on('error', (data) => {
  console.error('Error del servidor:', data);
  // { message: 'Descripción del error' }
});
```

---

## 🗄️ Estructura de Base de Datos

El WebSocket se conecta a las siguientes tablas de tu API:

- **`salas_chat`**: Salas de chat (directas o grupales)
  - `tipo_sala`: `'directo'` o `'grupal'`
  - `usuario_a_id`, `usuario_b_id`: Para chats directos
  - `grupo_id`: Para chats grupales

- **`mensajes`**: Mensajes enviados
  - `sala_chat_id`: Referencia a la sala
  - `remitente_id`: Usuario que envía el mensaje
  - `tipo_mensaje`: `'texto'`, `'imagen'`, `'archivo'`, `'audio'`, `'sistema'`
  - `contenido`: Texto del mensaje
  - `url_archivo`: URL del archivo (opcional)

- **`destinatarios_mensaje`**: Estado de entrega/lectura
  - `mensaje_id`: Referencia al mensaje
  - `destinatario_id`: Usuario destinatario
  - `entregado_en`: Timestamp de entrega
  - `leido_en`: Timestamp de lectura

- **`grupos`**: Grupos de chat
- **`miembros_grupo`**: Miembros de los grupos

---

## 🔒 Seguridad

### Para Producción:

1. **Cambia el `SECRET_KEY`** en el archivo `.env`:
   ```bash
   python generate_secret.py
   ```

2. **Configura CORS correctamente**:
   ```env
   CORS_ALLOWED_ORIGINS=https://tuapp.com,https://app.tuapp.com
   ```

3. **Usa HTTPS** con certificados SSL o proxy inverso (Nginx recomendado)

4. **Verifica autenticación**: Implementa validación de tokens JWT en el evento `connect`

---

## 📊 Monitoreo

El endpoint `/` proporciona información del servidor:

```bash
curl http://localhost:5000/
```

Respuesta:
```json
{
  "status": "ok",
  "service": "websocket_upred",
  "database": "MySQL",
  "connected_users": 5
}
```

---

## 🚨 Solución de Problemas

### Error: No se puede conectar a la BD
- Verifica que MySQL esté corriendo
- Verifica las credenciales en `.env`
- Verifica que la base de datos `upred_db` exista
- Verifica que las tablas estén creadas (ejecuta `setup_database.sql`)

### Error: Conexión WebSocket rechazada
- Asegúrate de pasar `user_id` en los query params al conectar
- Verifica que CORS esté configurado correctamente

### Los mensajes no se guardan
- Revisa los logs del servidor
- Verifica permisos del usuario de BD (INSERT, UPDATE, SELECT)
- Verifica que las tablas existan

---

## 🔄 Flujo Completo de Ejemplo

### Chat Directo:

```javascript
// 1. Conectar
const socket = io('http://localhost:5000', {
  query: { user_id: '123' }
});

// 2. Unirse al chat con otro usuario
socket.emit('join_direct_chat', { other_user_id: '456' });

socket.on('direct_chat_joined', (data) => {
  const { sala_uuid } = data;
  
  // 3. Enviar mensaje
  socket.emit('send_message', {
    sala_uuid: sala_uuid,
    message: 'Hola!',
    sender_id: '123',
    timestamp: new Date().toISOString(),
    type: 'directo',
    message_type: 'texto'
  });
});

// 4. Recibir mensajes
socket.on('receive_message', (data) => {
  console.log('Nuevo mensaje:', data.message);
  
  // 5. Marcar como leído
  socket.emit('mark_read', {
    mensaje_id: data.mensaje_id,
    user_id: '123'
  });
});
```

### Chat Grupal:

```javascript
// 1. Conectar (igual que antes)
const socket = io('http://localhost:5000', {
  query: { user_id: '123' }
});

// 2. Unirse al grupo
socket.emit('join_group', { group_id: '789' });

socket.on('group_joined', (data) => {
  const { sala_uuid } = data;
  
  // 3. Enviar mensaje al grupo
  socket.emit('send_message', {
    sala_uuid: sala_uuid,
    message: 'Hola grupo!',
    sender_id: '123',
    timestamp: new Date().toISOString(),
    type: 'grupal',
    message_type: 'texto'
  });
});

// 4. Recibir mensajes del grupo
socket.on('receive_message', (data) => {
  console.log('Mensaje del grupo:', data.message);
});

// 5. Al salir
socket.emit('leave_group', { group_id: '789' });
```

---

## 📝 Tipos de Mensajes Soportados

- `texto`: Mensajes de texto simple
- `imagen`: Mensajes con imágenes (incluye `url_archivo`)
- `archivo`: Documentos, PDFs, etc. (incluye `url_archivo`)
- `audio`: Mensajes de voz (incluye `url_archivo`)
- `sistema`: Mensajes automáticos del sistema

---

## 📚 Recursos Adicionales

- **Socket.IO Docs**: https://socket.io/docs/
- **Flask-SocketIO**: https://flask-socketio.readthedocs.io/
- **PyMySQL**: https://pymysql.readthedocs.io/

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs del servidor
2. Verifica la conexión a la base de datos
3. Asegúrate de que la versión de MySQL sea 8.0+
4. Verifica que todas las dependencias estén instaladas

**Versión**: 2.0 (MySQL)  
**Fecha**: 2026-02-25
