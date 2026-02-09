import * as Style from './style' // This should point to the file below
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import { useState } from 'react'
import api from "../../Services/service" 

function Books(){
    const [id, atualizaId] = useState();
    const [original_title, atualizaOriginalTitle] = useState();
    const [book_id, atualizaBookId] = useState()
    const [average_rating, atualizaRating]= useState()
    const [authors, atualizaAuthors] = useState()

    function createBook(){
        api.post("/createBook",{id:id, book_id:book_id, original_title:original_title, authors:authors, average_rating:average_rating})
        .then((resp)=>{
            alert(resp.data.alert); 
            sessionStorage.setItem("newUserId", id);
            window.location.href = "http://localhost:3000/"
        })
    }

    return(
        <div style={{minHeight: "100vh", display: "flex", flexDirection: "column"}}>
            <Header/>
            <Style.Container>
                <Style.FormCard>
                    <h2>Cadastrar Livro</h2>
                    
                    <Style.InputGroup>
                        <label>Id</label>
                        <input type='text' placeholder="Database ID"
                            onChange={e=>atualizaId(e.target.value)} value={id}/>
                    </Style.InputGroup>

                    <Style.InputGroup>
                        <label>GoodRead Id</label>
                        <input type='text' placeholder="External ID"
                            onChange={e=>atualizaBookId(e.target.value)} value={book_id}/>
                    </Style.InputGroup>

                    <Style.InputGroup>
                        <label>Title</label>
                        <input type='text' placeholder="Book Title"
                            onChange={e=>atualizaOriginalTitle(e.target.value)} value={original_title}/>
                    </Style.InputGroup>

                    <Style.InputGroup>
                        <label>Authors</label>
                        <input type='text' placeholder="Author Names"
                            onChange={e=>atualizaAuthors(e.target.value)} value={authors}/>
                    </Style.InputGroup>

                    <Style.InputGroup>
                        <label>Average Rating</label>
                        <input type='text' placeholder="e.g., 4.5"
                            onChange={e=>atualizaRating(e.target.value)} value={average_rating}/>
                    </Style.InputGroup>

                    <button onClick={createBook}>Cadastrar</button>
                </Style.FormCard>
            </Style.Container>
            <Footer/>
        </div>
    )
}
export default Books