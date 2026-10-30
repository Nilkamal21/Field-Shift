import React from "react";
import { Link } from "react-router-dom";
import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-left">
          <p className="footer-text">
            <strong>Field Shift</strong> &mdash; NASA Space Apps Challenge 2026
          </p>
          <p className="footer-subtext">
            Powered by NASA POWER, NASA SMAP, and NASA MODIS Earth observation data.
          </p>
        </div>
        <div className="footer-right">
          <Link to="/about" className="footer-link">
            How this works
          </Link>
          <span className="footer-divider">&bull;</span>
          <a
            href="https://power.larc.nasa.gov/"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
          >
            NASA Data Portal
          </a>
        </div>
      </div>
    </footer>
  );
}
