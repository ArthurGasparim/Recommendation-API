# Prioridade 1 — Simulador e visualização implementados

**Data:** 11 de agosto de 2026  
**Escopo:** primeira entrega do núcleo experimental da Prioridade 1

## Resultado

Foi implementado um laboratório visual para programar diferentes ataques em
momentos específicos, comparar cinco perfis de recomendadores e observar as
métricas sem defesa e com resposta orientada por observabilidade.

Esta entrega é uma **simulação exploratória**, não um resultado científico. Os
valores são sintéticos, determinísticos e declarados como tal no backend e no
frontend. Eles permitem validar o desenho dos experimentos antes da integração
dos modelos e baselines medidos.

## Modelos representados

- popularidade;
- conteúdo TF-IDF;
- filtragem colaborativa item-item;
- ALS;
- híbrido.

Cada perfil possui baseline, custo de inferência e suscetibilidade diferente por
ataque. Esses valores ficam centralizados em `experiments/simulator.py` para que
sejam posteriormente substituídos pelos resultados do pipeline real.

## Ataques configuráveis

- push attack;
- nuke attack;
- corrupção/duplicidade de dados;
- drift de distribuição;
- degradação de latência;
- indisponibilidade de dependência.

Cada ataque possui início, duração e intensidade. Ataques podem ocorrer
simultaneamente. O motor calcula início, detecção, mitigação progressiva,
encerramento e recuperação.

## Métricas temporais

- NDCG@10;
- Precision@10;
- Recall@10;
- cobertura do catálogo;
- latência p95;
- disponibilidade;
- qualidade dos dados.

O resumo também calcula perda acumulada de qualidade, tempo abaixo do SLO,
redução da perda, quantidade de detecções, MTTD e overhead de instrumentação.

## Visualização

A rota `/simulacoes`, exclusiva para administradores, possui:

- presets de campanhas coordenadas, dados/drift e infraestrutura;
- seleção simultânea dos modelos;
- editor de ataques com início, duração e intensidade;
- linha do tempo com ataques sobrepostos;
- gráfico SVG responsivo sem dependência externa de gráficos;
- faixas de ataque e marcadores de detecção;
- comparação clara entre sem defesa e resposta observável;
- troca de métrica e modelo em foco;
- cartões de indicadores;
- barras de redução da perda acumulada;
- tabela comparativa de todos os modelos;
- sequência dos eventos observados;
- aviso permanente de que os valores são sintéticos.

O foco individual evita sobrepor dez curvas no mesmo gráfico. A comparação
global permanece disponível nos cartões e na tabela.

## API

Foram adicionados:

- `GET /admin/experiments/catalog`: catálogo de modelos, ataques, métricas e
  configuração inicial;
- `POST /admin/experiments/simulate`: execução determinística e sem alteração do
  banco.

Os dois endpoints exigem token administrativo. A rota `/admin` já está coberta
pelo Ingress existente.

## Garantias do motor

- mesma configuração e semente produzem resposta idêntica;
- antes da detecção, a qualidade é igual nas duas condições;
- a instrumentação não aumenta artificialmente a qualidade;
- após a detecção, a resposta reduz progressivamente o impacto;
- a instrumentação introduz overhead explícito de latência;
- múltiplos ataques são combinados com limites físicos das métricas;
- configurações inválidas e ataques fora da janela são rejeitados.

## Testes executados

Backend:

```text
15 passed
```

Os testes cobrem catálogo, validação, determinismo, momento da detecção, redução
da perda acumulada, baseline sem ataques e autorização administrativa da API.

Frontend:

```text
2 passed
Compiled successfully
```

Os testes cobrem bloqueio para usuário não administrativo, carregamento do
cenário, aviso científico, renderização do gráfico e nova execução. O build de
produção React/Nginx foi aprovado.

Também foi executado smoke test dos containers locais com cinco modelos, seis
tipos de ataque, sete métricas, dez séries comparativas e eventos temporais.

## Como testar

1. subir API e frontend conforme o README;
2. entrar com um usuário listado em `ADMIN_USER_IDS`;
3. abrir o item **Laboratório** ou `http://localhost:3000/simulacoes`;
4. escolher um preset ou adicionar ataques manualmente;
5. selecionar os modelos;
6. executar a comparação;
7. alternar métrica e modelo no gráfico;
8. conferir perda acumulada, SLO, detecção e eventos.

## Próximas integrações científicas

Esta entrega não encerra a Prioridade 1. Permanecem:

1. implementar e avaliar os cinco modelos reais;
2. produzir divisões reproduzíveis do Goodbooks;
3. calcular baselines medidos com repetições;
4. fazer o simulador consumir resultados do pipeline em vez dos perfis
   sintéticos;
5. executar ataques sobre cópias controladas dos dados;
6. conectar Prometheus, logs e tracing locais aos cenários;
7. repetir o protocolo em um ciclo curto no EKS;
8. gerar tabelas e conclusões científicas somente a partir das medições reais.
