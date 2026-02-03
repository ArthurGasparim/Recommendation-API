import {BrowserRouter as Router,Routes, Route} from 'react-router-dom'
import Home from '../Views/Home'
import Usuario from '../Views/UserDetails'
import Books from '../Views/BookDetails'
export default function Rotas(){
    return(
        <Router>
            <Routes>
                <Route path="/" element={<Home/>}/>
                <Route path="/usuario" element={<Usuario/>}/>
                <Route path="/livro" element={<Books/>}/>
            </Routes>
        </Router>
    )
}