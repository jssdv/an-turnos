-- Esquema de An para SQLite (versión portable). Generado a partir de las migraciones PostgreSQL 001–011 sin RLS, roles ni funciones
-- (esas viven en an/web/sqlite_pg.py). Una clínica y un área: clinica_id/area_id valen 1.

-- 001_base.sql
-- Esquema base de An (PostgreSQL). Las columnas de negocio replican an/turnos/db.py; clinica_id y area_id van AL FINAL para que
-- los INSERT … VALUES posicionales del núcleo sigan valiendo. Una migración publicada no se edita: se agrega otra.

CREATE TABLE clinica (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre text NOT NULL, creada timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE area (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre text NOT NULL, tipo text NOT NULL DEFAULT 'turnos' CHECK (tipo IN ('turnos', 'radiologia')),
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id), UNIQUE (clinica_id, nombre));

CREATE TABLE periodo (id INTEGER PRIMARY KEY AUTOINCREMENT, clave text NOT NULL, revision int NOT NULL DEFAULT 0, publicado_en timestamptz, cerrado_en timestamptz,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id), UNIQUE (area_id, clave));

CREATE TABLE turno (
  codigo text, nombre text, inicio int, fin int, color text, cubre text, pausas text, dom_fest int, solver int, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, codigo)
);

CREATE TABLE colaborador (
  id INTEGER PRIMARY KEY AUTOINCREMENT, nombre text, tipo text, horas_sem REAL, pct REAL, permitidos text, puesto_fijo int, estudio text, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE novedad (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, tipo text, desde text, hasta text, nota text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE asignacion (
  mes text, version text, colab_id int, fecha text, turno text, origen text, fijo int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, mes, version, colab_id, fecha)
);

CREATE TABLE puesto_dia (
  mes text, fecha text, franja text, puesto int, colab_id int, pausa int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE capacitacion (
  mes text, fecha text, colab_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE tarifa (
  concepto text, valor REAL, desde text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE parametro (
  clave text, valor text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, clave)
);

CREATE TABLE periodo_estado (
  clave text, cerrado_en text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, clave)
);

CREATE TABLE cierre (
  periodo text, colab_id int, contratadas REAL, trabajadas REAL,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, periodo, colab_id)
);

CREATE TABLE banco_mov (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, fecha text, horas REAL, concepto text, nota text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE puesto (
  id INTEGER PRIMARY KEY AUTOINCREMENT, numero int, nombre text, color text, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  UNIQUE (area_id, numero)
);

CREATE TABLE demanda (
  id INTEGER PRIMARY KEY AUTOINCREMENT, puesto_id int, tipo_dia text, inicio int, fin int, personas int, obligatorio int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE persona_puesto (
  colab_id int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, colab_id, puesto_id)
);

CREATE TABLE asignacion_puesto (
  periodo text, fecha text, colab_id int, puesto_id int, desde int, hasta int, pausa int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE cambio_turno (
  id INTEGER PRIMARY KEY AUTOINCREMENT, periodo text, tipo text, registrado_en text, usuario text, colab_a int, colab_b int, celdas text, motivo text, excepcion int DEFAULT 0, anulado_en text, anulado_por text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

CREATE TABLE solicitud (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, tipo text, desde text, hasta text, turno text, prioridad text, nota text, registrado_en text, usuario text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);

-- 002_auth.sql
-- Usuarios, permisos por área, sesiones, intentos de ingreso y auditoría.
CREATE TABLE usuario (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  correo text NOT NULL UNIQUE CHECK (correo = lower(correo)),
  nombre text NOT NULL,
  hash_clave text NOT NULL,
  es_admin boolean NOT NULL DEFAULT 0,
  activo boolean NOT NULL DEFAULT 1,
  debe_cambiar boolean NOT NULL DEFAULT 1,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id)
);

CREATE TABLE usuario_area (
  usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
  area_id INTEGER NOT NULL REFERENCES area(id) ON DELETE CASCADE,
  permiso text NOT NULL CHECK (permiso IN ('ver', 'editar')),
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  PRIMARY KEY (usuario_id, area_id)
);
-- un solo usuario edita por área; los demás solo ven
CREATE UNIQUE INDEX un_editor_por_area ON usuario_area (area_id) WHERE permiso = 'editar';

-- sesion e intento_login no se tocan directamente desde la aplicación: solo por funciones SECURITY DEFINER (an/web/auth.py)
CREATE TABLE sesion (
  hash_token text PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
  creada timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultima timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE intento_login (correo text NOT NULL, ip text NOT NULL, fecha timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX ix_intento_login_correo_ip_fecha ON intento_login (correo, ip, fecha);

CREATE TABLE auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  usuario_id INTEGER,
  correo text,
  metodo text NOT NULL,
  ruta text NOT NULL,
  codigo int NOT NULL,
  ip text,
  evento text,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id)
);

-- Funciones de ingreso: SECURITY DEFINER para poder buscar usuario y sesión antes de conocer la clínica.
-- El dueño de estas funciones debe poder saltarse RLS (superusuario o BYPASSRLS): es el rol que aplica las migraciones.

-- 003_menores.sql
-- Purga de sesiones vencidas e intentos viejos, y la aplicación no toca esquema_version.

-- 004_trabajo.sql
-- Cola de trabajos del solver: una tabla; un trabajo activo (en_cola|corriendo) por clínica.
CREATE TABLE trabajo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo_id INTEGER NOT NULL REFERENCES periodo(id),
  tipo text NOT NULL CHECK (tipo IN ('generar', 'dotacion')),
  params jsonb NOT NULL DEFAULT '{}',
  revision_base int NOT NULL,
  estado text NOT NULL DEFAULT 'en_cola' CHECK (estado IN ('en_cola', 'corriendo', 'listo', 'fallido', 'cancelado', 'conflicto')),
  progreso jsonb,
  cancelar boolean NOT NULL DEFAULT 0,
  latido timestamptz,
  resultado jsonb,
  error text,
  creado_por INTEGER REFERENCES usuario(id),
  creado timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  terminado timestamptz,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);
CREATE UNIQUE INDEX un_trabajo_activo_por_clinica ON trabajo (clinica_id) WHERE estado IN ('en_cola', 'corriendo');
CREATE INDEX ix_trabajo_estado_creado ON trabajo (estado, creado);
-- solo por clínica: el 409 de «ya hay un cuadro generándose» debe ver los trabajos de todas las áreas; el permiso por área lo comprueban las rutas

-- 006_auditar_ingreso.sql
-- Auditoría de ingresos fallidos/bloqueados de usuarios que existen (la clínica sale del usuario; un correo inexistente no se audita:
-- ya queda en intento_login). Nunca recibe la contraseña ni el cuerpo.

-- 007_edicion.sql
-- Quién y cuándo cambió un periodo por última vez (lo muestra el 409 de revisión). Lo escribe la API de edición.
ALTER TABLE periodo ADD COLUMN modificado_por text;
ALTER TABLE periodo ADD COLUMN modificado_en timestamptz;

-- 008_cerrar_sesiones.sql
-- Cierra las sesiones de un usuario de la clínica del alcance (el administrador desactiva o restablece la clave de otro usuario).
-- `sesion` no se toca directamente desde la aplicación: solo por funciones SECURITY DEFINER.

-- 009_exporte.sql
-- Exportes en Excel de un periodo (Fase 6). Un exporte nuevo borra el anterior del mismo tipo y la descarga borra el archivo (numero = máximo + 1 por área, periodo y tipo).
CREATE TABLE exporte (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  periodo_id INTEGER NOT NULL REFERENCES periodo(id) ON DELETE CASCADE,
  tipo text NOT NULL CHECK (tipo IN ('cuadro', 'puestos', 'horas', 'semana')),
  numero int NOT NULL CHECK (numero >= 1),
  nombre_archivo text NOT NULL,
  contenido BLOB NOT NULL,
  creado_por INTEGER REFERENCES usuario(id),
  creado timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (area_id, periodo_id, tipo, numero)
);

-- 010_archivo.sql
-- Cuadro mensual de Radiología subido como .xlsx (Fase 7b; deja de usarse cuando Radiología se genere sola, Fase 7c).
CREATE TABLE archivo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre text NOT NULL,
  contenido BLOB NOT NULL,
  subido_por INTEGER REFERENCES usuario(id),
  subido timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id)
);
CREATE INDEX ix_archivo_area_id_subido_desc ON archivo (area_id, subido DESC);

-- 011_puesto_fijo.sql
-- Puesto fijado a mano en una celda del cuadro (el reparto automático lo respeta). Sin puestos en el área no se usa.
CREATE TABLE puesto_fijo (
  periodo text, fecha text, colab_id int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, periodo, fecha, colab_id)
);
