import React from "react";
import { Link, useLocation } from "react-router-dom";
import "./Header.css";

export default function Header() {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <header className="header">
      <div className="header-inner">
        {/* Brand Logo & Tagline */}
        <Link to="/" className="brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
            </svg>
          </div>
          <div className="brand-text">
            <h1 className="brand-title">Field Shift</h1>
            <p className="brand-subtitle">Smart crop advice from NASA satellites</p>
          </div>
        </Link>

        {/* 3 Step Navigation Pills */}
        <nav className="nav-pills" aria-label="Steps Navigation">
          <Link
            to="/"
            className={`nav-pill ${currentPath === "/" ? "active" : ""}`}
          >
            1 My field
          </Link>

          <Link
            to="/plan"
            className={`nav-pill ${currentPath === "/plan" ? "active" : ""}`}
          >
            2 What to do
          </Link>

          <Link
            to="/data"
            className={`nav-pill ${currentPath === "/data" ? "active" : ""}`}
          >
            3 Why
          </Link>
        </nav>
      </div>
    </header>
  );
}
