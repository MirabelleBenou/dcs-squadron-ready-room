FROM python:3.12-slim

WORKDIR /srv

# postgresql-client-16, depuis le dépôt officiel PGDG (apt.postgresql.org),
# en remplacement du paquet "postgresql-client" générique de Debian bookworm
# -- celui-ci résout en version 15, face à un serveur postgres:16
# (docker-compose.yml) : pg_dump refuse de sauvegarder un serveur d'une
# version majeure supérieure à la sienne (Lot 2.2a §2). Fournit pg_isready
# (attente de "db" dans entrypoint.sh) et pg_dump/pg_restore (sauvegarde
# avant migration, entrypoint.sh §3).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && printf 'Types: deb\nURIs: https://apt.postgresql.org/pub/repos/apt\nSuites: %s-pgdg\nComponents: main\nSigned-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc\n' "$VERSION_CODENAME" \
        > /etc/apt/sources.list.d/pgdg.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY VERSION .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Lot D1 -- module Debriefing : point de montage du volume nommé
# `debrief_raw` (cf. docker-compose.yml). Conteneur en root (aucune
# directive USER ici) -> pas de chown/chmod nécessaire.
RUN mkdir -p /data/debrief_raw

# Lot 3.2e, volet ② -- module Centre de Commandement : point de montage du
# volume nommé `crests` (cf. docker-compose.yml), écussons d'escadrille.
# Conteneur en root (aucune directive USER ici) -> pas de chown/chmod
# nécessaire, même raison que le volume ci-dessus.
RUN mkdir -p /data/crests

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
