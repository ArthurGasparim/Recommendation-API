#!/usr/bin/env bash
set -Eeuo pipefail

CLEANUP_CLUSTER_NAME="${CLEANUP_CLUSTER_NAME:-observability}"
CLEANUP_AWS_REGION="${CLEANUP_AWS_REGION:-us-east-1}"
CLEANUP_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_CONFIRM=false
CLEANUP_SKIP_BACKUP=false
CLEANUP_DELETE_ECR=false
CLEANUP_DELETE_IAM_POLICY=false

usage() {
  echo "Uso: $0 [--yes] [--skip-backup] [--delete-ecr] [--delete-iam-policy]"
  echo "Cluster: ${CLEANUP_CLUSTER_NAME} | Região: ${CLEANUP_AWS_REGION}"
}

for argument in "$@"; do
  case "$argument" in
    --yes) CLEANUP_CONFIRM=true ;;
    --skip-backup) CLEANUP_SKIP_BACKUP=true ;;
    --delete-ecr) CLEANUP_DELETE_ECR=true ;;
    --delete-iam-policy) CLEANUP_DELETE_IAM_POLICY=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Argumento desconhecido: $argument" >&2; usage; exit 2 ;;
  esac
done

if [[ "$CLEANUP_CONFIRM" != true ]]; then
  read -r -p "Remover o ambiente EKS '${CLEANUP_CLUSTER_NAME}' em '${CLEANUP_AWS_REGION}'? Digite o nome do cluster: " CLEANUP_TYPED_NAME
  if [[ "$CLEANUP_TYPED_NAME" != "$CLEANUP_CLUSTER_NAME" ]]; then
    echo "Confirmação inválida; nenhuma alteração realizada."
    exit 1
  fi
fi

if aws eks describe-cluster --name "$CLEANUP_CLUSTER_NAME" --region "$CLEANUP_AWS_REGION" >/dev/null 2>&1; then
  aws eks update-kubeconfig --name "$CLEANUP_CLUSTER_NAME" --region "$CLEANUP_AWS_REGION" >/dev/null

  if [[ "$CLEANUP_SKIP_BACKUP" != true ]] \
    && kubectl get pod -n dev -l app=postgres-db -o name 2>/dev/null | grep -q .; then
    echo "Criando backup do PostgreSQL antes do teardown..."
    "${CLEANUP_PROJECT_DIR}/scripts/backup_database.sh"
  elif [[ "$CLEANUP_SKIP_BACKUP" != true ]]; then
    echo "PostgreSQL não está em execução; não há pod disponível para backup."
  fi

  kubectl delete -k "${CLEANUP_PROJECT_DIR}/k8s/app/" --ignore-not-found=true || true
  kubectl delete -k "${CLEANUP_PROJECT_DIR}/k8s/monitoring/" --ignore-not-found=true || true

  for release_namespace in "monitoring:monitoring" "fluent-bit:logging" "kibana:logging" "elasticsearch:logging" "aws-load-balancer-controller:kube-system"; do
    CLEANUP_RELEASE="${release_namespace%%:*}"
    CLEANUP_NAMESPACE="${release_namespace##*:}"
    if helm status "$CLEANUP_RELEASE" -n "$CLEANUP_NAMESPACE" >/dev/null 2>&1; then
      helm uninstall "$CLEANUP_RELEASE" -n "$CLEANUP_NAMESPACE"
    fi
  done

  kubectl wait --for=delete ingress --all -A --timeout=180s >/dev/null 2>&1 || true
  # Remove PVCs/namespaces após o backup para não deixar volumes EBS cobrando.
  for CLEANUP_NAMESPACE_TO_DELETE in dev monitoring logging; do
    kubectl delete namespace "$CLEANUP_NAMESPACE_TO_DELETE" \
      --ignore-not-found=true --wait=true --timeout=180s || true
  done
  eksctl delete cluster --name "$CLEANUP_CLUSTER_NAME" --region "$CLEANUP_AWS_REGION"
else
  echo "Cluster '${CLEANUP_CLUSTER_NAME}' não existe; teardown do EKS ignorado."
fi

if [[ "$CLEANUP_DELETE_ECR" == true ]]; then
  for CLEANUP_REPOSITORY in fastapi-recommender react-frontend; do
    if aws ecr describe-repositories --repository-names "$CLEANUP_REPOSITORY" --region "$CLEANUP_AWS_REGION" >/dev/null 2>&1; then
      aws ecr delete-repository --repository-name "$CLEANUP_REPOSITORY" --force --region "$CLEANUP_AWS_REGION" >/dev/null
      echo "Repositório ECR removido: ${CLEANUP_REPOSITORY}"
    fi
  done
fi

if [[ "$CLEANUP_DELETE_IAM_POLICY" == true ]]; then
  CLEANUP_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  CLEANUP_POLICY_ARN="arn:aws:iam::${CLEANUP_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy"
  aws iam delete-policy --policy-arn "$CLEANUP_POLICY_ARN"
fi

echo "Teardown concluído. Kubeconfig e cache Docker local foram preservados."
