import * as Style from './style'
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import { useState } from 'react'
import api from "../../Services/service" 

function Usuario(){
    const [id, atualizaId] = useState();
    const [nome, atualizaNome] = useState();

    function createUser(){
        api.post("/createUser",{id:id, name:nome})
        .then((resp)=>{
            alert(resp.data.alert); 
            sessionStorage.setItem("newUserId", id);
            window.location.href = "http://localhost:3000/home"
        })
    }

    return(
        <div style={{minHeight: "100vh", display: "flex", flexDirection: "column"}}>
            <Header/>
            <Style.Container>
                <Style.FormCard>
                    <h2>Login / Cadastro</h2>
                    <Style.InputGroup>
                        <label>ID do Usuário</label>
                        <input type='text' placeholder="Digite seu ID"
                            onChange={e=>atualizaId(e.target.value)} value={id}/>
                    </Style.InputGroup>
                    <Style.InputGroup>
                        <label>Nome</label>
                        <input type='text' placeholder="Digite seu nome"
                            onChange={e=>atualizaNome(e.target.value)} value={nome}/>
                    </Style.InputGroup>
                    <button onClick={createUser}>Entrar</button>
                </Style.FormCard>
            </Style.Container>
            <Footer/> 
        </div>
    )
}
export default Usuario