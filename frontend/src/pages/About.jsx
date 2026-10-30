import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAboutInfo } from "../services/api";
import "./About.css";

export default function About() {
  const [aboutData, setAboutData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAboutInfo()
      .then((data) => {
        setAboutData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load information");
        setLoading(false);
      });
  }, []);

  return (
    <div className="about-page">
      {/* 1. HERO HEADER */}
      <div className="about-header">
        <span className="about-tag">NASA Space Apps Challenge 2026</span>
        <h1 className="about-title">How Field Shift Works</h1>
        <p className="about-subtitle">
          Adapting smallholder farms with NASA Earth observations and transparent agronomic rules.
        </p>
      </div>

      {loading ? (
        <div className="about-loading">
          <div className="about-spinner" />
          <p>Loading project & NASA dataset information...</p>
        </div>
      ) : error ? (
        <div className="about-error">
          <p>Could not connect to backend: {error}</p>
          <Link to="/" className="btn-return-link">&larr; Return to Form</Link>
        </div>
      ) : (
        <div className="about-content">
          {/* Mission Card */}
          <section className="about-card mission-card">
            <h2 className="section-title">The Challenge & Our Mission</h2>
            <p className="mission-text">
              {aboutData?.project?.core_mission}
            </p>
            <div className="region-meta">
              <span className="meta-item">
                <strong>Focus Region:</strong> {aboutData?.project?.target_region}
              </span>
              <span className="meta-divider">&bull;</span>
              <span className="meta-item">
                <strong>Supported Crops:</strong> {aboutData?.project?.supported_crops?.join(", ")}
              </span>
            </div>
          </section>

          {/* 3 NASA Datasets Section */}
          <section className="datasets-section">
            <h2 className="section-heading">Three NASA Datasets Used</h2>
            <p className="section-subheading">
              Every crop rotation recommendation is influenced by all three satellite observations.
            </p>

            <div className="datasets-grid">
              {aboutData?.nasa_datasets?.map((ds, idx) => (
                <div key={ds.name} className="dataset-card">
                  <div className="ds-top">
                    <span className="ds-number">0{idx + 1}</span>
                    <span className="ds-badge">{ds.dataset_id}</span>
                  </div>
                  <h3 className="ds-name">{ds.name}</h3>
                  <div className="ds-body">
                    <p className="ds-role">
                      <strong>What it tracks:</strong> {ds.role}
                    </p>
                    <p className="ds-impact">
                      <strong>How it shapes advice:</strong> {ds.agronomic_impact}
                    </p>
                    <p className="ds-access">
                      <strong>Access:</strong> {ds.access}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Scoring Engine Rules */}
          <section className="about-card rules-card">
            <h2 className="section-title">Transparent Decision Rules (No Black-Box AI)</h2>
            <p className="rules-intro">
              Unlike unpredictable AI/ML models that hallucinate advice, Field Shift uses deterministic, agronomist-verified scoring rules that provide clear explanations:
            </p>

            <div className="rules-list">
              {aboutData?.scoring_rules?.map((rule) => (
                <div key={rule.rule} className="rule-item">
                  <div className="rule-badge">&#10003;</div>
                  <div className="rule-content">
                    <h4 className="rule-name">{rule.rule}</h4>
                    <p className="rule-desc">{rule.explanation}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="transparency-callout">
              <span className="callout-icon">&#9878;</span>
              <p className="callout-text">
                {aboutData?.transparency_guarantee}
              </p>
            </div>
          </section>

          {/* Bottom Action */}
          <div className="about-action-wrap">
            <Link to="/" className="btn-start-plan">
              Plan your farm's 3-year rotation &rarr;
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
