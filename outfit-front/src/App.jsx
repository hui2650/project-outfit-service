import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'

import './App.css'
import Home from './pages/Home'
import Hero from './pages/Hero'
import UserPage from './pages/UserPage'
import { AppDataProvider } from './store/appDataStore.jsx'
import { LayoutProvider } from './store/layoutStore.jsx'

function App() {
  return (
    <AppDataProvider>
      <LayoutProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Hero />} />
            <Route path="/chat" element={<Home />} />
            <Route path="/userpage" element={<UserPage />} />
          </Routes>
        </BrowserRouter>
      </LayoutProvider>
    </AppDataProvider>
  )
}

export default App
