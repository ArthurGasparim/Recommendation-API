import * as Style from "./style"
import { FaStar } from "react-icons/fa";

function Card({img, title, author, average_rating}){
    return(
        <Style.Container>
            <Style.ImageContainer>
                <img src={img} alt={title} />
            </Style.ImageContainer>
            <Style.Info>
                <h3 title={title}>{title}</h3>
                <p className="author">{author ? author.split(",")[0] : "Unknown"}</p>
                <div className="rating">
                    <FaStar color="#FFD700" />
                    <span>{average_rating}</span>
                </div>
            </Style.Info>
        </Style.Container>
    )
}

export default Card