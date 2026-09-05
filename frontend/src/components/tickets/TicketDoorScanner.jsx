import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Html5QrcodeScanner,
} from "html5-qrcode";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const SCANNER_ID =
  "tng-event-ticket-scanner";

export default function TicketDoorScanner() {
  const scannerRef = useRef(null);

  const [token, setToken] =
    useState("");

  const [result, setResult] =
    useState(null);

  const [error, setError] =
    useState("");

  const [active, setActive] =
    useState(false);

  const [working, setWorking] =
    useState(false);

  useEffect(() => {
    return () => {
      stopScanner();
    };
  }, []);

  async function scanTicket(
    rawToken
  ) {
    const value = String(
      rawToken || ""
    ).trim();

    if (!value || working) return;

    setWorking(true);
    setResult(null);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/ticketing/scan`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
            Authorization:
              `Bearer ${localStorage.getItem(
                "token"
              )}`,
          },
          body: JSON.stringify({
            token: value,
          }),
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Ticket scan failed"
        );
      }

      setResult(body);
      setToken("");

      if (navigator.vibrate) {
        navigator.vibrate(
          body.ok
            ? 150
            : [150, 100, 150]
        );
      }
    } catch (err) {
      setError(
        err.message ||
        "Ticket scan failed"
      );

      if (navigator.vibrate) {
        navigator.vibrate([
          150,
          100,
          150,
        ]);
      }
    } finally {
      setWorking(false);
    }
  }

  async function startScanner() {
    if (
      scannerRef.current ||
      active
    ) {
      return;
    }

    setResult(null);
    setError("");
    setActive(true);

    const scanner =
      new Html5QrcodeScanner(
        SCANNER_ID,
        {
          fps: 12,
          qrbox: {
            width: 280,
            height: 280,
          },
          rememberLastUsedCamera:
            true,
          supportedScanTypes: [
            0,
            1,
          ],
          aspectRatio: 1.333334,
        },
        false
      );

    scannerRef.current =
      scanner;

    scanner.render(
      async (decodedText) => {
        await stopScanner();
        await scanTicket(
          decodedText
        );
      },
      () => {}
    );
  }

  async function stopScanner() {
    const scanner =
      scannerRef.current;

    if (!scanner) {
      setActive(false);
      return;
    }

    try {
      await scanner.clear();
    } catch (err) {
      console.warn(
        "Ticket scanner cleanup:",
        err
      );
    } finally {
      scannerRef.current =
        null;
      setActive(false);
    }
  }

  function reset() {
    setResult(null);
    setError("");
    setToken("");
  }

  return (
    <section style={styles.wrap}>
      <div style={styles.header}>
        <div>
          <h2
            style={{
              margin: 0,
            }}
          >
            Fight Night Door Scanner
          </h2>

          <div
            style={styles.sub}
          >
            Scan each ticket once.
            Duplicate scans will be
            rejected.
          </div>
        </div>

        {!active ? (
          <button
            style={styles.button}
            onClick={startScanner}
          >
            Start Camera
          </button>
        ) : (
          <button
            style={styles.darkButton}
            onClick={stopScanner}
          >
            Stop Camera
          </button>
        )}
      </div>

      {result && (
        <div
          style={
            result.ok
              ? styles.admit
              : styles.reject
          }
        >
          <div
            style={styles.bigStatus}
          >
            {result.ok
              ? "ADMIT"
              : "DO NOT ADMIT"}
          </div>

          <div>
            {result.result}
          </div>

          {result.ticket_number && (
            <strong>
              {
                result.ticket_number
              }
            </strong>
          )}

          <button
            style={{
              ...styles.darkButton,
              marginTop: 15,
            }}
            onClick={reset}
          >
            Scan Next Ticket
          </button>
        </div>
      )}

      {error && (
        <div style={styles.reject}>
          <div
            style={styles.bigStatus}
          >
            DO NOT ADMIT
          </div>

          <div>{error}</div>

          <button
            style={{
              ...styles.darkButton,
              marginTop: 15,
            }}
            onClick={reset}
          >
            Try Again
          </button>
        </div>
      )}

      {!result && !error && (
        <>
          <div
            id={SCANNER_ID}
            style={{
              marginTop: 18,
            }}
          />

          <div
            style={styles.manual}
          >
            <input
              value={token}
              placeholder="Manual ticket code / scanner input"
              onChange={(e) =>
                setToken(
                  e.target.value
                )
              }
              style={styles.input}
            />

            <button
              style={styles.button}
              disabled={working}
              onClick={() =>
                scanTicket(token)
              }
            >
              {working
                ? "Checking..."
                : "Check Ticket"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

const styles = {
  wrap: {
    marginTop: 35,
    padding: 22,
    border:
      "2px solid #111",
    borderRadius: 14,
    background: "#fff",
  },

  header: {
    display: "flex",
    justifyContent:
      "space-between",
    alignItems: "center",
    gap: 12,
    flexWrap: "wrap",
  },

  sub: {
    color: "#666",
    marginTop: 5,
  },

  manual: {
    display: "flex",
    gap: 10,
    marginTop: 18,
    flexWrap: "wrap",
  },

  input: {
    flex: 1,
    minWidth: 240,
    padding: 13,
    borderRadius: 8,
    border:
      "1px solid #aaa",
  },

  button: {
    border: 0,
    borderRadius: 8,
    padding: "12px 18px",
    background: "#d71920",
    color: "white",
    fontWeight: 900,
    cursor: "pointer",
  },

  darkButton: {
    border: 0,
    borderRadius: 8,
    padding: "12px 18px",
    background: "#111",
    color: "white",
    fontWeight: 800,
    cursor: "pointer",
  },

  admit: {
    marginTop: 20,
    padding: 28,
    borderRadius: 14,
    background: "#dff5e4",
    border:
      "3px solid #159447",
    textAlign: "center",
  },

  reject: {
    marginTop: 20,
    padding: 28,
    borderRadius: 14,
    background: "#ffe1e1",
    border:
      "3px solid #c1121f",
    textAlign: "center",
  },

  bigStatus: {
    fontWeight: 1000,
    fontSize: 38,
    marginBottom: 8,
  },
};
