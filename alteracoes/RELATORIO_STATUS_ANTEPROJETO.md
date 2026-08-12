# Relatório de aderência e estado do projeto

## Monitoramento de Qualidade dos Dados para Personalização de Recomendação de Produtos

**Data do levantamento:** 11 de agosto de 2026  
**Repositório analisado:** `Recommendation-API`, branch `main`, incluindo alterações locais ainda não commitadas  
**Anteprojeto analisado:** `{31032025195544}_Anteprojero IC 1 (2).docx`  
**Escopo complementar:** artefatos de operação AWS em `/home/arthur/AWS/comandos.txt` e `/home/arthur/AWS/projeto-iniciacao/iam_policy.json`

> **Nota de atualização:** este relatório preserva o diagnóstico anterior às
> correções. A Prioridade 0 foi executada posteriormente e está documentada em
> [`PRIORIDADE_0_IMPLEMENTADA.md`](PRIORIDADE_0_IMPLEMENTADA.md).

## 1. Como interpretar este relatório

Os estados usados abaixo têm significado estrito:

- **Pronto:** há um artefato implementado e a verificação disponível não revelou um bloqueio essencial para o escopo declarado daquele artefato. Não significa que todo o sistema esteja pronto para produção.
- **Em desenvolvimento:** há implementação ou configuração concreta, mas ela está incompleta, não foi validada de ponta a ponta ou possui defeitos conhecidos.
- **A desenvolver:** não foi encontrada implementação no projeto, ou existe somente material de estudo/comando sem integração e sem resultado verificável.

O relatório distingue o código do projeto do repositório externo `observability-zero-to-hero`. Esse segundo repositório contém material de estudo e experimentos locais; portanto, seus exemplos de Jaeger, OpenTelemetry, Alertmanager e Fluent Bit **não são considerados funcionalidades integradas ao `Recommendation-API`**.

## 2. Conclusão executiva

O projeto já possui um **protótipo técnico substancial**: dados do domínio, API FastAPI, banco PostgreSQL, interface React, dois Dockerfiles, manifestos Kubernetes e uma base de monitoramento com Prometheus/Grafana. A estrutura é suficiente para continuar a pesquisa sem recomeçar o desenvolvimento.

Entretanto, o sistema completo descrito no anteprojeto **ainda não pode ser considerado concluído nem validado**. Os principais motivos são:

1. Os recomendadores atuais são protótipos e apresentam erros funcionais confirmados; ALS e FP-Growth ainda não foram implementados.
2. A observabilidade implementada se concentra em métricas técnicas de HTTP/cluster. Ainda não existe monitoramento da **qualidade dos dados**, da qualidade das recomendações, de ataques de manipulação ou de comportamento anômalo, que é o núcleo do anteprojeto.
3. Logging centralizado está apenas iniciado e tracing com Jaeger/OpenTelemetry não está integrado à aplicação.
4. Não existe suíte de testes do projeto, experimento comparativo, teste de desempenho ou evidência quantitativa de redução de erros/falhas.
5. A infraestrutura AWS segue um ciclo deliberado de **subir, testar e derrubar** para controle de custos. Ela não está ativa no momento deste levantamento e ainda há ajustes locais não concluídos.
6. A revisão sistemática, a análise dos resultados e o artigo científico não estão materializados no repositório.

Em termos de fase, o trabalho está entre **protótipo implementado** e **preparação do ambiente experimental**. A fase científica de experimentação, comparação e conclusão ainda precisa ser executada.

## 3. Arquitetura existente

O desenho atual é:

`Usuário → ALB/Ingress → React/Nginx → FastAPI → PostgreSQL`

Em paralelo:

`Prometheus → endpoint /metrics da FastAPI → Grafana/Alertmanager`

Principais componentes encontrados:

| Componente | Implementação atual | Estado |
|---|---|---|
| Dados | Goodbooks-10k: livros, avaliações, tags, relações livro-tag e lista de leitura | Pronto como base de dados experimental |
| Backend | FastAPI, SQLModel/SQLAlchemy, endpoints de catálogo, usuários, avaliações, tags e recomendações | Em desenvolvimento |
| Recomendação por conteúdo | Pontuação manual por interseção de tags e nota média | Em desenvolvimento |
| Recomendação colaborativa | Similaridade de cosseno entre itens a partir da matriz usuário-item | Em desenvolvimento |
| Frontend | React com login/cadastro simples, catálogo, livro, avaliação, tags e consultas de recomendação | Em desenvolvimento |
| Persistência | PostgreSQL em Deployment Kubernetes | Em desenvolvimento; não há volume persistente |
| Empacotamento | Dockerfiles para FastAPI e React/Nginx | Pronto como base; imagem final não foi validada neste ambiente |
| Orquestração | Deployments e Services Kubernetes, Kustomize e Ingress ALB, já usados em ciclos temporários na AWS e atualmente em ajuste | Em desenvolvimento |
| Métricas | Instrumentação FastAPI, `/metrics`, ServiceMonitor, PrometheusRule e kube-prometheus-stack | Em desenvolvimento |
| Logs | Comandos de instalação de Elasticsearch/Kibana e configuração inicial do Fluent Bit | Em desenvolvimento inicial |
| Traces | Material de estudo externo sobre Jaeger/OpenTelemetry | A desenvolver no projeto |
| Experimentos científicos | Não há pipeline, notebooks, resultados ou relatório comparativo | A desenvolver |

Observação: o README descreve NLB, banco “gerenciado”, arquitetura GitOps e uma pilha completa com ELK e Jaeger. O código atual usa **Ingress ALB**, PostgreSQL dentro do cluster sem persistência, não contém pipeline GitOps e ainda não integra Jaeger. O README precisa ser ajustado para refletir o estado real.

## 4. O que já está pronto

### 4.1 Base de dados para experimentação

Os cinco CSVs necessários estão presentes em `data/`, totalizando aproximadamente 2,94 milhões de registros (sem contar cabeçalhos):

- 10.000 livros;
- 981.756 avaliações;
- 34.252 tags;
- 999.912 relações entre livros e tags;
- 912.705 registros de “quero ler”.

Isso atende à necessidade inicial de uma massa de dados realista para construir e comparar recomendadores.

### 4.2 Estrutura básica do backend

Já existem:

- modelos SQLModel para livros, avaliações, usuários, tags e lista de leitura;
- criação das tabelas no startup;
- carregamento dos CSVs para o PostgreSQL;
- endpoints de listagem e consulta de livros;
- cadastro/login simplificado de usuário;
- cadastro de livro;
- registro/atualização de avaliação;
- inclusão de tags e lista de leitura;
- três endpoints destinados a recomendações;
- CORS configurável;
- exposição de métricas Prometheus.

Os arquivos Python passaram na verificação de sintaxe com `py_compile`.

### 4.3 Interface web inicial

A aplicação React possui:

- página de identificação do usuário;
- catálogo de livros;
- cartões e detalhes de livro;
- formulário administrativo de cadastro de livro;
- envio de avaliação, tag e marcação de leitura futura;
- campos para consultar recomendações por livro e por usuário;
- estilos próprios com `styled-components`;
- roteamento de SPA;
- configuração de URL da API em tempo de execução, atualmente em ajuste.

### 4.4 Base de containerização e Kubernetes

Já foram preparados:

- imagem Python/Uvicorn para a API;
- build multiestágio Node/Nginx para o frontend;
- Deployments com duas réplicas para API e frontend;
- Services internos para API, frontend e PostgreSQL;
- Kustomizations para aplicação e monitoramento;
- Ingress ALB para aplicação e para a pilha de monitoramento;
- política IAM do AWS Load Balancer Controller;
- roteiro operacional para EKS, ECR, Helm e ALB;
- script de limpeza do ambiente.

`kubectl kustomize` conseguiu renderizar os conjuntos `k8s/app` e `k8s/monitoring`, o que confirma a estrutura YAML/Kustomize básica. Isso não comprova que todos os recursos funcionam dentro do cluster.

### 4.5 Base de métricas

O backend usa `prometheus-fastapi-instrumentator`; há `ServiceMonitor` para coletar `/metrics`, regra de latência, regra de indisponibilidade e configuração inicial de Prometheus, Grafana e Alertmanager pelo `kube-prometheus-stack`.

Esta é uma boa base para o pilar de **métricas**, mas ainda não representa a observabilidade completa nem o monitoramento da qualidade dos dados.

## 5. O que está sendo desenvolvido agora

As alterações locais não commitadas mostram uma frente ativa de adaptação para nuvem:

- substituição de URLs fixas do frontend por `window.ENV.API_URL`;
- geração de `config.js` no container React a partir de variável de ambiente;
- configuração do Nginx para servir corretamente as rotas da SPA;
- mudança dos Services de `LoadBalancer` para `ClusterIP` atrás de um Ingress único;
- criação de `k8s/app/ingress_dev.yaml`;
- ajuste do backend para escutar em `0.0.0.0` e aceitar origem configurada por ambiente;
- configuração de endereços externos de Prometheus e Alertmanager;
- health check do ALB para Prometheus;
- criação de roteiro de teardown/limpeza da AWS.

Essa frente ainda não está fechada porque:

- `k8s/app/ingress_dev.yaml` não consta em `k8s/app/kustomization.yml`; portanto, `kubectl apply -k k8s/app/` não cria o Ingress da aplicação;
- a origem configurada para o backend aponta para um endereço de monitoramento e contém espaço ao final;
- existem três mecanismos/endpoints diferentes para a URL do frontend/API, com valores inconsistentes;
- várias alterações são arquivos não rastreados ou modificações ainda sem commit;
- não foi possível executar o build React local porque Node/npm não estão instalados no ambiente atual;
- não há teste de ponta a ponta depois dessas mudanças.

Também há uma frente inicial de logging:

- `/home/arthur/AWS/comandos.txt` contém a instalação manual de Elasticsearch, Kibana e Fluent Bit;
- `k8s/logging/fluentbit-values.yaml` define uma saída para Elasticsearch;
- o repositório de estudo contém experimentos locais de Fluent Bit.

No projeto principal, porém, a senha ainda é placeholder e não há manifests/valores completos, validação de ingestão, política de retenção, índice, dashboard ou integração reproduzível da pilha.

## 6. Problemas confirmados que impedem considerar o protótipo concluído

Esta seção não pretende ser uma lista exaustiva. Ela registra os erros que puderam ser confirmados por teste ou inspeção durante o levantamento e é compatível com a informação do responsável de que ainda existem outros erros em correção.

### 6.1 Recomendadores

Testes sintéticos diretos nas funções atuais confirmaram:

- a recomendação baseada em um livro inclui o próprio livro consultado entre os resultados;
- a recomendação baseada no perfil por tags (`get_recommendation_item_basedUsu`) falha com `TypeError`, pois trata IDs inteiros como registros de livro;
- o recomendador colaborativo usa `iloc[user_id]`, confundindo ID de usuário com posição da linha; para determinados IDs isso seleciona outro usuário ou gera `IndexError`;
- o recomendador colaborativo retorna posições de colunas, não os IDs reais dos livros;
- apesar do nome “User Based”, o cálculo existente produz similaridade **item-item** com base em avaliações;
- o README chama a solução de híbrida, mas não há uma função que combine os escores de conteúdo e colaborativo em um único ranking.

Outros riscos encontrados por inspeção:

- o módulo `recommender.py` lê e imprime o dataset inteiro ao ser importado, criando efeito colateral e custo desnecessário;
- a matriz e o modelo são criados somente no startup; novas avaliações, tags, leituras ou o `/loadTest` não atualizam o estado do recomendador;
- não há tratamento consistente de usuário/livro inexistente, cold start ou dados insuficientes em todos os endpoints;
- a similaridade completa entre 10.000 itens pode consumir muita memória por réplica e ainda não foi medida;
- a relação adicionada por `/tag` pode misturar o ID interno do livro com `goodreads_book_id`.

### 6.2 Integração frontend/backend

- O frontend chama `POST /buy`, mas esse endpoint não existe na FastAPI nem no Ingress.
- O redirecionamento após compra ainda aponta para `localhost`.
- A interface não possui tratamento consistente de loading, erro HTTP ou validação.
- O “login” aceita somente ID e nome; não existe autenticação ou autorização real.
- A regra administrativa `id == 111` existe apenas no frontend e pode ser contornada.
- O backend não restringe a nota ao intervalo de 1 a 5.
- `/clearTables` e `/loadTest` são operações destrutivas expostas por GET e sem proteção.

Esses pontos são particularmente relevantes porque o anteprojeto pretende proteger o sistema contra dados falsos, incorretos e usuários mal-intencionados.

### 6.3 Infraestrutura e segurança operacional

- O PostgreSQL não possui PVC; reiniciar ou recriar o pod pode eliminar os dados.
- Não há readiness/liveness probes, limites/requests de recursos, autoscaling ou política de disponibilidade.
- As imagens usam a tag mutável `latest`.
- Não há pipeline CI/CD ou GitOps, apesar da descrição no README.
- Credenciais de banco, identificadores de conta/recursos e endereços específicos estão codificados nos arquivos.
- Existe um Secret de e-mail versionado em Base64, que não é criptografia.
- O repositório externo de estudo contém credencial de Elasticsearch em texto simples nas alterações locais. Essas credenciais devem ser rotacionadas e migradas para AWS Secrets Manager, External Secrets ou Kubernetes Secrets gerenciados com segurança.
- O arquivo `custom_kube_prometheus_stack.yml` declara `alertmanager` duas vezes; a segunda chave pode sobrescrever a primeira e descartar selector, estratégia e réplicas.
- `alertmangerconfig.yml` no projeto está vazio e uma severidade de alerta está escrita como `criticalS`.
- O script `cleanup.sh` apaga todo o kubeconfig local, executa limpeza global do Docker e procura balanceadores por um critério amplo. Ele precisa de confirmações, escopo e proteções antes de uso rotineiro.
- O repositório versiona o ambiente virtual Python: aproximadamente 11,8 mil arquivos sob `venv/`. Também existem dependências/cache volumosos no diretório de trabalho. Faltam `.gitignore` e `.dockerignore` adequados na raiz.

### 6.4 Situação atual da AWS

Uma consulta somente leitura, realizada em 11 de agosto de 2026 na região `us-east-1`, verificou:

- credenciais AWS válidas;
- nenhum cluster EKS listado;
- nenhum contexto Kubernetes local configurado;
- ausência dos repositórios ECR `fastapi-recommender` e `react-frontend`;
- ausência de Load Balancers Kubernetes;
- permanência da política IAM `AWSLoadBalancerControllerIAMPolicy`.

Esse estado é **intencional**: o ambiente é provisionado para desenvolvimento/teste e depois removido para evitar custo contínuo. Portanto, a ausência atual dos recursos não deve ser interpretada como ausência de implantação anterior. Ela significa apenas que **não havia um ciclo de execução ativo no instante da consulta**, o que também impede validar de ponta a ponta a versão atual sem subir novamente o ambiente.

## 7. Aderência aos objetivos específicos do anteprojeto

| Objetivo do anteprojeto | Evidência encontrada | Classificação |
|---|---|---|
| Desenvolver revisão sistemática | O anteprojeto contém contextualização e referências, mas não há protocolo, strings de busca, bases consultadas, critérios, seleção ou síntese sistemática | A desenvolver/documentar |
| Analisar projetos de observabilidade aplicada a recomendações | Há referências no anteprojeto e um repositório de estudo de observabilidade, mas não há matriz comparativa voltada a recomendadores | Em desenvolvimento inicial |
| Estudar CF, CB/ALS, FP-Growth e outros | Há protótipos por tags e por similaridade de avaliações; ALS e FP-Growth estão ausentes | Em desenvolvimento |
| Estudar ELK, EFK, Jaeger e outros | Prometheus/Grafana estão iniciados; há estudo externo e comandos de ELK/EFK; Jaeger não está integrado | Em desenvolvimento |
| Construir site de teste | Interface React e API existem, mas há rotas quebradas, validação insuficiente e ausência de teste ponta a ponta | Em desenvolvimento avançado |
| Construir modelos de recomendação em Python | Existem dois baselines, porém com defeitos funcionais e sem validação de qualidade | Em desenvolvimento |
| Colocar ferramentas na nuvem | A implantação já é realizada em ciclos temporários de subida/teste/remoção para controle de custo; a automação e a versão atual ainda têm ajustes pendentes | Em desenvolvimento, com implantação experimental já realizada |
| Avaliar resultados | Não foram encontrados resultados quantitativos | A desenvolver |
| Comparar algoritmos de recomendação | Não há pipeline, protocolo, métricas ou tabelas de comparação | A desenvolver |
| Comparar métodos de observabilidade | Não há experimento controlado nem comparação de cobertura, custo ou capacidade de detecção | A desenvolver |
| Apresentar relatório detalhado dos resultados | Este arquivo registra o estado, mas o relatório científico de resultados ainda depende dos experimentos | A desenvolver após os testes |

## 8. O que ainda precisa ser desenvolvido

### Prioridade 0 — tornar o protótipo correto, seguro e reproduzível

1. Corrigir os três fluxos de recomendação, separar IDs de posições e excluir itens já vistos/o próprio item quando apropriado.
2. Remover o carregamento executado durante o import e criar um ciclo explícito de treinamento/atualização do modelo.
3. Criar testes unitários para os algoritmos e testes de integração para todos os endpoints.
4. Alinhar frontend, FastAPI e Ingress, incluindo decisão sobre remover ou implementar `/buy`.
5. Adicionar validação de avaliações, tags, IDs e limites de payload.
6. Proteger ou remover `/clearTables` e `/loadTest`; usar métodos HTTP adequados e autorização.
7. Implementar autenticação/autorização real para usuários e administração.
8. Remover segredos do código, rotacionar os segredos já expostos e parametrizar configurações.
9. Corrigir o Ingress/Kustomize e executar um teste ponta a ponta local/cluster.
10. Adicionar persistência ao PostgreSQL ou migrar para serviço gerenciado, com backup e recuperação.

### Prioridade 1 — entregar o núcleo científico do anteprojeto

1. Definir baselines claros:
   - popularidade/não personalizado;
   - conteúdo por tags com TF-IDF/cosseno;
   - filtragem colaborativa item-item e/ou user-user correta;
   - ALS;
   - FP-Growth/regras de associação, se mantido no escopo;
   - método híbrido com regra de combinação explícita.
2. Separar treino, validação e teste temporalmente para evitar vazamento de dados.
3. Medir qualidade com métricas adequadas, por exemplo Precision@K, Recall@K, NDCG@K, MAP@K, cobertura, diversidade e novidade. RMSE/MAE podem complementar modelos de predição de nota, mas não substituem métricas de ranking.
4. Medir CPU, memória, duração de treinamento, latência de inferência, throughput e tamanho dos artefatos.
5. Definir ataques/corrupções reproduzíveis: avaliações em massa, push/nuke attack, IDs inválidos, duplicatas, valores fora da escala, ausência de campos, mudança de distribuição e indisponibilidade de dependências.
6. Criar métricas de qualidade dos dados e do recomendador:
   - volume e taxa de eventos;
   - nulidade, duplicidade, validade e integridade referencial;
   - distribuição de notas/tags e detecção de drift;
   - concentração de avaliações por usuário/item;
   - taxa de recomendações vazias, repetidas ou já consumidas;
   - métricas offline do ranking e, se possível, feedback online.
7. Comparar cenário sem observabilidade, com métricas, com logs e com tracing, medindo cobertura de detecção, tempo de detecção, tempo de diagnóstico e overhead.
8. Documentar protocolo, sementes, hardware, versões, datasets, hipóteses e critérios estatísticos.

### Prioridade 2 — completar observabilidade

1. **Métricas:** corrigir regras, criar dashboards versionados, SLOs/SLIs e alertas de aplicação, dados e recomendação.
2. **Logs:** usar logs estruturados, correlação por request/user/model version, completar Elasticsearch + Fluent Bit + Kibana e validar retenção/consulta.
3. **Tracing:** instrumentar FastAPI, chamadas ao banco e fluxo de recomendação com OpenTelemetry; exportar para Jaeger e correlacionar traces, métricas e logs.
4. Versionar configurações reproduzíveis de Helm, evitando comandos manuais sem estado declarado.
5. Adicionar health/readiness checks, recursos, HPA quando justificado e dashboards de custo/capacidade.
6. Provisionar TLS, DNS e gestão segura de segredos para uma implantação externa.

### Prioridade 3 — concluir os produtos acadêmicos

1. Executar e documentar a revisão sistemática com protocolo verificável.
2. Produzir tabela de trabalhos relacionados e lacunas encontradas.
3. Congelar a metodologia experimental antes dos testes finais.
4. Executar experimentos, armazenar resultados brutos e gerar gráficos/tabelas reproduzíveis.
5. Discutir ameaças à validade, limitações e implicações práticas.
6. Atualizar o README técnico e criar instruções completas de reprodução.
7. Redigir relatório final e artigo científico.

## 9. Sequência recomendada de execução

Uma ordem prática para reduzir retrabalho é:

1. **Estabilização local:** corrigir algoritmos e integração; adicionar testes e segurança mínima.
2. **Pipeline experimental:** implementar baselines, métricas e divisão dos dados; gerar resultados de referência sem observabilidade.
3. **Métricas de aplicação e dados:** instrumentar qualidade, latência e recursos; criar dashboards e alertas.
4. **Logs e tracing:** completar EFK/ELK e Jaeger/OpenTelemetry com correlação.
5. **Cenários de falha/ataque:** injetar problemas controlados e medir detecção, diagnóstico, qualidade e overhead.
6. **Implantação AWS reproduzível:** recriar o ambiente com segredos, persistência, TLS e manifests corrigidos.
7. **Análise e escrita:** consolidar tabelas, discutir resultados e finalizar relatório/artigo.

## 10. Verificações realizadas neste levantamento

| Verificação | Resultado |
|---|---|
| Leitura integral do anteprojeto | Concluída |
| Inspeção do código, manifests, README, Git e alterações locais | Concluída |
| Sintaxe de `main.py`, `recommender.py` e `db/db.py` | Aprovada por `py_compile` |
| Renderização de `k8s/app` com Kustomize | Aprovada; o Ingress da aplicação não faz parte do conjunto renderizado |
| Renderização de `k8s/monitoring` com Kustomize | Aprovada estruturalmente |
| Testes sintéticos dos recomendadores | Um fluxo executou com recomendação do próprio item; dois erros/erros de indexação foram confirmados |
| Suíte automatizada própria | Não existe no repositório |
| Build React | Não executado: Node/npm ausentes no ambiente atual |
| Execução ponta a ponta com PostgreSQL | Não comprovada neste levantamento |
| Estado AWS `us-east-1` | Sem EKS, ECR do projeto ou Load Balancer ativo, coerente com o teardown intencional para controle de custos |

## 11. Relação com o cronograma original

O cronograma do anteprojeto previa modelagem/protótipo entre agosto e novembro de 2025, testes entre novembro de 2025 e fevereiro de 2026, análise entre dezembro de 2025 e março de 2026 e escrita científica até maio de 2026.

Na data deste levantamento, o repositório evidencia avanço forte na modelagem do protótipo e início da infraestrutura de observabilidade, mas não comprova a conclusão das etapas de testes, análise de resultados e artigo. Assim, o cronograma deve ser replanejado a partir das prioridades acima, com entregáveis verificáveis para cada etapa.

## 12. Definição objetiva de conclusão do projeto

O projeto poderá ser considerado aderente ao anteprojeto quando houver, no mínimo:

- aplicação ponta a ponta funcional e testada;
- dois ou mais recomendadores corretos, incluindo os métodos escolhidos após a revisão;
- comparação reprodutível de qualidade e desempenho;
- métricas, logs e traces realmente integrados;
- monitoramento específico de qualidade dos dados e da recomendação;
- cenários controlados de dados falsos, ataques e falhas;
- evidência quantitativa de detecção/redução dos problemas;
- infraestrutura reproduzível e segura;
- relatório científico com metodologia, resultados, discussão e limitações.

Até esses critérios serem atendidos, a descrição mais precisa é: **protótipo de sistema de recomendação implementado, com observabilidade de métricas e implantação em nuvem em desenvolvimento, ainda sem validação experimental e científica completa**.
