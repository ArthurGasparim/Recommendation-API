import { useEffect, useState } from "react"
import api from "../../Services/service"
import * as Style from "./style"
import { useParams } from "react-router-dom"
import Header from "../../Components/Header"
import Footer from "../../Components/Footer"

function BookPage(){
    const [book,updateBook] = useState({})
    const {book_id} = useParams()
    function getBookData(){
        api.get("/getBook/"+book_id).then(resp =>{
            updateBook(resp.data)
        })
    }
    useEffect(()=>{
        getBookData()
    },[])
    return(
        <div>
            <Header/>
            <Style.Container>
                <Style.Line><span>Original Title:&nbsp;</span><p>{book.original_title}</p></Style.Line>
                 <Style.Line><span>Authors:&nbsp;</span><p>{book.authors}</p></Style.Line>
                  <Style.Line><span>Average Rating:&nbsp;</span><p>{book.average_rating}</p></Style.Line>
                <Style.Form>
                        <Style.Form>
                            <label for="rating">Rating (between 1 and 5):</label>
                            <input type="number"  name="rating" min="1" max="5"/>
                            <button>Submit Rating</button>
                        </Style.Form>
                        <Style.Form>
                            <label for="tag">Tag:</label>
                            <input type="text" id="quantity" name="tag"/>
                            <button>AddTag</button>
                        </Style.Form>
                </Style.Form>
                
            </Style.Container>
            
            <Footer/> 
        </div>
            

    )
}

export default BookPage