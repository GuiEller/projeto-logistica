#!/usr/bin/env bash
# A imagem oficial do Postgres roda tudo o que está em /docker-entrypoint-initdb.d
# uma única vez, na primeira subida, com o banco vazio. É isso que faz o
# "docker compose up" entregar o banco pronto, sem ninguém rodar SQL na mão.
set -euo pipefail

for migration in /projeto/db/migrations/*.sql; do
  echo ">> $migration"
  psql -q -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$migration"
done

echo ">> testes de integridade"
psql -q -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -f /projeto/sql/testes/integridade.sql
