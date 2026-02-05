import * as Style from './style'
import React, {useState, useEffect} from 'react';
import Header from '../../Components/Header'
import Card from '../../Components/BookCard';
import Footer from '../../Components/Footer'
import api from '../../Services/service'
import { data, Link } from 'react-router-dom';
function Home(){
    const [Resposta, atualizaResposta] = useState([])
    const [id,atualizaId] = useState();
    const [RecomendIB,atualizaIB] = useState([])
    const [RecomendUB,atualizaUB] = useState([])
     function recommendacoesIB(){
        const idib = document.getElementById("idIB").value;
        api.get("/RecIB/"+idib).then(resp =>{
            console.log(resp.data)
            atualizaIB(resp.data)
        })

    }

    function recommendacoesUB(){
        const idub = document.getElementById("idUB").value;
        api.get("/RecUB/"+idub).then(resp =>{
            atualizaUB(resp.data)
        })

    }

    async function CarregaBoooks() {
    await api.get('/all')
    .then(resp=>{
        atualizaResposta(resp.data)
        console.log("Data"+resp.data)
        console.log("Resposta1"+Resposta)
    }
    )
    }

   

    useEffect(() => {
    api.get("/").then(resp=>{
         CarregaBoooks()
        console.log("Resposta:"+Resposta)
        const newUserId = sessionStorage.getItem("newUserId");
        if (newUserId) {
            atualizaId(newUserId)
        }
    })
   
  }, []);
    return(
        <div>
            <Header caminho={!id ? "usuario" : ""} admin={id==111}/>
            <p>Todos os Livros</p>
           
            <Style.ScrollBar>
                 
                {Resposta.map(c=>(
                <Link to={`/Book/${c.id}`}>
                <Style.Item>
                        <Card img ={c.image_url} title={c.title} author={c.authors} average_rating = {c.average_rating}/>
                    </Style.Item>
                 </Link>
                ))}
            </Style.ScrollBar>
                <p>Recomendações Item Based</p>
                <input id='idIB' type='number'></input>
                <button onClick={recommendacoesIB}>Pegar recomendações para o ID</button>
            <Style.ScrollBar>
                 
                {RecomendIB.map(c=>(
                <Link to={`/Book/${c.id}`}>
                <Style.Item>
                        <Card img ={c.image_url} title={c.title} author={c.authors} average_rating = {c.average_rating}/>
                    </Style.Item>
                 </Link>
                ))}
            </Style.ScrollBar>
            <p>Recomendações User Based</p>
            <input id='idUB' type='number'></input>
            <button onClick={recommendacoesUB}>Pegar recomendações para o ID</button>
            <Style.ScrollBar>
                 
                {RecomendUB.map(c=>(
                <Link to={`/Book/${c.id}`}>
                <Style.Item>
                        <Card img ={c.image_url} title={c.title} author={c.authors} average_rating = {c.average_rating}/>
                    </Style.Item>
                 </Link>
                ))}
            </Style.ScrollBar>
            <Footer/> 
        </div>
    )
}
export default Home