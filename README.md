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
Jaeger/OpenTelemetry e os experimentos científicos comparativos continuam nas
próximas prioridades.

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

- posicionar e sobrepor ataques em uma linha do tempo;
- comparar popularidade, conteúdo TF-IDF, item-item, ALS e híbrido;
- alternar entre sete métricas temporais;
- comparar cada modelo sem defesa e com resposta orientada por observabilidade;
- inspecionar detecção, perda acumulada, tempo abaixo do SLO e overhead;
- usar presets de ataques coordenados, qualidade dos dados e infraestrutura.

Os valores atuais são uma **simulação exploratória determinística**, identificada
como tal na API e na interface. Eles servem para validar cenários, visualização e
protocolo e não devem ser apresentados como resultados científicos medidos. O
pipeline experimental substituirá os perfis sintéticos por baselines reais.

Endpoints administrativos:

- `GET /admin/experiments/catalog`;
- `POST /admin/experiments/simulate`.

O documento técnico da entrega está em
[`alteracoes/PRIORIDADE_1_SIMULADOR_IMPLEMENTADO.md`](alteracoes/PRIORIDADE_1_SIMULADOR_IMPLEMENTADO.md).

## EKS

Antes da implantação, crie os segredos conforme
[`k8s/app/README.md`](k8s/app/README.md). Depois:

```bash
kubectl apply -k k8s/app/
kubectl apply -k k8s/monitoring/
```

O PostgreSQL usa StatefulSet e PVC de 20 GiB. Antes do teardown, `cleanup.sh`
faz backup local por padrão:

```bash
./cleanup.sh
```

Backups ficam em `backups/` e podem ser restaurados com:

```bash
./scripts/restore_database.sh backups/bookstore-AAAAMMDDTHHMMSSZ.dump
```

`cleanup.sh` preserva ECR, política IAM, kubeconfig e cache Docker. A exclusão de
ECR/IAM precisa ser solicitada por flags explícitas; consulte `./cleanup.sh -h`.
