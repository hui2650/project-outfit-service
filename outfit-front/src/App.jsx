import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'

import './App.css'
import Home from './pages/Home'
import Hero from './pages/Hero'
import UserPage from './pages/UserPage'
import { AppDataProvider } from './store/appDataStore.jsx'
import { LayoutProvider } from './store/layoutStore.jsx'
import { TransitionProvider } from './store/transitionStore.jsx'
import UserPageNickName from './pages/UserPageNickName.jsx'
import UserPageStyle from './pages/UserPageStyle.jsx'

function App() {
  return (
    <AppDataProvider>
      <LayoutProvider>
        <TransitionProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Hero />} />
              <Route path="/chat" element={<Home />} />
              <Route
                path="/user-info-nickname"
                element={<UserPageNickName />}
              />
              <Route path="//user-info-style" element={<UserPageStyle />} />
              <Route path="/userpage" element={<UserPage />} />
            </Routes>
          </BrowserRouter>
        </TransitionProvider>
      </LayoutProvider>
    </AppDataProvider>
  )
}

export default App
