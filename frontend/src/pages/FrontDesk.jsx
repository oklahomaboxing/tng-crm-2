import React, { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function FrontDesk() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submitCheckin(e) {
    e.preventDefault();
    if (!code.trim()) return;

    setError("");
    setResult(null);

    try {
      const r = await fetch(`${API}/api/checkin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
        body: JSON.stringify({ code }),
      });

      const j = await r.json();

      if (!r.ok) {
        throw new Error(j.detail || "Check-in failed");
      }

      setResult(j.member);
      setCode("");

      setTimeout(() => {
        setResult(null);
        inputRef.current?.focus();
      }, 3500);
    } catch (err) {
      setError(err.message);
      setCode("");
      inputRef.current?.focus();
    }
  }

  return (
    <main style={styles.page}>
      <section style={styles.card}>
        <h1>🥊 TNG BOXING</h1>
        <h2>Front Desk Check-In</h2>

        <form onSubmit={submitCheckin}>
          <input
            ref={inputRef}
            style={styles.input}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Scan barcode, QR code, or type member number"
            autoFocus
          />
          <button style={styles.button}>Check In</button>
        </form>

        {error && <div style={styles.error}>❌ {error}</div>}

        {result ? (
          <div style={styles.success}>
            <h1>✅ WELCOME!</h1>
            <h2>{result.name}</h2>
            <p><b>Status:</b> {result.status || "active"}</p>
            <p><b>Membership:</b> {result.membership || "Membership"}</p>
            <p><b>Member #:</b> {result.member_number}</p>
            <p><b>Total Visits:</b> {result.total_checkins || 0}</p>
          </div>
        ) : (
          <div style={styles.waiting}>
            Waiting for member scan...
          </div>
        )}
      </section>
    </main>
  );
}

const styles = {
  page: {
    minHeight: "75vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#0b0b0f",
    color: "white",
    borderRadius: 18,
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 760,
    textAlign: "center",
  },
  input: {
    width: "100%",
    padding: 20,
    fontSize: 22,
    borderRadius: 14,
    border: "3px solid #d71920",
    textAlign: "center",
    marginTop: 20,
    boxSizing: "border-box",
  },
  button: {
    marginTop: 14,
    padding: 16,
    width: "100%",
    borderRadius: 12,
    border: 0,
    background: "#d71920",
    color: "white",
    fontSize: 20,
    fontWeight: "bold",
    cursor: "pointer",
  },
  waiting: {
    marginTop: 30,
    padding: 24,
    background: "#181820",
    borderRadius: 16,
    fontSize: 22,
  },
  success: {
    marginTop: 30,
    padding: 28,
    background: "#0f7a34",
    borderRadius: 18,
    fontSize: 22,
  },
  error: {
    marginTop: 24,
    padding: 20,
    background: "#7a1010",
    borderRadius: 14,
    fontSize: 20,
  },
};