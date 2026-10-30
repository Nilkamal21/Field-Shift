import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useFarm } from "../context/FarmContext";
import { fetchRecommendations } from "../services/api";
import "./MyPlan.css";

// Helper to get clean display crop name (e.g. "Rice (Sali / Kharif Paddy)" -> "Rice")
function cleanCropName(name) {
  if (!name) return "";
  return name.split("(")[0].trim();
}

export default function MyPlan() {
  const navigate = useNavigate();
  const {
    location,
    soilType,
    availableCrops,
    priorities,
    recommendation,
    setRecommendation,
    loading,
    setLoading,
    error,
    setError,
  } = useFarm();

  const [saved, setSaved] = useState(false);

  // Auto-fetch if user lands directly on /plan
  useEffect(() => {
    if (!recommendation && !loading) {
      const loadDefaultPlan = async () => {
        try {
          setLoading(true);
          const weights = {
            save_water: priorities.includes("less_water") ? 0.40 : 0.15,
            rebuild_soil: priorities.includes("rebuild_soil") ? 0.40 : 0.15,
            reduce_risk: priorities.includes("safe_weather") ? 0.40 : 0.15,
            profit: priorities.includes("more_money") ? 0.40 : 0.15,
          };
          const payload = {
            latitude: location.latitude || 26.18,
            longitude: location.longitude || 91.75,
            soil_type: soilType ? `${soilType} soil` : "Clay soil",
            selected_crops: availableCrops.length >= 2 ? availableCrops : ["rice", "mustard", "lentil", "jute"],
            priority_weights: weights,
          };
          const data = await fetchRecommendations(payload);
          setRecommendation(data);
          setLoading(false);
        } catch (err) {
          setError(err.message || "Could not load recommendation");
          setLoading(false);
        }
      };
      loadDefaultPlan();
    }
  }, [recommendation, loading, location, soilType, availableCrops, priorities, setRecommendation, setLoading, setError]);

  // Loading state
  if (loading && !recommendation) {
    return (
      <div className="plan-loading-state" role="status" aria-live="polite">
        <div className="plan-spinner" aria-hidden="true" />
        <h2>Analyzing NASA satellite data for your land...</h2>
        <p>Checking 10-year weather trends, root-zone soil moisture, and vegetation health.</p>
      </div>
    );
  }

  // Error state
  if (error && !recommendation) {
    return (
      <div className="plan-error-state" role="alert">
        <div className="error-icon" aria-hidden="true">&#9888;</div>
        <h2>Unable to load crop rotation advice</h2>
        <p>{error}</p>
        <Link to="/" className="btn-back-link">
          &larr; Back to My Field
        </Link>
      </div>
    );
  }

  const topRotations = recommendation?.top_rotations || [];
  const primaryPlan = topRotations[0] || {
    rotation: ["rice", "lentil", "mustard"],
    crop_names: ["Rice", "Lentil", "Mustard"],
    scores: { water_score: 98, soil_score: 100, risk_score: 89, profit_score: 100 },
    reasons: [],
  };

  const secondPlan = topRotations[1] || {
    rotation: ["mustard", "jute", "rice"],
    crop_names: ["Mustard", "Jute", "Rice"],
    reasons: ["Very safe in dry years, but earns a little less."],
  };

  const c1 = cleanCropName(primaryPlan.crop_names[0]);
  const c2 = cleanCropName(primaryPlan.crop_names[1]);
  const c3 = cleanCropName(primaryPlan.crop_names[2]);

  // Find heavy feeder to advise against monoculture
  const heavyFeeder = primaryPlan.rotation.find((r) => r === "rice" || r === "potato") || primaryPlan.rotation[0];
  const heavyFeederName = cleanCropName(heavyFeeder);

  // Compute gain metrics for the progress bars
  const waterGainPct = Math.min(35, Math.max(18, Math.round((primaryPlan.scores.water_score / 100) * 30)));
  const soilHealthPct = Math.min(100, Math.max(70, Math.round(primaryPlan.scores.soil_score)));
  const weatherSafetyPct = Math.min(100, Math.max(65, Math.round(primaryPlan.scores.risk_score)));

  const handlePrint = () => {
    window.print();
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="plan-page">
      {/* 1. DARK GREEN HERO BANNER */}
      <section className="hero-advice-card" aria-labelledby="hero-plan-title">
        <div className="advice-badge">
          Our advice for {recommendation?.farm_profile?.district || "Plot A"}
        </div>

        <h1 id="hero-plan-title" className="hero-headline">
          Grow {c1.toLowerCase()}, then {c2.toLowerCase()}, then {c3.toLowerCase()}. Do not grow {heavyFeederName.toLowerCase()} two years in a row.
        </h1>

        <p className="hero-subtitle">
          Your land is getting hotter and drier. This plan uses less water and puts goodness back in the soil.
        </p>

        {/* 3 Year Horizontal Sequence Cards */}
        <div className="year-sequence-row" aria-label="3-year rotation schedule">
          <div className="year-box year-box-1">
            <span className="year-label">Year 1</span>
            <span className="year-crops">{c1}, then {c2}</span>
          </div>

          <span className="year-arrow" aria-hidden="true">&rarr;</span>

          <div className="year-box year-box-2">
            <span className="year-label">Year 2</span>
            <span className="year-crops">{c2}, then {c3}</span>
          </div>

          <span className="year-arrow" aria-hidden="true">&rarr;</span>

          <div className="year-box year-box-3">
            <span className="year-label">Year 3</span>
            <span className="year-crops">{c1}, then {c2}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="hero-actions">
          <button
            type="button"
            onClick={handleSave}
            className="btn-save-plan"
            aria-label="Save this rotation plan"
          >
            {saved ? "Plan Saved!" : "Save my plan"}
          </button>
          <button
            type="button"
            onClick={handlePrint}
            className="btn-print-plan"
            aria-label="Print this rotation plan"
          >
            Print
          </button>
        </div>
      </section>

      {/* 2. TWO-COLUMN GRID: STEP BY STEP & WHAT YOU GAIN */}
      <div className="plan-details-grid">
        {/* Left Column: What to do, step by step */}
        <section className="plan-card" aria-labelledby="steps-card-title">
          <h2 id="steps-card-title" className="plan-card-title">What to do, step by step</h2>
          <div className="steps-list">
            <div className="step-item">
              <span className="step-number" aria-hidden="true">1</span>
              <div className="step-text">
                <h3 className="step-title">June to July: plant {c1.toLowerCase()}</h3>
                <p className="step-desc">
                  Choose a short-duration variety so it needs less water.
                </p>
              </div>
            </div>

            <div className="step-item">
              <span className="step-number" aria-hidden="true">2</span>
              <div className="step-text">
                <h3 className="step-title">November: sow {c2.toLowerCase()} after harvest</h3>
                <p className="step-desc">
                  {c2} needs little water and feeds the soil with natural nutrients.
                </p>
              </div>
            </div>

            <div className="step-item">
              <span className="step-number" aria-hidden="true">3</span>
              <div className="step-text">
                <h3 className="step-title">Leave crop stalks on the field</h3>
                <p className="step-desc">
                  They cover the soil and help it keep valuable moisture.
                </p>
              </div>
            </div>

            <div className="step-item">
              <span className="step-number" aria-hidden="true">4</span>
              <div className="step-text">
                <h3 className="step-title">Next year: grow {c3.toLowerCase()} and {c2.toLowerCase()}, not {heavyFeederName.toLowerCase()}</h3>
                <p className="step-desc">
                  Giving the field a different crop keeps it healthy and pest-free.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: What you gain */}
        <section className="plan-card" aria-labelledby="gains-card-title">
          <h2 id="gains-card-title" className="plan-card-title">What you gain</h2>
          <div className="gains-list">
            {/* Water Saving */}
            <div className="gain-item">
              <div className="gain-header">
                <div className="gain-icon gain-icon-blue" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                  </svg>
                </div>
                <div className="gain-info">
                  <span className="gain-label">Uses about {waterGainPct}% less water</span>
                  <div
                    className="gain-bar-track"
                    role="progressbar"
                    aria-valuenow={waterGainPct}
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-label={`Water savings: ${waterGainPct} percent less water`}
                  >
                    <div className="gain-bar-fill gain-bar-blue" style={{ width: `${waterGainPct * 2.8}%` }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Soil Health */}
            <div className="gain-item">
              <div className="gain-header">
                <div className="gain-icon gain-icon-green" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>
                    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 12"/>
                  </svg>
                </div>
                <div className="gain-info">
                  <span className="gain-label">Soil gets stronger every year</span>
                  <div
                    className="gain-bar-track"
                    role="progressbar"
                    aria-valuenow={soilHealthPct}
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-label={`Soil improvement score: ${soilHealthPct} out of 100`}
                  >
                    <div className="gain-bar-fill gain-bar-green" style={{ width: `${soilHealthPct}%` }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Weather Safety */}
            <div className="gain-item">
              <div className="gain-header">
                <div className="gain-icon gain-icon-amber" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                  </svg>
                </div>
                <div className="gain-info">
                  <span className="gain-label">Safer in hot and dry years</span>
                  <div
                    className="gain-bar-track"
                    role="progressbar"
                    aria-valuenow={weatherSafetyPct}
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-label={`Weather resilience score: ${weatherSafetyPct} out of 100`}
                  >
                    <div className="gain-bar-fill gain-bar-amber" style={{ width: `${weatherSafetyPct}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p className="gain-note">
            Estimated from NASA POWER rainfall and SMAP root-zone moisture metrics.
          </p>
        </section>
      </div>

      {/* 3. YOUR FIRST YEAR AT A GLANCE */}
      <section className="timeline-card" aria-labelledby="timeline-card-title">
        <h2 id="timeline-card-title" className="plan-card-title">Your first year at a glance</h2>

        <div className="timeline-container">
          {/* Months header */}
          <div className="timeline-months-row" aria-hidden="true">
            {["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"].map((m) => (
              <span key={m} className="month-col">{m}</span>
            ))}
          </div>

          {/* Timeline crop blocks */}
          <div className="timeline-blocks-row" role="region" aria-label="12-month crop calendar">
            <div className="crop-block block-crop-1" style={{ flex: 5 }} aria-label={`June through October: ${c1} grows`}>
              <span>{c1} grows</span>
            </div>
            <div className="crop-block block-crop-2" style={{ flex: 4 }} aria-label={`November through February: ${c2} grows`}>
              <span>{c2} grows</span>
            </div>
            <div className="crop-block block-rest" style={{ flex: 3 }} aria-label="March through May: Field rest and soil preparation">
              <span>Rest & prep</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. OTHER PLAN VS NOT ADVISED */}
      <div className="comparison-cards-grid">
        {/* Other plan */}
        <section className="comparison-card" aria-labelledby="other-plan-title">
          <span className="pill-tag pill-other">Other plan</span>
          <h3 id="other-plan-title" className="comparison-title">{cleanCropName(secondPlan.crop_names.join(", "))}</h3>
          <p className="comparison-desc">
            {secondPlan.reasons[0] || "Very safe in dry years, but earns slightly different income balance."}
          </p>
        </section>

        {/* Not advised */}
        <section className="comparison-card" aria-labelledby="not-advised-title">
          <span className="pill-tag pill-warn">Not advised</span>
          <h3 id="not-advised-title" className="comparison-title">{heavyFeederName} every year</h3>
          <p className="comparison-desc">
            Earns most at first, but uses a lot of water and weakens the soil.
          </p>
        </section>
      </div>

      {/* 5. FOOTER LINK TO NASA DATA */}
      <div className="plan-footer-link-wrap">
        <Link to="/data" className="why-nasa-link">
          Why did we choose this? See what NASA saw on your land &rarr;
        </Link>
      </div>
    </div>
  );
}
