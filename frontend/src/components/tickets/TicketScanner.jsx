import { useState } from "react";
import axios from "axios";

export default function TicketScanner({ eventId }) {
  const [result, setResult] = useState(null);
  const token = localStorage.getItem("token");

  async function handleToken(scannedToken) {
    try {
      const { data } = await axios.post("/api/ticketing/scan", {
        event_id: eventId,
        token: scannedToken,
        device_label: navigator.userAgent
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResult(data);
    } catch {
      setResult({ok:false, result:"error"});
    }
  }

  // Wire handleToken() into the camera scanner component TNG OS already uses
  // for front-desk QR/barcode scanning.
  return (
    <div>
      <h2>Door Scanner</h2>
      {result && (
        <div>
          <strong>{result.ok ? "ADMIT" : "DO NOT ADMIT"}</strong>
          <div>{result.result}</div>
          {result.ticket_number && <div>{result.ticket_number}</div>}
        </div>
      )}
    </div>
  );
}
