# Herramientas de respaldo: pg_dump/pg_restore/psql 16 + age (cifrado con clave pública) + ssh-keygen (firma de cada respaldo). También sirve de servidor desechable para restaurar.
FROM postgres:16-alpine
RUN apk add --no-cache age openssh-keygen
