/**
 * api.js
 * Client service to communicate with the FastAPI Field Shift backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error("Backend service unreachable");
  return res.json();
}

export async function fetchCrops() {
  const res = await fetch(`${API_BASE_URL}/crops`);
  if (!res.ok) throw new Error("Failed to fetch crop catalog");
  return res.json();
}

export async function fetchRecommendations(payload) {
  const res = await fetch(`${API_BASE_URL}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to generate recommendation plan");
  }

  return res.json();
}

export async function fetchAboutInfo() {
  const res = await fetch(`${API_BASE_URL}/about`);
  if (!res.ok) throw new Error("Failed to fetch educational info");
  return res.json();
}
