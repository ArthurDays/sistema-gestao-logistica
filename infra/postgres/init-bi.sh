#!/bin/sh
set -eu

export PGPASSWORD="$POSTGRES_PASSWORD"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=bi_user="$METABASE_BI_USER" --set=bi_password="$METABASE_BI_PASSWORD" \
  --set=app_user="$METABASE_APP_USER" --set=app_password="$METABASE_APP_PASSWORD" \
  --set=domain_user="$DOMAIN_APP_USER" --set=domain_password="$DOMAIN_APP_PASSWORD" <<-'SQL'
  SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', :'domain_user')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'domain_user') \gexec
  SELECT format(
    'ALTER ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION',
    :'domain_user', :'domain_password'
  ) \gexec

  SELECT format('CREATE ROLE %I LOGIN', :'bi_user')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'bi_user') \gexec
  SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'bi_user', :'bi_password') \gexec

  SELECT format('CREATE ROLE %I LOGIN', :'app_user')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec
  SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password') \gexec

  SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'bi_user') \gexec
  SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'bi_user') \gexec
  SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'domain_user') \gexec
  SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'domain_user') \gexec
  SELECT format(
    'ALTER %s %I.%I OWNER TO %I',
    CASE c.relkind
      WHEN 'S' THEN 'SEQUENCE'
      WHEN 'v' THEN 'VIEW'
      WHEN 'm' THEN 'MATERIALIZED VIEW'
      ELSE 'TABLE'
    END,
    n.nspname,
    c.relname,
    :'domain_user'
  )
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S', 'v', 'm') \gexec
SQL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  --set=app_db="${METABASE_APP_DB:-metabase}" --set=app_user="$METABASE_APP_USER" <<-'SQL'
  SELECT format('CREATE DATABASE %I OWNER %I', :'app_db', :'app_user')
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'app_db') \gexec
SQL
