import * as Style from './style'
import logo from '../../Assets/logo.jpg'
import { FaUserCircle, FaBook, FaSignInAlt } from 'react-icons/fa';

function Header({caminho, admin}){
    return(
        <Style.Container>
            <Style.Wrapper>
                <a href='/' className="logo-area">
                    
                    <img src={logo} alt="Logo" onError={(e) => {e.target.style.display='none'}} />
                    <span>BookMarket</span>
                </a> 
                <Style.Nav>
                    {caminho === "usuario" && (
                        <a href='/usuario'>
                            <FaSignInAlt /> Login
                        </a>
                    )}
                    {admin && (
                        <a href='/livro'>
                            <FaBook /> Cadastrar Livro
                        </a>
                    )}
                </Style.Nav>
            </Style.Wrapper>
        </Style.Container>
    )
}
export default Header