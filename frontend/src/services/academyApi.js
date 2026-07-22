const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("token") || "";
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Academy request failed");
  return data;
}

export const academyApi = {
  dashboard: () => request("/api/academy/dashboard"),
  programs: () => request("/api/academy/programs"),
  createProgram: (payload) => request("/api/academy/programs", { method: "POST", body: JSON.stringify(payload) }),
  classes: () => request("/api/academy/classes"),
  createClass: (payload) => request("/api/academy/classes", { method: "POST", body: JSON.stringify(payload) }),
  sessions: () => request("/api/academy/sessions"),
  startSession: (payload) => request("/api/academy/sessions", { method: "POST", body: JSON.stringify(payload) }),
  completeSession: (id, payload) => request(`/api/academy/sessions/${id}`, { method: "PATCH", body: JSON.stringify({ ...payload, status: "completed" }) }),
};
