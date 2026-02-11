import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";

import "./App.css";
import Home from "./pages/Home";
import Hero from "./pages/Hero";
import UserPage from "./pages/UserPage";
import NickNameInput from "./pages/NickNameInput.jsx";
import StyleInput from "./pages/StyleInput.jsx";
import { AppDataProvider } from "./store/appDataStore.jsx";
import { LayoutProvider } from "./store/layoutStore.jsx";
import { TransitionProvider } from "./store/transitionStore.jsx";

function App() {
  return (
    <AppDataProvider>
      <LayoutProvider>
        <TransitionProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Hero />} />
              <Route path="/chat" element={<Home />} />
              <Route path="/nicknameinput" element={<NickNameInput />} />
              <Route path="/styleinput" element={<StyleInput />} />
              <Route path="/userpage" element={<UserPage />} />
            </Routes>
          </BrowserRouter>
        </TransitionProvider>
      </LayoutProvider>
    </AppDataProvider>
  );
}

export default App;
