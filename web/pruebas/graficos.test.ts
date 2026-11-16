// node --test pruebas/   (Node 22.18+ ejecuta TypeScript sin compilar)
import assert from "node:assert/strict";
import { test } from "node:test";
import { rangoAnterior, tonoMapa, trazo, variacion } from "../src/componentes/trazo.ts";

test("trazo escala de abajo (0) hacia arriba (máximo)", () => {
  assert.equal(trazo([0, 5, 10], 100, 50, 10), "M0,50 L50,25 L100,0");
});

test("un punto con máximo 0 no da NaN", () => {
  assert.equal(trazo([3], 100, 50, 0), "M0,50");
});

test("tonoMapa: rojo según el faltante, gris si está cubierto, nada sin demanda", () => {
  assert.deepEqual(tonoMapa(2, 2), { tono: "falta", alfa: 1 });
  assert.deepEqual(tonoMapa(1, 2), { tono: "falta", alfa: 0.5 });
  assert.deepEqual(tonoMapa(0, 2), { tono: "cubierto", alfa: 1 });
  assert.deepEqual(tonoMapa(0.01, 2), { tono: "cubierto", alfa: 1 });  // menos de 0,05 personas: cubierto, no «faltan 0»
  assert.deepEqual(tonoMapa(null, 2), { tono: "vacio", alfa: 0 });
  assert.deepEqual(tonoMapa(0.5, 0), { tono: "falta", alfa: 1 });  // sin máximo no divide por cero
});

test("tonoMapa: azul donde sobra gente, pero si falta manda el rojo", () => {
  assert.deepEqual(tonoMapa(0, 2, 1, 2), { tono: "sobra", alfa: 0.5 });
  assert.deepEqual(tonoMapa(0.5, 2, 1, 2), { tono: "falta", alfa: 0.25 });
  assert.deepEqual(tonoMapa(0, 2, 0.01, 2), { tono: "cubierto", alfa: 1 });
  assert.deepEqual(tonoMapa(0, 2, 1, 0), { tono: "sobra", alfa: 1 });
});

test("rangoAnterior: los meses justo antes, del mismo largo, cruzando el año", () => {
  assert.deepEqual(rangoAnterior("2026-05", "2026-10"), ["2025-11", "2026-04"]);
  assert.deepEqual(rangoAnterior("2026-01", "2026-01"), ["2025-12", "2025-12"]);
});

test("variacion: flecha, cifra y unidad; sin dato anterior, nada", () => {
  assert.equal(variacion(5.5, 4.25, "pp"), "▲ 1,3 pp frente al rango anterior");
  assert.equal(variacion(2, 5, "días"), "▼ 3 días frente al rango anterior");
  assert.equal(variacion(3, 3.01, "h"), "Igual que el rango anterior");
  assert.equal(variacion(3, null, "h"), undefined);
  assert.equal(variacion(2, 1, "personas"), "▲ 1 persona frente al rango anterior");
  assert.equal(variacion(2, 1, "pp"), "▲ 1 pp frente al rango anterior");
});
