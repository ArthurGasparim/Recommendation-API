import * as Style from './style'
import React, {useState, useEffect} from 'react';
import Header from '../../Components/Header'
import Card from '../../Components/BookCard';
import Footer from '../../Components/Footer'
import api from '../../Services/service'
import { Link } from 'react-router-dom';

function Home(){
    const [Resposta, atualizaResposta] = useState([])
    const [id, atualizaId] = useState();
    const [RecomendIB, atualizaIB] = useState([])
    const [RecomendUB, atualizaUB] = useState([])

    function recommendacoesIB(){
        const idib = document.getElementById("idIB").value;
        api.get("/RecIB/"+idib).then(resp =>{
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
        await api.get('/all').then(resp=>{
            atualizaResposta(resp.data)
        })
    }

    useEffect(() => {
        api.get("/").then(resp=>{
            CarregaBoooks()
            const newUserId = sessionStorage.getItem("newUserId");
            if (newUserId) {
                atualizaId(newUserId)
            }
        })
    }, []);

    return(
        <div style={{minHeight: "100vh", display: "flex", flexDirection: "column"}}>
            <Header caminho={!id ? "usuario" : ""} admin={id==111}/>
            
            <Style.Container>
                <Style.Section>
                    <Style.SectionTitle>Todos os Livros</Style.SectionTitle>
                    <Style.ScrollBar>
                        {Resposta.map(c=>(
                            <Link to={`/Book/${c.id}`} key={c.id}>
                                <Card img={c.image_url} title={c.title} author={c.authors} average_rating={c.average_rating}/>
                            </Link>
                        ))}
                    </Style.ScrollBar>
                </Style.Section>

                <Style.Section>
                    <Style.SectionTitle>Recomendações Item Based</Style.SectionTitle>
                    <Style.InputGroup>
                        <input id='idIB' type='number' placeholder="ID do Livro" />
                        <button onClick={recommendacoesIB}>Buscar</button>
                    </Style.InputGroup>
                    
                    {RecomendIB.length > 0 && (
                        <Style.ScrollBar>
                            {RecomendIB.map(c=>(
                                <Link to={`/Book/${c.id}`} key={c.id}>
                                    <Card img={c.image_url} title={c.title} author={c.authors} average_rating={c.average_rating}/>
                                </Link>
                            ))}
                        </Style.ScrollBar>
                    )}
                </Style.Section>

                <Style.Section>
                    <Style.SectionTitle>Recomendações User Based</Style.SectionTitle>
                    <Style.InputGroup>
                        <input id='idUB' type='number' placeholder="ID do Usuário" />
                        <button onClick={recommendacoesUB}>Buscar</button>
                    </Style.InputGroup>
                    
                    {RecomendUB.length > 0 && (
                        <Style.ScrollBar>
                            {RecomendUB.map(c=>(
                                <Link to={`/Book/${c.id}`} key={c.id}>
                                    <Card img={c.image_url} title={c.title} author={c.authors} average_rating={c.average_rating}/>
                                </Link>
                            ))}
                        </Style.ScrollBar>
                    )}
                </Style.Section>
            </Style.Container>

            <Footer/> 
        </div>
    )
}
export default Home