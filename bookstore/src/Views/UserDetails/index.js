import * as Style from './style'
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import { useState } from 'react'
import api from "../../Services/service" 

function Usuario(){
    const [id, atualizaId] = useState();
    const [nome, atualizaNome] = useState();
    const [senha, atualizaSenha] = useState("");
    const [erro, atualizaErro] = useState("");

    function createUser(){
        atualizaErro("")
        api.post("/createUser",{id:Number(id), name:nome, password:senha})
        .then((resp)=>{
            alert(resp.data.alert); 
            sessionStorage.setItem("newUserId", id);
            sessionStorage.setItem("accessToken", resp.data.access_token);
            sessionStorage.setItem("isAdmin", String(resp.data.is_admin));
            window.location.href = "/home"
        })
        .catch((error)=>{
            atualizaErro(error.response?.data?.detail || "Não foi possível autenticar")
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
                    <Style.InputGroup>
                        <label>Senha</label>
                        <input type='password' placeholder="Mínimo de 8 caracteres"
                            minLength="8" onChange={e=>atualizaSenha(e.target.value)} value={senha}/>
                    </Style.InputGroup>
                    {erro && <p role="alert">{erro}</p>}
                    <button disabled={!id || !nome || senha.length < 8} onClick={createUser}>Entrar</button>
                </Style.FormCard>
            </Style.Container>
            <Footer/> 
        </div>
    )
}
export default Usuario
