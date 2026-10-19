# Recommendation API

Protótipo de pesquisa para recomendação de livros e observabilidade. A aplicação
é composta por FastAPI, React, PostgreSQL, Docker e Kubernetes/EKS.

O ambiente AWS é temporário: ele é provisionado durante desenvolvimento e
experimentos e removido em seguida para controle de custos.

## Estado atual

Estão integrados:

- recomendação por conteúdo com tags;
- recomendação personalizada por conteúdo;
- filtragem colaborativa item-item com matriz esparsa;
- autenticação por senha e token assinado;
- autorização de usuário e administrador;
- PostgreSQL, métricas Prometheus e interface React;
- Docker, Kustomize, Ingress ALB e persistência por PVC.

Prometheus/Grafana constituem a base atual de métricas. Logging centralizado,
Jaeger/OpenTelemetry continuam nas próximas prioridades. O laboratório já
executa experimentos comparativos medidos sobre o snapshot real, além da
simulação exploratória usada para planejar cenários.

O levantamento completo está em
[`alteracoes/RELATORIO_STATUS_ANTEPROJETO.md`](alteracoes/RELATORIO_STATUS_ANTEPROJETO.md).

## Desenvolvimento local

O caminho mais simples usa SQLite e não depende de nenhum recurso da AWS. No
primeiro terminal, construa e execute a API:

```bash
docker build -t recommendation-api-local .
docker volume create recommendation-api-local-data
LOCAL_AUTH_SECRET="$(openssl rand -hex 32)"
docker run --rm --name recommendation-api-local \
  -p 5000:5000 \
  -e AUTH_SECRET="$LOCAL_AUTH_SECRET" \
  -e ADMIN_USER_IDS="1" \
  -v recommendation-api-local-data:/app/runtime \
  recommendation-api-local
```

No segundo terminal, execute o frontend:

```bash
docker build -t recommendation-frontend-local ./bookstore
docker run --rm --name recommendation-frontend-local \
  -p 3000:8080 recommendation-frontend-local
```

Acesse `http://localhost:3000`. O ID `1` será administrador porque está em
`ADMIN_USER_IDS`. A documentação interativa da API fica em
`http://127.0.0.1:5000/docs`; health e readiness ficam em `/health` e `/ready`.

O volume mantém o SQLite quando o container é derrubado. Para apagar somente os
dados desse ambiente local, pare a API e execute
`docker volume rm recommendation-api-local-data`.

Sem `DATABASE_URL` ou variáveis `POSTGRES_*`, a API usa SQLite. No acesso por
`localhost`, o frontend usa `http://127.0.0.1:5000`. No EKS, frontend e API
compartilham o mesmo Ingress e a URL da API é relativa. Em produção,
`AUTH_SECRET` com pelo menos 32 caracteres é obrigatório.

Para executar sem Docker, crie e ative um ambiente Python, instale
`requirements-dev.txt`, defina `AUTH_SECRET` e `ADMIN_USER_IDS` e inicie
`uvicorn main:app --host 0.0.0.0 --port 5000`.

## Autenticação

`POST /createUser` cria a conta na primeira chamada e autentica nas chamadas
seguintes. Exemplo de corpo:

```json
{
  "id": 1,
  "name": "Usuário",
  "password": "uma-senha-forte"
}
```

O token retornado deve ser enviado como `Authorization: Bearer <token>`. Os IDs
administrativos são definidos por `ADMIN_USER_IDS`; não há mais autorização
baseada somente no frontend.

Operações destrutivas e de manutenção ficam em:

- `DELETE /admin/data`;
- `POST /admin/load-test-data`;
- `POST /admin/data/load` (carga assíncrona usada pelo painel);
- `POST /admin/experiments/real/run`;
- `POST /admin/experiments/real/suite`;
- `GET /admin/experiments/real/suite/{job_id}/xlsx`;
- `GET /admin/experiments/real/metrics`;
- `POST /admin/recommendations/rebuild`.

Todas exigem token administrativo. Os antigos `GET /clearTables` e
`GET /loadTest` foram removidos.

## Testes

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q
kubectl kustomize k8s/app
kubectl kustomize k8s/monitoring
```

Os testes cobrem algoritmos, cold start, IDs reais, autenticação, autorização,
validação, atualização do modelo e fluxos integrados da API.

## Laboratório de resiliência

Usuários administrativos acessam `http://localhost:3000/simulacoes` pelo item
**Laboratório** do cabeçalho. A página permite:

- carregar no PostgreSQL os CSVs Goodbooks empacotados na API;
- executar ataques controlados sobre uma cópia do snapshot, sem alterar o banco;
- escolher popularidade regularizada, conteúdo por tags ou item-item;
- ativar ou desativar a detecção e a resposta orientada por observabilidade;
- obter NDCG, Precision, Recall, hit rate, cobertura, latência, disponibilidade
  e qualidade dos dados realmente medidos;
- acompanhar as tarefas e consultar os resultados persistidos no PostgreSQL;
- testar sequencialmente todos os modelos contra todos os ataques, nos modos
  sem e com observabilidade;
- baixar uma planilha XLSX com qualidade inicial, qualidade sem observabilidade,
  qualidade com observabilidade, degradação detalhada dos dados e métricas
  operacionais;
- posicionar e sobrepor ataques em uma linha do tempo;
- comparar modelos em cenários exploratórios de maior duração;
- alternar entre sete métricas temporais;
- comparar cada modelo sem defesa e com resposta orientada por observabilidade;
- inspecionar detecção, perda acumulada, tempo abaixo do SLO e overhead;
- usar presets de ataques coordenados, qualidade dos dados e infraestrutura.

O primeiro bloco da página produz resultados medidos. O painel temporal abaixo
dele continua sendo uma **simulação exploratória determinística**, identificada
como tal na API e na interface, e não deve ser apresentado como resultado
científico medido.

A bateria reutiliza o mesmo recorte e os três baselines, além de calcular o
modelo por tags com uma matriz esparsa vetorizada. No cenário sem observabilidade,
o lote atacado permanece bruto: dados inválidos, órfãos e duplicados aparecem na
aba **Dados** do XLSX, em vez de serem sanitizados implicitamente.

Endpoints administrativos:

- `POST /admin/data/load`;
- `GET /admin/jobs/{job_id}`;
- `GET /admin/experiments/real/catalog`;
- `POST /admin/experiments/real/run`;
- `POST /admin/experiments/real/suite`;
- `GET /admin/experiments/real/suite/{job_id}/xlsx`;
- `GET /admin/experiments/real/metrics`;
- `GET /admin/experiments/catalog`;
- `POST /admin/experiments/simulate`.

O documento técnico do fluxo AWS está em
[`alteracoes/LABORATORIO_REAL_AWS_IMPLEMENTADO.md`](alteracoes/LABORATORIO_REAL_AWS_IMPLEMENTADO.md).

## EKS/AWS

O script de implantação constrói as imagens, publica no ECR, aplica os manifests,
instala o AWS Load Balancer Controller e, por padrão, Prometheus/Grafana. Ele não
cria um cluster sem autorização explícita.

```bash
export DEPLOY_ADMIN_USER_IDS="1"
export DEPLOY_POSTGRES_PASSWORD="troque-esta-senha"
./scripts/deploy_aws.sh --create-cluster
```

Se o cluster `observability` já estiver ativo, remova `--create-cluster`. Consulte
as opções e o procedimento de segredos em [`k8s/app/README.md`](k8s/app/README.md).

O PostgreSQL usa StatefulSet e PVC de 20 GiB. Antes do teardown, `cleanup.sh`
faz backup local e remove todos os recursos AWS do projeto, incluindo EKS,
ALBs, EBS, ECR, logs, VPCs residuais e IAM:

```bash
./cleanup.sh
```

O script exige a confirmação `DESTRUIR observability`. Ao terminar, ele executa
uma auditoria e retorna erro se ainda encontrar algum recurso do projeto. A
auditoria também pode ser repetida sem alterar a AWS:

```bash
./cleanup.sh --audit-only
```

Backups ficam em `backups/` e podem ser restaurados com:

```bash
./scripts/restore_database.sh backups/bookstore-AAAAMMDDTHHMMSSZ.dump
```

O kubeconfig, os backups e as imagens Docker locais são preservados porque não
geram cobrança AWS. Se o PostgreSQL estiver indisponível, o teardown para antes
da destruição; `--skip-backup` só deve ser usado quando a perda dos dados for
aceita explicitamente. Consulte [`alteracoes/DESTRUICAO_AWS_IMPLEMENTADA.md`](alteracoes/DESTRUICAO_AWS_IMPLEMENTADA.md).
