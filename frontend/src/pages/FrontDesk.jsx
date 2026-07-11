import React, { useEffect, useRef, useState } from "react";
import { Html5QrcodeScanner } from "html5-qrcode";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const SCANNER_ID = "tng-tablet-checkin-scanner";

export default function FrontDesk() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [checkingIn, setCheckingIn] = useState(false);
  const [scannerActive, setScannerActive] = useState(false);
  const [kioskMode, setKioskMode] = useState(true);

  const inputRef = useRef(null);
  const scannerRef = useRef(null);
  const resetTimerRef = useRef(null);

  useEffect(() => {
    if (kioskMode) {
      startScanner();
    } else {
      inputRef.current?.focus();
    }

    return () => {
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
      stopScanner();
    };
  }, [kioskMode]);

  async function checkInMember(rawCode) {
    const normalizedCode = String(rawCode || "").trim();
    if (!normalizedCode || checkingIn) return;

    setCheckingIn(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API}/api/checkin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ code: normalizedCode }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Check-in failed");

      setResult(data.member);
      setCode("");
      if (navigator.vibrate) navigator.vibrate(150);

      resetTimerRef.current = setTimeout(() => {
        setResult(null);
        setError("");
        if (kioskMode) startScanner();
        else inputRef.current?.focus();
      }, 3500);
    } catch (err) {
      setError(err.message || "Check-in failed");
      setCode("");
      if (navigator.vibrate) navigator.vibrate([150, 100, 150]);

      resetTimerRef.current = setTimeout(() => {
        setError("");
        if (kioskMode) startScanner();
        else inputRef.current?.focus();
      }, 3500);
    } finally {
      setCheckingIn(false);
    }
  }

  async function submitCheckin(event) {
    event.preventDefault();
    await checkInMember(code);
  }

  function startScanner() {
    if (scannerRef.current || result || error) return;

    setScannerActive(true);

    const scanner = new Html5QrcodeScanner(
      SCANNER_ID,
      {
        fps: 12,
        qrbox: { width: 280, height: 220 },
        rememberLastUsedCamera: true,
        supportedScanTypes: [0, 1],
        aspectRatio: 1.333334,
      },
      false
    );

    scannerRef.current = scanner;

    scanner.render(
      async (decodedText) => {
        await stopScanner();
        await checkInMember(decodedText);
      },
      () => {}
    );
  }

  async function stopScanner() {
    const scanner = scannerRef.current;

    if (!scanner) {
      setScannerActive(false);
      return;
    }

    try {
      await scanner.clear();
    } catch (err) {
      console.warn("Scanner cleanup warning:", err);
    } finally {
      scannerRef.current = null;
      setScannerActive(false);
    }
  }

  async function toggleKioskMode() {
    if (kioskMode) {
      await stopScanner();
      setKioskMode(false);
      inputRef.current?.focus();
    } else {
      setKioskMode(true);
    }
  }

  async function enterFullscreen() {
    if (document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
    }
  }

  function resetScreen() {
    if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    setResult(null);
    setError("");
    setCode("");
    if (kioskMode) startScanner();
    else inputRef.current?.focus();
  }

  return (
    <main style={result ? styles.pageSuccess : error ? styles.pageError : styles.page}>
      <section style={styles.shell}>
        <header style={styles.header}>
          <div>
            <div style={styles.brand}>TNG BOXING</div>
            <div style={styles.subtitle}>TABLET CHECK-IN</div>
          </div>

          <div style={styles.headerActions}>
            <button type="button" style={styles.smallButton} onClick={enterFullscreen}>
              Full Screen
            </button>
            <button type="button" style={styles.smallButton} onClick={toggleKioskMode}>
              {kioskMode ? "Manual Mode" : "Camera Mode"}
            </button>
          </div>
        </header>

        {result ? (
          <section style={styles.successCard} onClick={resetScreen}>
            <div style={styles.statusIcon}>✓</div>
            <div style={styles.successLabel}>CHECK-IN COMPLETE</div>
            <h1 style={styles.memberName}>{result.name}</h1>

            <div style={styles.infoGrid}>
              <Info label="Status" value={result.status || "active"} />
              <Info label="Membership" value={result.membership || "Membership"} />
              <Info label="Member #" value={result.member_number || "-"} />
              <Info label="Total Visits" value={result.total_checkins || 0} />
            </div>

            <div style={styles.tapMessage}>Tap anywhere for the next member</div>
          </section>
        ) : error ? (
          <section style={styles.errorCard} onClick={resetScreen}>
            <div style={styles.statusIcon}>✕</div>
            <div style={styles.errorTitle}>CHECK-IN FAILED</div>
            <div style={styles.errorMessage}>{error}</div>
            <div style={styles.tapMessage}>Tap anywhere to try again</div>
          </section>
        ) : kioskMode ? (
          <section style={styles.scannerCard}>
            <div style={styles.scanTitle}>Hold your QR code in front of the camera</div>
            <div style={styles.scanSubtitle}>
              Membership cards and barcodes can also be scanned.
            </div>

            <div style={styles.scannerFrame}>
              <div id={SCANNER_ID} style={styles.scannerContainer} />
            </div>

            {!scannerActive && (
              <button type="button" style={styles.primaryButton} onClick={startScanner}>
                Start Camera
              </button>
            )}

            {checkingIn && <div style={styles.processing}>Checking member in...</div>}
          </section>
        ) : (
          <section style={styles.manualCard}>
            <div style={styles.scanTitle}>Manual or handheld scanner check-in</div>

            <form onSubmit={submitCheckin}>
              <input
                ref={inputRef}
                style={styles.input}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Scan or enter member number"
                autoComplete="off"
                disabled={checkingIn}
              />

              <button
                type="submit"
                style={{ ...styles.primaryButton, opacity: checkingIn ? 0.65 : 1 }}
                disabled={checkingIn}
              >
                {checkingIn ? "Checking In..." : "Check In"}
              </button>
            </form>
          </section>
        )}
      </section>
    </main>
  );
}

function Info({ label, value }) {
  return (
    <div style={styles.infoItem}>
      <span style={styles.infoLabel}>{label}</span>
      <span style={styles.infoValue}>{value}</span>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "calc(100vh - 110px)",
    background: "#07070a",
    color: "white",
    borderRadius: 20,
    padding: "clamp(14px, 3vw, 28px)",
    boxSizing: "border-box",
  },
  pageSuccess: {
    minHeight: "calc(100vh - 110px)",
    background: "#053817",
    color: "white",
    borderRadius: 20,
    padding: "clamp(14px, 3vw, 28px)",
    boxSizing: "border-box",
  },
  pageError: {
    minHeight: "calc(100vh - 110px)",
    background: "#4b0808",
    color: "white",
    borderRadius: 20,
    padding: "clamp(14px, 3vw, 28px)",
    boxSizing: "border-box",
  },
  shell: { width: "100%", maxWidth: 1000, margin: "0 auto" },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 16,
    flexWrap: "wrap",
    marginBottom: 20,
  },
  brand: { fontSize: "clamp(28px, 5vw, 46px)", fontWeight: 900, letterSpacing: 2 },
  subtitle: {
    marginTop: 3,
    color: "#c9c9ce",
    fontSize: "clamp(13px, 2vw, 18px)",
    letterSpacing: 3,
  },
  headerActions: { display: "flex", gap: 10, flexWrap: "wrap" },
  smallButton: {
    minHeight: 44,
    padding: "10px 14px",
    borderRadius: 12,
    border: "1px solid #3b3b44",
    background: "#18181f",
    color: "white",
    fontWeight: 800,
    cursor: "pointer",
  },
  scannerCard: {
    background: "#111118",
    border: "1px solid #292934",
    borderRadius: 22,
    padding: "clamp(18px, 4vw, 34px)",
    textAlign: "center",
    boxShadow: "0 20px 60px rgba(0,0,0,.3)",
  },
  manualCard: {
    background: "#111118",
    border: "1px solid #292934",
    borderRadius: 22,
    padding: "clamp(20px, 5vw, 40px)",
    textAlign: "center",
  },
  scanTitle: { fontSize: "clamp(22px, 4vw, 34px)", fontWeight: 900 },
  scanSubtitle: {
    marginTop: 8,
    marginBottom: 20,
    color: "#c7c7cc",
    fontSize: "clamp(14px, 2.5vw, 18px)",
  },
  scannerFrame: {
    maxWidth: 700,
    margin: "0 auto",
    padding: 12,
    background: "white",
    borderRadius: 18,
    overflow: "hidden",
  },
  scannerContainer: { width: "100%" },
  input: {
    width: "100%",
    padding: "clamp(18px, 4vw, 28px)",
    fontSize: "clamp(20px, 4vw, 30px)",
    textAlign: "center",
    borderRadius: 16,
    border: "4px solid #d71920",
    boxSizing: "border-box",
    outline: "none",
    marginTop: 22,
  },
  primaryButton: {
    width: "100%",
    minHeight: 62,
    marginTop: 16,
    padding: "16px 20px",
    borderRadius: 14,
    border: 0,
    background: "#d71920",
    color: "white",
    fontSize: "clamp(18px, 3vw, 24px)",
    fontWeight: 900,
    cursor: "pointer",
  },
  processing: { marginTop: 16, fontSize: 18, fontWeight: 800, color: "#ffd37a" },
  successCard: {
    background: "#0f7a34",
    borderRadius: 24,
    padding: "clamp(26px, 6vw, 54px)",
    textAlign: "center",
    boxShadow: "0 24px 70px rgba(0,0,0,.35)",
    cursor: "pointer",
  },
  errorCard: {
    background: "#8a1111",
    borderRadius: 24,
    padding: "clamp(26px, 6vw, 54px)",
    textAlign: "center",
    boxShadow: "0 24px 70px rgba(0,0,0,.35)",
    cursor: "pointer",
  },
  statusIcon: { fontSize: "clamp(70px, 12vw, 110px)", lineHeight: 1, fontWeight: 900 },
  successLabel: {
    marginTop: 14,
    fontSize: "clamp(16px, 3vw, 24px)",
    fontWeight: 900,
    letterSpacing: 2,
  },
  errorTitle: { marginTop: 14, fontSize: "clamp(24px, 5vw, 42px)", fontWeight: 900 },
  errorMessage: { marginTop: 12, fontSize: "clamp(18px, 3vw, 26px)" },
  memberName: { margin: "12px 0 24px", fontSize: "clamp(30px, 6vw, 58px)" },
  infoGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: 14,
  },
  infoItem: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    padding: 18,
    borderRadius: 16,
    background: "rgba(0,0,0,.22)",
  },
  infoLabel: {
    color: "#d6f5df",
    fontSize: 13,
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  infoValue: {
    fontSize: "clamp(18px, 3vw, 28px)",
    fontWeight: 900,
    textTransform: "capitalize",
    overflowWrap: "anywhere",
  },
  tapMessage: { marginTop: 24, fontSize: 15, color: "rgba(255,255,255,.8)" },
};