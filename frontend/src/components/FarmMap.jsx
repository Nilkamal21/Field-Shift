import React, { useEffect, useRef, useState, useCallback } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./FarmMap.css";

// Assam towns quick coordinates for instant search without network delay
const KAMRUP_TOWNS = [
  { name: "Hajo", lat: 26.2483, lon: 91.5284 },
  { name: "Guwahati", lat: 26.1445, lon: 91.7362 },
  { name: "Rangia", lat: 26.4719, lon: 91.6318 },
  { name: "Palashbari", lat: 26.1264, lon: 91.5036 },
  { name: "Boko", lat: 25.9754, lon: 91.2294 },
  { name: "Sualkuchi", lat: 26.1719, lon: 91.5724 },
  { name: "North Guwahati", lat: 26.2083, lon: 91.7167 },
  { name: "Chaygaon", lat: 26.0500, lon: 91.4333 },
  { name: "Kamalpur", lat: 26.3667, lon: 91.6833 },
  { name: "Goroimari", lat: 26.1000, lon: 91.3167 },
];

// Helper to create a custom circular pin icon matching Image 1 & 2
function createPinIcon() {
  return L.divIcon({
    className: "custom-field-pin-wrapper",
    html: `
      <div class="custom-field-pin">
        <div class="pin-pulse"></div>
        <div class="pin-dot"></div>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

// Helper to create numbered corner dot icons for the 4-dots connector
function createCornerDotIcon(index) {
  return L.divIcon({
    className: "corner-dot-wrapper",
    html: `<div class="corner-dot">${index}</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

export default function FarmMap({
  location,
  onLocationChange,
  fieldSize,
  onFieldSizeChange,
  fieldUnit,
  onFieldUnitChange,
}) {
  const mapContainerRef = useRef(null);
  const modalMapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const modalMapInstanceRef = useRef(null);

  // Map state
  const [isMaximized, setIsMaximized] = useState(false);
  const [mapType, setMapType] = useState("satellite"); // 'satellite' | 'map'
  const [selectionMode, setSelectionMode] = useState("tap"); // 'tap' | 'dots'
  const [cornerDots, setCornerDots] = useState([]); // array of [lat, lon]
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  // Layers refs
  const pinMarkerRef = useRef(null);
  const fieldPolygonRef = useRef(null);
  const dotMarkersRef = useRef([]);

  const modalPinMarkerRef = useRef(null);
  const modalFieldPolygonRef = useRef(null);
  const modalDotMarkersRef = useRef([]);

  // Tile layer URLs
  const SATELLITE_URL =
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
  const SATELLITE_ATTRIB =
    '&copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics';

  const STREET_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  const STREET_ATTRIB =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

  // Build a simulated field polygon around a single tapped center point
  const getSimulatedPlotCoords = useCallback((lat, lon) => {
    const latDelta = 0.00075; // approx 80 meters
    const lonDelta = 0.0011;  // approx 110 meters
    return [
      [lat + latDelta, lon - lonDelta],
      [lat + latDelta * 0.9, lon + lonDelta],
      [lat - latDelta, lon + lonDelta * 0.95],
      [lat - latDelta * 0.95, lon - lonDelta],
    ];
  }, []);

  // Update map graphics (pin & polygon) for a given map instance
  const updateMapGraphics = useCallback(
    (map, pinRef, polyRef, dotsRef) => {
      if (!map) return;

      // Clear existing temporary dot markers
      if (dotsRef.current) {
        dotsRef.current.forEach((m) => map.removeLayer(m));
        dotsRef.current = [];
      }

      // If user is in 4-dots mode and has clicked some points
      if (selectionMode === "dots" && cornerDots.length > 0) {
        // Draw corner dot markers
        cornerDots.forEach((pt, idx) => {
          const marker = L.marker(pt, {
            icon: createCornerDotIcon(idx + 1),
            interactive: false,
          }).addTo(map);
          dotsRef.current.push(marker);
        });

        // Draw connected lines or closed polygon
        if (polyRef.current) {
          map.removeLayer(polyRef.current);
          polyRef.current = null;
        }

        if (cornerDots.length >= 2) {
          polyRef.current = L.polygon(cornerDots, {
            color: "#C28B36",
            weight: 2.5,
            dashArray: "5, 4",
            fillColor: "#D8AE64",
            fillOpacity: 0.45,
          }).addTo(map);
        }

        // Center pin if 4 dots completed
        if (cornerDots.length === 4) {
          const avgLat =
            cornerDots.reduce((sum, p) => sum + p[0], 0) / 4;
          const avgLon =
            cornerDots.reduce((sum, p) => sum + p[1], 0) / 4;
          if (pinRef.current) {
            pinRef.current.setLatLng([avgLat, avgLon]);
          } else {
            pinRef.current = L.marker([avgLat, avgLon], {
              icon: createPinIcon(),
              draggable: true,
            }).addTo(map);
          }
        }
      } else {
        // Single tap mode: center pin + simulated dashed field plot
        const currentLat = location.latitude || 26.18;
        const currentLon = location.longitude || 91.75;

        if (pinRef.current) {
          pinRef.current.setLatLng([currentLat, currentLon]);
        } else {
          pinRef.current = L.marker([currentLat, currentLon], {
            icon: createPinIcon(),
            draggable: true,
          }).addTo(map);

          // Allow dragging the red pin to fine-tune
          pinRef.current.on("dragend", (e) => {
            const pos = e.target.getLatLng();
            onLocationChange({
              ...location,
              latitude: Number(pos.lat.toFixed(4)),
              longitude: Number(pos.lng.toFixed(4)),
            });
          });
        }

        // Draw dashed rectangular field boundary
        if (polyRef.current) {
          map.removeLayer(polyRef.current);
        }
        const coords = getSimulatedPlotCoords(currentLat, currentLon);
        polyRef.current = L.polygon(coords, {
          color: "#C28B36",
          weight: 2.5,
          dashArray: "5, 4",
          fillColor: "#D8AE64",
          fillOpacity: 0.45,
        }).addTo(map);
      }
    },
    [location, selectionMode, cornerDots, onLocationChange, getSimulatedPlotCoords]
  );

  // Initialize embedded inline map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const lat = location.latitude || 26.18;
    const lon = location.longitude || 91.75;

    const map = L.map(mapContainerRef.current, {
      center: [lat, lon],
      zoom: 16,
      zoomControl: false,
    });

    const tileLayer = L.tileLayer(
      mapType === "satellite" ? SATELLITE_URL : STREET_URL,
      {
        attribution:
          mapType === "satellite" ? SATELLITE_ATTRIB : STREET_ATTRIB,
        maxZoom: 19,
      }
    ).addTo(map);

    mapInstanceRef.current = { map, tileLayer };

    // Map click handler
    map.on("click", (e) => {
      const clickLat = Number(e.latlng.lat.toFixed(4));
      const clickLon = Number(e.latlng.lng.toFixed(4));

      if (selectionMode === "dots") {
        setCornerDots((prev) => {
          if (prev.length >= 4) {
            return [[clickLat, clickLon]];
          }
          const next = [...prev, [clickLat, clickLon]];
          if (next.length === 4) {
            // Compute centroid
            const avgLat = Number(
              (next.reduce((sum, p) => sum + p[0], 0) / 4).toFixed(4)
            );
            const avgLon = Number(
              (next.reduce((sum, p) => sum + p[1], 0) / 4).toFixed(4)
            );
            onLocationChange({
              ...location,
              latitude: avgLat,
              longitude: avgLon,
            });
          }
          return next;
        });
      } else {
        // Single tap placement
        onLocationChange({
          ...location,
          latitude: clickLat,
          longitude: clickLon,
        });
      }
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []); // Run once on mount

  // Sync inline map graphics when state changes
  useEffect(() => {
    if (mapInstanceRef.current?.map) {
      updateMapGraphics(
        mapInstanceRef.current.map,
        pinMarkerRef,
        fieldPolygonRef,
        dotMarkersRef
      );
    }
  }, [location, selectionMode, cornerDots, updateMapGraphics]);

  // Sync map center if coordinates change
  useEffect(() => {
    if (mapInstanceRef.current?.map) {
      const current = mapInstanceRef.current.map.getCenter();
      if (
        Math.abs(current.lat - location.latitude) > 0.005 ||
        Math.abs(current.lng - location.longitude) > 0.005
      ) {
        mapInstanceRef.current.map.setView(
          [location.latitude, location.longitude],
          16,
          { animate: true }
        );
      }
    }
  }, [location.latitude, location.longitude]);

  // Handle map type toggle (Satellite vs Street Map)
  useEffect(() => {
    const url = mapType === "satellite" ? SATELLITE_URL : STREET_URL;
    const attrib =
      mapType === "satellite" ? SATELLITE_ATTRIB : STREET_ATTRIB;

    if (mapInstanceRef.current?.tileLayer) {
      mapInstanceRef.current.tileLayer.setUrl(url);
    }
    if (modalMapInstanceRef.current?.tileLayer) {
      modalMapInstanceRef.current.tileLayer.setUrl(url);
    }
  }, [mapType]);

  // Initialize maximized modal map when opened
  useEffect(() => {
    if (!isMaximized) {
      if (modalMapInstanceRef.current?.map) {
        modalMapInstanceRef.current.map.remove();
        modalMapInstanceRef.current = null;
      }
      return;
    }

    // Modal container is now mounted
    const timer = setTimeout(() => {
      if (!modalMapContainerRef.current) return;

      const lat = location.latitude || 26.18;
      const lon = location.longitude || 91.75;

      const modalMap = L.map(modalMapContainerRef.current, {
        center: [lat, lon],
        zoom: 16,
        zoomControl: false,
      });

      const tileLayer = L.tileLayer(
        mapType === "satellite" ? SATELLITE_URL : STREET_URL,
        {
          attribution:
            mapType === "satellite" ? SATELLITE_ATTRIB : STREET_ATTRIB,
          maxZoom: 19,
        }
      ).addTo(modalMap);

      modalMapInstanceRef.current = { map: modalMap, tileLayer };

      modalMap.on("click", (e) => {
        const clickLat = Number(e.latlng.lat.toFixed(4));
        const clickLon = Number(e.latlng.lng.toFixed(4));

        if (selectionMode === "dots") {
          setCornerDots((prev) => {
            if (prev.length >= 4) {
              return [[clickLat, clickLon]];
            }
            const next = [...prev, [clickLat, clickLon]];
            if (next.length === 4) {
              const avgLat = Number(
                (next.reduce((sum, p) => sum + p[0], 0) / 4).toFixed(4)
              );
              const avgLon = Number(
                (next.reduce((sum, p) => sum + p[1], 0) / 4).toFixed(4)
              );
              onLocationChange({
                ...location,
                latitude: avgLat,
                longitude: avgLon,
              });
            }
            return next;
          });
        } else {
          onLocationChange({
            ...location,
            latitude: clickLat,
            longitude: clickLon,
          });
        }
      });

      updateMapGraphics(
        modalMap,
        modalPinMarkerRef,
        modalFieldPolygonRef,
        modalDotMarkersRef
      );
    }, 50);

    return () => clearTimeout(timer);
  }, [isMaximized]);

  // Sync modal map graphics
  useEffect(() => {
    if (isMaximized && modalMapInstanceRef.current?.map) {
      updateMapGraphics(
        modalMapInstanceRef.current.map,
        modalPinMarkerRef,
        modalFieldPolygonRef,
        modalDotMarkersRef
      );
    }
  }, [isMaximized, location, selectionMode, cornerDots, updateMapGraphics]);

  // Search village or town
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    const queryLower = searchQuery.trim().toLowerCase();

    // Check Kamrup pre-defined towns first
    const matched = KAMRUP_TOWNS.find((t) =>
      t.name.toLowerCase().includes(queryLower)
    );

    if (matched) {
      onLocationChange({
        name: `${matched.name}, Kamrup`,
        latitude: matched.lat,
        longitude: matched.lon,
      });
      if (mapInstanceRef.current?.map) {
        mapInstanceRef.current.map.setView([matched.lat, matched.lon], 16);
      }
      if (modalMapInstanceRef.current?.map) {
        modalMapInstanceRef.current.map.setView([matched.lat, matched.lon], 16);
      }
      return;
    }

    // Live OpenStreetMap Nominatim search
    try {
      setIsSearching(true);
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery + ", Assam, India"
        )}`
      );
      const data = await res.json();
      setIsSearching(false);

      if (data && data.length > 0) {
        const first = data[0];
        const newLat = Number(Number(first.lat).toFixed(4));
        const newLon = Number(Number(first.lon).toFixed(4));
        const shortName = first.display_name.split(",")[0];

        onLocationChange({
          name: `${shortName}, Assam`,
          latitude: newLat,
          longitude: newLon,
        });

        if (mapInstanceRef.current?.map) {
          mapInstanceRef.current.map.setView([newLat, newLon], 16);
        }
        if (modalMapInstanceRef.current?.map) {
          modalMapInstanceRef.current.map.setView([newLat, newLon], 16);
        }
      }
    } catch {
      setIsSearching(false);
    }
  };

  // Zoom helpers
  const handleZoomIn = (isModal = false) => {
    const target = isModal
      ? modalMapInstanceRef.current?.map
      : mapInstanceRef.current?.map;
    if (target) target.zoomIn();
  };

  const handleZoomOut = (isModal = false) => {
    const target = isModal
      ? modalMapInstanceRef.current?.map
      : mapInstanceRef.current?.map;
    if (target) target.zoomOut();
  };

  // Use my location (GPS)
  const handleGps = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = Number(pos.coords.latitude.toFixed(4));
          const lon = Number(pos.coords.longitude.toFixed(4));
          onLocationChange({
            name: "My GPS Location",
            latitude: lat,
            longitude: lon,
          });
          if (mapInstanceRef.current?.map) {
            mapInstanceRef.current.map.setView([lat, lon], 17);
          }
          if (modalMapInstanceRef.current?.map) {
            modalMapInstanceRef.current.map.setView([lat, lon], 17);
          }
        },
        () => {
          onLocationChange({
            name: "Kamrup, Assam",
            latitude: 26.18,
            longitude: 91.75,
          });
        }
      );
    }
  };

  return (
    <div className="farm-map-component">
      {/* Search & GPS Pickers (Row A & B matching Image 1) */}
      <div className="map-input-row">
        <div className="input-group-search">
          <label htmlFor="village-search-input" className="input-sublabel">
            A. Type your village or town
          </label>
          <form onSubmit={handleSearch} className="search-form">
            <input
              id="village-search-input"
              type="text"
              placeholder="Example: Hajo, Rangia, Palashbari..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="town-search-input"
            />
            <button type="submit" className="btn-search-submit" disabled={isSearching}>
              {isSearching ? "Searching..." : "Search"}
            </button>
          </form>
        </div>

        <div className="input-group-gps">
          <span className="input-sublabel">B. Use your phone GPS</span>
          <button type="button" onClick={handleGps} className="btn-use-gps">
            Use my location
          </button>
        </div>
      </div>

      <div className="map-instruction-label">
        C. Then tap on your field in the satellite photo
      </div>

      {/* Embedded Map Box */}
      <div className="map-frame">
        <div ref={mapContainerRef} className="leaflet-mount-container" />

        {/* Mode Selector Top Left: Tap on field vs Connect 4 dots */}
        <div className="map-mode-selector">
          <button
            type="button"
            onClick={() => {
              setSelectionMode("tap");
              setCornerDots([]);
            }}
            className={`mode-btn ${selectionMode === "tap" ? "active" : ""}`}
            title="Tap once anywhere to place your field"
          >
            Tap on your field
          </button>
          <button
            type="button"
            onClick={() => {
              setSelectionMode("dots");
              setCornerDots([]);
            }}
            className={`mode-btn ${selectionMode === "dots" ? "active" : ""}`}
            title="Click 4 corner points to connect dots around your plot"
          >
            Connect 4 dots {cornerDots.length > 0 && `(${cornerDots.length}/4)`}
          </button>
        </div>

        {/* Top Right Maximize Button */}
        <button
          type="button"
          onClick={() => setIsMaximized(true)}
          className="btn-map-control btn-maximize"
          title="Maximize map to full screen"
          aria-label="Maximize map"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
        </button>

        {/* Zoom Controls */}
        <div className="map-zoom-controls">
          <button
            type="button"
            onClick={() => handleZoomIn(false)}
            className="btn-zoom"
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            onClick={() => handleZoomOut(false)}
            className="btn-zoom"
            title="Zoom out"
          >
            &minus;
          </button>
        </div>

        {/* Bottom Left Satellite / Map Switcher */}
        <div className="map-type-toggle">
          <button
            type="button"
            onClick={() => setMapType("satellite")}
            className={`type-btn ${mapType === "satellite" ? "active" : ""}`}
          >
            Satellite
          </button>
          <button
            type="button"
            onClick={() => setMapType("map")}
            className={`type-btn ${mapType === "map" ? "active" : ""}`}
          >
            Map
          </button>
        </div>

        {/* Attribution watermark */}
        <div className="satellite-watermark">
          Real satellite imagery loaded via NASA/Esri
        </div>
      </div>

      {/* Below Map: Field pill, size input, and helpful notes */}
      <div className="map-bottom-bar">
        <div className="field-info-pill">
          Field marked near {location.name}
        </div>

        <div className="field-size-wrap">
          <label htmlFor="field-size-input" className="field-size-label">
            Field size
          </label>
          <input
            id="field-size-input"
            type="number"
            min="0.1"
            step="0.5"
            value={fieldSize}
            onChange={(e) => onFieldSizeChange(e.target.value)}
            className="field-size-input"
          />
          <select
            value={fieldUnit}
            onChange={(e) => onFieldUnitChange(e.target.value)}
            className="field-unit-select"
            aria-label="Field size unit"
          >
            <option value="Bigha">Bigha</option>
            <option value="Acre">Acre</option>
            <option value="Hectare">Hectare</option>
            <option value="Katha">Katha</option>
          </select>
        </div>
      </div>

      <p className="map-foot-caption">
        {selectionMode === "dots"
          ? `Tap 4 corners of your field (${cornerDots.length}/4 dots placed). Click any point to start fresh.`
          : "No need to draw the edges. One tap on your field is enough, or choose 'Connect 4 dots' above."}
      </p>

      {/* FULLSCREEN MAXIMIZED MAP MODAL (Matching Image 2) */}
      {isMaximized && (
        <div className="fullscreen-map-modal" role="dialog" aria-modal="true">
          {/* Top Bar */}
          <div className="modal-top-bar">
            <button
              type="button"
              onClick={() => setIsMaximized(false)}
              className="btn-modal-close"
            >
              &times; Close map
            </button>

            <form onSubmit={handleSearch} className="modal-search-form">
              <input
                type="text"
                placeholder="Type your village or town (e.g. Hajo, Guwahati)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="modal-search-input"
              />
            </form>

            <button
              type="button"
              onClick={handleGps}
              className="btn-modal-gps"
            >
              Use my location
            </button>
          </div>

          {/* Modal Map Mount */}
          <div className="modal-map-mount">
            <div ref={modalMapContainerRef} className="leaflet-modal-container" />

            {/* Mode Selector in Modal */}
            <div className="modal-mode-badge-wrap">
              <div className="map-mode-selector">
                <button
                  type="button"
                  onClick={() => {
                    setSelectionMode("tap");
                    setCornerDots([]);
                  }}
                  className={`mode-btn ${selectionMode === "tap" ? "active" : ""}`}
                >
                  Tap on your field
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectionMode("dots");
                    setCornerDots([]);
                  }}
                  className={`mode-btn ${selectionMode === "dots" ? "active" : ""}`}
                >
                  Connect 4 dots {cornerDots.length > 0 && `(${cornerDots.length}/4)`}
                </button>
              </div>
            </div>

            {/* Modal Zoom Controls */}
            <div className="map-zoom-controls modal-zoom">
              <button
                type="button"
                onClick={() => handleZoomIn(true)}
                className="btn-zoom"
              >
                +
              </button>
              <button
                type="button"
                onClick={() => handleZoomOut(true)}
                className="btn-zoom"
              >
                &minus;
              </button>
            </div>

            {/* Floating Instructions Card (Bottom-Left) */}
            <div className="modal-how-to-card">
              <h4 className="how-to-title">How to mark your field</h4>
              <ol className="how-to-steps">
                <li>Type your village or use GPS</li>
                <li>Zoom in until you see your field</li>
                <li>Tap on your field or connect 4 dots</li>
                <li>Drag the red pin if it is not right</li>
              </ol>
            </div>

            {/* Center Confirmation Button (Bottom-Center) */}
            <div className="modal-confirm-wrap">
              <button
                type="button"
                onClick={() => setIsMaximized(false)}
                className="btn-confirm-field"
              >
                This is my field
              </button>
            </div>

            {/* Satellite / Map Switcher (Bottom-Right) */}
            <div className="map-type-toggle modal-type-toggle">
              <button
                type="button"
                onClick={() => setMapType("satellite")}
                className={`type-btn ${mapType === "satellite" ? "active" : ""}`}
              >
                Satellite
              </button>
              <button
                type="button"
                onClick={() => setMapType("map")}
                className={`type-btn ${mapType === "map" ? "active" : ""}`}
              >
                Map
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
