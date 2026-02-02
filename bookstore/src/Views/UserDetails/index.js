import * as Style from './style'
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import { useState } from 'react'
import api from "../../Services/service" 
function Usuario(){
    const [id, atualizaId] = useState();
    const [nome,atualizaNome] = useState();
    function createUser(){
        console.log("Ola")
        api.post("/createUser",{id:id,name:nome})
        .then((resp)=>{
            console.log(resp)
            alert(resp.data.alert); sessionStorage.setItem("newUserId", id);window.location.href = "http://localhost:3000/"}
        )
    }
    return(
        <div>
            <Header/>
            <Style.Container>
                <span>Id</span>
                <input type='text' placeholder="User's ID"
                        onChange={e=>atualizaId(e.target.value)} value={id}/>
                <span>Name</span>
                <input type='text' placeholder="User's Name"
                        onChange={e=>atualizaNome(e.target.value)} value={nome}/>
                <br></br>
                <button onClick={createUser}>Login</button>
            </Style.Container>
             
            <Footer/> 
        </div>
    )
}
export default Usuario