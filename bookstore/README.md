# Frontend BookMarket

Interface React do protótipo de recomendação.

## Desenvolvimento

```bash
npm ci
npm start
```

Com hostname `localhost`, `public/config.js` direciona as requisições para a API
em `http://127.0.0.1:5000`. O token retornado por `/createUser` é mantido no
`sessionStorage` e inserido automaticamente nas requisições Axios.

## Produção

```bash
docker build -t recommendation-frontend .
docker run --rm -p 8080:8080 recommendation-frontend
```

A imagem final usa Nginx não-root na porta 8080 e entrega as rotas React como
SPA. No EKS, API e frontend usam o mesmo ALB, portanto a URL da API é relativa.
