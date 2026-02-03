import * as Style from "./style"

function Card({title,author,average_rating}){
    
    return(
        <Style.Container>
            <div></div>
            <Style.Bottom>
                <p>{title}</p>
                <p>{author}</p>
                <p>{average_rating}</p>
            </Style.Bottom>
        </Style.Container>
    )
}

export default Card