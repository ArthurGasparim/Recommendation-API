import * as Style from './style'
import logo from '../../Assets/logo.jpg'
function Header(){
    return(
        <Style.Container>
            <img src={logo}></img>
        </Style.Container>
    )
}
export default Header