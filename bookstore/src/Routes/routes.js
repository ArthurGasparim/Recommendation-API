import {BrowserRouter as Router,Routes, Route} from 'react-router-dom'
import Home from '../Views/Home'
import Usuario from '../Views/UserDetails'
export default function Rotas(){
    return(
        <Router>
            <Routes>
                <Route path="/" element={<Home/>}/>
                <Route path="/usuario" element={<Usuario/>}/>
            </Routes>
        </Router>
    )
}