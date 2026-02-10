import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";

import "./App.css";
import Home from "./pages/Home";
import Hero from "./pages/Hero";
import User from "./pages/User";
import { AppDataProvider } from "./store/appDataStore.jsx";
import { LayoutProvider } from "./store/layoutStore.jsx";

function App() {
  return (
    <AppDataProvider>
      <LayoutProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Hero />} />
            <Route path="/chat" element={<Home />} />
            <Route path="/user" element={<User />} />
          </Routes>
        </BrowserRouter>
      </LayoutProvider>
    </AppDataProvider>
  );
}

export default App;
