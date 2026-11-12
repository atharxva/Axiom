// In production, when served by FastAPI or via reverse proxy, API_BASE is empty (relative /api).
// In local development, if VITE_API_URL is set or if running on Vite dev server (port 5173), fallback to localhost:8000.
export const API_BASE = import.meta.env.VITE_API_BASE || (window.location.port === "5173" ? "http://localhost:8000" : "");

