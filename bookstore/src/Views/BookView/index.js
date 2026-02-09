import { useEffect, useState } from "react"
import api from "../../Services/service"
import * as Style from "./style"
import { useParams } from "react-router-dom"
import Header from "../../Components/Header"
import Footer from "../../Components/Footer"

function BookPage(){
    const [book, updateBook] = useState({})
    const [rating, updateRating] = useState()
    const [tag, updateTag] = useState()
    const [read, updateRead] = useState(false)
    const {book_id} = useParams()
    const [id, updateId] = useState()

    function getBookData(){
        api.get("/getBook/"+book_id).then(resp =>{
            updateBook(resp.data)
        })
    }

    function submitRating(){
        if(rating){
            api.post("/rating",{book_id:book_id, user_id:id, rating:rating})
            .then(resp=>{alert("Rating cadastrada com sucesso")})
        }
    }

    function buyBook(){
        api.post("/buy",{book_id:book_id, id:id})
        window.location.href="http://localhost:3000/"
    }

    function addTag(){
         if(tag){
            api.post("/tag",{book_id:book_id, tag_name:tag})
            .then(resp=>{
                alert("Tag cadastrada com sucesso");
                updateTag("");
            })
        }
    }

    useEffect(()=>{
        getBookData()
        updateId(sessionStorage.getItem("newUserId"))
    },[])

    function controlRead(value){
        updateRead(value)
        api.post("/read",{book_id:book_id, value:value, id:id}).then()
    }

    return(
        <div style={{minHeight: "100vh", display: "flex", flexDirection: "column"}}>
            <Header/>
            <Style.Container>
                <Style.ContentWrapper>
                    <Style.ImageWrapper>
                         {/* Fallback image logic can be added here */}
                        <img src={book.image_url} alt={book.title}/>
                    </Style.ImageWrapper>
                    
                    <Style.Details>
                        <Style.Title>{book.title}</Style.Title>
                        <Style.Meta>
                            <p><strong>By:</strong> {book.authors}</p>
                            <div className="rating-badge">★ {book.average_rating}</div>
                        </Style.Meta>

                        <Style.ActionSection>
                            <Style.Card>
                                <h4>Avaliar Livro</h4>
                                <div className="input-row">
                                    <input 
                                        onChange={e=>{updateRating(e.target.value)}} 
                                        type="number" 
                                        name="rating" 
                                        min="1" max="5" 
                                        placeholder="1-5"
                                    />
                                    <button onClick={submitRating}>Enviar</button>
                                </div>
                            </Style.Card>

                            <Style.Card>
                                <h4>Adicionar Tag</h4>
                                <div className="input-row">
                                    <input 
                                        onChange={e=>{updateTag(e.target.value)}} 
                                        type="text" 
                                        value={tag || ''}
                                        placeholder="Nova Tag"
                                    />
                                    <button onClick={addTag}>Add</button>
                                </div>
                            </Style.Card>

                            <Style.Card>
                                <label className="checkbox-container">
                                    <input 
                                        onChange={e=>{controlRead(e.target.checked)}} 
                                        checked={read || false} 
                                        type="checkbox"
                                    />
                                    <span>Marcar como "Ler depois"</span>
                                </label>
                            </Style.Card>

                            <button className="buy-btn" onClick={buyBook}>Comprar Agora</button>
                        </Style.ActionSection>
                    </Style.Details>
                </Style.ContentWrapper>
            </Style.Container>
            <Footer/> 
        </div>
    )
}

export default BookPage