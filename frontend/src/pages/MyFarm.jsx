import React from "react";
import { useNavigate } from "react-router-dom";
import { useFarm } from "../context/FarmContext";
import { fetchRecommendations } from "../services/api";
import FarmMap from "../components/FarmMap";
import "./MyFarm.css";

export default function MyFarm() {
  const navigate = useNavigate();
  const {
    location,
    setLocation,
    fieldSize,
    setFieldSize,
    fieldUnit,
    setFieldUnit,
    soilType,
    setSoilType,
    lastCrop,
    setLastCrop,
    availableCrops,
    toggleCrop,
    priorities,
    togglePriority,
    setRecommendation,
    loading,
    setLoading,
    error,
    setError,
  } = useFarm();

  // Soil options
  const soilOptions = [
    { id: "clay", title: "Clay", desc: "Sticky, holds water" },
    { id: "loam", title: "Loam", desc: "Soft and crumbly" },
    { id: "sandy", title: "Sandy", desc: "Loose, dries fast" },
  ];

  // All 5 crops in the system
  const cropList = [
    { id: "rice", name: "Rice" },
    { id: "mustard", name: "Mustard" },
    { id: "lentil", name: "Lentil" },
    { id: "potato", name: "Potato" },
    { id: "jute", name: "Jute" },
  ];

  // Question 4 order matching design
  const q4Crops = [
    { id: "rice", name: "Rice" },
    { id: "mustard", name: "Mustard" },
    { id: "lentil", name: "Lentil" },
    { id: "jute", name: "Jute" },
    { id: "potato", name: "Potato" },
  ];

  // Priority goals
  const priorityOptions = [
    { id: "less_water", label: "Use less water" },
    { id: "rebuild_soil", label: "Make soil stronger" },
    { id: "safe_weather", label: "Be safe from bad weather" },
    { id: "more_money", label: "Earn more money" },
  ];

  // Human-readable summary labels for the sidebar
  const getSoilLabel = () => {
    const s = soilOptions.find((o) => o.id === soilType);
    return `${s ? s.title : "Clay"} soil`;
  };

  const getLastCropLabel = () => {
    const c = cropList.find((c) => c.id === lastCrop);
    return `Last crop: ${c ? c.name.toLowerCase() : "rice"}`;
  };

  const getPrioritySummary = () => {
    const map = {
      less_water: "less water",
      rebuild_soil: "stronger soil",
      safe_weather: "safe from weather",
      more_money: "more income",
    };
    const active = priorities.map((p) => map[p] || p);
    return active.length > 0 ? `Wants: ${active.join(", ")}` : "Wants: balanced plan";
  };

  // Form submission connected to live FastAPI backend POST /recommend
  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError(null);

    // Validation: at least 2 crops
    if (availableCrops.length < 2) {
      setError("Please pick at least 2 crops you can grow so we can build a rotation.");
      return;
    }

    // Map priority choices to weights
    const weights = {
      save_water: priorities.includes("less_water") ? 0.40 : 0.15,
      rebuild_soil: priorities.includes("rebuild_soil") ? 0.40 : 0.15,
      reduce_risk: priorities.includes("safe_weather") ? 0.40 : 0.15,
      profit: priorities.includes("more_money") ? 0.40 : 0.15,
    };

    const payload = {
      latitude: location.latitude,
      longitude: location.longitude,
      soil_type: `${getSoilLabel()}`,
      selected_crops: availableCrops,
      priority_weights: weights,
    };

    try {
      setLoading(true);
      const data = await fetchRecommendations(payload);
      setRecommendation(data);
      setLoading(false);
      navigate("/plan");
    } catch (err) {
      setLoading(false);
      const msg = err.message || "";
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        setError(
          "Could not connect to the Field Shift backend. Please verify your Python FastAPI server is running on http://localhost:8000."
        );
      } else {
        setError(msg || "Something went wrong while analyzing NASA data. Please try again.");
      }
    }
  };

  return (
    <div className="farm-page">
      {/* Page Heading */}
      <div className="page-header">
        <h1 className="page-title">Let's plan your next 3 years</h1>
        <p className="page-subtitle">Answer 5 simple questions. It takes about one minute.</p>
      </div>

      <div className="farm-layout">
        {/* Left Column: Form Questionnaire */}
        <form className="questions-list" onSubmit={handleSubmit} noValidate>
          {/* Question 1: Location & Interactive Satellite Map with 4-Dots Connector */}
          <section className="question-card" aria-labelledby="q1-title">
            <div className="question-header">
              <span className="q-badge" aria-hidden="true">1</span>
              <div className="q-title-wrap">
                <h2 id="q1-title" className="q-title">Where is your field?</h2>
                <span className="q-hint">Pick the easiest way for you</span>
              </div>
            </div>

            <FarmMap
              location={location}
              onLocationChange={setLocation}
              fieldSize={fieldSize}
              onFieldSizeChange={setFieldSize}
              fieldUnit={fieldUnit}
              onFieldUnitChange={setFieldUnit}
            />
          </section>

          {/* Question 2: Soil Type */}
          <section className="question-card" aria-labelledby="q2-title">
            <div className="question-header">
              <span className="q-badge" aria-hidden="true">2</span>
              <h2 id="q2-title" className="q-title">What is your soil like?</h2>
            </div>
            <div className="tile-grid tile-grid-3" role="radiogroup" aria-labelledby="q2-title">
              {soilOptions.map((opt) => {
                const isSelected = soilType === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    aria-label={`${opt.title} soil: ${opt.desc}`}
                    onClick={() => setSoilType(opt.id)}
                    className={`tile-btn ${isSelected ? "selected" : ""}`}
                  >
                    <div className="tile-top">
                      <span className="tile-name">{opt.title}</span>
                      <span className={`radio-dot ${isSelected ? "checked" : ""}`} aria-hidden="true" />
                    </div>
                    <span className="tile-desc">{opt.desc}</span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Question 3: Last Crop */}
          <section className="question-card" aria-labelledby="q3-title">
            <div className="question-header">
              <span className="q-badge" aria-hidden="true">3</span>
              <h2 id="q3-title" className="q-title">What did you grow last?</h2>
            </div>
            <div className="tile-grid tile-grid-5" role="radiogroup" aria-labelledby="q3-title">
              {cropList.map((crop) => {
                const isSelected = lastCrop === crop.id;
                return (
                  <button
                    key={crop.id}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    aria-label={`Last crop grown: ${crop.name}`}
                    onClick={() => setLastCrop(crop.id)}
                    className={`tile-btn tile-btn-compact ${isSelected ? "selected" : ""}`}
                  >
                    <span className={`radio-dot ${isSelected ? "checked" : ""}`} aria-hidden="true" />
                    <span className="tile-name">{crop.name}</span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Question 4: Crops you can grow */}
          <section className="question-card" aria-labelledby="q4-title">
            <div className="question-header">
              <span className="q-badge" aria-hidden="true">4</span>
              <h2 id="q4-title" className="q-title">Which crops can you grow?</h2>
            </div>
            <div className="tile-grid tile-grid-5" role="group" aria-labelledby="q4-title">
              {q4Crops.map((crop) => {
                const isChecked = availableCrops.includes(crop.id);
                return (
                  <button
                    key={crop.id}
                    type="button"
                    role="checkbox"
                    aria-checked={isChecked}
                    aria-label={`Can grow ${crop.name}`}
                    onClick={() => toggleCrop(crop.id)}
                    className={`tile-btn tile-btn-compact ${isChecked ? "selected" : ""}`}
                  >
                    <span className={`checkbox-box ${isChecked ? "checked" : ""}`} aria-hidden="true">
                      {isChecked && <span className="check-mark">&#10003;</span>}
                    </span>
                    <span className="tile-name">{crop.name}</span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Question 5: Priorities */}
          <section className="question-card" aria-labelledby="q5-title">
            <div className="question-header">
              <span className="q-badge" aria-hidden="true">5</span>
              <div className="q-title-wrap">
                <h2 id="q5-title" className="q-title">What do you want most?</h2>
                <span className="q-hint">Pick up to 2</span>
              </div>
            </div>
            <div className="tile-grid tile-grid-4" role="group" aria-labelledby="q5-title">
              {priorityOptions.map((opt) => {
                const isChecked = priorities.includes(opt.id);
                return (
                  <button
                    key={opt.id}
                    type="button"
                    role="checkbox"
                    aria-checked={isChecked}
                    aria-label={`Priority: ${opt.label}`}
                    onClick={() => togglePriority(opt.id)}
                    className={`tile-btn tile-btn-priority ${isChecked ? "selected" : ""}`}
                  >
                    <span className={`checkbox-box ${isChecked ? "checked" : ""}`} aria-hidden="true">
                      {isChecked && <span className="check-mark">&#10003;</span>}
                    </span>
                    <span className="tile-name">{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </form>

        {/* Right Column: Sticky "Your answers" Sidebar */}
        <aside className="sidebar-col" aria-label="Farm choices summary">
          <div className="answers-card" aria-live="polite">
            <h2 className="answers-title">Your answers</h2>
            <ul className="answers-list">
              <li>{location.name}</li>
              <li>{fieldSize} {fieldUnit}</li>
              <li>{getSoilLabel()}</li>
              <li>{getLastCropLabel()}</li>
              <li>{availableCrops.length} crops to choose from</li>
              <li>{getPrioritySummary()}</li>
            </ul>

            {/* Error Message Alert */}
            {error && (
              <div className="error-alert" role="alert">
                <span className="error-icon" aria-hidden="true">&#9888;</span>
                <p className="error-text">{error}</p>
              </div>
            )}

            {/* Submit Button with Loading State */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className={`btn-submit ${loading ? "loading" : ""}`}
              aria-label={loading ? "Analyzing NASA satellite data" : "Show crop rotation recommendations"}
            >
              {loading ? (
                <span className="btn-loading-content">
                  <span className="spinner" aria-hidden="true" />
                  Checking NASA satellites...
                </span>
              ) : (
                "Show me what to do"
              )}
            </button>

            <p className="sidebar-footnote">
              We check NASA satellite data for your field to give honest advice.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
