-- =====================================================================
-- ESQUEMA NORMALIZADO - RED SOCIAL UNIVERSITARIA
-- Motor objetivo: PostgreSQL 15+
-- Todo en un solo script
-- =====================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================================
-- TIPOS ENUM
-- =====================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_usuario_enum') THEN
        CREATE TYPE rol_usuario_enum AS ENUM ('estudiante', 'moderador', 'administrador');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_usuario_enum') THEN
        CREATE TYPE estado_usuario_enum AS ENUM ('activo', 'suspendido', 'eliminado');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audiencia_publicacion_enum') THEN
        CREATE TYPE audiencia_publicacion_enum AS ENUM ('general', 'carrera');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'privacidad_grupo_enum') THEN
        CREATE TYPE privacidad_grupo_enum AS ENUM ('publico', 'privado');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_miembro_grupo_enum') THEN
        CREATE TYPE rol_miembro_grupo_enum AS ENUM ('dueno', 'admin', 'miembro');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_membresia_enum') THEN
        CREATE TYPE estado_membresia_enum AS ENUM ('pendiente', 'activo', 'rechazado', 'salio');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_sala_chat_enum') THEN
        CREATE TYPE tipo_sala_chat_enum AS ENUM ('directo', 'grupal');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_mensaje_enum') THEN
        CREATE TYPE tipo_mensaje_enum AS ENUM ('texto', 'imagen', 'archivo', 'audio', 'sistema');
    END IF;
END $$;

-- =====================================================================
-- ESTRUCTURA ACADÉMICA
-- =====================================================================

CREATE TABLE IF NOT EXISTS sedes (
    id                  BIGSERIAL PRIMARY KEY,
    codigo              VARCHAR(30) NOT NULL UNIQUE,
    nombre              VARCHAR(120) NOT NULL,
    ciudad              VARCHAR(80),
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facultades (
    id                  BIGSERIAL PRIMARY KEY,
    codigo              VARCHAR(30) NOT NULL UNIQUE,
    nombre              VARCHAR(120) NOT NULL,
    sede_id             BIGINT REFERENCES sedes(id) ON DELETE SET NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS carreras (
    id                  BIGSERIAL PRIMARY KEY,
    codigo              VARCHAR(30) NOT NULL UNIQUE,
    nombre              VARCHAR(120) NOT NULL,
    facultad_id         BIGINT REFERENCES facultades(id) ON DELETE SET NULL,
    activa              BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cuatrimestres (
    id                  BIGSERIAL PRIMARY KEY,
    numero              SMALLINT NOT NULL UNIQUE,
    descripcion         VARCHAR(80),
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_numero_cuatrimestre CHECK (numero >= 1 AND numero <= 20)
);

-- =====================================================================
-- CATÁLOGO DE CORREOS INSTITUCIONALES (WHITELIST)
-- =====================================================================

CREATE TABLE IF NOT EXISTS catalogo_correos (
    id                          BIGSERIAL PRIMARY KEY,
    correo_institucional        CITEXT NOT NULL UNIQUE,
    matricula                   VARCHAR(30) UNIQUE,
    carrera_id                  BIGINT REFERENCES carreras(id) ON DELETE SET NULL,
    cuatrimestre_id             BIGINT REFERENCES cuatrimestres(id) ON DELETE SET NULL,
    habilitado                  BOOLEAN NOT NULL DEFAULT TRUE,
    usado                       BOOLEAN NOT NULL DEFAULT FALSE,
    consumido_por_usuario_id    BIGINT,
    consumido_en                TIMESTAMPTZ,
    notas                       TEXT,
    creado_en                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_correo_institucional_formato CHECK (position('@' in correo_institucional) > 1)
);

-- =====================================================================
-- USUARIOS (ESTUDIANTES) Y PERFIL
-- =====================================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id                      BIGSERIAL PRIMARY KEY,
    correo_institucional    CITEXT NOT NULL UNIQUE,
    hash_contrasena         TEXT NOT NULL,
    nombre                  VARCHAR(80) NOT NULL,
    apellido_paterno        VARCHAR(80) NOT NULL,
    apellido_materno        VARCHAR(80),
    fecha_nacimiento        DATE NOT NULL,
    telefono                VARCHAR(30),
    foto_perfil_url         TEXT,
    biografia               TEXT,
    carrera_id              BIGINT REFERENCES carreras(id) ON DELETE SET NULL,
    cuatrimestre_id         BIGINT REFERENCES cuatrimestres(id) ON DELETE SET NULL,
    rol                     rol_usuario_enum NOT NULL DEFAULT 'estudiante',
    estado                  estado_usuario_enum NOT NULL DEFAULT 'activo',
    correo_verificado       BOOLEAN NOT NULL DEFAULT FALSE,
    ultima_conexion_en      TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    eliminado_en            TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_catalogo_consumido_por_usuario'
    ) THEN
        ALTER TABLE catalogo_correos
            ADD CONSTRAINT fk_catalogo_consumido_por_usuario
            FOREIGN KEY (consumido_por_usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS dispositivos_usuario (
    id                      BIGSERIAL PRIMARY KEY,
    usuario_id              BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    uuid_dispositivo        VARCHAR(120) NOT NULL,
    plataforma              VARCHAR(20) NOT NULL DEFAULT 'android',
    token_push              TEXT,
    activo                  BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ultima_actividad_en     TIMESTAMPTZ,
    UNIQUE (usuario_id, uuid_dispositivo)
);

CREATE VIEW vista_estudiantes AS
SELECT
    u.id,
    trim(concat_ws(' ', u.nombre, u.apellido_paterno, u.apellido_materno)) AS nombre_completo,
    EXTRACT(YEAR FROM age(current_date, u.fecha_nacimiento))::INT AS edad,
    c.nombre AS carrera,
    cu.numero AS cuatrimestre,
    u.correo_institucional,
    u.estado,
    u.creado_en
FROM usuarios u
LEFT JOIN carreras c ON c.id = u.carrera_id
LEFT JOIN cuatrimestres cu ON cu.id = u.cuatrimestre_id;

-- =====================================================================
-- RELACIONES ENTRE USUARIOS
-- =====================================================================

CREATE TABLE IF NOT EXISTS seguidores (
    seguidor_id             BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    seguido_id              BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (seguidor_id, seguido_id),
    CONSTRAINT chk_no_seguirse_a_si_mismo CHECK (seguidor_id <> seguido_id)
);

-- =====================================================================
-- PUBLICACIONES (NORMALIZADAS)
-- =====================================================================

CREATE TABLE IF NOT EXISTS tipos_publicacion (
    id                      BIGSERIAL PRIMARY KEY,
    codigo                  VARCHAR(30) NOT NULL UNIQUE,
    nombre                  VARCHAR(60) NOT NULL,
    descripcion             VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS publicaciones (
    id                          BIGSERIAL PRIMARY KEY,
    autor_id                    BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_publicacion_id         BIGINT REFERENCES tipos_publicacion(id) ON DELETE SET NULL,
    titulo                      VARCHAR(180) NOT NULL,
    contenido                   TEXT NOT NULL,
    audiencia                   audiencia_publicacion_enum NOT NULL DEFAULT 'general',
    carrera_objetivo_id         BIGINT REFERENCES carreras(id) ON DELETE SET NULL,
    cuatrimestre_objetivo_id    BIGINT REFERENCES cuatrimestres(id) ON DELETE SET NULL,
    permite_comentarios         BOOLEAN NOT NULL DEFAULT TRUE,
    es_anonima                  BOOLEAN NOT NULL DEFAULT FALSE,
    activa                      BOOLEAN NOT NULL DEFAULT TRUE,
    programada_para             TIMESTAMPTZ,
    publicada_en                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizada_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    eliminada_en                TIMESTAMPTZ,
    CONSTRAINT chk_audiencia_publicacion CHECK (
        (audiencia = 'general' AND carrera_objetivo_id IS NULL AND cuatrimestre_objetivo_id IS NULL)
        OR
        (audiencia = 'carrera' AND carrera_objetivo_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS multimedia_publicacion (
    id                      BIGSERIAL PRIMARY KEY,
    publicacion_id          BIGINT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    tipo                    tipo_mensaje_enum NOT NULL,
    url_archivo             TEXT NOT NULL,
    url_miniatura           TEXT,
    orden                   INT NOT NULL DEFAULT 1,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comentarios_publicacion (
    id                          BIGSERIAL PRIMARY KEY,
    publicacion_id              BIGINT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    usuario_id                  BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    comentario_padre_id         BIGINT REFERENCES comentarios_publicacion(id) ON DELETE CASCADE,
    contenido                   TEXT NOT NULL,
    activo                      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalogo_reacciones (
    id                      BIGSERIAL PRIMARY KEY,
    codigo                  VARCHAR(30) NOT NULL UNIQUE,
    nombre                  VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS reacciones_publicacion (
    publicacion_id          BIGINT NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    usuario_id              BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    reaccion_id             BIGINT NOT NULL REFERENCES catalogo_reacciones(id) ON DELETE RESTRICT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (publicacion_id, usuario_id)
);

-- =====================================================================
-- GRUPOS Y COMUNIDAD
-- =====================================================================

CREATE TABLE IF NOT EXISTS grupos (
    id                      BIGSERIAL PRIMARY KEY,
    nombre                  VARCHAR(120) NOT NULL,
    descripcion             TEXT,
    carrera_id              BIGINT REFERENCES carreras(id) ON DELETE SET NULL,
    privacidad              privacidad_grupo_enum NOT NULL DEFAULT 'publico',
    usuario_dueno_id        BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    foto_grupo_url          TEXT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (nombre, carrera_id)
);

CREATE TABLE IF NOT EXISTS miembros_grupo (
    grupo_id                BIGINT NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
    usuario_id              BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol_miembro             rol_miembro_grupo_enum NOT NULL DEFAULT 'miembro',
    estado_membresia        estado_membresia_enum NOT NULL DEFAULT 'activo',
    unido_en                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    salio_en                TIMESTAMPTZ,
    PRIMARY KEY (grupo_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS publicaciones_grupo (
    id                      BIGSERIAL PRIMARY KEY,
    grupo_id                BIGINT NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
    autor_id                BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo                  VARCHAR(180) NOT NULL,
    contenido               TEXT NOT NULL,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- MENSAJERÍA 1 A 1 Y GRUPAL
-- =====================================================================

CREATE TABLE IF NOT EXISTS salas_chat (
    id                      BIGSERIAL PRIMARY KEY,
    sala_uuid               UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tipo_sala               tipo_sala_chat_enum NOT NULL,
    usuario_a_id            BIGINT REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_b_id            BIGINT REFERENCES usuarios(id) ON DELETE CASCADE,
    grupo_id                BIGINT REFERENCES grupos(id) ON DELETE CASCADE,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_forma_sala_chat CHECK (
        (tipo_sala = 'directo' AND usuario_a_id IS NOT NULL AND usuario_b_id IS NOT NULL AND grupo_id IS NULL AND usuario_a_id <> usuario_b_id)
        OR
        (tipo_sala = 'grupal' AND grupo_id IS NOT NULL AND usuario_a_id IS NULL AND usuario_b_id IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sala_directa_par_usuarios
    ON salas_chat (LEAST(usuario_a_id, usuario_b_id), GREATEST(usuario_a_id, usuario_b_id))
    WHERE tipo_sala = 'directo';

CREATE UNIQUE INDEX IF NOT EXISTS uq_sala_grupal_por_grupo
    ON salas_chat (grupo_id)
    WHERE tipo_sala = 'grupal';

CREATE TABLE IF NOT EXISTS mensajes (
    id                      BIGSERIAL PRIMARY KEY,
    mensaje_uuid            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    sala_chat_id            BIGINT NOT NULL REFERENCES salas_chat(id) ON DELETE CASCADE,
    remitente_id            BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo_mensaje            tipo_mensaje_enum NOT NULL DEFAULT 'texto',
    contenido               TEXT,
    url_archivo             TEXT,
    metadatos               JSONB NOT NULL DEFAULT '{}'::jsonb,
    enviado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    editado_en              TIMESTAMPTZ,
    eliminado_en            TIMESTAMPTZ,
    CONSTRAINT chk_contenido_mensaje CHECK (
        contenido IS NOT NULL OR url_archivo IS NOT NULL OR tipo_mensaje = 'sistema'
    )
);

CREATE TABLE IF NOT EXISTS destinatarios_mensaje (
    mensaje_id              BIGINT NOT NULL REFERENCES mensajes(id) ON DELETE CASCADE,
    destinatario_id         BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    entregado_en            TIMESTAMPTZ,
    leido_en                TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (mensaje_id, destinatario_id)
);

-- =====================================================================
-- NOTIFICACIONES Y AUDITORÍA
-- =====================================================================

CREATE TABLE IF NOT EXISTS notificaciones (
    id                      BIGSERIAL PRIMARY KEY,
    usuario_id              BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo                    VARCHAR(50) NOT NULL,
    titulo                  VARCHAR(120) NOT NULL,
    cuerpo                  TEXT,
    datos                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    leida                   BOOLEAN NOT NULL DEFAULT FALSE,
    creada_en               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    leida_en                TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS auditoria (
    id                      BIGSERIAL PRIMARY KEY,
    actor_usuario_id        BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    accion                  VARCHAR(100) NOT NULL,
    entidad                 VARCHAR(100) NOT NULL,
    entidad_id              VARCHAR(100),
    detalle                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    creada_en               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- FUNCIÓN GENÉRICA PARA actualizaciones de timestamp
-- =====================================================================

CREATE OR REPLACE FUNCTION fn_actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_facultades_actualizado_en') THEN
        CREATE TRIGGER trg_facultades_actualizado_en
        BEFORE UPDATE ON facultades
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_carreras_actualizado_en') THEN
        CREATE TRIGGER trg_carreras_actualizado_en
        BEFORE UPDATE ON carreras
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_cuatrimestres_actualizado_en') THEN
        CREATE TRIGGER trg_cuatrimestres_actualizado_en
        BEFORE UPDATE ON cuatrimestres
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_catalogo_correos_actualizado_en') THEN
        CREATE TRIGGER trg_catalogo_correos_actualizado_en
        BEFORE UPDATE ON catalogo_correos
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_usuarios_actualizado_en') THEN
        CREATE TRIGGER trg_usuarios_actualizado_en
        BEFORE UPDATE ON usuarios
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_publicaciones_actualizada_en') THEN
        CREATE TRIGGER trg_publicaciones_actualizada_en
        BEFORE UPDATE ON publicaciones
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_comentarios_publicacion_actualizado_en') THEN
        CREATE TRIGGER trg_comentarios_publicacion_actualizado_en
        BEFORE UPDATE ON comentarios_publicacion
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_grupos_actualizado_en') THEN
        CREATE TRIGGER trg_grupos_actualizado_en
        BEFORE UPDATE ON grupos
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_publicaciones_grupo_actualizado_en') THEN
        CREATE TRIGGER trg_publicaciones_grupo_actualizado_en
        BEFORE UPDATE ON publicaciones_grupo
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_salas_chat_actualizado_en') THEN
        CREATE TRIGGER trg_salas_chat_actualizado_en
        BEFORE UPDATE ON salas_chat
        FOR EACH ROW EXECUTE FUNCTION fn_actualizar_timestamp();
    END IF;
END $$;

-- =====================================================================
-- REGLA DE NEGOCIO: SOLO CORREOS DE CATÁLOGO PUEDEN REGISTRARSE
-- =====================================================================

CREATE OR REPLACE FUNCTION fn_validar_catalogo_en_registro()
RETURNS TRIGGER AS $$
DECLARE
    v_catalogo_id BIGINT;
    v_habilitado BOOLEAN;
    v_usado BOOLEAN;
BEGIN
    SELECT id, habilitado, usado
    INTO v_catalogo_id, v_habilitado, v_usado
    FROM catalogo_correos
    WHERE correo_institucional = NEW.correo_institucional
    LIMIT 1;

    IF v_catalogo_id IS NULL THEN
        RAISE EXCEPTION 'El correo % no está en el catálogo institucional', NEW.correo_institucional;
    END IF;

    IF NOT v_habilitado THEN
        RAISE EXCEPTION 'El correo % está deshabilitado para registro', NEW.correo_institucional;
    END IF;

    IF v_usado THEN
        RAISE EXCEPTION 'El correo % ya fue utilizado', NEW.correo_institucional;
    END IF;

    NEW.correo_verificado = TRUE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_usuarios_validar_catalogo') THEN
        CREATE TRIGGER trg_usuarios_validar_catalogo
        BEFORE INSERT ON usuarios
        FOR EACH ROW
        EXECUTE FUNCTION fn_validar_catalogo_en_registro();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION fn_consumir_catalogo_post_registro()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE catalogo_correos
    SET
        usado = TRUE,
        consumido_por_usuario_id = NEW.id,
        consumido_en = NOW(),
        actualizado_en = NOW()
    WHERE correo_institucional = NEW.correo_institucional
      AND usado = FALSE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_usuarios_consumir_catalogo') THEN
        CREATE TRIGGER trg_usuarios_consumir_catalogo
        AFTER INSERT ON usuarios
        FOR EACH ROW
        EXECUTE FUNCTION fn_consumir_catalogo_post_registro();
    END IF;
END $$;

-- =====================================================================
-- FUNCIONES DE NEGOCIO PRINCIPALES
-- =====================================================================

CREATE OR REPLACE FUNCTION fn_registrar_estudiante(
    p_correo_institucional CITEXT,
    p_hash_contrasena TEXT,
    p_nombre VARCHAR(80),
    p_apellido_paterno VARCHAR(80),
    p_apellido_materno VARCHAR(80) DEFAULT NULL,
    p_fecha_nacimiento DATE DEFAULT NULL,
    p_telefono VARCHAR(30) DEFAULT NULL,
    p_foto_perfil_url TEXT DEFAULT NULL,
    p_biografia TEXT DEFAULT NULL,
    p_carrera_id BIGINT DEFAULT NULL,
    p_cuatrimestre_id BIGINT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_usuario_id BIGINT;
    v_carrera_catalogo BIGINT;
    v_cuatrimestre_catalogo BIGINT;
BEGIN
    SELECT carrera_id, cuatrimestre_id
    INTO v_carrera_catalogo, v_cuatrimestre_catalogo
    FROM catalogo_correos
    WHERE correo_institucional = p_correo_institucional
    LIMIT 1;

    INSERT INTO usuarios (
        correo_institucional,
        hash_contrasena,
        nombre,
        apellido_paterno,
        apellido_materno,
        fecha_nacimiento,
        telefono,
        foto_perfil_url,
        biografia,
        carrera_id,
        cuatrimestre_id
    )
    VALUES (
        p_correo_institucional,
        p_hash_contrasena,
        p_nombre,
        p_apellido_paterno,
        p_apellido_materno,
        COALESCE(p_fecha_nacimiento, DATE '2000-01-01'),
        p_telefono,
        p_foto_perfil_url,
        p_biografia,
        COALESCE(p_carrera_id, v_carrera_catalogo),
        COALESCE(p_cuatrimestre_id, v_cuatrimestre_catalogo)
    )
    RETURNING id INTO v_usuario_id;

    INSERT INTO auditoria (actor_usuario_id, accion, entidad, entidad_id, detalle)
    VALUES (
        v_usuario_id,
        'registro_estudiante',
        'usuarios',
        v_usuario_id::TEXT,
        jsonb_build_object('correo', p_correo_institucional)
    );

    RETURN v_usuario_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_crear_publicacion(
    p_autor_id BIGINT,
    p_titulo VARCHAR(180),
    p_contenido TEXT,
    p_audiencia audiencia_publicacion_enum DEFAULT 'general',
    p_carrera_objetivo_id BIGINT DEFAULT NULL,
    p_cuatrimestre_objetivo_id BIGINT DEFAULT NULL,
    p_tipo_publicacion_codigo VARCHAR(30) DEFAULT 'general',
    p_permite_comentarios BOOLEAN DEFAULT TRUE,
    p_es_anonima BOOLEAN DEFAULT FALSE
)
RETURNS BIGINT AS $$
DECLARE
    v_publicacion_id BIGINT;
    v_tipo_publicacion_id BIGINT;
BEGIN
    SELECT id
    INTO v_tipo_publicacion_id
    FROM tipos_publicacion
    WHERE codigo = p_tipo_publicacion_codigo
    LIMIT 1;

    IF v_tipo_publicacion_id IS NULL THEN
        RAISE EXCEPTION 'No existe tipo_publicacion con código %', p_tipo_publicacion_codigo;
    END IF;

    IF p_audiencia = 'carrera' AND p_carrera_objetivo_id IS NULL THEN
        RAISE EXCEPTION 'Si audiencia es carrera, carrera_objetivo_id es obligatorio';
    END IF;

    IF p_audiencia = 'general' THEN
        p_carrera_objetivo_id := NULL;
        p_cuatrimestre_objetivo_id := NULL;
    END IF;

    INSERT INTO publicaciones (
        autor_id,
        tipo_publicacion_id,
        titulo,
        contenido,
        audiencia,
        carrera_objetivo_id,
        cuatrimestre_objetivo_id,
        permite_comentarios,
        es_anonima
    )
    VALUES (
        p_autor_id,
        v_tipo_publicacion_id,
        p_titulo,
        p_contenido,
        p_audiencia,
        p_carrera_objetivo_id,
        p_cuatrimestre_objetivo_id,
        p_permite_comentarios,
        p_es_anonima
    )
    RETURNING id INTO v_publicacion_id;

    INSERT INTO auditoria (actor_usuario_id, accion, entidad, entidad_id, detalle)
    VALUES (
        p_autor_id,
        'crear_publicacion',
        'publicaciones',
        v_publicacion_id::TEXT,
        jsonb_build_object('audiencia', p_audiencia, 'carrera_objetivo_id', p_carrera_objetivo_id)
    );

    RETURN v_publicacion_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_crear_grupo(
    p_usuario_dueno_id BIGINT,
    p_nombre VARCHAR(120),
    p_descripcion TEXT DEFAULT NULL,
    p_carrera_id BIGINT DEFAULT NULL,
    p_privacidad privacidad_grupo_enum DEFAULT 'publico',
    p_foto_grupo_url TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_grupo_id BIGINT;
BEGIN
    INSERT INTO grupos (
        nombre,
        descripcion,
        carrera_id,
        privacidad,
        usuario_dueno_id,
        foto_grupo_url
    )
    VALUES (
        p_nombre,
        p_descripcion,
        p_carrera_id,
        p_privacidad,
        p_usuario_dueno_id,
        p_foto_grupo_url
    )
    RETURNING id INTO v_grupo_id;

    INSERT INTO miembros_grupo (grupo_id, usuario_id, rol_miembro, estado_membresia)
    VALUES (v_grupo_id, p_usuario_dueno_id, 'dueno', 'activo')
    ON CONFLICT (grupo_id, usuario_id) DO NOTHING;

    INSERT INTO salas_chat (tipo_sala, grupo_id)
    VALUES ('grupal', v_grupo_id)
    ON CONFLICT DO NOTHING;

    INSERT INTO auditoria (actor_usuario_id, accion, entidad, entidad_id, detalle)
    VALUES (
        p_usuario_dueno_id,
        'crear_grupo',
        'grupos',
        v_grupo_id::TEXT,
        jsonb_build_object('privacidad', p_privacidad)
    );

    RETURN v_grupo_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_obtener_o_crear_sala_directa(
    p_usuario_1 BIGINT,
    p_usuario_2 BIGINT
)
RETURNS BIGINT AS $$
DECLARE
    v_sala_id BIGINT;
    v_u1 BIGINT;
    v_u2 BIGINT;
BEGIN
    IF p_usuario_1 = p_usuario_2 THEN
        RAISE EXCEPTION 'No se puede abrir chat directo con el mismo usuario';
    END IF;

    v_u1 := LEAST(p_usuario_1, p_usuario_2);
    v_u2 := GREATEST(p_usuario_1, p_usuario_2);

    SELECT id
    INTO v_sala_id
    FROM salas_chat
    WHERE tipo_sala = 'directo'
      AND usuario_a_id = v_u1
      AND usuario_b_id = v_u2
    LIMIT 1;

    IF v_sala_id IS NULL THEN
        INSERT INTO salas_chat (tipo_sala, usuario_a_id, usuario_b_id)
        VALUES ('directo', v_u1, v_u2)
        RETURNING id INTO v_sala_id;
    END IF;

    RETURN v_sala_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_enviar_mensaje_directo(
    p_remitente_id BIGINT,
    p_destinatario_id BIGINT,
    p_tipo_mensaje tipo_mensaje_enum DEFAULT 'texto',
    p_contenido TEXT DEFAULT NULL,
    p_url_archivo TEXT DEFAULT NULL,
    p_metadatos JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE(sala_chat_id BIGINT, mensaje_id BIGINT) AS $$
DECLARE
    v_sala_id BIGINT;
    v_mensaje_id BIGINT;
BEGIN
    v_sala_id := fn_obtener_o_crear_sala_directa(p_remitente_id, p_destinatario_id);

    INSERT INTO mensajes (
        sala_chat_id,
        remitente_id,
        tipo_mensaje,
        contenido,
        url_archivo,
        metadatos
    )
    VALUES (
        v_sala_id,
        p_remitente_id,
        p_tipo_mensaje,
        p_contenido,
        p_url_archivo,
        COALESCE(p_metadatos, '{}'::jsonb)
    )
    RETURNING id INTO v_mensaje_id;

    INSERT INTO destinatarios_mensaje (mensaje_id, destinatario_id)
    VALUES (v_mensaje_id, p_destinatario_id)
    ON CONFLICT DO NOTHING;

    INSERT INTO auditoria (actor_usuario_id, accion, entidad, entidad_id, detalle)
    VALUES (
        p_remitente_id,
        'enviar_mensaje_directo',
        'mensajes',
        v_mensaje_id::TEXT,
        jsonb_build_object('sala_chat_id', v_sala_id, 'destinatario_id', p_destinatario_id)
    );

    RETURN QUERY SELECT v_sala_id, v_mensaje_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_enviar_mensaje_grupal(
    p_remitente_id BIGINT,
    p_grupo_id BIGINT,
    p_tipo_mensaje tipo_mensaje_enum DEFAULT 'texto',
    p_contenido TEXT DEFAULT NULL,
    p_url_archivo TEXT DEFAULT NULL,
    p_metadatos JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE(sala_chat_id BIGINT, mensaje_id BIGINT, cantidad_destinatarios BIGINT) AS $$
DECLARE
    v_sala_id BIGINT;
    v_mensaje_id BIGINT;
    v_cantidad BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM miembros_grupo mg
        WHERE mg.grupo_id = p_grupo_id
          AND mg.usuario_id = p_remitente_id
          AND mg.estado_membresia = 'activo'
    ) THEN
        RAISE EXCEPTION 'El usuario % no pertenece al grupo %', p_remitente_id, p_grupo_id;
    END IF;

    SELECT id INTO v_sala_id
    FROM salas_chat
    WHERE tipo_sala = 'grupal'
      AND grupo_id = p_grupo_id
    LIMIT 1;

    IF v_sala_id IS NULL THEN
        INSERT INTO salas_chat (tipo_sala, grupo_id)
        VALUES ('grupal', p_grupo_id)
        RETURNING id INTO v_sala_id;
    END IF;

    INSERT INTO mensajes (
        sala_chat_id,
        remitente_id,
        tipo_mensaje,
        contenido,
        url_archivo,
        metadatos
    )
    VALUES (
        v_sala_id,
        p_remitente_id,
        p_tipo_mensaje,
        p_contenido,
        p_url_archivo,
        COALESCE(p_metadatos, '{}'::jsonb)
    )
    RETURNING id INTO v_mensaje_id;

    INSERT INTO destinatarios_mensaje (mensaje_id, destinatario_id)
    SELECT v_mensaje_id, mg.usuario_id
    FROM miembros_grupo mg
    WHERE mg.grupo_id = p_grupo_id
      AND mg.estado_membresia = 'activo'
      AND mg.usuario_id <> p_remitente_id
    ON CONFLICT DO NOTHING;

    SELECT COUNT(*)
    INTO v_cantidad
    FROM destinatarios_mensaje dm
    WHERE dm.mensaje_id = v_mensaje_id;

    INSERT INTO auditoria (actor_usuario_id, accion, entidad, entidad_id, detalle)
    VALUES (
        p_remitente_id,
        'enviar_mensaje_grupal',
        'mensajes',
        v_mensaje_id::TEXT,
        jsonb_build_object('grupo_id', p_grupo_id, 'sala_chat_id', v_sala_id, 'cantidad_destinatarios', v_cantidad)
    );

    RETURN QUERY SELECT v_sala_id, v_mensaje_id, v_cantidad;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_marcar_mensaje_entregado(
    p_mensaje_id BIGINT,
    p_usuario_id BIGINT
)
RETURNS VOID AS $$
BEGIN
    UPDATE destinatarios_mensaje
    SET entregado_en = COALESCE(entregado_en, NOW())
    WHERE mensaje_id = p_mensaje_id
      AND destinatario_id = p_usuario_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_marcar_mensaje_leido(
    p_mensaje_id BIGINT,
    p_usuario_id BIGINT
)
RETURNS VOID AS $$
BEGIN
    UPDATE destinatarios_mensaje
    SET
        entregado_en = COALESCE(entregado_en, NOW()),
        leido_en = COALESCE(leido_en, NOW())
    WHERE mensaje_id = p_mensaje_id
      AND destinatario_id = p_usuario_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- ÍNDICES
-- =====================================================================

CREATE INDEX IF NOT EXISTS idx_usuarios_carrera ON usuarios(carrera_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_cuatrimestre ON usuarios(cuatrimestre_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_estado ON usuarios(estado);
CREATE INDEX IF NOT EXISTS idx_usuarios_ultima_conexion ON usuarios(ultima_conexion_en DESC);

CREATE INDEX IF NOT EXISTS idx_publicaciones_autor ON publicaciones(autor_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_audiencia_carrera ON publicaciones(audiencia, carrera_objetivo_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_publicada_en ON publicaciones(publicada_en DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_activas ON publicaciones(activa, publicada_en DESC);

CREATE INDEX IF NOT EXISTS idx_comentarios_publicacion ON comentarios_publicacion(publicacion_id);
CREATE INDEX IF NOT EXISTS idx_reacciones_publicacion ON reacciones_publicacion(publicacion_id);

CREATE INDEX IF NOT EXISTS idx_grupos_carrera ON grupos(carrera_id);
CREATE INDEX IF NOT EXISTS idx_miembros_grupo_usuario ON miembros_grupo(usuario_id);
CREATE INDEX IF NOT EXISTS idx_publicaciones_grupo ON publicaciones_grupo(grupo_id);

CREATE INDEX IF NOT EXISTS idx_mensajes_sala_enviado ON mensajes(sala_chat_id, enviado_en DESC);
CREATE INDEX IF NOT EXISTS idx_mensajes_remitente_enviado ON mensajes(remitente_id, enviado_en DESC);
CREATE INDEX IF NOT EXISTS idx_destinatarios_usuario_entregado ON destinatarios_mensaje(destinatario_id, entregado_en);
CREATE INDEX IF NOT EXISTS idx_destinatarios_usuario_leido ON destinatarios_mensaje(destinatario_id, leido_en);

CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario_no_leidas ON notificaciones(usuario_id, leida, creada_en DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_actor_fecha ON auditoria(actor_usuario_id, creada_en DESC);

-- =====================================================================
-- DATOS SEMILLA
-- =====================================================================

INSERT INTO sedes (codigo, nombre, ciudad)
VALUES ('MAIN', 'Campus Principal', 'Ciudad Universitaria')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO facultades (codigo, nombre, sede_id)
SELECT 'ING', 'Facultad de Ingeniería', s.id FROM sedes s WHERE s.codigo = 'MAIN'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO facultades (codigo, nombre, sede_id)
SELECT 'SAL', 'Facultad de Ciencias de la Salud', s.id FROM sedes s WHERE s.codigo = 'MAIN'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO carreras (codigo, nombre, facultad_id)
SELECT 'SIS', 'Ingeniería de Sistemas', f.id FROM facultades f WHERE f.codigo = 'ING'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO carreras (codigo, nombre, facultad_id)
SELECT 'IND', 'Ingeniería Industrial', f.id FROM facultades f WHERE f.codigo = 'ING'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO carreras (codigo, nombre, facultad_id)
SELECT 'MED', 'Medicina', f.id FROM facultades f WHERE f.codigo = 'SAL'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO cuatrimestres (numero, descripcion)
VALUES
    (1, 'Primer cuatrimestre'),
    (2, 'Segundo cuatrimestre'),
    (3, 'Tercer cuatrimestre'),
    (4, 'Cuarto cuatrimestre')
ON CONFLICT (numero) DO NOTHING;

INSERT INTO tipos_publicacion (codigo, nombre, descripcion)
VALUES
    ('general', 'General', 'Contenido general de la comunidad'),
    ('academica', 'Académica', 'Avisos académicos y tareas'),
    ('evento', 'Evento', 'Eventos estudiantiles o institucionales'),
    ('oportunidad', 'Oportunidad', 'Becas, empleos o convocatorias')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO catalogo_reacciones (codigo, nombre)
VALUES
    ('me_gusta', 'Me gusta'),
    ('me_encanta', 'Me encanta'),
    ('interesante', 'Interesante'),
    ('apoyo', 'Apoyo')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO catalogo_correos (correo_institucional, matricula, carrera_id, cuatrimestre_id)
SELECT '20260001@universidad.edu', '20260001', c.id, cu.id
FROM carreras c CROSS JOIN cuatrimestres cu
WHERE c.codigo = 'SIS' AND cu.numero = 2
ON CONFLICT (correo_institucional) DO NOTHING;

INSERT INTO catalogo_correos (correo_institucional, matricula, carrera_id, cuatrimestre_id)
SELECT '20260002@universidad.edu', '20260002', c.id, cu.id
FROM carreras c CROSS JOIN cuatrimestres cu
WHERE c.codigo = 'MED' AND cu.numero = 3
ON CONFLICT (correo_institucional) DO NOTHING;

COMMIT;

-- =====================================================================
-- CONSULTAS Y USOS RÁPIDOS
-- =====================================================================

-- 1) Registrar estudiante (valida contra catalogo_correos)
-- SELECT fn_registrar_estudiante(
--   '20260001@universidad.edu',
--   'hash_bcrypt_o_argon2',
--   'Hugo',
--   'Pérez',
--   'López',
--   DATE '2002-06-15',
--   '999999999',
--   NULL,
--   'Me gusta la programación',
--   NULL,
--   NULL
-- );

-- 2) Crear publicación general o por carrera
-- SELECT fn_crear_publicacion(1, 'Bienvenida', 'Hola comunidad universitaria', 'general', NULL, NULL, 'general', TRUE, FALSE);
-- SELECT fn_crear_publicacion(1, 'Aviso SIS', 'Reunión de laboratorio', 'carrera', (SELECT id FROM carreras WHERE codigo='SIS'), 2, 'academica', TRUE, FALSE);

-- 3) Crear grupo y enviar mensajes
-- SELECT fn_crear_grupo(1, 'Comunidad SIS', 'Grupo oficial de Sistemas', (SELECT id FROM carreras WHERE codigo='SIS'), 'publico', NULL);
-- SELECT * FROM fn_enviar_mensaje_directo(1, 2, 'texto', 'Hola, ¿cómo vas?', NULL, '{"origen":"app_android"}'::jsonb);
-- SELECT * FROM fn_enviar_mensaje_grupal(1, 1, 'texto', 'Bienvenidos al grupo', NULL, '{"origen":"app_android"}'::jsonb);

-- 4) Marcar estados de mensaje
-- SELECT fn_marcar_mensaje_entregado(10, 2);
-- SELECT fn_marcar_mensaje_leido(10, 2);

-- 5) Feed de publicaciones para un estudiante
-- SELECT p.*
-- FROM publicaciones p
-- JOIN usuarios u ON u.id = :usuario_id
-- WHERE p.activa = TRUE
--   AND (
--       p.audiencia = 'general'
--       OR (
--           p.audiencia = 'carrera'
--           AND p.carrera_objetivo_id = u.carrera_id
--           AND (p.cuatrimestre_objetivo_id IS NULL OR p.cuatrimestre_objetivo_id = u.cuatrimestre_id)
--       )
--   )
-- ORDER BY p.publicada_en DESC;

git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/IDS-HUGO/WEBSOCKET_REDUP.git
git push -u origin main
