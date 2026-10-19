#!/usr/bin/env bash
set -Eeuo pipefail

# Teardown completo do ambiente criado por scripts/deploy_aws.sh.
# O objetivo é remover os recursos faturáveis do projeto, preservando apenas
# um backup local do PostgreSQL e os artefatos Docker locais.

CLEANUP_CLUSTER_NAME="${CLEANUP_CLUSTER_NAME:-observability}"
CLEANUP_AWS_REGION="${CLEANUP_AWS_REGION:-us-east-1}"
CLEANUP_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_WAIT_SECONDS="${CLEANUP_WAIT_SECONDS:-900}"
CLEANUP_PROJECT_TAG_KEY="recommendation-api:cluster"
CLEANUP_ASSUME_YES=false
CLEANUP_SKIP_BACKUP=false
CLEANUP_AUDIT_ONLY=false
CLEANUP_OIDC_PROVIDER_ARN=""
CLEANUP_VPC_ID=""
CLEANUP_AUDIT_FOUND=0
CLEANUP_ERRORS=()
CLEANUP_CAPTURED_VOLUME_IDS=()
CLEANUP_CAPTURED_LOAD_BALANCERS=()
CLEANUP_CAPTURED_TARGET_GROUPS=()
CLEANUP_CAPTURED_EIP_IDS=()
CLEANUP_ECR_REPOSITORIES=(fastapi-recommender react-frontend)

usage() {
  cat <<EOF
Uso: $0 [opções]

Remove o ambiente AWS do projeto: aplicações Kubernetes, ALBs, volumes EBS,
Prometheus/Grafana, cluster EKS e nós, ECR, logs e recursos IAM próprios.
Um backup local do PostgreSQL é criado antes da destruição.

Opções:
  --yes             não solicita a confirmação digitada
  --skip-backup     destrói mesmo sem criar o backup local
  --audit-only      apenas procura recursos remanescentes; não remove nada
  -h, --help        mostra esta ajuda

Variáveis:
  CLEANUP_CLUSTER_NAME   padrão: observability
  CLEANUP_AWS_REGION     padrão: us-east-1
  CLEANUP_WAIT_SECONDS   espera por recursos assíncronos; padrão: 900

ATENÇÃO: a destruição AWS é irreversível. O único dado preservado por padrão é
o dump local criado em backups/. Imagens Docker locais também são preservadas.
EOF
}

for CLEANUP_ARGUMENT in "$@"; do
  case "$CLEANUP_ARGUMENT" in
    --yes) CLEANUP_ASSUME_YES=true ;;
    --skip-backup) CLEANUP_SKIP_BACKUP=true ;;
    --audit-only) CLEANUP_AUDIT_ONLY=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Argumento desconhecido: $CLEANUP_ARGUMENT" >&2; usage; exit 2 ;;
  esac
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Comando obrigatório não encontrado: $1" >&2
    exit 1
  }
}

normalize_aws_list() {
  tr '\t' '\n' | sed -e '/^$/d' -e '/^None$/d' | sort -u
}

add_unique() {
  local -n CLEANUP_TARGET_ARRAY="$1"
  local CLEANUP_VALUE="$2"
  local CLEANUP_EXISTING
  [[ -n "$CLEANUP_VALUE" && "$CLEANUP_VALUE" != "None" ]] || return 0
  for CLEANUP_EXISTING in "${CLEANUP_TARGET_ARRAY[@]:-}"; do
    [[ "$CLEANUP_EXISTING" == "$CLEANUP_VALUE" ]] && return 0
  done
  CLEANUP_TARGET_ARRAY+=("$CLEANUP_VALUE")
}

record_error() {
  CLEANUP_ERRORS+=("$1")
  echo "ERRO: $1" >&2
}

cluster_exists() {
  aws eks describe-cluster \
    --name "$CLEANUP_CLUSTER_NAME" \
    --region "$CLEANUP_AWS_REGION" >/dev/null 2>&1
}

tagged_resource_arns() {
  local CLEANUP_RESOURCE_TYPE="$1"
  local CLEANUP_TAG_KEY
  {
    for CLEANUP_TAG_KEY in "$CLEANUP_PROJECT_TAG_KEY" "elbv2.k8s.aws/cluster"; do
      aws resourcegroupstaggingapi get-resources \
        --region "$CLEANUP_AWS_REGION" \
        --resource-type-filters "$CLEANUP_RESOURCE_TYPE" \
        --tag-filters "Key=${CLEANUP_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
        --query 'ResourceTagMappingList[].ResourceARN' \
        --output text
    done
    aws resourcegroupstaggingapi get-resources \
      --region "$CLEANUP_AWS_REGION" \
      --resource-type-filters "$CLEANUP_RESOURCE_TYPE" \
      --tag-filters "Key=kubernetes.io/cluster/${CLEANUP_CLUSTER_NAME},Values=owned,shared" \
      --query 'ResourceTagMappingList[].ResourceARN' \
      --output text
  } | normalize_aws_list
}

cluster_load_balancers() {
  local CLEANUP_ARN
  local CLEANUP_VPC
  {
    tagged_resource_arns elasticloadbalancing:loadbalancer
    while IFS= read -r CLEANUP_VPC; do
      [[ -n "$CLEANUP_VPC" ]] || continue
      aws elbv2 describe-load-balancers \
        --region "$CLEANUP_AWS_REGION" \
        --query "LoadBalancers[?VpcId=='${CLEANUP_VPC}'].LoadBalancerArn" \
        --output text
    done < <(cluster_vpc_ids)
    for CLEANUP_ARN in "${CLEANUP_CAPTURED_LOAD_BALANCERS[@]:-}"; do
      if [[ -n "$CLEANUP_ARN" ]] && aws elbv2 describe-load-balancers \
        --region "$CLEANUP_AWS_REGION" --load-balancer-arns "$CLEANUP_ARN" \
        >/dev/null 2>&1; then
        echo "$CLEANUP_ARN"
      fi
    done
  } | normalize_aws_list
}

cluster_target_groups() {
  local CLEANUP_ARN
  local CLEANUP_VPC
  {
    tagged_resource_arns elasticloadbalancing:targetgroup
    while IFS= read -r CLEANUP_VPC; do
      [[ -n "$CLEANUP_VPC" ]] || continue
      aws elbv2 describe-target-groups \
        --region "$CLEANUP_AWS_REGION" \
        --query "TargetGroups[?VpcId=='${CLEANUP_VPC}'].TargetGroupArn" \
        --output text
    done < <(cluster_vpc_ids)
    for CLEANUP_ARN in "${CLEANUP_CAPTURED_TARGET_GROUPS[@]:-}"; do
      if [[ -n "$CLEANUP_ARN" ]] && aws elbv2 describe-target-groups \
        --region "$CLEANUP_AWS_REGION" --target-group-arns "$CLEANUP_ARN" \
        >/dev/null 2>&1; then
        echo "$CLEANUP_ARN"
      fi
    done
  } | normalize_aws_list
}

cluster_stack_names() {
  aws cloudformation describe-stacks \
    --region "$CLEANUP_AWS_REGION" \
    --query "Stacks[?starts_with(StackName, 'eksctl-${CLEANUP_CLUSTER_NAME}-')].StackName" \
    --output text | normalize_aws_list
}

cluster_instance_ids() {
  local CLEANUP_VPC
  {
    aws ec2 describe-instances \
      --region "$CLEANUP_AWS_REGION" \
      --filters \
        "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
        'Name=instance-state-name,Values=pending,running,stopping,stopped' \
      --query 'Reservations[].Instances[].InstanceId' --output text
    while IFS= read -r CLEANUP_VPC; do
      [[ -n "$CLEANUP_VPC" ]] || continue
      aws ec2 describe-instances \
        --region "$CLEANUP_AWS_REGION" \
        --filters \
          "Name=vpc-id,Values=${CLEANUP_VPC}" \
          'Name=instance-state-name,Values=pending,running,stopping,stopped' \
        --query 'Reservations[].Instances[].InstanceId' --output text
    done < <(cluster_vpc_ids)
    aws ec2 describe-instances \
      --region "$CLEANUP_AWS_REGION" \
      --filters \
        "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
        'Name=instance-state-name,Values=pending,running,stopping,stopped' \
      --query 'Reservations[].Instances[].InstanceId' --output text
  } | normalize_aws_list
}

cluster_volume_ids() {
  local CLEANUP_VOLUME_ID
  {
    aws ec2 describe-volumes \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Volumes[].VolumeId' --output text
    aws ec2 describe-volumes \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Volumes[].VolumeId' --output text
    for CLEANUP_VOLUME_ID in "${CLEANUP_CAPTURED_VOLUME_IDS[@]:-}"; do
      if aws ec2 describe-volumes \
        --region "$CLEANUP_AWS_REGION" \
        --volume-ids "$CLEANUP_VOLUME_ID" >/dev/null 2>&1; then
        echo "$CLEANUP_VOLUME_ID"
      fi
    done
  } | normalize_aws_list
}

cluster_snapshot_ids() {
  {
    aws ec2 describe-snapshots \
      --region "$CLEANUP_AWS_REGION" --owner-ids self \
      --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Snapshots[].SnapshotId' --output text
    aws ec2 describe-snapshots \
      --region "$CLEANUP_AWS_REGION" --owner-ids self \
      --filters "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Snapshots[].SnapshotId' --output text
  } | normalize_aws_list
}

cluster_nat_gateway_ids() {
  local CLEANUP_VPC
  {
    aws ec2 describe-nat-gateways \
      --region "$CLEANUP_AWS_REGION" \
      --filter "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text
    aws ec2 describe-nat-gateways \
      --region "$CLEANUP_AWS_REGION" \
      --filter "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text
    while IFS= read -r CLEANUP_VPC; do
      [[ -n "$CLEANUP_VPC" ]] || continue
      aws ec2 describe-nat-gateways \
        --region "$CLEANUP_AWS_REGION" \
        --filter "Name=vpc-id,Values=${CLEANUP_VPC}" \
        --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text
    done < <(cluster_vpc_ids)
  } | normalize_aws_list
}

cluster_eip_ids() {
  local CLEANUP_EIP_ID
  local CLEANUP_NAT_ID
  {
    aws ec2 describe-addresses \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Addresses[].AllocationId' --output text
    aws ec2 describe-addresses \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Addresses[].AllocationId' --output text
    while IFS= read -r CLEANUP_NAT_ID; do
      [[ -n "$CLEANUP_NAT_ID" ]] || continue
      aws ec2 describe-nat-gateways \
        --region "$CLEANUP_AWS_REGION" \
        --nat-gateway-ids "$CLEANUP_NAT_ID" \
        --query 'NatGateways[].NatGatewayAddresses[].AllocationId' --output text
    done < <(cluster_nat_gateway_ids)
    for CLEANUP_EIP_ID in "${CLEANUP_CAPTURED_EIP_IDS[@]:-}"; do
      if [[ -n "$CLEANUP_EIP_ID" ]] && aws ec2 describe-addresses \
        --region "$CLEANUP_AWS_REGION" --allocation-ids "$CLEANUP_EIP_ID" \
        >/dev/null 2>&1; then
        echo "$CLEANUP_EIP_ID"
      fi
    done
  } | normalize_aws_list
}

cluster_vpc_ids() {
  {
    aws ec2 describe-vpcs \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Vpcs[].VpcId' --output text
    aws ec2 describe-vpcs \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=tag:${CLEANUP_PROJECT_TAG_KEY},Values=${CLEANUP_CLUSTER_NAME}" \
      --query 'Vpcs[].VpcId' --output text
    if [[ -n "$CLEANUP_VPC_ID" ]] && aws ec2 describe-vpcs \
      --region "$CLEANUP_AWS_REGION" --vpc-ids "$CLEANUP_VPC_ID" >/dev/null 2>&1; then
      echo "$CLEANUP_VPC_ID"
    fi
  } | normalize_aws_list
}

cluster_eks_security_group_ids() {
  aws ec2 describe-security-groups \
    --region "$CLEANUP_AWS_REGION" \
    --filters "Name=tag:aws:eks:cluster-name,Values=${CLEANUP_CLUSTER_NAME}" \
    --query 'SecurityGroups[].GroupId' --output text | normalize_aws_list
}

cluster_vpc_endpoint_ids() {
  local CLEANUP_VPC
  while IFS= read -r CLEANUP_VPC; do
    [[ -n "$CLEANUP_VPC" ]] || continue
    aws ec2 describe-vpc-endpoints \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'VpcEndpoints[].VpcEndpointId' --output text
  done < <(cluster_vpc_ids) | normalize_aws_list
}

cluster_network_interface_ids() {
  local CLEANUP_VPC
  while IFS= read -r CLEANUP_VPC; do
    [[ -n "$CLEANUP_VPC" ]] || continue
    aws ec2 describe-network-interfaces \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'NetworkInterfaces[].NetworkInterfaceId' --output text
  done < <(cluster_vpc_ids) | normalize_aws_list
}

cluster_log_groups() {
  {
    aws logs describe-log-groups \
      --region "$CLEANUP_AWS_REGION" \
      --log-group-name-prefix "/aws/eks/${CLEANUP_CLUSTER_NAME}/" \
      --query 'logGroups[].logGroupName' --output text
    aws logs describe-log-groups \
      --region "$CLEANUP_AWS_REGION" \
      --log-group-name-prefix "/aws/containerinsights/${CLEANUP_CLUSTER_NAME}/" \
      --query 'logGroups[].logGroupName' --output text
  } | normalize_aws_list
}

audit_item() {
  local CLEANUP_KIND="$1"
  local CLEANUP_ITEMS="$2"
  [[ -n "$CLEANUP_ITEMS" ]] || return 0
  CLEANUP_AUDIT_FOUND=$((CLEANUP_AUDIT_FOUND + 1))
  echo "  - ${CLEANUP_KIND}: ${CLEANUP_ITEMS//$'\n'/, }"
}

audit_resources() {
  local CLEANUP_REPOSITORY
  local CLEANUP_POLICY_ARN
  CLEANUP_AUDIT_FOUND=0
  echo "Auditoria AWS do projeto (${CLEANUP_AWS_REGION}):"

  if cluster_exists; then
    audit_item "cluster EKS" "$CLEANUP_CLUSTER_NAME"
  fi
  audit_item "stacks CloudFormation" "$(cluster_stack_names)"
  audit_item "load balancers" "$(cluster_load_balancers)"
  audit_item "target groups" "$(cluster_target_groups)"
  audit_item "instâncias EC2" "$(cluster_instance_ids)"
  audit_item "volumes EBS" "$(cluster_volume_ids)"
  audit_item "snapshots EBS" "$(cluster_snapshot_ids)"
  audit_item "NAT gateways" "$(cluster_nat_gateway_ids)"
  audit_item "Elastic IPs" "$(cluster_eip_ids)"
  audit_item "VPC endpoints" "$(cluster_vpc_endpoint_ids)"
  audit_item "interfaces de rede" "$(cluster_network_interface_ids)"
  audit_item "security groups gerenciados pelo EKS" "$(cluster_eks_security_group_ids)"
  audit_item "VPCs" "$(cluster_vpc_ids)"
  audit_item "log groups" "$(cluster_log_groups)"

  for CLEANUP_REPOSITORY in "${CLEANUP_ECR_REPOSITORIES[@]}"; do
    if aws ecr describe-repositories \
      --region "$CLEANUP_AWS_REGION" \
      --repository-names "$CLEANUP_REPOSITORY" >/dev/null 2>&1; then
      audit_item "repositório ECR" "$CLEANUP_REPOSITORY"
    fi
  done

  CLEANUP_POLICY_ARN="arn:aws:iam::${CLEANUP_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy"
  if aws iam get-policy --policy-arn "$CLEANUP_POLICY_ARN" >/dev/null 2>&1; then
    audit_item "política IAM" "$CLEANUP_POLICY_ARN"
  fi
  if [[ -n "$CLEANUP_OIDC_PROVIDER_ARN" ]] && aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "$CLEANUP_OIDC_PROVIDER_ARN" >/dev/null 2>&1; then
    audit_item "provedor OIDC" "$CLEANUP_OIDC_PROVIDER_ARN"
  fi

  if [[ "$CLEANUP_AUDIT_FOUND" -eq 0 ]]; then
    echo "  Nenhum recurso do projeto foi encontrado."
  fi
}

capture_cluster_metadata() {
  local CLEANUP_ISSUER
  local CLEANUP_HANDLE
  local CLEANUP_VALUE

  CLEANUP_VPC_ID="$(aws eks describe-cluster \
    --name "$CLEANUP_CLUSTER_NAME" --region "$CLEANUP_AWS_REGION" \
    --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
  CLEANUP_ISSUER="$(aws eks describe-cluster \
    --name "$CLEANUP_CLUSTER_NAME" --region "$CLEANUP_AWS_REGION" \
    --query 'cluster.identity.oidc.issuer' --output text)"
  if [[ -n "$CLEANUP_ISSUER" && "$CLEANUP_ISSUER" != "None" ]]; then
    CLEANUP_OIDC_PROVIDER_ARN="arn:aws:iam::${CLEANUP_ACCOUNT_ID}:oidc-provider/${CLEANUP_ISSUER#https://}"
  fi

  while IFS= read -r CLEANUP_HANDLE; do
    CLEANUP_VALUE="${CLEANUP_HANDLE##*/}"
    [[ "$CLEANUP_VALUE" == vol-* ]] && add_unique CLEANUP_CAPTURED_VOLUME_IDS "$CLEANUP_VALUE"
  done < <(
    kubectl get pv -o jsonpath='{range .items[*]}{.spec.csi.volumeHandle}{"\n"}{.spec.awsElasticBlockStore.volumeID}{"\n"}{end}' 2>/dev/null \
      | sed '/^$/d'
  )

  while IFS= read -r CLEANUP_VALUE; do
    add_unique CLEANUP_CAPTURED_LOAD_BALANCERS "$CLEANUP_VALUE"
  done < <(tagged_resource_arns elasticloadbalancing:loadbalancer)
  while IFS= read -r CLEANUP_VALUE; do
    add_unique CLEANUP_CAPTURED_TARGET_GROUPS "$CLEANUP_VALUE"
  done < <(tagged_resource_arns elasticloadbalancing:targetgroup)

  while IFS= read -r CLEANUP_VALUE; do
    add_unique CLEANUP_CAPTURED_EIP_IDS "$CLEANUP_VALUE"
  done < <(
    aws ec2 describe-nat-gateways \
      --region "$CLEANUP_AWS_REGION" \
      --filter "Name=vpc-id,Values=${CLEANUP_VPC_ID}" \
      --query 'NatGateways[].NatGatewayAddresses[].AllocationId' --output text \
      | normalize_aws_list
  )
}

capture_residual_stack_metadata() {
  local CLEANUP_CLUSTER_STACK="eksctl-${CLEANUP_CLUSTER_NAME}-cluster"
  local CLEANUP_ENDPOINT
  local CLEANUP_ISSUER_ID

  if ! aws cloudformation describe-stacks \
    --region "$CLEANUP_AWS_REGION" \
    --stack-name "$CLEANUP_CLUSTER_STACK" >/dev/null 2>&1; then
    return 0
  fi

  CLEANUP_VPC_ID="$(aws cloudformation describe-stacks \
    --region "$CLEANUP_AWS_REGION" \
    --stack-name "$CLEANUP_CLUSTER_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='VPC'].OutputValue | [0]" \
    --output text)"
  [[ "$CLEANUP_VPC_ID" != "None" ]] || CLEANUP_VPC_ID=""

  # Quando o control plane já foi excluído fora do eksctl, o endpoint exportado
  # pela stack ainda contém o ID usado no provedor OIDC criado para o cluster.
  CLEANUP_ENDPOINT="$(aws cloudformation describe-stacks \
    --region "$CLEANUP_AWS_REGION" \
    --stack-name "$CLEANUP_CLUSTER_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='Endpoint'].OutputValue | [0]" \
    --output text)"
  CLEANUP_ENDPOINT="${CLEANUP_ENDPOINT#https://}"
  CLEANUP_ISSUER_ID="${CLEANUP_ENDPOINT%%.*}"
  if [[ -n "$CLEANUP_ISSUER_ID" && "$CLEANUP_ISSUER_ID" != "None" ]]; then
    CLEANUP_OIDC_PROVIDER_ARN="arn:aws:iam::${CLEANUP_ACCOUNT_ID}:oidc-provider/oidc.eks.${CLEANUP_AWS_REGION}.amazonaws.com/id/${CLEANUP_ISSUER_ID}"
  fi
}

backup_database() {
  local CLEANUP_POSTGRES_POD
  [[ "$CLEANUP_SKIP_BACKUP" == false ]] || {
    echo "Backup ignorado por solicitação explícita."
    return 0
  }
  CLEANUP_POSTGRES_POD="$(kubectl get pod -n dev -l app=postgres-db \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [[ -z "$CLEANUP_POSTGRES_POD" ]]; then
    echo "PostgreSQL não está disponível para backup." >&2
    echo "Corrija o pod ou execute novamente com --skip-backup se aceita perder os dados." >&2
    exit 1
  fi
  echo "Criando backup local do PostgreSQL..."
  "${CLEANUP_PROJECT_DIR}/scripts/backup_database.sh"
}

delete_kubernetes_frontends() {
  local CLEANUP_NAMESPACE
  local CLEANUP_NAME
  local CLEANUP_TYPE
  local CLEANUP_DEADLINE

  echo "Removendo Ingresses antes do cluster para liberar os ALBs..."
  while IFS=$'\t' read -r CLEANUP_NAMESPACE CLEANUP_NAME; do
    [[ -n "$CLEANUP_NAMESPACE" && -n "$CLEANUP_NAME" ]] || continue
    kubectl delete ingress "$CLEANUP_NAME" -n "$CLEANUP_NAMESPACE" \
      --ignore-not-found --wait=false || record_error "Falha ao remover Ingress ${CLEANUP_NAMESPACE}/${CLEANUP_NAME}"
  done < <(kubectl get ingress -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

  echo "Removendo Services do tipo LoadBalancer..."
  while IFS=$'\t' read -r CLEANUP_NAMESPACE CLEANUP_NAME CLEANUP_TYPE; do
    [[ "$CLEANUP_TYPE" == "LoadBalancer" ]] || continue
    kubectl delete service "$CLEANUP_NAME" -n "$CLEANUP_NAMESPACE" \
      --ignore-not-found --wait=false || record_error "Falha ao remover Service ${CLEANUP_NAMESPACE}/${CLEANUP_NAME}"
  done < <(kubectl get service -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.type}{"\n"}{end}' 2>/dev/null || true)

  kubectl wait --for=delete ingress --all --all-namespaces \
    --timeout="${CLEANUP_WAIT_SECONDS}s" >/dev/null 2>&1 || true

  CLEANUP_DEADLINE=$((SECONDS + CLEANUP_WAIT_SECONDS))
  while [[ -n "$(cluster_load_balancers)" && "$SECONDS" -lt "$CLEANUP_DEADLINE" ]]; do
    sleep 10
  done
}

force_delete_load_balancers() {
  local CLEANUP_ARN
  while IFS= read -r CLEANUP_ARN; do
    [[ -n "$CLEANUP_ARN" ]] || continue
    echo "Removendo load balancer remanescente: $CLEANUP_ARN"
    if aws elbv2 delete-load-balancer \
      --region "$CLEANUP_AWS_REGION" --load-balancer-arn "$CLEANUP_ARN"; then
      aws elbv2 wait load-balancers-deleted \
        --region "$CLEANUP_AWS_REGION" --load-balancer-arns "$CLEANUP_ARN" \
        || record_error "Timeout removendo load balancer $CLEANUP_ARN"
    else
      record_error "Falha ao remover load balancer $CLEANUP_ARN"
    fi
  done < <(cluster_load_balancers)

  while IFS= read -r CLEANUP_ARN; do
    [[ -n "$CLEANUP_ARN" ]] || continue
    echo "Removendo target group remanescente: $CLEANUP_ARN"
    aws elbv2 delete-target-group \
      --region "$CLEANUP_AWS_REGION" --target-group-arn "$CLEANUP_ARN" \
      || record_error "Falha ao remover target group $CLEANUP_ARN"
  done < <(cluster_target_groups)
}

uninstall_kubernetes_stack() {
  local CLEANUP_RELEASE_NAMESPACE
  local CLEANUP_RELEASE
  local CLEANUP_NAMESPACE

  kubectl delete -k "${CLEANUP_PROJECT_DIR}/k8s/monitoring" \
    --ignore-not-found=true --wait=false \
    || record_error "Falha removendo manifests de monitoramento"
  kubectl delete -k "${CLEANUP_PROJECT_DIR}/k8s/app" \
    --ignore-not-found=true --wait=false \
    || record_error "Falha removendo manifests da aplicação"

  for CLEANUP_RELEASE_NAMESPACE in \
    "monitoring:monitoring" \
    "fluent-bit:logging" \
    "kibana:logging" \
    "elasticsearch:logging"; do
    CLEANUP_RELEASE="${CLEANUP_RELEASE_NAMESPACE%%:*}"
    CLEANUP_NAMESPACE="${CLEANUP_RELEASE_NAMESPACE##*:}"
    if helm status "$CLEANUP_RELEASE" -n "$CLEANUP_NAMESPACE" >/dev/null 2>&1; then
      helm uninstall "$CLEANUP_RELEASE" -n "$CLEANUP_NAMESPACE" \
        || record_error "Falha removendo Helm release ${CLEANUP_RELEASE}"
    fi
  done

  for CLEANUP_NAMESPACE in dev monitoring logging; do
    kubectl delete namespace "$CLEANUP_NAMESPACE" \
      --ignore-not-found=true --wait=true --timeout="${CLEANUP_WAIT_SECONDS}s" \
      || record_error "Falha removendo namespace ${CLEANUP_NAMESPACE}"
  done

  if helm status aws-load-balancer-controller -n kube-system >/dev/null 2>&1; then
    helm uninstall aws-load-balancer-controller -n kube-system \
      || record_error "Falha removendo AWS Load Balancer Controller"
  fi
}

delete_cluster() {
  echo "Removendo nós, stacks e control plane do EKS..."
  if ! eksctl delete cluster \
    --name "$CLEANUP_CLUSTER_NAME" \
    --region "$CLEANUP_AWS_REGION" \
    --wait --force --timeout 40m; then
    record_error "eksctl não conseguiu concluir a exclusão do cluster"
  fi
}

delete_residual_cloudformation_stacks() {
  local CLEANUP_MAIN_STACK="eksctl-${CLEANUP_CLUSTER_NAME}-cluster"
  local CLEANUP_STACK
  local CLEANUP_STACKS=()
  mapfile -t CLEANUP_STACKS < <(cluster_stack_names)

  # Addons e nodegroups dependem da stack principal. A stack do cluster deve
  # ser sempre a última, inclusive quando o control plane já foi apagado fora
  # do eksctl e restaram stacks CREATE_COMPLETE.
  for CLEANUP_STACK in "${CLEANUP_STACKS[@]}"; do
    [[ -n "$CLEANUP_STACK" && "$CLEANUP_STACK" != "$CLEANUP_MAIN_STACK" ]] || continue
    delete_cloudformation_stack "$CLEANUP_STACK"
  done

  # O EKS cria um security group fora da stack principal. Quando o control
  # plane já desapareceu, esse grupo pode sobreviver alguns minutos e impedir
  # a exclusão da VPC pertencente ao CloudFormation.
  delete_orphan_eks_security_groups

  for CLEANUP_STACK in "${CLEANUP_STACKS[@]}"; do
    [[ "$CLEANUP_STACK" == "$CLEANUP_MAIN_STACK" ]] || continue
    delete_cloudformation_stack "$CLEANUP_STACK"
  done
}

delete_cloudformation_stack() {
  local CLEANUP_STACK="$1"
  local CLEANUP_STATUS
  local CLEANUP_DEADLINE=$((SECONDS + CLEANUP_WAIT_SECONDS))

  CLEANUP_STATUS="$(aws cloudformation describe-stacks \
    --region "$CLEANUP_AWS_REGION" --stack-name "$CLEANUP_STACK" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
  [[ -n "$CLEANUP_STATUS" ]] || return 0

  if [[ "$CLEANUP_STATUS" == "DELETE_IN_PROGRESS" ]]; then
    echo "A exclusão da stack já está em andamento: $CLEANUP_STACK"
  else
    echo "Removendo stack CloudFormation remanescente: $CLEANUP_STACK"
    if ! aws cloudformation delete-stack \
      --region "$CLEANUP_AWS_REGION" --stack-name "$CLEANUP_STACK"; then
      record_error "Falha solicitando exclusão da stack $CLEANUP_STACK"
      return 0
    fi
  fi

  while true; do
    CLEANUP_STATUS="$(aws cloudformation describe-stacks \
      --region "$CLEANUP_AWS_REGION" --stack-name "$CLEANUP_STACK" \
      --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
    if [[ -z "$CLEANUP_STATUS" ]]; then
      echo "Stack removida: $CLEANUP_STACK"
      return 0
    fi
    if [[ "$CLEANUP_STATUS" == "DELETE_FAILED" ]]; then
      record_error "Stack entrou em DELETE_FAILED: $CLEANUP_STACK"
      return 0
    fi
    if [[ "$SECONDS" -ge "$CLEANUP_DEADLINE" ]]; then
      record_error "Tempo limite aguardando a stack $CLEANUP_STACK (estado: $CLEANUP_STATUS)"
      return 0
    fi
    echo "Aguardando stack $CLEANUP_STACK (estado: $CLEANUP_STATUS)..."
    sleep 15
  done
}

delete_orphan_eks_security_groups() {
  local CLEANUP_GROUP_ID
  local CLEANUP_INTERFACES

  cluster_exists && return 0
  while IFS= read -r CLEANUP_GROUP_ID; do
    [[ -n "$CLEANUP_GROUP_ID" ]] || continue
    CLEANUP_INTERFACES="$(aws ec2 describe-network-interfaces \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=group-id,Values=${CLEANUP_GROUP_ID}" \
      --query 'NetworkInterfaces[].NetworkInterfaceId' --output text \
      | normalize_aws_list)"
    if [[ -n "$CLEANUP_INTERFACES" ]]; then
      record_error "Security group $CLEANUP_GROUP_ID ainda usado por: ${CLEANUP_INTERFACES//$'\n'/, }"
      continue
    fi
    echo "Removendo security group órfão criado pelo EKS: $CLEANUP_GROUP_ID"
    aws ec2 delete-security-group \
      --region "$CLEANUP_AWS_REGION" --group-id "$CLEANUP_GROUP_ID" \
      || record_error "Falha removendo security group órfão $CLEANUP_GROUP_ID"
  done < <(cluster_eks_security_group_ids)
}

delete_orphan_instances() {
  local CLEANUP_IDS=()
  mapfile -t CLEANUP_IDS < <(cluster_instance_ids)
  [[ "${#CLEANUP_IDS[@]}" -gt 0 ]] || return 0
  echo "Encerrando instâncias EC2 remanescentes: ${CLEANUP_IDS[*]}"
  aws ec2 terminate-instances \
    --region "$CLEANUP_AWS_REGION" --instance-ids "${CLEANUP_IDS[@]}" >/dev/null \
    || record_error "Falha encerrando instâncias EC2"
  aws ec2 wait instance-terminated \
    --region "$CLEANUP_AWS_REGION" --instance-ids "${CLEANUP_IDS[@]}" \
    || record_error "Timeout aguardando instâncias EC2"
}

delete_orphan_volumes_and_snapshots() {
  local CLEANUP_VOLUME_ID
  local CLEANUP_SNAPSHOT_ID
  local CLEANUP_STATE
  local CLEANUP_DEADLINE=$((SECONDS + CLEANUP_WAIT_SECONDS))

  while IFS= read -r CLEANUP_VOLUME_ID; do
    [[ -n "$CLEANUP_VOLUME_ID" ]] || continue
    CLEANUP_STATE="$(aws ec2 describe-volumes \
      --region "$CLEANUP_AWS_REGION" --volume-ids "$CLEANUP_VOLUME_ID" \
      --query 'Volumes[0].State' --output text 2>/dev/null || true)"
    while [[ "$CLEANUP_STATE" == "in-use" && "$SECONDS" -lt "$CLEANUP_DEADLINE" ]]; do
      sleep 10
      CLEANUP_STATE="$(aws ec2 describe-volumes \
        --region "$CLEANUP_AWS_REGION" --volume-ids "$CLEANUP_VOLUME_ID" \
        --query 'Volumes[0].State' --output text 2>/dev/null || true)"
    done
    if [[ "$CLEANUP_STATE" == "available" ]]; then
      echo "Removendo volume EBS remanescente: $CLEANUP_VOLUME_ID"
      aws ec2 delete-volume \
        --region "$CLEANUP_AWS_REGION" --volume-id "$CLEANUP_VOLUME_ID" \
        || record_error "Falha removendo volume $CLEANUP_VOLUME_ID"
    elif [[ -n "$CLEANUP_STATE" && "$CLEANUP_STATE" != "None" ]]; then
      record_error "Volume ainda está em uso: $CLEANUP_VOLUME_ID ($CLEANUP_STATE)"
    fi
  done < <(cluster_volume_ids)

  while IFS= read -r CLEANUP_SNAPSHOT_ID; do
    [[ -n "$CLEANUP_SNAPSHOT_ID" ]] || continue
    echo "Removendo snapshot EBS: $CLEANUP_SNAPSHOT_ID"
    aws ec2 delete-snapshot \
      --region "$CLEANUP_AWS_REGION" --snapshot-id "$CLEANUP_SNAPSHOT_ID" \
      || record_error "Falha removendo snapshot $CLEANUP_SNAPSHOT_ID"
  done < <(cluster_snapshot_ids)
}

delete_orphan_network_costs() {
  local CLEANUP_NAT_ID
  local CLEANUP_EIP_ID
  local CLEANUP_STATE

  while IFS= read -r CLEANUP_NAT_ID; do
    [[ -n "$CLEANUP_NAT_ID" ]] || continue
    echo "Removendo NAT gateway remanescente: $CLEANUP_NAT_ID"
    aws ec2 delete-nat-gateway \
      --region "$CLEANUP_AWS_REGION" --nat-gateway-id "$CLEANUP_NAT_ID" >/dev/null \
      || record_error "Falha removendo NAT gateway $CLEANUP_NAT_ID"
    aws ec2 wait nat-gateway-deleted \
      --region "$CLEANUP_AWS_REGION" --nat-gateway-ids "$CLEANUP_NAT_ID" \
      || record_error "Timeout removendo NAT gateway $CLEANUP_NAT_ID"
  done < <(cluster_nat_gateway_ids)

  while IFS= read -r CLEANUP_EIP_ID; do
    [[ -n "$CLEANUP_EIP_ID" ]] || continue
    CLEANUP_STATE="$(aws ec2 describe-addresses \
      --region "$CLEANUP_AWS_REGION" --allocation-ids "$CLEANUP_EIP_ID" \
      --query 'Addresses[0].AssociationId' --output text 2>/dev/null || true)"
    if [[ -z "$CLEANUP_STATE" || "$CLEANUP_STATE" == "None" ]]; then
      echo "Liberando Elastic IP: $CLEANUP_EIP_ID"
      aws ec2 release-address \
        --region "$CLEANUP_AWS_REGION" --allocation-id "$CLEANUP_EIP_ID" \
        || record_error "Falha liberando Elastic IP $CLEANUP_EIP_ID"
    else
      record_error "Elastic IP ainda está associado: $CLEANUP_EIP_ID"
    fi
  done < <(cluster_eip_ids)
}

delete_orphan_vpcs() {
  local CLEANUP_ENDPOINT_IDS=()
  local CLEANUP_ENI_ID
  local CLEANUP_ENI_STATE
  local CLEANUP_VPC
  local CLEANUP_ID
  local CLEANUP_IS_MAIN
  local CLEANUP_IS_DEFAULT
  local CLEANUP_DEADLINE

  mapfile -t CLEANUP_ENDPOINT_IDS < <(cluster_vpc_endpoint_ids)
  if [[ "${#CLEANUP_ENDPOINT_IDS[@]}" -gt 0 ]]; then
    echo "Removendo VPC endpoints: ${CLEANUP_ENDPOINT_IDS[*]}"
    aws ec2 delete-vpc-endpoints \
      --region "$CLEANUP_AWS_REGION" \
      --vpc-endpoint-ids "${CLEANUP_ENDPOINT_IDS[@]}" >/dev/null \
      || record_error "Falha removendo VPC endpoints"
  fi

  CLEANUP_DEADLINE=$((SECONDS + CLEANUP_WAIT_SECONDS))
  while [[ -n "$(cluster_vpc_endpoint_ids)" && "$SECONDS" -lt "$CLEANUP_DEADLINE" ]]; do
    sleep 10
  done

  while IFS= read -r CLEANUP_ENI_ID; do
    [[ -n "$CLEANUP_ENI_ID" ]] || continue
    CLEANUP_ENI_STATE="$(aws ec2 describe-network-interfaces \
      --region "$CLEANUP_AWS_REGION" --network-interface-ids "$CLEANUP_ENI_ID" \
      --query 'NetworkInterfaces[0].Status' --output text 2>/dev/null || true)"
    if [[ "$CLEANUP_ENI_STATE" == "available" ]]; then
      echo "Removendo interface de rede órfã: $CLEANUP_ENI_ID"
      aws ec2 delete-network-interface \
        --region "$CLEANUP_AWS_REGION" --network-interface-id "$CLEANUP_ENI_ID" \
        || record_error "Falha removendo interface $CLEANUP_ENI_ID"
    elif [[ -n "$CLEANUP_ENI_STATE" && "$CLEANUP_ENI_STATE" != "None" ]]; then
      record_error "Interface de rede ainda está em uso: $CLEANUP_ENI_ID"
    fi
  done < <(cluster_network_interface_ids)

  while IFS= read -r CLEANUP_VPC; do
    [[ -n "$CLEANUP_VPC" ]] || continue
    echo "Limpando dependências da VPC órfã: $CLEANUP_VPC"

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      aws ec2 detach-internet-gateway \
        --region "$CLEANUP_AWS_REGION" \
        --internet-gateway-id "$CLEANUP_ID" --vpc-id "$CLEANUP_VPC" \
        || record_error "Falha desanexando Internet Gateway $CLEANUP_ID"
      aws ec2 delete-internet-gateway \
        --region "$CLEANUP_AWS_REGION" --internet-gateway-id "$CLEANUP_ID" \
        || record_error "Falha removendo Internet Gateway $CLEANUP_ID"
    done < <(aws ec2 describe-internet-gateways \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=attachment.vpc-id,Values=${CLEANUP_VPC}" \
      --query 'InternetGateways[].InternetGatewayId' --output text | normalize_aws_list)

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      aws ec2 delete-egress-only-internet-gateway \
        --region "$CLEANUP_AWS_REGION" --egress-only-internet-gateway-id "$CLEANUP_ID" >/dev/null \
        || record_error "Falha removendo Egress-only Gateway $CLEANUP_ID"
    done < <(aws ec2 describe-egress-only-internet-gateways \
      --region "$CLEANUP_AWS_REGION" \
      --query "EgressOnlyInternetGateways[?Attachments[?VpcId=='${CLEANUP_VPC}']].EgressOnlyInternetGatewayId" \
      --output text | normalize_aws_list)

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      aws ec2 delete-subnet --region "$CLEANUP_AWS_REGION" --subnet-id "$CLEANUP_ID" \
        || record_error "Falha removendo subnet $CLEANUP_ID"
    done < <(aws ec2 describe-subnets \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'Subnets[].SubnetId' --output text | normalize_aws_list)

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      CLEANUP_IS_MAIN="$(aws ec2 describe-route-tables \
        --region "$CLEANUP_AWS_REGION" --route-table-ids "$CLEANUP_ID" \
        --query 'length(RouteTables[0].Associations[?Main==`true`])' --output text)"
      if [[ "$CLEANUP_IS_MAIN" == "0" ]]; then
        aws ec2 delete-route-table \
          --region "$CLEANUP_AWS_REGION" --route-table-id "$CLEANUP_ID" \
          || record_error "Falha removendo route table $CLEANUP_ID"
      fi
    done < <(aws ec2 describe-route-tables \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'RouteTables[].RouteTableId' --output text | normalize_aws_list)

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      CLEANUP_IS_DEFAULT="$(aws ec2 describe-network-acls \
        --region "$CLEANUP_AWS_REGION" --network-acl-ids "$CLEANUP_ID" \
        --query 'NetworkAcls[0].IsDefault' --output text)"
      if [[ "$CLEANUP_IS_DEFAULT" == "False" || "$CLEANUP_IS_DEFAULT" == "false" ]]; then
        aws ec2 delete-network-acl \
          --region "$CLEANUP_AWS_REGION" --network-acl-id "$CLEANUP_ID" \
          || record_error "Falha removendo network ACL $CLEANUP_ID"
      fi
    done < <(aws ec2 describe-network-acls \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'NetworkAcls[].NetworkAclId' --output text | normalize_aws_list)

    while IFS= read -r CLEANUP_ID; do
      [[ -n "$CLEANUP_ID" ]] || continue
      aws ec2 delete-security-group \
        --region "$CLEANUP_AWS_REGION" --group-id "$CLEANUP_ID" \
        || record_error "Falha removendo security group $CLEANUP_ID"
    done < <(aws ec2 describe-security-groups \
      --region "$CLEANUP_AWS_REGION" \
      --filters "Name=vpc-id,Values=${CLEANUP_VPC}" \
      --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text | normalize_aws_list)

    aws ec2 delete-vpc --region "$CLEANUP_AWS_REGION" --vpc-id "$CLEANUP_VPC" \
      || record_error "Falha removendo VPC $CLEANUP_VPC"
  done < <(cluster_vpc_ids)
}

delete_ecr_repositories() {
  local CLEANUP_REPOSITORY
  for CLEANUP_REPOSITORY in "${CLEANUP_ECR_REPOSITORIES[@]}"; do
    if aws ecr describe-repositories \
      --region "$CLEANUP_AWS_REGION" \
      --repository-names "$CLEANUP_REPOSITORY" >/dev/null 2>&1; then
      echo "Removendo ECR e todas as imagens: $CLEANUP_REPOSITORY"
      aws ecr delete-repository \
        --region "$CLEANUP_AWS_REGION" \
        --repository-name "$CLEANUP_REPOSITORY" --force >/dev/null \
        || record_error "Falha removendo ECR $CLEANUP_REPOSITORY"
    fi
  done
}

delete_cloudwatch_logs() {
  local CLEANUP_LOG_GROUP
  while IFS= read -r CLEANUP_LOG_GROUP; do
    [[ -n "$CLEANUP_LOG_GROUP" ]] || continue
    echo "Removendo CloudWatch Log Group: $CLEANUP_LOG_GROUP"
    aws logs delete-log-group \
      --region "$CLEANUP_AWS_REGION" --log-group-name "$CLEANUP_LOG_GROUP" \
      || record_error "Falha removendo log group $CLEANUP_LOG_GROUP"
  done < <(cluster_log_groups)
}

delete_iam_resources() {
  local CLEANUP_POLICY_ARN="arn:aws:iam::${CLEANUP_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy"
  local CLEANUP_ENTITY
  local CLEANUP_VERSION

  if aws iam get-policy --policy-arn "$CLEANUP_POLICY_ARN" >/dev/null 2>&1; then
    while IFS= read -r CLEANUP_ENTITY; do
      [[ -n "$CLEANUP_ENTITY" ]] || continue
      aws iam detach-role-policy --role-name "$CLEANUP_ENTITY" --policy-arn "$CLEANUP_POLICY_ARN" \
        || record_error "Falha desanexando política da role $CLEANUP_ENTITY"
    done < <(aws iam list-entities-for-policy --policy-arn "$CLEANUP_POLICY_ARN" \
      --query 'PolicyRoles[].RoleName' --output text | normalize_aws_list)
    while IFS= read -r CLEANUP_ENTITY; do
      [[ -n "$CLEANUP_ENTITY" ]] || continue
      aws iam detach-user-policy --user-name "$CLEANUP_ENTITY" --policy-arn "$CLEANUP_POLICY_ARN" \
        || record_error "Falha desanexando política do usuário $CLEANUP_ENTITY"
    done < <(aws iam list-entities-for-policy --policy-arn "$CLEANUP_POLICY_ARN" \
      --query 'PolicyUsers[].UserName' --output text | normalize_aws_list)
    while IFS= read -r CLEANUP_ENTITY; do
      [[ -n "$CLEANUP_ENTITY" ]] || continue
      aws iam detach-group-policy --group-name "$CLEANUP_ENTITY" --policy-arn "$CLEANUP_POLICY_ARN" \
        || record_error "Falha desanexando política do grupo $CLEANUP_ENTITY"
    done < <(aws iam list-entities-for-policy --policy-arn "$CLEANUP_POLICY_ARN" \
      --query 'PolicyGroups[].GroupName' --output text | normalize_aws_list)
    while IFS= read -r CLEANUP_VERSION; do
      [[ -n "$CLEANUP_VERSION" ]] || continue
      aws iam delete-policy-version \
        --policy-arn "$CLEANUP_POLICY_ARN" --version-id "$CLEANUP_VERSION" \
        || record_error "Falha removendo versão IAM $CLEANUP_VERSION"
    done < <(aws iam list-policy-versions --policy-arn "$CLEANUP_POLICY_ARN" \
      --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text | normalize_aws_list)
    aws iam delete-policy --policy-arn "$CLEANUP_POLICY_ARN" \
      || record_error "Falha removendo política IAM do Load Balancer Controller"
  fi

  if [[ -n "$CLEANUP_OIDC_PROVIDER_ARN" ]] && aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "$CLEANUP_OIDC_PROVIDER_ARN" >/dev/null 2>&1; then
    aws iam delete-open-id-connect-provider \
      --open-id-connect-provider-arn "$CLEANUP_OIDC_PROVIDER_ARN" \
      || record_error "Falha removendo provedor OIDC"
  fi
}

require_command aws
if ! [[ "$CLEANUP_WAIT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "CLEANUP_WAIT_SECONDS deve ser um inteiro positivo." >&2
  exit 2
fi
CLEANUP_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

capture_residual_stack_metadata

if cluster_exists; then
  require_command kubectl
  require_command eksctl
  require_command helm
  aws eks update-kubeconfig \
    --name "$CLEANUP_CLUSTER_NAME" \
    --region "$CLEANUP_AWS_REGION" >/dev/null
  capture_cluster_metadata
fi

if [[ "$CLEANUP_AUDIT_ONLY" == true ]]; then
  audit_resources
  if [[ "$CLEANUP_AUDIT_FOUND" -gt 0 ]]; then
    echo "Foram encontrados recursos do projeto que podem manter custo." >&2
    exit 1
  fi
  exit 0
fi

if [[ "$CLEANUP_ASSUME_YES" != true ]]; then
  echo "Serão removidos EKS, nós, ALBs, EBS, ECR, logs e IAM do projeto."
  read -r -p "Digite 'DESTRUIR ${CLEANUP_CLUSTER_NAME}' para continuar: " CLEANUP_TYPED_CONFIRMATION
  if [[ "$CLEANUP_TYPED_CONFIRMATION" != "DESTRUIR ${CLEANUP_CLUSTER_NAME}" ]]; then
    echo "Confirmação inválida; nenhuma alteração foi realizada."
    exit 1
  fi
fi

if cluster_exists; then
  backup_database
  delete_kubernetes_frontends
  force_delete_load_balancers
  uninstall_kubernetes_stack
  delete_cluster
else
  echo "Cluster EKS não encontrado; limpando recursos periféricos remanescentes."
fi

if ! cluster_exists; then
  delete_residual_cloudformation_stacks
  delete_orphan_instances
  force_delete_load_balancers
  delete_orphan_volumes_and_snapshots
  delete_orphan_network_costs
  delete_orphan_vpcs
else
  record_error "O cluster ainda existe; recursos internos não foram removidos manualmente"
fi

delete_ecr_repositories
delete_cloudwatch_logs
delete_iam_resources

audit_resources
if [[ "${#CLEANUP_ERRORS[@]}" -gt 0 || "$CLEANUP_AUDIT_FOUND" -gt 0 ]]; then
  echo
  echo "O teardown terminou com pendências; não é possível afirmar custo zero." >&2
  if [[ "${#CLEANUP_ERRORS[@]}" -gt 0 ]]; then
    printf '  - %s\n' "${CLEANUP_ERRORS[@]}" >&2
  fi
  echo "Corrija as pendências e execute: ./cleanup.sh --audit-only" >&2
  exit 1
fi

echo
echo "Teardown concluído e auditoria do projeto limpa."
echo "O backup local, o kubeconfig e as imagens Docker locais foram preservados."
echo "Custos históricos já lançados e recursos alheios a este projeto não são cobertos por esta auditoria."
