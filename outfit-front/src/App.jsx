import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'

import './App.css'
import Home from './pages/Home'
import Hero from './pages/Hero'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Hero />} />
        <Route path="/chat" element={<Home />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
