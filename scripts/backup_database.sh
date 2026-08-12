#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_NAMESPACE="${BACKUP_NAMESPACE:-dev}"
BACKUP_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_OUTPUT_DIR="${BACKUP_OUTPUT_DIR:-${BACKUP_PROJECT_DIR}/backups}"
BACKUP_TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_OUTPUT_DIR}/bookstore-${BACKUP_TIMESTAMP}.dump"

BACKUP_POD="$(kubectl get pod -n "$BACKUP_NAMESPACE" -l app=postgres-db -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "$BACKUP_POD" ]]; then
  echo "Pod PostgreSQL não encontrado no namespace '${BACKUP_NAMESPACE}'." >&2
  exit 1
fi

mkdir -p "$BACKUP_OUTPUT_DIR"
kubectl exec -n "$BACKUP_NAMESPACE" "$BACKUP_POD" -- /bin/sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "O backup foi criado vazio; operação interrompida." >&2
  exit 1
fi

chmod 600 "$BACKUP_FILE"
echo "Backup criado em: ${BACKUP_FILE}"
