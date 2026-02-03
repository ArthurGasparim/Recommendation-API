import * as Style from './style'
import Header from '../../Components/Header'
import Footer from '../../Components/Footer'
import { useState } from 'react'
import api from "../../Services/service" 
function Books(){
    const [id, atualizaId] = useState();
    const [original_title,atualizaOriginalTitle] = useState();
    const [book_id,atualizaBookId] = useState()
    const [average_rating,atualizaRating]= useState()
    const [authors,atualizaAuthors] = useState()
    function createBook(){
        api.post("/createBook",{id:id,book_id:book_id,original_title:original_title,authors:authors,average_rating:average_rating})
        .then((resp)=>{
            console.log(resp)
            alert(resp.data.alert); sessionStorage.setItem("newUserId", id);window.location.href = "http://localhost:3000/"}
        )
    }
    return(
        <div>
            <Style.Container>
                <Header/>
                <span>Id</span>
                <input type='text' placeholder="Book's ID"
                        onChange={e=>atualizaId(e.target.value)} value={id}/>
                <span>GoodRead Id</span>
                <input type='text' placeholder="Book's GoodRead'sID"
                        onChange={e=>atualizaBookId(e.target.value)} value={book_id}/>
                <span>Title</span>
                <input type='text' placeholder="Book's Title"
                        onChange={e=>atualizaOriginalTitle(e.target.value)} value={ original_title}/>
                <span>Authors</span>
                <input type='text' placeholder="Book's Authors"
                        onChange={e=>atualizaAuthors(e.target.value)} value={authors}/>
                <span>Average Rating</span>
                <input type='text' placeholder="Book's Average Rating"
                        onChange={e=>atualizaRating(e.target.value)} value={average_rating}/>
                <br></br>
                <button onClick={createBook}>Login</button>
            </Style.Container>
            <Footer/>
        </div>
    )
}
export default Books