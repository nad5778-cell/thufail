const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function getPicSummary() {
  return get("/api/pic/summary");
}

export function getPicRecords(picCode, { limit = 200, offset = 0 } = {}) {
  return get(`/api/pic/${encodeURIComponent(picCode)}/records?limit=${limit}&offset=${offset}`);
}

export function getNationalIdentityAnomalies(picCode) {
  return get(`/api/pic/${encodeURIComponent(picCode)}/anomalies/national-identity`);
}

export function getNationalIdentityAnomaliesDownloadUrl(picCode) {
  return `${BASE_URL}/api/pic/${encodeURIComponent(picCode)}/anomalies/national-identity.xlsx`;
}
