# Implantação do ambiente `dev` na AWS

O caminho recomendado é o script idempotente na raiz do projeto. Ele cria os
repositórios ECR quando necessário, publica API e frontend, prepara o controlador
do ALB, instala o add-on EBS CSI, aplica o PostgreSQL em volume gp3 criptografado
e instala a observabilidade.

Se o cluster já existir:

```bash
export DEPLOY_ADMIN_USER_IDS="1"
export DEPLOY_POSTGRES_PASSWORD="defina-uma-senha-forte"
./scripts/deploy_aws.sh
```

Se o cluster tiver sido removido para economizar, a recriação precisa ser
solicitada de forma explícita porque inicia cobrança:

```bash
./scripts/deploy_aws.sh --create-cluster
```

Use `./scripts/deploy_aws.sh --help` para alterar cluster, região, versão do
Kubernetes, tag e opções.
O Secret existente é preservado em atualizações. Não execute rollout da API
enquanto uma carga ou um experimento estiver em andamento; o pod possui cinco
minutos de encerramento gracioso, mas uma interrupção do nó ainda pode encerrar
uma tarefa local.

## Criação manual do Secret

Os manifests não contêm senhas. Antes de `kubectl apply -k k8s/app/`, crie o
Secret diretamente no cluster:

```bash
read -r -p "ID(s) administrativo(s), separados por vírgula: " ADMIN_IDS_INPUT
read -r -s -p "Senha do PostgreSQL: " POSTGRES_PASSWORD_INPUT
echo
AUTH_SECRET_INPUT="$(openssl rand -hex 32)"

kubectl create namespace dev --dry-run=client -o yaml | kubectl apply -f -
kubectl -n dev create secret generic recommendation-secrets \
  --from-literal=postgres-database=bookstore_db \
  --from-literal=postgres-user=bookstore_app \
  --from-literal=postgres-password="$POSTGRES_PASSWORD_INPUT" \
  --from-literal=auth-secret="$AUTH_SECRET_INPUT" \
  --from-literal=admin-user-ids="$ADMIN_IDS_INPUT" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Não salve os valores digitados em arquivo nem faça commit do Secret gerado.
Como o ambiente é removido para controle de custos, gere uma nova chave a cada
ciclo ou restaure-a de um gerenciador de segredos.

## Verificação

```bash
kubectl -n dev get pods,svc,ingress,pvc
kubectl -n dev rollout status deployment/fastapi-recommender
kubectl -n dev rollout status deployment/react-frontend
kubectl -n dev logs deployment/fastapi-recommender --tail=100
```

Depois que o campo `ADDRESS` do Ingress aparecer, abra o endereço e autentique
um usuário cujo ID esteja em `DEPLOY_ADMIN_USER_IDS`. A página `/simulacoes`
contém os botões **Carregar dados dos CSVs**, **Executar ataque** e **Obter
métricas**.

## Destruição completa e controle de custos

Na raiz do projeto, execute:

```bash
./cleanup.sh
```

O procedimento cria um dump local do PostgreSQL, remove primeiro Ingresses e
Services externos, espera a liberação dos ALBs e então remove namespaces,
Prometheus/Grafana, EKS, EBS, ECR, logs, VPCs e recursos IAM do projeto. A
confirmação digitada deve ser exatamente `DESTRUIR observability`.

Confira o resultado quantas vezes desejar com a operação somente de leitura:

```bash
./cleanup.sh --audit-only
```

Código de saída zero significa que a auditoria não encontrou recursos associados
ao projeto. Código diferente de zero significa que existe uma pendência e o
script não declara o ambiente livre de custos.
