import * as Style from './style'
import logo from '../../Assets/logo.jpg'
function Header({caminho}){
    return(
        <Style.Container>
            <a href='/'><img src={logo}></img></a> 
            {caminho=="usuario" && <a href='/usuario'>Login</a>}
        </Style.Container>
    )
}
export default Header