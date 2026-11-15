// node --test pruebas/   (Node 22.18+ ejecuta TypeScript sin compilar)
import assert from "node:assert/strict";
import { test } from "node:test";
import { leerLista } from "../src/pantallas/pegar.ts";

test("lee filas pegadas de Excel", () => {
  const r = leerLista("Nombre\tHoras\tDedicación\nAna Pérez\t42\t100\nLuis\t36,5\t50 %\nMarta;24;0,5\n\nana perez\t40\nJosé\nMala\t99\nOtra\t42\t0\n", ["José"]);
  assert.deepEqual(r.personas, [
    { nombre: "Ana Pérez", horas_sem: 42, pct: 1 },
    { nombre: "Luis", horas_sem: 36.5, pct: 0.5 },
    { nombre: "Marta", horas_sem: 24, pct: 0.5 },
  ]);
  assert.deepEqual(r.repetidas, ["ana perez", "José"]);  // repetida en la lista y ya en el área (sin tildes ni mayúsculas)
  assert.equal(r.errores.length, 2);
  assert.match(r.errores[0], /Línea 8 \(Mala\)/);
});

test("solo nombres: 42 h y tiempo completo", () => {
  assert.deepEqual(leerLista("Uno\nDos").personas.map((p) => [p.horas_sem, p.pct]), [[42, 1], [42, 1]]);
});
