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

      if (!r.ok) throw new Error(j.detail || "Check-in failed");

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
    <main style={result ? styles.pageSuccess : styles.page}>
      <section style={styles.card}>
        <div style={styles.brand}>🥊 TNG BOXING</div>
        <div style={styles.subTitle}>FRONT DESK CHECK-IN</div>

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
            <div style={styles.bigCheck}>✅</div>
            <h1>WELCOME!</h1>
            <h2>{result.name}</h2>

            <div style={styles.infoGrid}>
              <div><b>Status</b><span>{result.status || "active"}</span></div>
              <div><b>Membership</b><span>{result.membership || "Membership"}</span></div>
              <div><b>Member #</b><span>{result.member_number}</span></div>
              <div><b>Total Visits</b><span>{result.total_checkins || 0}</span></div>
            </div>
          </div>
        ) : (
          <div style={styles.waiting}>
            <h2>Ready for next member</h2>
            <p>Scan barcode or enter member number</p>
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
  pageSuccess: {
    minHeight: "75vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#063b19",
    color: "white",
    borderRadius: 18,
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 900,
    textAlign: "center",
  },
  brand: {
    fontSize: 42,
    fontWeight: "900",
    letterSpacing: 2,
  },
  subTitle: {
    fontSize: 20,
    color: "#ddd",
    marginBottom: 25,
    letterSpacing: 3,
  },
  input: {
    width: "100%",
    padding: 24,
    fontSize: 26,
    borderRadius: 16,
    border: "4px solid #d71920",
    textAlign: "center",
    boxSizing: "border-box",
  },
  button: {
    marginTop: 14,
    padding: 18,
    width: "100%",
    borderRadius: 14,
    border: 0,
    background: "#d71920",
    color: "white",
    fontSize: 22,
    fontWeight: "bold",
    cursor: "pointer",
  },
  waiting: {
    marginTop: 35,
    padding: 35,
    background: "#181820",
    borderRadius: 20,
    fontSize: 24,
  },
  success: {
    marginTop: 35,
    padding: 40,
    background: "#0f7a34",
    borderRadius: 22,
    fontSize: 24,
    boxShadow: "0 20px 60px rgba(0,0,0,.35)",
  },
  bigCheck: {
    fontSize: 70,
  },
  infoGrid: {
    marginTop: 25,
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 16,
  },
  error: {
    marginTop: 24,
    padding: 24,
    background: "#7a1010",
    borderRadius: 16,
    fontSize: 22,
  },
};