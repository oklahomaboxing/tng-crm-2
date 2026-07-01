export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function authHeaders() {
  return {
    Authorization: "Bearer " + localStorage.getItem("token"),
  };
}