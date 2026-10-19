# Roteiro da apresentação final

**Título:** Monitoramento de Qualidade dos Dados para Personalização de Recomendação de Produtos  
**Duração estimada:** aproximadamente 12 minutos  
**Apresentador:** Arthur Guarizi Gasparim  
**Orientador:** Prof. Dr. Mário Augusto Pazoti

## Sequência e tempo sugerido

| Slide | Seção | Assunto | Tempo |
|---:|---|---|---:|
| 1 | Abertura | Título e identificação | 0:15 |
| 2 | Introdução | Problema e motivação | 0:30 |
| 3 | Introdução | Objetivo e pergunta de pesquisa | 0:30 |
| 4 | Observabilidade | Métricas, logs, tracing e resposta | 0:35 |
| 5 | Métricas | Definições usadas na avaliação | 0:35 |
| 6 | Recomendação | Três modelos realmente executados | 0:35 |
| 7 | Implementação | Dados e pipeline | 0:25 |
| 8 | Implementação | Arquitetura técnica | 0:25 |
| 9 | Implementação | Sistema web funcional | 0:20 |
| 10 | Implementação | Testes e reprodutibilidade | 0:25 |
| 11 | Metodologia | Bateria pareada e medida | 0:35 |
| 12 | Metodologia | Mapa dos seis ataques | 0:35 |
| 13 | Resultados | Push attack por modelo | 0:40 |
| 14 | Resultados | Nuke attack por modelo | 0:40 |
| 15 | Resultados | Corrupção de dados por modelo | 0:45 |
| 16 | Resultados | Drift de distribuição por modelo | 0:45 |
| 17 | Resultados | Degradação de latência por modelo | 0:45 |
| 18 | Resultados | Indisponibilidade e fallback por modelo | 0:50 |
| 19 | Resultados | Síntese da qualidade de recomendação | 0:35 |
| 20 | Discussão | Onde a observabilidade ajudou | 0:35 |
| 21 | Conclusão | Entregas e próximos refinamentos | 0:35 |
| 22 | Encerramento | Agradecimento | 0:10 |

**Total aproximado:** 12 minutos. Para chegar a 10 minutos, apresente os
slides 7 a 10 como um único bloco de implementação e resuma push e nuke como
duas variações do mesmo ataque coordenado.

## Números que devem ser destacados

- A bateria usa **3 modelos**, **6 ataques**, **18 comparações** e **36
  execuções**, concluídas em **102,4 segundos**.
- O experimento mantém seed 42, intensidade de 30%, 100 usuários e Top-10,
  sem alterar o banco principal.
- Na corrupção, o score de qualidade cai de **1,000 para 0,471** e retorna a
  **1,000** após a quarentena. O NDCG de conteúdo cai **9,5%** e é restaurado.
- No drift, a nota média muda de **3,822 para 4,182**. O conteúdo perde **19,9%**
  de NDCG e o item-item perde **100%**; ambos retornam ao valor inicial.
- Na latência, o p95 médio muda de **35,81 ms para 88,54 ms** e recua para
  **78,31 ms** com resposta observável: melhora parcial, não recuperação total.
- Na indisponibilidade, a disponibilidade muda de **100% para 41%** e retorna a
  **99%**. As falhas agregadas caem de **177 para 3**, redução de **98,3%**.

## Mensagem principal

A observabilidade torna a degradação mensurável e orienta a resposta. Seu efeito
depende do problema: recupera completamente corrupção e drift, reduz parcialmente
a latência e recupera a disponibilidade durante uma falha. No último caso, o
fallback mantém o serviço ativo, mas não preserva a relevância personalizada.

## Cuidados durante a apresentação

- Não afirme que todo ataque precisa reduzir NDCG. Latência afeta operação;
  push e nuke exigem métricas específicas de exposição e posição do item-alvo.
- Explique que NDCG valoriza acertos nas primeiras posições, enquanto p95 mede a
  cauda de latência e o score de dados mede domínio, integridade e unicidade.
- Ao falar de indisponibilidade, destaque o trade-off entre disponibilidade e
  relevância: o fallback foi operacionalmente eficaz, mas perdeu personalização.
- Os números dos slides são medições da planilha exportada em 19/10/2026, e não
  valores ilustrativos.
- As notas do apresentador também estão incluídas dentro do PowerPoint.
