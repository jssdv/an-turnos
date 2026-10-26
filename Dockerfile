# Imágenes de producción (docker-compose.prod.yml). API y trabajador comparten `servidor`; `caddy` lleva el front compilado.
FROM python:3.13-slim AS servidor
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements-web.txt requirements-servidor.txt ./
RUN pip install -r requirements-servidor.txt
COPY an ./an
COPY web/sembrar_demo.py ./web/sembrar_demo.py
RUN useradd --system --uid 10001 an
USER an
EXPOSE 8000
CMD ["uvicorn", "an.web.app:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM caddy:2 AS caddy
COPY --from=web /web/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
