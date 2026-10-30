import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { FarmProvider } from "./context/FarmContext";
import Header from "./components/Header";
import Footer from "./components/Footer";
import MyFarm from "./pages/MyFarm";
import MyPlan from "./pages/MyPlan";
import NasaData from "./pages/NasaData";
import About from "./pages/About";

export default function App() {
  return (
    <FarmProvider>
      <Router>
        <div className="app-container">
          <Header />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<MyFarm />} />
              <Route path="/plan" element={<MyPlan />} />
              <Route path="/data" element={<NasaData />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </FarmProvider>
  );
}
