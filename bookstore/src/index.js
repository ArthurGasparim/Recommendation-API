import React from 'react';
import ReactDOM from 'react-dom/client';
import Rotas from './Routes/routes';
import GlobalStyle from './styles/GlobalStyle';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <GlobalStyle/>
    <Rotas />
  </React.StrictMode>
);
