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
  "https://sea-lion-app-2-gxyfr.ondigitalocean.app";

const SCANNER_ID =
  "tng-event-ticket-scanner";

export default function TicketDoorScanner({ eventId, mode = "checkin" }) {
  const scannerRef = useRef(null);
  const busyRef = useRef(false);
  const [review,setReview] = useState(null);
  const activation=mode === "activation";

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

    if (!value || busyRef.current) return;
    if (!eventId) { setError("Select an event before scanning tickets."); return; }

    busyRef.current=true;
    setWorking(true);
    setResult(null);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/ticketing/${activation ? "paper-tickets/resolve" : "scan"}`,
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
            event_id: Number(eventId),
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

      if(activation)setReview(body);else setResult(body);
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
      busyRef.current=false;
      setWorking(false);
    }
  }

  async function activateTicket() {
    if(!review || busyRef.current)return;
    if(!window.confirm(`Confirm cash payment of $${(review.price_cents/100).toFixed(2)} received for ${review.ticket_number}? This records a cash sale and commission. It does not charge a card or check anyone in.`))return;
    busyRef.current=true;setWorking(true);setError('');
    try{
      const response=await fetch(`${API}/api/ticketing/paper-batches/${review.batch_id}/record-sales`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${localStorage.getItem('token')}`},body:JSON.stringify({ticket_ids:[review.ticket_id],confirm_total_cents:review.price_cents})});
      const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Could not record sale');
      setReview(null);setResult({ok:true,result:body.new_sales_recorded?'Sale recorded. Ticket activated. Use door check-in separately for admission.':'Sale was already recorded. Check admission status; do not collect payment again.',ticket_number:review.ticket_number});
    }catch(e){setError(e.message+' Refresh and check the batch before retrying if the connection failed.');}
    finally{busyRef.current=false;setWorking(false);}
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
    setReview(null);
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
            {activation ? "Activate Paper Ticket" : "Fight Night Door Scanner"}
          </h2>

          <div
            style={styles.sub}
          >
            {activation ? "For cash paper sales: scan, review, then confirm cash payment. Clover purchases activate automatically after verified payment. Activation does not admit the customer." : "Scan each ticket once. Duplicate scans will be rejected."}
          </div>
        </div>

        {!active ? (
          <button
            style={styles.button}
            onClick={startScanner}
            disabled={working || !!review}
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

      {review && !error && <div style={styles.reject}>
        <h3>Confirm cash payment received</h3><strong>{review.ticket_number}</strong>
        <p>{review.ticket_type_name} · {review.seller_name}</p><p>Face value: <strong>${(review.price_cents/100).toFixed(2)}</strong></p>
        <p>Only confirm after collecting payment. This records a cash sale and fighter commission; it does not charge a card or admit anyone.</p>
        <button style={styles.button} disabled={working} onClick={activateTicket}>{working?'Recording…':'Cash received — activate ticket'}</button>
        <button style={{...styles.darkButton,marginLeft:10}} disabled={working} onClick={reset}>Cancel</button>
      </div>}
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
              ? (activation ? "ACTIVATION RESULT" : "ADMIT")
              : "DO NOT ADMIT"}
          </div>

          <div>
            {result.result === "not_activated" ? "Paper ticket not activated. Ask staff to verify and record the sale." : result.result}
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

      {!result && !error && !review && (
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
                : activation ? "Look up paper ticket" : "Check Ticket"}
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
