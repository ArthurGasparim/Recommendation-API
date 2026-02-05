import { useEffect, useState } from "react"
import api from "../../Services/service"
import * as Style from "./style"
import { useParams } from "react-router-dom"
import Header from "../../Components/Header"
import Footer from "../../Components/Footer"

function BookPage(){
    const [book,updateBook] = useState({})
    const[rating,updateRating] = useState()
    const [tag,updateTag] = useState()
    const [read,updateRead] = useState(false)
    const {book_id} = useParams()
    const [id,updateId] = useState()
    function getBookData(){
        api.get("/getBook/"+book_id).then(resp =>{
            updateBook(resp.data)
        })
    }

    function submitRating(){
        if(rating){
        console.log(book_id+","+rating+","+id)
        api.post("/rating",{book_id:book_id,user_id:id,rating:rating}).then(resp=>{alert("Rating cadastrada com sucesso")})
        }
        
    }


    function buyBook(){
        api.post("/buy",{book_id:book_id,id:id})
        window.location.href="http://localhost:3000/"
        }


    function addTag(){
        
         if(tag){
            api.post("/tag",{book_id:book_id,tag_name:tag}).then(resp=>{alert("Tag cadastrada com sucesso");var tag = document.getElementById("quantity")
        tag.value = ""})
        }
        
    }

    useEffect(()=>{
        getBookData()
        updateId(sessionStorage.getItem("newUserId"))
    },[])

    function controlRead(value){
        updateRead(value)
        console.log(book_id+","+value+","+id)
        api.post("/read",{book_id:book_id,value:value,id:id}).then()
    }
    return(
        <div>
            <Header/>
            <Style.Container>
                <Style.Line><span>Original Title:&nbsp;</span><p>{book.original_title}</p></Style.Line>
                 <Style.Line><span>Authors:&nbsp;</span><p>{book.authors}</p></Style.Line>
                  <Style.Line><span>Average Rating:&nbsp;</span><p>{book.average_rating}</p></Style.Line>
                <Style.FormContainer>
                        <Style.Form>
                            <label for="rating">Rating (between 1 and 5):</label><br></br>
                            <input onChange={e=>{updateRating(e.target.value)}} type="number"  name="rating" min="1" max="5"/>
                            <br></br>
                            <button onClick={submitRating}>Submit Rating</button>
                        </Style.Form>
                        <Style.Form>
                            <label for="tag">Tag:</label> <br></br>
                            <input onChange={e=>{updateTag(e.target.value);}} type="text" id="quantity" name="tag"/>
                             <br></br>
                            <button onClick={e=>{addTag(e)}}>AddTag</button>
                        </Style.Form>
                        <Style.Form>
                            <label for="read">To Read:</label>
                            <input onChange={e=>{controlRead(e.target.checked)}} checked={read || false} type="checkbox" id="read" name="read"/>
                        </Style.Form>
                        <Style.Form>
                            <button onClick={buyBook}>Comprar livro</button>
                        </Style.Form>
                </Style.FormContainer>
                
            </Style.Container>
            
            <Footer/> 
        </div>
            

    )
}

export default BookPage