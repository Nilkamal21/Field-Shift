import React, { createContext, useContext, useState } from "react";

const FarmContext = createContext();

export function FarmProvider({ children }) {
  // Form input state matching Image 1 & 2
  const [location, setLocation] = useState({
    name: "Hajo, Kamrup",
    latitude: 26.2483,
    longitude: 91.5284,
  });

  const [fieldSize, setFieldSize] = useState("2");
  const [fieldUnit, setFieldUnit] = useState("Bigha");

  const [soilType, setSoilType] = useState("clay"); // 'clay' | 'loam' | 'sandy'
  const [lastCrop, setLastCrop] = useState("rice"); // 'rice' | 'mustard' | 'lentil' | 'potato' | 'jute'
  const [availableCrops, setAvailableCrops] = useState(["rice", "mustard", "lentil", "jute"]);
  const [priorities, setPriorities] = useState(["less_water", "safe_weather"]); // up to 2

  // API response state
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Helper toggle for available crops (ensuring at least 2)
  const toggleCrop = (cropId) => {
    setAvailableCrops((prev) => {
      if (prev.includes(cropId)) {
        if (prev.length <= 2) return prev; // keep at least 2
        return prev.filter((id) => id !== cropId);
      } else {
        return [...prev, cropId];
      }
    });
  };

  // Helper toggle for priorities (max 2)
  const togglePriority = (pKey) => {
    setPriorities((prev) => {
      if (prev.includes(pKey)) {
        if (prev.length <= 1) return prev; // keep at least 1
        return prev.filter((k) => k !== pKey);
      } else {
        if (prev.length >= 2) {
          return [prev[1], pKey]; // replace oldest selection
        }
        return [...prev, pKey];
      }
    });
  };

  return (
    <FarmContext.Provider
      value={{
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
        setAvailableCrops,
        toggleCrop,
        priorities,
        setPriorities,
        togglePriority,
        recommendation,
        setRecommendation,
        loading,
        setLoading,
        error,
        setError,
      }}
    >
      {children}
    </FarmContext.Provider>
  );
}

export function useFarm() {
  const context = useContext(FarmContext);
  if (!context) {
    throw new Error("useFarm must be used within a FarmProvider");
  }
  return context;
}
