import { useState } from "react"
import api from "../../Services/service"
import * as Style from "./style"
import { useParams } from "react-router-dom"

function BookPage(){
    const [book,updateBook] = useState()
    const {book_id} = useParams()
    function getBookData(){
        api.get("/getBook").then(resp =>{
            updateBook(resp.data)
        })
    }
    return(
        <div>Teste</div>

    )
}