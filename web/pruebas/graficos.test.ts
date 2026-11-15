// node --test pruebas/   (Node 22.18+ ejecuta TypeScript sin compilar)
import assert from "node:assert/strict";
import { test } from "node:test";
import { tonoMapa, trazo } from "../src/componentes/trazo.ts";

test("trazo escala de abajo (0) hacia arriba (máximo)", () => {
  assert.equal(trazo([0, 5, 10], 100, 50, 10), "M0,50 L50,25 L100,0");
});

test("un punto con máximo 0 no da NaN", () => {
  assert.equal(trazo([3], 100, 50, 0), "M0,50");
});

test("tonoMapa: rojo si falta, azul si sobra, gris justo, nada sin dato", () => {
  assert.deepEqual(tonoMapa(-2, 2), { tono: "falta", alfa: 1 });
  assert.deepEqual(tonoMapa(1, 2), { tono: "sobra", alfa: 0.5 });
  assert.deepEqual(tonoMapa(0, 2), { tono: "justo", alfa: 1 });
  assert.deepEqual(tonoMapa(null, 2), { tono: "vacio", alfa: 0 });
  assert.deepEqual(tonoMapa(-0.1, 0), { tono: "falta", alfa: 1 });  // sin máximo no divide por cero
});
