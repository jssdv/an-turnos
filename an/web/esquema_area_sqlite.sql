-- Esquema de un área de An (archivo area_<id>.db, adjunto a an.db como esquema `area`). Versión 1.
-- Las mismas tablas de área de esquema_sqlite.sql (v12 + 013) sin las claves foráneas a clinica/area/usuario (viven en otro archivo).
-- clinica_id y area_id se conservan (valen 1 dentro del archivo) para no tocar el SQL del núcleo. Migraciones: migraciones_area/ desde 002.

CREATE TABLE periodo (id INTEGER PRIMARY KEY AUTOINCREMENT, clave text NOT NULL, revision int NOT NULL DEFAULT 0, publicado_en timestamptz, cerrado_en timestamptz,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1, UNIQUE (area_id, clave));

CREATE TABLE turno (
  codigo text, nombre text, inicio int, fin int, color text, cubre text, pausas text, dom_fest int, solver int, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, codigo)
);

CREATE TABLE colaborador (
  id INTEGER PRIMARY KEY AUTOINCREMENT, nombre text, tipo text, horas_sem REAL, pct REAL, permitidos text, puesto_fijo int, estudio text, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE novedad (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, tipo text, desde text, hasta text, nota text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE asignacion (
  mes text, version text, colab_id int, fecha text, turno text, origen text, fijo int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, mes, version, colab_id, fecha)
);

CREATE TABLE puesto_dia (
  mes text, fecha text, franja text, puesto int, colab_id int, pausa int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE capacitacion (
  mes text, fecha text, colab_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE tarifa (
  concepto text, valor REAL, desde text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE parametro (
  clave text, valor text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, clave)
);

CREATE TABLE periodo_estado (
  clave text, cerrado_en text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, clave)
);

CREATE TABLE cierre (
  periodo text, colab_id int, contratadas REAL, trabajadas REAL,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, periodo, colab_id)
);

CREATE TABLE banco_mov (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, fecha text, horas REAL, concepto text, nota text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE puesto (
  id INTEGER PRIMARY KEY AUTOINCREMENT, numero int, nombre text, color text, activo int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  UNIQUE (area_id, numero)
);

CREATE TABLE demanda (
  id INTEGER PRIMARY KEY AUTOINCREMENT, puesto_id int, tipo_dia text, inicio int, fin int, personas int, obligatorio int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE persona_puesto (
  colab_id int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, colab_id, puesto_id)
);

CREATE TABLE asignacion_puesto (
  periodo text, fecha text, colab_id int, puesto_id int, desde int, hasta int, pausa int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE cambio_turno (
  id INTEGER PRIMARY KEY AUTOINCREMENT, periodo text, tipo text, registrado_en text, usuario text, colab_a int, colab_b int, celdas text, motivo text, excepcion int DEFAULT 0, anulado_en text, anulado_por text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE solicitud (
  id INTEGER PRIMARY KEY AUTOINCREMENT, colab_id int, tipo text, desde text, hasta text, turno text, prioridad text, nota text, registrado_en text, usuario text,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

ALTER TABLE periodo ADD COLUMN modificado_por text;

ALTER TABLE periodo ADD COLUMN modificado_en timestamptz;

CREATE TABLE exporte (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  periodo_id INTEGER NOT NULL REFERENCES periodo(id) ON DELETE CASCADE,
  tipo text NOT NULL CHECK (tipo IN ('cuadro', 'puestos', 'horas', 'semana')),
  numero int NOT NULL CHECK (numero >= 1),
  nombre_archivo text NOT NULL,
  contenido BLOB NOT NULL,
  creado_por INTEGER,
  creado timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (area_id, periodo_id, tipo, numero)
);

CREATE TABLE archivo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre text NOT NULL,
  contenido BLOB NOT NULL,
  subido_por INTEGER,
  subido timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX ix_archivo_area_id_subido_desc ON archivo (area_id, subido DESC);

CREATE TABLE puesto_fijo (
  periodo text, fecha text, colab_id int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, periodo, fecha, colab_id)
);

CREATE TABLE puesto_fijo_mitad (
  periodo text, fecha text, colab_id int, tramo int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1,
  area_id INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (area_id, periodo, fecha, colab_id, tramo)
);
