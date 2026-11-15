-- 002: cuándo se registró cada ausencia (hora local del PC). Las filas anteriores quedan en NULL: «sin dato».
ALTER TABLE novedad ADD COLUMN registrado_en text;
