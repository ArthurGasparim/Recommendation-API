# Planejamento da Prioridade 1 — Núcleo científico e experimental

**Prazo:** 1 a 2 meses  
**Pergunta de pesquisa:** Como a observabilidade e o monitoramento da qualidade dos dados auxiliam na detecção de falhas e preservam a qualidade de sistemas de recomendação?

> **Estado da execução:** o simulador exploratório e o dashboard temporal foram
> implementados como primeira entrega. Eles validam cenários, comparação e
> visualização, mas ainda usam perfis sintéticos explicitamente identificados.
> A substituição desses perfis por medições do pipeline real permanece nas etapas
> de treinamento e experimentação deste plano.

## 1. Decisões definidas

- A base experimental inicial permanece sendo o Goodbooks.
- Como o Goodbooks não fornece timestamps das avaliações, a avaliação utiliza divisão estratificada por usuário, com sementes fixas e separação entre treino, validação e teste.
- São implementados e comparados: popularidade, recomendação por conteúdo, filtragem colaborativa item-item, ALS e modelo híbrido.
- FP-Growth fica para uma etapa posterior, pois a base atual não contém transações de carrinho ou compra em conjunto.
- `NDCG@10` é a métrica principal de qualidade do ranking.
- Os testes incluem o cenário íntegro e cenários controlados de avaliações falsas, dados inválidos/duplicados, drift e degradação da infraestrutura.
- Todos os experimentos possuem uma versão local reproduzível.
- A AWS/EKS é utilizada em ciclos curtos para confirmar o comportamento em nuvem e controlar custos.

## 2. Objetivo da implementação

Construir um ambiente experimental reproduzível que permita:

1. treinar e comparar diferentes modelos de recomendação;
2. medir qualidade do ranking, cobertura, diversidade, novidade e desempenho;
3. injetar falhas, ataques e corrupções de dados de maneira controlada;
4. verificar quais sinais de observabilidade detectam cada problema;
5. medir tempo de detecção, diagnóstico e recuperação;
6. calcular o overhead introduzido por métricas, logs e tracing;
7. reproduzir localmente os experimentos executados na nuvem.

## 3. Recomendadores a implementar

### 3.1 Popularidade

Ranking não personalizado baseado em quantidade de avaliações e nota média, com regularização para impedir que poucos votos produzam posições artificiais. Ele funciona como baseline mínimo: os modelos personalizados precisam justificar sua complexidade apresentando resultados superiores ou outras vantagens mensuráveis.

### 3.2 Conteúdo com TF-IDF

Tags, autores e demais atributos disponíveis são transformados em vetores TF-IDF. A similaridade de cosseno encontra itens com características próximas e o perfil do usuário é construído a partir dos livros avaliados. Livros já consumidos são excluídos e usuários sem histórico recebem fallback por popularidade.

### 3.3 Filtragem colaborativa item-item

A matriz esparsa usuário-item representa as avaliações. A similaridade entre os itens e as notas fornecidas pelo usuário formam o ranking. Treinamento, persistência e inferência ficam separados para evitar a reconstrução do modelo a cada requisição.

### 3.4 ALS

A fatoração matricial ALS cria representações latentes de usuários e itens. São avaliados número de fatores, regularização, iterações e confiança. Hiperparâmetros são selecionados somente na validação; o teste final permanece isolado.

### 3.5 Modelo híbrido

Os escores de conteúdo e do modelo colaborativo são normalizados e combinados por pesos explícitos. Os pesos são selecionados na validação e registrados em cada execução. Em cold start, o modelo utiliza conteúdo e, na ausência de atributos e histórico, popularidade.

## 4. Pipeline experimental

O pipeline é independente da API e executa as seguintes etapas:

1. validar tipos, domínios, chaves e integridade dos CSVs;
2. consolidar duplicatas conforme regras documentadas;
3. criar divisões estratificadas de treino, validação e teste por usuário;
4. treinar cada modelo com a mesma divisão de dados;
5. gerar rankings para `K = 5, 10 e 20`;
6. calcular todas as métricas definidas neste documento;
7. repetir experimentos com sementes fixas;
8. salvar média, dispersão, configuração, versões, duração e hardware;
9. produzir tabelas e gráficos diretamente dos resultados brutos.

Estrutura planejada:

```text
experiments/
├── configs/
├── datasets/
├── scenarios/
├── results/
├── run_experiment.py
├── evaluate.py
└── report.py
```

Resultados tabulares são armazenados em CSV ou Parquet. Configurações e metadados são registrados em JSON ou YAML. Nenhum valor de gráfico ou tabela é editado manualmente.

## 5. Como a observabilidade se relaciona com as métricas

A observabilidade não aumenta diretamente a precisão matemática de um recomendador. Ela evidencia problemas de dados, modelo e infraestrutura. A melhoria ou recuperação ocorre quando o sinal observado aciona validação, bloqueio de dados, limitação de abuso, retreinamento, ajuste ou rollback.

```text
problema → sinal → alerta → diagnóstico → ação corretiva → recuperação
```

### 5.1 Métricas de qualidade do ranking

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **Precision@K** | Proporção dos `K` itens recomendados que são relevantes: `relevantes recuperados / K`. Mede quanto da lista é útil. | Acompanha quedas por modelo, versão e segmento, relacionando-as com alterações nos dados e permitindo retreinamento ou rollback. |
| **Recall@K** | Proporção dos itens relevantes do usuário recuperados entre os `K`: `relevantes recuperados / total de relevantes`. | Detecta perda de recuperação causada por falha de ingestão, redução de cobertura ou drift. |
| **NDCG@K** | Avalia relevância e posição. Itens relevantes nas primeiras posições recebem maior peso: `NDCG = DCG / DCG ideal`. Varia entre 0 e 1. | Revela degradação do ranking mesmo quando a API continua respondendo normalmente. É a métrica principal em `K = 10`. |
| **MAP@K** | Calcula a precisão em cada posição relevante e depois a média entre usuários. Recompensa vários acertos posicionados cedo. | Mostra degradações graduais e permite comparar versões, grupos de usuários e cenários de ataque. |
| **Hit Rate@K** | Percentual de usuários que recebe pelo menos um item relevante entre os primeiros `K`. | Evidencia usuários sem qualquer recomendação útil e relaciona o problema a cold start ou ausência de atributos. |
| **MRR@K** | Média do inverso da posição do primeiro item relevante: `1 / posição`. | Detecta quando o primeiro resultado útil passa a aparecer mais abaixo na lista. |

`NDCG@10` é a medida principal. Precision, Recall, MAP, Hit Rate e MRR oferecem interpretações complementares e evitam concluir a partir de uma única característica do ranking.

### 5.2 Métricas de predição de nota

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **MAE** | Média de `|nota prevista - nota real|`. Mantém a unidade da escala e é simples de interpretar. | Um aumento persistente indica envelhecimento, corrupção ou mudança do comportamento e pode acionar reavaliação. |
| **RMSE** | Raiz da média dos erros quadráticos. Penaliza erros grandes com maior intensidade. | Destaca o surgimento de previsões muito incorretas e ajuda a localizar usuários ou itens afetados. |

MAE e RMSE são usados somente nos modelos que predizem notas. Um erro pequeno de nota não garante um bom ranking Top-K, portanto eles não substituem NDCG, Precision e Recall.

### 5.3 Métricas além da acurácia

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **Cobertura de catálogo** | `itens distintos recomendados / itens recomendáveis`. Mede quanto do catálogo aparece nas listas. | Detecta concentração anormal em poucos livros após implantação, falha ou ataque. |
| **Cobertura de usuários** | `usuários com lista válida / usuários consultados`. | Contadores de listas vazias revelam cold start não tratado ou inferência indisponível. |
| **Diversidade intra-lista** | Média de `1 - similaridade` entre os itens da mesma lista. | Identifica perda de variedade causada por tags ausentes, drift ou concentração artificial. |
| **Novidade** | Utiliza a autoinformação do item: `-log2(probabilidade de interação)`. Itens menos populares recebem maior valor. | Detecta colapso para itens populares ou promoção artificial, sempre analisada junto com relevância. |
| **Personalização** | Mede a diferença entre listas de usuários distintos, por exemplo com dissimilaridade de Jaccard. | Revela quando todos passam a receber a mesma lista por falha de perfil, cache ou modelo. |

### 5.4 Métricas de qualidade dos dados

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **Taxa de nulidade** | `registros com campo obrigatório nulo / registros recebidos`. | Alerta sobre cargas incompletas antes que atributos ou recomendações sejam degradados. |
| **Taxa de invalidade** | `registros fora do domínio / registros recebidos`, incluindo notas fora de 1 a 5 e IDs inválidos. | Permite rejeitar ou colocar lotes em quarentena e localizar a fonte defeituosa. |
| **Taxa de duplicidade** | `registros com chave repetida / registros recebidos`. | Impede que repetições distorçam popularidade, preferências e treinamento. |
| **Integridade referencial** | `relações com usuário ou item inexistente / relações avaliadas`. | Detecta referências órfãs antes de criar o modelo. |
| **Volume/taxa de eventos** | Registros por lote e eventos por segundo. | Alterações abruptas revelam falha de coleta, repetição de carga ou ataque em massa. |
| **Drift** | Compara distribuições atuais e de referência usando PSI ou divergência de Jensen-Shannon. | Mostra mudanças nas notas, tags e popularidade antes que a degradação se espalhe. |

### 5.5 Métricas do comportamento do recomendador

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **Listas vazias** | `requisições sem recomendação / requisições de recomendação`. | Detecta dados insuficientes, cold start sem fallback e erros silenciosos. |
| **Itens já consumidos** | `itens recomendados já avaliados ou lidos / itens recomendados`. | Um aumento indica falha de filtro ou perfil desatualizado. |
| **Duplicatas na lista** | `posições repetidas / posições retornadas`. O esperado é zero. | Evidencia regressão na composição ou na fusão do modelo híbrido. |
| **Itens inválidos** | `itens inexistentes ou indisponíveis / itens recomendados`. | Revela dessincronização entre catálogo, modelo e banco. |
| **Concentração** | Participação dos itens mais recomendados, Gini ou entropia. | Ajuda a detectar popularidade excessiva, push attack e colapso do ranking. |

### 5.6 Métricas de desempenho e recursos

| Métrica | Como funciona | Contribuição da observabilidade |
|---|---|---|
| **Tempo de treinamento** | Duração total e por etapa de preparação e treinamento. | Relaciona duração com volume, configuração, CPU e memória. |
| **Latência de inferência** | Percentis `p50`, `p95` e `p99`; a média não é suficiente. | Histogramas e traces localizam requisições lentas e a etapa responsável. |
| **Throughput** | Recomendações concluídas por segundo. | Em conjunto com latência e erros, identifica saturação. |
| **Taxa de erros** | `requisições com falha / total de requisições`, separada por endpoint e versão. | Detecta regressões e indisponibilidade. |
| **CPU e memória** | Consumo médio, sustentado e pico durante treino e inferência. | Evita saturação e falhas por falta de memória e permite comparar modelos. |
| **Tamanho do modelo** | Memória e armazenamento ocupados pelo artefato. | Estima custo de carga, armazenamento e manutenção de versões para rollback. |
| **Disponibilidade** | `tempo atendendo corretamente / tempo observado`. | Probes e testes sintéticos distinguem processo ativo de serviço utilizável. |

### 5.7 Métricas da eficácia da observabilidade

| Métrica | Como funciona | Finalidade |
|---|---|---|
| **Taxa de detecção** | `cenários injetados detectados / cenários injetados`. | Mede diretamente a cobertura do monitoramento. |
| **Precisão dos alertas** | `alertas verdadeiros / todos os alertas`. | Evita considerar bom um sistema que gera ruído excessivo. |
| **Recall dos alertas** | `problemas detectados / problemas injetados`. | Mede quantos problemas reais não passam despercebidos. |
| **MTTD** | Tempo médio entre o início do problema e a detecção. | Mede a velocidade de percepção. |
| **Tempo de diagnóstico** | Tempo entre detectar e identificar corretamente a causa. | Compara a contribuição de métricas, logs e traces. |
| **MTTR** | Tempo entre o início do problema e a restauração do estado saudável. | Resume detecção, diagnóstico e ação corretiva. |
| **Falsos positivos/negativos** | Alerta sem problema ou problema sem alerta. | Os cenários controlados fornecem o gabarito para calcular ambos. |

### 5.8 Overhead da observabilidade

O custo de cada configuração é calculado em relação ao baseline:

```text
overhead (%) = (valor instrumentado - valor baseline) / valor baseline × 100
```

São medidos aumento de latência, redução de throughput, CPU, memória, armazenamento, tráfego e custo no EKS. O stack é adequado quando melhora a capacidade e a velocidade de detecção com overhead conhecido e aceitável para o ambiente experimental.

## 6. Casos de teste

### 6.1 Funcionais e algorítmicos

- usuário e item conhecidos;
- usuário novo, item novo e ausência de histórico;
- usuário com uma única interação;
- itens sem tags ou com atributos incompletos;
- exclusão de itens já consumidos;
- IDs reais preservados no ranking;
- ranking sem duplicatas ou itens inexistentes;
- mesma semente produzindo o mesmo resultado;
- API, modelo persistido e pipeline retornando resultados consistentes;
- divisão de dados sem vazamento entre treino, validação e teste.

### 6.2 Ataques, corrupção e falhas

Os cenários são executados inicialmente nas intensidades de 1%, 5% e 10%, ajustadas após observar o baseline:

- **push attack:** usuários artificiais promovem um livro-alvo;
- **nuke attack:** usuários artificiais prejudicam um livro-alvo;
- **dados inválidos:** notas fora da escala, IDs inexistentes e campos ausentes;
- **duplicidade:** repetição de avaliações e relações livro-tag;
- **drift:** alteração controlada na distribuição de notas, tags ou popularidade;
- **degradação:** banco lento, falha temporária e aumento de latência.

Cada cenário registra estado inicial, injeção, resultado esperado, sinal observável, alerta correspondente e recuperação.

## 7. Stack de observabilidade local

O stack pode funcionar localmente. A implementação utiliza perfis para evitar o consumo simultâneo de todas as ferramentas.

### 7.1 Perfil rápido com Docker Compose

Inclui:

- API, frontend e PostgreSQL;
- Prometheus;
- Grafana;
- Alertmanager.

Esse perfil atende ao desenvolvimento diário, testes automatizados e experimentos de métricas.

### 7.2 Perfil de logging

Inclui logs JSON da FastAPI, Fluent Bit, Elasticsearch e Kibana. Os logs recebem `request_id`, versão do modelo, revisão do dataset e resultado, sem armazenar senha, token ou identificador pessoal direto.

### 7.3 Perfil de tracing

Inclui OpenTelemetry Collector e Jaeger. São instrumentadas requisições HTTP, consultas ao banco, preparação de atributos e inferência do recomendador.

### 7.4 Perfil completo

Executa métricas, logs e traces juntos para os testes finais, condicionado à memória disponível na máquina. Os perfis isolados permitem trabalhar com menor consumo.

## 8. Paridade local, Kubernetes e AWS

São mantidos três níveis:

1. **Docker Compose:** ciclo rápido e menor custo para desenvolvimento;
2. **kind:** cluster Kubernetes local para validar manifests e Helm charts;
3. **EKS:** ciclos curtos para validar ALB, persistência EBS, escalabilidade e custos reais.

Dashboards, regras, datasources e configurações ficam versionados e reutilizados entre os ambientes sempre que a ferramenta permitir.

O mesmo experimento é executado em quatro configurações:

1. sem coleta adicional;
2. somente métricas;
3. métricas e logs;
4. métricas, logs e tracing.

Isso permite comparar detecção, diagnóstico e overhead de cada pilar.

## 9. Instrumentação planejada

- métricas de qualidade dos dados por lote e janela;
- métricas offline por modelo, versão e cenário;
- contadores de listas vazias, duplicadas, inválidas e já consumidas;
- histogramas de latência de API, banco e inferência;
- duração, CPU e memória de treinamento;
- versão do modelo, dataset, divisão, semente e configuração;
- logs estruturados com correlação;
- spans de API, banco, atributos e inferência;
- dashboards de qualidade, aplicação e infraestrutura;
- alertas definidos a partir da variabilidade normal do baseline.

## 10. Protocolo de análise

1. executar o baseline íntegro;
2. executar as mesmas divisões e sementes em todos os modelos;
3. medir o cenário sem instrumentação adicional;
4. repetir com métricas, logs e tracing;
5. aplicar as mesmas corrupções e intensidades;
6. comparar qualidade, detecção, diagnóstico e overhead;
7. apresentar média, dispersão e quantidade de repetições;
8. não ajustar modelos ou alertas usando o teste final;
9. conservar dados brutos e configuração de cada execução.

O melhor modelo não é escolhido por uma única medida. A decisão considera qualidade do ranking, cobertura, diversidade, novidade, custo computacional, resistência às corrupções e capacidade de diagnóstico.

## 11. Entregáveis

- cinco métodos de recomendação implementados;
- pipeline reproduzível de treino, avaliação e relatório;
- testes unitários, de integração e de cenários controlados;
- stack local com perfis de métricas, logs e tracing;
- dashboards e alertas versionados;
- resultados brutos e tabelas comparativas;
- roteiro de reprodução local e no EKS;
- documentação de metodologia, resultados, limitações e ameaças à validade.

## 12. Cronograma de oito semanas

| Semana | Entrega |
|---|---|
| 1 | Protocolo, validação dos dados, divisões e baseline de popularidade |
| 2 | Conteúdo TF-IDF e filtragem colaborativa item-item |
| 3 | ALS, modelo híbrido e seleção na validação |
| 4 | Pipeline de métricas e ampliação dos testes |
| 5 | Stack local, dashboards, alertas, logs e tracing |
| 6 | Injeção de ataques/corrupções e experimentos locais |
| 7 | Repetições, análise e ciclo curto no EKS |
| 8 | Consolidação dos resultados e redação acadêmica |

Se o prazo efetivo se aproximar de quatro semanas, o núcleo mínimo mantém popularidade, conteúdo, item-item, ALS, híbrido, métricas de ranking, Prometheus/Grafana e três cenários de corrupção. A comparação completa de logging, tracing e EKS segue imediatamente depois, sem alterar o protocolo já definido.

## 13. Critério de conclusão

A Prioridade 1 é considerada concluída quando outra pessoa consegue, apenas com a documentação:

1. reproduzir a divisão dos dados;
2. treinar os cinco modelos;
3. executar os cenários controlados;
4. obter as mesmas métricas dentro da variação registrada;
5. relacionar cada alerta ao problema injetado;
6. repetir o fluxo localmente e em pelo menos um ciclo controlado no EKS.
