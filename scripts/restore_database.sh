#!/usr/bin/env bash
set -Eeuo pipefail

RESTORE_NAMESPACE="${RESTORE_NAMESPACE:-dev}"
RESTORE_CONFIRM=false
RESTORE_FILE=""

for argument in "$@"; do
  case "$argument" in
    --yes) RESTORE_CONFIRM=true ;;
    *)
      if [[ -z "$RESTORE_FILE" ]]; then
        RESTORE_FILE="$argument"
      else
        echo "Uso: $0 CAMINHO_DO_BACKUP [--yes]" >&2
        exit 2
      fi
      ;;
  esac
done

if [[ -z "$RESTORE_FILE" || ! -f "$RESTORE_FILE" ]]; then
  echo "Informe um arquivo de backup existente." >&2
  exit 2
fi

if [[ "$RESTORE_CONFIRM" != true ]]; then
  read -r -p "A restauração substituirá dados no PostgreSQL. Digite RESTAURAR: " RESTORE_TYPED_CONFIRMATION
  [[ "$RESTORE_TYPED_CONFIRMATION" == "RESTAURAR" ]] || exit 1
fi

RESTORE_POD="$(kubectl get pod -n "$RESTORE_NAMESPACE" -l app=postgres-db -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "$RESTORE_POD" ]]; then
  echo "Pod PostgreSQL não encontrado no namespace '${RESTORE_NAMESPACE}'." >&2
  exit 1
fi

kubectl exec -i -n "$RESTORE_NAMESPACE" "$RESTORE_POD" -- /bin/sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' \
  < "$RESTORE_FILE"

kubectl rollout restart deployment/fastapi-recommender -n "$RESTORE_NAMESPACE"
kubectl rollout status deployment/fastapi-recommender -n "$RESTORE_NAMESPACE" --timeout=300s

echo "Restauração concluída a partir de: ${RESTORE_FILE}"
