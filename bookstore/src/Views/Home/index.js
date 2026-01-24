import * as Style from './style'
import React, {useState, useEffect} from 'react';
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import api from '../../Services/service'
function Home(){
    const [Resposta, atualizaResposta] = useState("Ola")
    async function verificaAtrasadas() {
    await api.get('/')
    .then(resp=>{
        atualizaResposta(resp.data.message)
        console.log(resp.data.message)
    }
    )
    }
    return(
        <div>
            <Header caminho = "usuario"/>
            Home
            {Resposta}
            <button onClick={verificaAtrasadas}>Teste</button>
            <Footer/> 
        </div>
    )
}
export default Home