-- Puesto fijado a mano en una celda del cuadro (el reparto automático lo respeta). Sin puestos en el área no se usa.
CREATE TABLE puesto_fijo (
  periodo text, fecha text, colab_id int, puesto_id int,
  clinica_id bigint NOT NULL DEFAULT current_setting('app.clinica')::bigint REFERENCES clinica(id),
  area_id bigint NOT NULL DEFAULT current_setting('app.area')::bigint REFERENCES area(id),
  PRIMARY KEY (area_id, periodo, fecha, colab_id)
);
ALTER TABLE puesto_fijo ENABLE ROW LEVEL SECURITY;
ALTER TABLE puesto_fijo FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento ON puesto_fijo USING (clinica_id = current_setting('app.clinica')::bigint AND area_id = current_setting('app.area')::bigint);

DO $$
BEGIN
  EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON puesto_fijo TO an_app';
END $$;
