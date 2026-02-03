import * as Style from './style'
import React, {useState, useEffect} from 'react';
import Header from '../../Components/Header'
import Card from '../../Components/BookCard';
import Footer from '../../Components/Footer'
import api from '../../Services/service'
import { Link } from 'react-router-dom';
function Home(){
    const [Resposta, atualizaResposta] = useState([])
    const [id,atualizaId] = useState();
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
    CarregaBoooks()
    console.log("Resposta:"+Resposta)
    const newUserId = sessionStorage.getItem("newUserId");
    if (newUserId) {
        atualizaId(newUserId)
    }
  }, []);
    useEffect(() => {
    console.log("Agora o estado atualizou:", Resposta);
}, [Resposta]);
    return(
        <div>
            <Header caminho={!id ? "usuario" : ""} admin={id==111}/>
            <p>Todos os Livros</p>
           
            <Style.ScrollBar>
                 
                {Resposta.map(c=>(
                <Link to={`/Book/${c.id}`}>
                <Style.Item>
                        <Card title={c.original_title} author={c.authors} average_rating = {c.average_rating}/>
                    </Style.Item>
                 </Link>
                ))}
            </Style.ScrollBar>
           
            <p>Recomendações Item Based</p>
            <p>Recomendações User Based</p>
            <Footer/> 
        </div>
    )
}
export default Home