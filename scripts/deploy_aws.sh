#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_CLUSTER_NAME="${DEPLOY_CLUSTER_NAME:-observability}"
DEPLOY_AWS_REGION="${DEPLOY_AWS_REGION:-us-east-1}"
DEPLOY_KUBERNETES_VERSION="${DEPLOY_KUBERNETES_VERSION:-1.34}"
DEPLOY_NODE_TYPE="${DEPLOY_NODE_TYPE:-t3.large}"
DEPLOY_NODE_COUNT="${DEPLOY_NODE_COUNT:-2}"
DEPLOY_IMAGE_TAG="${DEPLOY_IMAGE_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
DEPLOY_CREATE_CLUSTER=false
DEPLOY_SKIP_BUILD=false
DEPLOY_SKIP_OBSERVABILITY=false

usage() {
  cat <<EOF
Uso: $0 [opções]

Implanta API, frontend e PostgreSQL no EKS. A criação do cluster, que gera
custo na AWS, só ocorre com --create-cluster.

Opções:
  --create-cluster       cria o EKS caso ele não exista
  --skip-build           reutiliza imagens já existentes no ECR
  --skip-observability   não instala Prometheus e Grafana
  -h, --help             mostra esta ajuda

Variáveis:
  DEPLOY_CLUSTER_NAME       padrão: observability
  DEPLOY_AWS_REGION        padrão: us-east-1
  DEPLOY_KUBERNETES_VERSION padrão: 1.34
  DEPLOY_NODE_TYPE         padrão: t3.large
  DEPLOY_NODE_COUNT        padrão: 2
  DEPLOY_IMAGE_TAG         tag imutável das imagens
  DEPLOY_ADMIN_USER_IDS    IDs administrativos separados por vírgula
  DEPLOY_POSTGRES_PASSWORD senha usada apenas na criação inicial do Secret
  DEPLOY_AUTH_SECRET       chave de autenticação; se omitida, é gerada
EOF
}

for DEPLOY_ARGUMENT in "$@"; do
  case "$DEPLOY_ARGUMENT" in
    --create-cluster) DEPLOY_CREATE_CLUSTER=true ;;
    --skip-build) DEPLOY_SKIP_BUILD=true ;;
    --skip-observability) DEPLOY_SKIP_OBSERVABILITY=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Argumento desconhecido: $DEPLOY_ARGUMENT" >&2; usage; exit 2 ;;
  esac
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Comando obrigatório não encontrado: $1" >&2
    exit 1
  }
}

for DEPLOY_COMMAND in aws docker kubectl openssl; do
  require_command "$DEPLOY_COMMAND"
done

if ! aws eks describe-cluster \
  --name "$DEPLOY_CLUSTER_NAME" \
  --region "$DEPLOY_AWS_REGION" >/dev/null 2>&1; then
  if [[ "$DEPLOY_CREATE_CLUSTER" != true ]]; then
    echo "O cluster '$DEPLOY_CLUSTER_NAME' não existe em '$DEPLOY_AWS_REGION'." >&2
    echo "Execute novamente com --create-cluster quando quiser iniciar a cobrança." >&2
    exit 1
  fi
  require_command eksctl
  echo "Criando o cluster EKS '$DEPLOY_CLUSTER_NAME'..."
  eksctl create cluster \
    --name "$DEPLOY_CLUSTER_NAME" \
    --region "$DEPLOY_AWS_REGION" \
    --version "$DEPLOY_KUBERNETES_VERSION" \
    --tags "recommendation-api:managed=true,recommendation-api:cluster=${DEPLOY_CLUSTER_NAME}" \
    --managed \
    --node-ami-family AmazonLinux2023 \
    --node-type "$DEPLOY_NODE_TYPE" \
    --nodes "$DEPLOY_NODE_COUNT" \
    --nodes-min 1 \
    --nodes-max 3
fi

aws eks update-kubeconfig \
  --name "$DEPLOY_CLUSTER_NAME" \
  --region "$DEPLOY_AWS_REGION" >/dev/null

DEPLOY_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
DEPLOY_CLUSTER_ARN="$(aws eks describe-cluster \
  --name "$DEPLOY_CLUSTER_NAME" --region "$DEPLOY_AWS_REGION" \
  --query 'cluster.arn' --output text)"
aws eks tag-resource \
  --resource-arn "$DEPLOY_CLUSTER_ARN" \
  --tags "recommendation-api:managed=true,recommendation-api:cluster=${DEPLOY_CLUSTER_NAME}"
DEPLOY_REGISTRY="${DEPLOY_ACCOUNT_ID}.dkr.ecr.${DEPLOY_AWS_REGION}.amazonaws.com"
DEPLOY_API_IMAGE="${DEPLOY_REGISTRY}/fastapi-recommender:${DEPLOY_IMAGE_TAG}"
DEPLOY_FRONT_IMAGE="${DEPLOY_REGISTRY}/react-frontend:${DEPLOY_IMAGE_TAG}"

for DEPLOY_REPOSITORY in fastapi-recommender react-frontend; do
  if ! aws ecr describe-repositories \
    --repository-names "$DEPLOY_REPOSITORY" \
    --region "$DEPLOY_AWS_REGION" >/dev/null 2>&1; then
    aws ecr create-repository \
      --repository-name "$DEPLOY_REPOSITORY" \
      --image-scanning-configuration scanOnPush=true \
      --tags \
        Key=recommendation-api:managed,Value=true \
        Key=recommendation-api:cluster,Value="$DEPLOY_CLUSTER_NAME" \
      --region "$DEPLOY_AWS_REGION" >/dev/null
  fi
  DEPLOY_REPOSITORY_ARN="$(aws ecr describe-repositories \
    --repository-names "$DEPLOY_REPOSITORY" --region "$DEPLOY_AWS_REGION" \
    --query 'repositories[0].repositoryArn' --output text)"
  aws ecr tag-resource \
    --resource-arn "$DEPLOY_REPOSITORY_ARN" \
    --tags \
      Key=recommendation-api:managed,Value=true \
      Key=recommendation-api:cluster,Value="$DEPLOY_CLUSTER_NAME"
done

if [[ "$DEPLOY_SKIP_BUILD" != true ]]; then
  aws ecr get-login-password --region "$DEPLOY_AWS_REGION" \
    | docker login --username AWS --password-stdin "$DEPLOY_REGISTRY"
  docker build --platform linux/amd64 -t "$DEPLOY_API_IMAGE" "$DEPLOY_PROJECT_DIR"
  docker build --platform linux/amd64 -t "$DEPLOY_FRONT_IMAGE" "$DEPLOY_PROJECT_DIR/bookstore"
  docker push "$DEPLOY_API_IMAGE"
  docker push "$DEPLOY_FRONT_IMAGE"
else
  for DEPLOY_IMAGE in "$DEPLOY_API_IMAGE" "$DEPLOY_FRONT_IMAGE"; do
    DEPLOY_REPOSITORY="${DEPLOY_IMAGE#*/}"
    DEPLOY_REPOSITORY="${DEPLOY_REPOSITORY%%:*}"
    if ! aws ecr describe-images \
      --repository-name "$DEPLOY_REPOSITORY" \
      --image-ids imageTag="$DEPLOY_IMAGE_TAG" \
      --region "$DEPLOY_AWS_REGION" >/dev/null 2>&1; then
      echo "Imagem não encontrada no ECR: $DEPLOY_IMAGE" >&2
      exit 1
    fi
  done
fi

kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n dev get secret recommendation-secrets >/dev/null 2>&1; then
  DEPLOY_ADMIN_USER_IDS="${DEPLOY_ADMIN_USER_IDS:-}"
  DEPLOY_POSTGRES_PASSWORD="${DEPLOY_POSTGRES_PASSWORD:-}"
  DEPLOY_AUTH_SECRET="${DEPLOY_AUTH_SECRET:-$(openssl rand -hex 32)}"

  if [[ -z "$DEPLOY_ADMIN_USER_IDS" && -t 0 ]]; then
    read -r -p "ID(s) administrativo(s), separados por vírgula: " DEPLOY_ADMIN_USER_IDS
  fi
  if [[ -z "$DEPLOY_POSTGRES_PASSWORD" && -t 0 ]]; then
    read -r -s -p "Senha do PostgreSQL: " DEPLOY_POSTGRES_PASSWORD
    echo
  fi
  if [[ -z "$DEPLOY_ADMIN_USER_IDS" || -z "$DEPLOY_POSTGRES_PASSWORD" ]]; then
    echo "Defina DEPLOY_ADMIN_USER_IDS e DEPLOY_POSTGRES_PASSWORD para criar o Secret." >&2
    exit 1
  fi

  kubectl -n dev create secret generic recommendation-secrets \
    --from-literal=postgres-database=bookstore_db \
    --from-literal=postgres-user=bookstore_app \
    --from-literal=postgres-password="$DEPLOY_POSTGRES_PASSWORD" \
    --from-literal=auth-secret="$DEPLOY_AUTH_SECRET" \
    --from-literal=admin-user-ids="$DEPLOY_ADMIN_USER_IDS"
else
  echo "Secret recommendation-secrets preservado."
fi

# O Ingress depende do AWS Load Balancer Controller.
require_command eksctl
require_command helm
eksctl utils associate-iam-oidc-provider \
  --cluster "$DEPLOY_CLUSTER_NAME" \
  --region "$DEPLOY_AWS_REGION" \
  --approve

# O PostgreSQL utiliza um PVC gp3. O add-on gerenciado recebe somente a
# política necessária para provisionar e excluir os volumes EBS do cluster.
if aws eks describe-addon \
  --cluster-name "$DEPLOY_CLUSTER_NAME" \
  --addon-name aws-ebs-csi-driver \
  --region "$DEPLOY_AWS_REGION" >/dev/null 2>&1; then
  echo "Add-on aws-ebs-csi-driver já instalado; configuração IAM preservada."
else
  eksctl create addon \
    --cluster "$DEPLOY_CLUSTER_NAME" \
    --region "$DEPLOY_AWS_REGION" \
    --name aws-ebs-csi-driver \
    --version latest \
    --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
    --force --wait
fi

DEPLOY_LB_POLICY_NAME="AWSLoadBalancerControllerIAMPolicy"
DEPLOY_LB_POLICY_ARN="arn:aws:iam::${DEPLOY_ACCOUNT_ID}:policy/${DEPLOY_LB_POLICY_NAME}"
if ! aws iam get-policy --policy-arn "$DEPLOY_LB_POLICY_ARN" >/dev/null 2>&1; then
  aws iam create-policy \
    --policy-name "$DEPLOY_LB_POLICY_NAME" \
    --policy-document "file://${DEPLOY_PROJECT_DIR}/k8s/iam_policy.json" \
    --tags \
      Key=recommendation-api:managed,Value=true \
      Key=recommendation-api:cluster,Value="$DEPLOY_CLUSTER_NAME" >/dev/null
fi
aws iam tag-policy \
  --policy-arn "$DEPLOY_LB_POLICY_ARN" \
  --tags \
    Key=recommendation-api:managed,Value=true \
    Key=recommendation-api:cluster,Value="$DEPLOY_CLUSTER_NAME"

eksctl create iamserviceaccount \
  --cluster "$DEPLOY_CLUSTER_NAME" \
  --region "$DEPLOY_AWS_REGION" \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn "$DEPLOY_LB_POLICY_ARN" \
  --tags "recommendation-api:managed=true,recommendation-api:cluster=${DEPLOY_CLUSTER_NAME}" \
  --override-existing-serviceaccounts \
  --approve

helm repo add eks https://aws.github.io/eks-charts --force-update
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName="$DEPLOY_CLUSTER_NAME" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 10m

kubectl apply -k "$DEPLOY_PROJECT_DIR/k8s/app"
kubectl -n dev set image deployment/fastapi-recommender fastapi="$DEPLOY_API_IMAGE"
kubectl -n dev set image deployment/react-frontend frontend="$DEPLOY_FRONT_IMAGE"
kubectl -n dev rollout status statefulset/postgres-db --timeout=10m
kubectl -n dev rollout status deployment/fastapi-recommender --timeout=10m
kubectl -n dev rollout status deployment/react-frontend --timeout=10m

# Reforça a rastreabilidade do volume mesmo se o cluster for removido fora do
# cleanup.sh e o PV deixar de estar disponível para consulta.
DEPLOY_POSTGRES_PV="$(kubectl -n dev get pvc postgres-data-postgres-db-0 \
  -o jsonpath='{.spec.volumeName}')"
DEPLOY_POSTGRES_VOLUME_ID="$(kubectl get pv "$DEPLOY_POSTGRES_PV" \
  -o jsonpath='{.spec.csi.volumeHandle}')"
if [[ "$DEPLOY_POSTGRES_VOLUME_ID" == vol-* ]]; then
  aws ec2 create-tags \
    --region "$DEPLOY_AWS_REGION" \
    --resources "$DEPLOY_POSTGRES_VOLUME_ID" \
    --tags \
      Key=recommendation-api:managed,Value=true \
      Key=recommendation-api:cluster,Value="$DEPLOY_CLUSTER_NAME"
fi

if [[ "$DEPLOY_SKIP_OBSERVABILITY" != true ]]; then
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
  kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
  helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
    -n monitoring \
    -f "$DEPLOY_PROJECT_DIR/k8s/monitoring/custom_kube_prometheus_stack.yml" \
    --wait --timeout 15m
  kubectl wait --for=condition=Established \
    crd/servicemonitors.monitoring.coreos.com \
    crd/prometheusrules.monitoring.coreos.com \
    --timeout=120s
  kubectl apply -k "$DEPLOY_PROJECT_DIR/k8s/monitoring"
fi

DEPLOY_HOSTNAME="$(kubectl -n dev get ingress app-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
echo
echo "Implantação concluída com a tag: $DEPLOY_IMAGE_TAG"
if [[ -n "$DEPLOY_HOSTNAME" ]]; then
  echo "Aplicação: http://${DEPLOY_HOSTNAME}"
else
  echo "O ALB ainda está sendo criado. Consulte: kubectl -n dev get ingress app-ingress -w"
fi
echo "Painel administrativo: /simulacoes"
