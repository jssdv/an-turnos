-- Puesto fijado a mano por mitad (tramo 1 = mañana, 2 = tarde) en una C partida. Excluyente con puesto_fijo de la misma celda.
CREATE TABLE puesto_fijo_mitad (
  periodo text, fecha text, colab_id int, tramo int, puesto_id int,
  clinica_id INTEGER NOT NULL DEFAULT 1 REFERENCES clinica(id),
  area_id INTEGER NOT NULL DEFAULT 1 REFERENCES area(id),
  PRIMARY KEY (area_id, periodo, fecha, colab_id, tramo)
);
