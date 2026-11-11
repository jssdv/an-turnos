-- Un archivo por área: las tablas de cada área pasan a area_<id>.db (esquema_area_sqlite.sql). Antes de este SQL, esquema.py copia
-- las filas de cada área a su archivo (pre-paso en Python de la 014). Aquí: trabajo sin la clave foránea a periodo (ya vive en otro
-- archivo), se quitan las tablas de área de an.db y los permisos del administrador (edita todas las áreas sin fila).
CREATE TABLE trabajo_nueva (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo_id INTEGER NOT NULL,
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
INSERT INTO trabajo_nueva SELECT * FROM trabajo;
DROP TABLE trabajo;
ALTER TABLE trabajo_nueva RENAME TO trabajo;
CREATE UNIQUE INDEX un_trabajo_activo_por_clinica ON trabajo (clinica_id) WHERE estado IN ('en_cola', 'corriendo');
CREATE INDEX ix_trabajo_estado_creado ON trabajo (estado, creado);

DROP TABLE puesto_fijo_mitad;
DROP TABLE puesto_fijo;
DROP TABLE archivo;
DROP TABLE exporte;
DROP TABLE solicitud;
DROP TABLE cambio_turno;
DROP TABLE asignacion_puesto;
DROP TABLE persona_puesto;
DROP TABLE demanda;
DROP TABLE puesto;
DROP TABLE banco_mov;
DROP TABLE cierre;
DROP TABLE periodo_estado;
DROP TABLE parametro;
DROP TABLE tarifa;
DROP TABLE capacitacion;
DROP TABLE puesto_dia;
DROP TABLE asignacion;
DROP TABLE novedad;
DROP TABLE colaborador;
DROP TABLE turno;
DROP TABLE periodo;

DELETE FROM usuario_area WHERE usuario_id IN (SELECT id FROM usuario WHERE es_admin);
