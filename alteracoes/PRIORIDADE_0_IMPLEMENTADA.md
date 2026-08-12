# Correções implementadas — Prioridade 0

**Data:** 11 de agosto de 2026  
**Escopo:** estabilização funcional, segurança básica, reprodutibilidade e preparação para o próximo ciclo temporário na AWS

## Resultado geral

Os dez itens da Prioridade 0 foram implementados no código e validados
localmente. A aplicação agora possui recomendadores corrigidos, autenticação e
autorização no backend, validação de entradas, atualização versionada do modelo,
persistência do PostgreSQL, backup antes do teardown e configuração Kubernetes
sem segredos versionados.

Duas confirmações dependem de ações externas e, por isso, não foram simuladas:

1. a implantação completa no EKS será validada quando o próximo ciclo pago for
   iniciado;
2. credenciais que já tenham sido utilizadas fora do Git precisam ser rotacionadas
   nos respectivos provedores. Os valores locais foram removidos, mas remover um
   arquivo não invalida uma credencial externa nem apaga o histórico remoto.

## 1. Recomendadores corrigidos

Alterações em `recommender.py`:

- removida a execução automática de leitura/impressão do dataset durante import;
- recomendação por livro não inclui mais o próprio livro;
- recomendação por perfil deixou de tratar IDs inteiros como registros;
- itens já avaliados são excluídos dos rankings personalizados;
- filtragem colaborativa retorna IDs reais de livros, não posições de matriz;
- o ID do usuário é resolvido por mapeamento, não por `iloc[user_id]`;
- cold start retorna ranking por nota média;
- tags são associadas por `good_id`/`goodreads_book_id` corretamente;
- a matriz densa item-item foi substituída por representação esparsa;
- o cálculo colaborativo passou a ser item-item de forma explícita e consistente.

## 2. Ciclo explícito de atualização do modelo

Foi criada a tabela `model_revision` e um snapshot versionado por instância da
API:

- alterações em livro, avaliação, tag ou lista de leitura incrementam a revisão;
- qualquer réplica detecta revisão diferente no PostgreSQL;
- o snapshot e o modelo colaborativo são reconstruídos antes da próxima
  recomendação;
- a leitura verifica a revisão antes e depois para evitar publicar snapshot
  inconsistente durante escrita concorrente;
- `GET /recommendations/status` informa revisão, estado de atualização e volume;
- `POST /admin/recommendations/rebuild` força reconstrução administrativa.

## 3. Testes automatizados

Foi criada a pasta `tests/` com testes de:

- recomendação por conteúdo;
- recomendação personalizada;
- filtragem colaborativa e IDs reais;
- cold start;
- hash de senha com salt;
- assinatura e adulteração de token;
- cadastro/login;
- autorização administrativa e isolamento entre usuários;
- validação de notas e IDs;
- criação/listagem/consulta de livros;
- avaliação, tag e lista de leitura;
- carga administrativa de dados;
- atualização e reconstrução do modelo;
- remoção das rotas destrutivas antigas.

Resultado final:

```text
9 passed
```

Foram acrescentados `pytest.ini` e `requirements-dev.txt`. As versões de runtime
também foram fixadas em `requirements.txt` para builds reproduzíveis.

## 4. Frontend e API alinhados

- O frontend agora solicita senha no cadastro/login.
- O token é salvo na sessão e inserido automaticamente pelo Axios.
- A permissão administrativa não depende mais de `id == 111` no navegador.
- Consultas personalizadas usam o usuário autenticado.
- A URL da API é local em desenvolvimento e relativa no ALB.
- URLs antigas de Load Balancer foram removidas do frontend.
- A ação `/buy` foi removida por não existir regra de negócio correspondente.
- Redirecionamentos fixos para `localhost` foram removidos.
- O Nginx entrega corretamente rotas SPA e roda sem root na porta 8080.
- O build React terminou com sucesso e sem avisos de ESLint.

## 5. Validação de entrada

Foram criados schemas específicos para:

- usuário e senha;
- livro;
- avaliação limitada de 1 a 5;
- tag normalizada e limitada;
- lista de leitura;
- IDs positivos e paginação entre 1 e 100 itens.

Livro inexistente retorna `404`, duplicidade retorna `409`, falta de autenticação
retorna `401` e falta de autorização retorna `403`.

## 6. Operações destrutivas protegidas

Foram removidas:

- `GET /clearTables`;
- `GET /loadTest`.

Foram criadas:

- `DELETE /admin/data`;
- `POST /admin/load-test-data`.

As novas rotas exigem token administrativo. Usuários comuns não conseguem
executá-las.

## 7. Autenticação e autorização reais

Foi adicionado `auth.py` com:

- PBKDF2-HMAC-SHA256 com salt aleatório e 600 mil iterações;
- comparação resistente a timing attack;
- token com expiração e assinatura HMAC-SHA256;
- chave efêmera em desenvolvimento quando não configurada;
- `AUTH_SECRET` obrigatório e com tamanho mínimo em produção;
- consulta da permissão administrativa no banco a cada requisição;
- proteção das mutações e recomendações personalizadas;
- bloqueio de acesso aos dados personalizados de outro usuário.

A tabela `user_credentials` separa senha/role dos usuários do domínio. Contas
antigas sem credencial retornam `409` em vez de serem apropriadas sem senha.

## 8. Segredos e dependências

- Senha fixa do PostgreSQL foi removida do código.
- FastAPI e PostgreSQL usam `secretKeyRef` para `recommendation-secrets`.
- O Secret de e-mail versionado foi removido.
- Credenciais encontradas nos arquivos locais de estudo de Fluent Bit/Jaeger
  foram substituídas por placeholders.
- Endereços específicos de ALB foram removidos das configurações da aplicação.
- `.gitignore`, `.dockerignore` e `bookstore/.dockerignore` foram criados.
- Bytecodes Python versionados, que preservavam configurações antigas, foram
  removidos; o `venv` local foi preservado para não quebrar o ambiente.
- A auditoria do frontend caiu de 57 vulnerabilidades, incluindo 2 críticas,
  para **0 vulnerabilidades nas dependências de produção**.
- Restam 28 avisos no toolchain de desenvolvimento do Create React App. Essas
  dependências existem no estágio de build e não são copiadas para a imagem
  final Nginx. A remoção completa requer futura migração do CRA, sem aplicar o
  `npm audit fix --force` que sugeria uma alteração quebradora.

Instruções para criar o Secret sem gravá-lo em arquivo estão em
`k8s/app/README.md`.

## 9. Ingress e validação ponta a ponta

- `ingress_dev.yaml` foi incluído no `kustomization.yml`.
- Rotas administrativas, health e status do modelo foram adicionadas.
- `/metrics` deixou de ser exposto pelo Ingress público; o ServiceMonitor acessa
  internamente.
- API e frontend usam Services `ClusterIP` atrás de um único ALB.
- Foram adicionados health, readiness e startup probes.
- Foram adicionados requests/limits e execução não-root.
- Imagens passaram a usar tag `1.0.0` em vez de `latest`.

Validações executadas:

- `kubectl kustomize k8s/app`: 7 recursos renderizados, incluindo Ingress e
  StatefulSet;
- `kubectl kustomize k8s/monitoring`: 3 recursos renderizados;
- build da imagem FastAPI: aprovado;
- build da imagem React/Nginx: aprovado;
- health check dos dois containers: aprovado;
- integração temporária FastAPI + PostgreSQL 16: `/ready`, autenticação e criação
  de livro aprovados com confirmação do dialeto PostgreSQL;
- a imagem usa SQLite somente como fallback e respeita as variáveis
  `POSTGRES_*` quando o PostgreSQL está configurado;
- a carga do Goodbooks consolida chaves compostas duplicadas em avaliações e
  tags antes da inserção, mantendo compatibilidade com as restrições do banco;
- varredura pelos segredos conhecidos no diretório do projeto: nenhum valor
  encontrado;
- `git diff --check`: aprovado.

O EKS não foi provisionado nesta correção para respeitar o ciclo de custos.

## 10. Persistência, backup, restauração e teardown

- PostgreSQL passou de Deployment sem volume para StatefulSet.
- Foi criado PVC de 20 GiB.
- Foram adicionados probes e recursos do banco.
- `scripts/backup_database.sh` cria dump completo, privado e datado.
- `scripts/restore_database.sh` restaura o dump e reinicia a API para recarregar o
  modelo.
- `cleanup.sh` cria backup automaticamente antes do teardown quando o banco está
  disponível.
- O script exige confirmação do nome do cluster, salvo uso explícito de `--yes`.
- Remoções amplas de kubeconfig e cache Docker foram eliminadas.
- Exclusão de ECR e política IAM passou a exigir flags específicas.
- Namespaces/PVCs são removidos depois do backup para evitar volumes EBS órfãos.
- Releases de monitoring, logging e AWS Load Balancer Controller são tratadas.

## Mudanças incompatíveis que exigem atenção

1. `POST /createUser` agora exige `password` com no mínimo 8 caracteres.
2. Rotas de escrita exigem `Authorization: Bearer <token>`.
3. Administradores precisam constar em `ADMIN_USER_IDS` no Secret.
4. As rotas `/clearTables` e `/loadTest` não existem mais.
5. O frontend Nginx usa a porta interna 8080.
6. As imagens Kubernetes esperam a tag `1.0.0`.
7. Restaurar banco antigo com usuários sem `user_credentials` exige recriar essas
   contas ou executar uma migração administrativa.

## Ações externas ainda necessárias

Antes do próximo ciclo AWS:

1. rotacionar no provedor qualquer senha de e-mail/Elasticsearch que tenha sido
   usada anteriormente;
2. criar `recommendation-secrets` seguindo `k8s/app/README.md`;
3. publicar as imagens com tag `1.0.0` na ECR;
4. subir o EKS e executar smoke test pelo ALB;
5. confirmar criação/remoção do volume EBS durante o ciclo de backup e teardown;
6. se o repositório já foi compartilhado, planejar limpeza do histórico Git dos
   segredos antigos sem reescrever o histórico de forma unilateral.
