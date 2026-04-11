# Reporte Tecnico WebSocket (Soporte Persona 1 y Persona 2)

## Resumen

Este documento resume el rol del servicio WebSocket en la solucion completa RED-UP para Persona 1 y Persona 2.

## Rol del servicio

1. Mensajeria en tiempo real (socket) para chats directos y grupales.
2. Complemento de baja latencia para la API REST.
3. Integracion con la app movil en navegacion unificada de chat.

## Aporte a Persona 1

1. Continuidad funcional de chat mientras notificaciones push cubren escenarios con app en background.
2. Contribucion al modelo hibrido de comunicacion:
   - WebSocket para tiempo real activo.
   - FCM para reenganche y eventos fuera de sesion activa.
3. Compatibilidad con estrategia offline/online de la app (eventos no criticos se sincronizan por API).

## Aporte a Persona 2

1. Mejor UX de chat por inmediatez de entrega y recepcion.
2. Base para indicadores de conexion/reconexion en UI movil.

## Arquitectura tecnica

1. Servicio independiente de API (proceso separado).
2. Despliegue recomendado detras de Nginx con upgrade de conexion.
3. Operacion en EC2 con dominio dedicado para socket.

## Estado de integracion

1. Rama principal actualizada.
2. Servicio validado para convivencia con API y app movil.
3. Documentacion de deployment y seguridad existente en repositorio.
