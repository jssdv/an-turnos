// node --test pruebas/   (Node 22.18+ ejecuta TypeScript sin compilar)
import assert from "node:assert/strict";
import { test } from "node:test";
import { trazo } from "../src/componentes/trazo.ts";

test("trazo escala de abajo (0) hacia arriba (máximo)", () => {
  assert.equal(trazo([0, 5, 10], 100, 50, 10), "M0,50 L50,25 L100,0");
});

test("un punto con máximo 0 no da NaN", () => {
  assert.equal(trazo([3], 100, 50, 0), "M0,50");
});
