# Preparação dos segredos do ambiente `dev`

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
