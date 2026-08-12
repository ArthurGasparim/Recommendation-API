## Introdução e Justificativa

Os sistemas de recomendação influenciam a experiência dos usuários em e-commerce e mídias sociais. Entretanto, dados incorretos, falhas de comunicação e ações mal-intencionadas comprometem sua eficiência e confiabilidade. A observabilidade acompanha o comportamento da aplicação por meio de métricas, logs e rastreamento. Assim, o estudo contribui para a qualidade desses serviços e para o conhecimento acadêmico sobre a aplicação conjunta dessas técnicas.

## Objetivos

O projeto desenvolve um sistema funcional de recomendação de produtos com suporte de observabilidade. A aplicação utiliza técnicas baseadas em conteúdo e filtragem colaborativa, monitora seu funcionamento e analisa qualidade, consumo de recursos e tempo de execução. O estudo identifica como a observabilidade amplia a confiabilidade e o conhecimento sobre o recomendador.

## Material e Métodos

A pesquisa adota uma abordagem qualitativa e experimental, apoiada em revisão da literatura sobre recomendação e observabilidade. O protótipo utiliza Python, FastAPI, React, PostgreSQL, Docker, Kubernetes e computação em nuvem, com o conjunto Goodbooks como base experimental. Os métodos de recomendação são aplicados aos dados de livros, avaliações e preferências. Prometheus e Grafana apresentam métricas da aplicação. Testes funcionais e de desempenho analisam recomendações, disponibilidade, latência e consumo de recursos em ambiente controlado.

## Resultados

O trabalho apresenta uma aplicação web que cadastra usuários, livros, avaliações, tags e listas de leitura e produz recomendações por conteúdo e filtragem colaborativa. A aplicação processa a base Goodbooks e mantém validação, autenticação e atualização do modelo. A instrumentação fornece métricas de disponibilidade, requisições e latência, permitindo identificar falhas e alterações no sistema. Os resultados demonstram a viabilidade de integrar recomendação e observabilidade em ambiente reproduzível e preparado para execução em nuvem.

## Conclusões

Os resultados confirmam que a observabilidade amplia a visibilidade sobre o funcionamento do sistema de recomendação e auxilia a identificação de falhas, degradações e dados inadequados. A integração das técnicas torna o protótipo mais confiável, reproduzível e adequado à análise experimental, contribuindo para aplicações de e-commerce e para estudos posteriores na área.

## Órgão de fomento financiador da pesquisa

Não se aplica.
