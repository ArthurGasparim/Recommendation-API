# Laboratório real de resiliência na AWS

## Objetivo entregue

Foi implementado um fluxo administrativo único para colocar o sistema no EKS,
manter os dados Goodbooks no PostgreSQL do cluster, executar ataques controlados
com ou sem resposta orientada por observabilidade e obter as métricas medidas no
próprio painel.

O ataque nunca é aplicado ao banco principal. A API copia o snapshot carregado,
separa uma coorte reprodutível de usuários, oculta um item relevante de cada
usuário, mede o baseline, aplica o ataque na cópia e mede novamente. A seed, o
modelo, a intensidade e o tamanho da coorte ficam registrados junto ao resultado.

## Fluxo do painel

1. **Carregar dados dos CSVs** inicia a importação assíncrona de `books.csv`,
   `ratings.csv`, `tags.csv`, `book_tags.csv` e `to_read.csv`. A gravação ocorre
   em uma transação; em caso de falha, o banco preserva o estado anterior.
2. **Executar ataque** permite escolher modelo, ataque, intensidade, seed,
   quantidade de usuários e a condição com ou sem observabilidade.
3. **Obter métricas** consulta a última medição concluída e a situação das
   execuções recentes. O progresso da tarefa atual aparece em tempo real.
4. **Testar todos e gerar XLSX** percorre os três modelos e os seis ataques,
   executando cada combinação sem e com observabilidade. São 18 comparações e
   36 cenários sequenciais, todos com a mesma seed, coorte, intensidade e top-k.
   Ao terminar, o navegador baixa a planilha automaticamente. O botão **Baixar
   último XLSX** permite recuperar novamente o relatório persistido.

As tarefas e seus resultados JSON são persistidos na tabela `admin_jobs`. Assim,
qualquer réplica da API pode consultar o resultado criado por outra réplica.

## Modelos e ataques reais disponíveis

Modelos:

- popularidade regularizada;
- recomendação por conteúdo com tags;
- filtragem colaborativa item-item com matriz esparsa.

Ataques:

- push e nuke por perfis artificiais;
- corrupção de domínio, integridade e unicidade;
- mudança controlada da distribuição das notas;
- degradação real de latência;
- falha controlada de dependência.

Com observabilidade ativa, os sinais do experimento acionam a resposta adequada:
rollback do lote, quarentena, circuit breaker ou fallback de popularidade. Sem
observabilidade, o cenário atacado é avaliado sem resposta automática. Prometheus
coleta os resultados e gera alertas, mas a resposta do experimento é executada
pela lógica controlada da aplicação, não pelo Prometheus.

## Métricas produzidas

Cada execução registra NDCG@K, Precision@K, Recall@K, hit rate, cobertura do
catálogo, latências p50/p95/p99, disponibilidade, falhas, qualidade dos dados,
tempo de detecção, tempo de recuperação e duração total. Também são expostas no
`/metrics` as séries de duração, NDCG, latência p95, qualidade dos dados, contagem
do dataset e estado das tarefas administrativas.

O resultado diferencia claramente `baseline`, `measured` e `deltas`. O método
registra que um item relevante, com nota mínima 4, é ocultado por usuário. Como o
Goodbooks não contém timestamps suficientes para uma divisão temporal fiel, essa
limitação permanece declarada no JSON.

A planilha da bateria possui quatro abas:

- **Qualidade**: NDCG, Precision, Recall, hit rate, cobertura e qualidade dos
  dados nas condições inicial, sem observabilidade e com observabilidade;
- **Operação**: latências, disponibilidade, falhas, detecção, resposta e tempos;
- **Dados**: score, registros inválidos, referências órfãs, duplicidade, nota
  média e volume nas condições inicial, sem observabilidade e com observabilidade;
- **Metodologia**: configuração, tamanho do snapshot e definições utilizadas.

O relatório é gerado em memória a partir do JSON salvo em `admin_jobs`. Portanto,
não depende do sistema de arquivos efêmero do pod e continua disponível após um
rollout ou recarregamento da página.

## Otimização da bateria completa

O índice livro × tag é construído uma vez como matriz esparsa e o Jaccard é
calculado vetorialmente. O recorte experimental, a coorte, as listas de leitura
e um baseline por modelo também são reutilizados durante os 36 cenários. Isso
remove a repetição anterior de percorrer 10.000 livros, recalcular o recorte e
reconstruir o mesmo baseline para cada ataque e modo.

O cenário sem observabilidade conserva o frame atacado bruto. Assim, o teste de
corrupção passa a medir efetivamente violações de domínio, referências órfãs e
duplicidades. Apenas o cenário com resposta aplicada restaura ou coloca em
quarentena o lote degradado.

## Segurança e operação

- Todos os endpoints de carga e experimento exigem token de administrador.
- Apenas uma carga ou experimento real pode ficar ativo por vez no cluster.
- O PostgreSQL usa PVC de 20 GiB e os manifests não contêm senhas.
- Cargas e resultados permanecem disponíveis entre réplicas da API.
- O Deployment usa rollout sem indisponibilidade e encerramento gracioso de cinco
  minutos para reduzir o risco de interromper tarefas em andamento.
- O `cleanup.sh` cria backup antes de remover o ambiente, salvo quando isso é
  desativado explicitamente, remove também os recursos periféricos cobrados e
  termina com uma auditoria independente.

## Implantação

```bash
export DEPLOY_ADMIN_USER_IDS="1"
export DEPLOY_POSTGRES_PASSWORD="defina-uma-senha-forte"
./scripts/deploy_aws.sh --create-cluster
```

O parâmetro `--create-cluster` é usado apenas quando o EKS não existe. Sem ele, o
script não cria infraestrutura cobrada. Em atualizações do servidor já ativo,
execute apenas `./scripts/deploy_aws.sh`.

Após o deploy, obtenha o endereço com:

```bash
kubectl -n dev get ingress app-ingress
```

Cadastre ou autentique o ID administrativo e abra `/simulacoes`. Para produzir
a matriz comparativa completa, mantenha a seed e os parâmetros desejados e use
**Testar todos e gerar XLSX**. Para uma inspeção rápida de apenas uma combinação,
continue usando **Executar ataque** e escolha manualmente o modo.

## Validação realizada

O fluxo completo foi exercitado em contêiner com os CSVs empacotados. A carga
resultou em 10.000 livros, 979.478 avaliações consolidadas, 34.252 tags, 999.904
relações livro-tag e 912.705 registros de leitura. Em seguida, o mesmo ataque
item-item foi executado sem e com observabilidade, gerando dois IDs persistidos e
recuperáveis pelo endpoint de métricas. Esses números validam a carga; não devem
ser tratados como resultado comparativo final, que depende das configurações e
repetições escolhidas para o protocolo científico.
