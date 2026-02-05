import * as Style from "./style"

function Card({img,title,author,average_rating}){
    
    return(
        <Style.Container>
            <img src={img}></img>
            <Style.Bottom>
                <p>{title}</p>
                <p>{author.split(",")[0]}</p>
                <p>{average_rating}</p>
            </Style.Bottom>
        </Style.Container>
    )
}

export default Card