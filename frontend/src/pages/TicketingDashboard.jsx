import React, { useEffect, useState } from "react";
import EventTicketSales from "./EventTicketSales.jsx";
import TicketDoorScanner from "../components/tickets/TicketDoorScanner.jsx";

const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const API = API_BASE;

function authHeaders() {
  const token = localStorage.getItem("token");

  return {
    Authorization: `Bearer ${token}`,
  };
}

function money(cents) {
  return `$${((Number(cents) || 0) / 100).toFixed(2)}`;
}

export default function TicketingDashboard() {
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [summary, setSummary] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [sellerQr, setSellerQr] = useState(null);
  const [sellerQrOpen, setSellerQrOpen] = useState(false);
  const [sellerActionMessage, setSellerActionMessage] = useState("");

  async function loadEvents() {
    try {
      const response = await fetch(`${API}/api/boxing/events`, {
        headers: authHeaders(),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load events");
      }

      const rows = Array.isArray(data) ? data : [];
      setEvents(rows);

      if (!eventId && rows.length > 0) {
        setEventId(String(rows[0].id));
      }
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function loadSummary(selectedEventId = eventId) {
    if (!selectedEventId) return;

    try {
      const response = await fetch(
        `${API}/api/ticketing/events/${selectedEventId}/report`,
        {
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load ticket report");
      }

      setSummary(data);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function downloadReport(path, filename) {
    try {
      setBusy(true);
      setMessage("");

      const response = await fetch(`${API}${path}`, {
        headers: authHeaders(),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Download failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function emailSellerReports() {
    if (!eventId) return;

    try {
      setBusy(true);
      setMessage("");

      const response = await fetch(
        `${API}/api/ticketing/events/${eventId}/email-seller-reports`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not email reports");
      }

      const sent =
        data.reports?.filter((item) => item.status === "sent").length || 0;

      setMessage(`${sent} seller report(s) emailed successfully.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    if (eventId) {
      loadSummary(eventId);
    }
  }, [eventId]);

  const selectedEvent = events.find(
    (event) => String(event.id) === String(eventId)
  );

  async function loadSellerQr(seller) {
    try {
      setSellerActionMessage("");

      const response = await fetch(
        `${API}/api/ticketing/events/${eventId}/sellers/${seller.seller_id}/qr`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load seller QR."
        );
      }

      setSellerQr({
        ...body,
        display_name: seller.display_name,
      });
      setSellerQrOpen(true);
    } catch (error) {
      setSellerActionMessage(
        error.message || "Could not load seller QR."
      );
    }
  }

  function sellerTicketUrl(seller) {
    return (
      `https://tngos.tngboxinggym.com/events/${eventId}/tickets` +
      `?seller=${seller.public_code}`
    );
  }

  async function copySellerLink(seller) {
    const url = sellerTicketUrl(seller);

    try {
      await navigator.clipboard.writeText(url);
      setSellerActionMessage(
        `Ticket link copied for ${seller.display_name}.`
      );
    } catch {
      setSellerActionMessage("Could not copy ticket link.");
    }
  }

  async function emailSellerLink(seller) {
    try {
      setSellerActionMessage("");

      const response = await fetch(
        `${API}/api/ticketing/events/${eventId}/sellers/${seller.seller_id}/email-link`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not email ticket link."
        );
      }

      setSellerActionMessage(
        `Ticket link and QR emailed to ${body.email}.`
      );
    } catch (error) {
      setSellerActionMessage(
        error.message || "Could not email ticket link."
      );
    }
  }

  return (
    <div
      style={{
        padding: 24,
        maxWidth: 1400,
        margin: "0 auto",
      }}
    >
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ marginBottom: 6 }}>Event Ticket Sales</h1>

        <div style={{ color: "#666" }}>
          Live sales, fighter commissions, ticket scanning and post-event
          reports.
        </div>
      </div>

      {message && (
        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          {message}
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <select
          value={eventId}
          onChange={(event) => setEventId(event.target.value)}
          style={{
            minWidth: 280,
            padding: 12,
            borderRadius: 8,
          }}
        >
          <option value="">Select Event</option>

          {events.map((event) => (
            <option key={event.id} value={event.id}>
              {event.name}
              {event.event_date ? ` — ${event.event_date}` : ""}
            </option>
          ))}
        </select>

        <button
          onClick={() => loadSummary()}
          disabled={!eventId || busy}
          style={{ padding: "12px 18px" }}
        >
          Refresh
        </button>

        <button
          disabled={!eventId || busy}
          onClick={() =>
            downloadReport(
              `${API_BASE}/api/ticketing/events/${eventId}/report.pdf`,
              `tng_event_${eventId}_master_report.pdf`
            )
          }
          style={{ padding: "12px 18px" }}
        >
          Master PDF
        </button>

        <button
          disabled={!eventId || busy}
          onClick={() =>
            downloadReport(
              `${API_BASE}/api/ticketing/events/${eventId}/report.csv`,
              `tng_event_${eventId}_ticket_report.csv`
            )
          }
          style={{ padding: "12px 18px" }}
        >
          Master CSV
        </button>

        <button
          disabled={!eventId || busy}
          onClick={emailSellerReports}
          style={{ padding: "12px 18px" }}
        >
          Email Seller Reports
        </button>
      </div>

      {selectedEvent && (
        <div style={{ marginBottom: 18 }}>
          <strong>{selectedEvent.name}</strong>
          {selectedEvent.venue && <> — {selectedEvent.venue}</>}
        </div>
      )}

      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
            gap: 14,
            marginBottom: 30,
          }}
        >
          <div style={cardStyle}>
            <div style={labelStyle}>Tickets Sold</div>
            <div style={valueStyle}>{summary.tickets_sold || 0}</div>
          </div>

          <div style={cardStyle}>
            <div style={labelStyle}>Checked In</div>
            <div style={valueStyle}>{summary.tickets_scanned || 0}</div>
          </div>

          <div style={cardStyle}>
            <div style={labelStyle}>Gross Sales</div>
            <div style={valueStyle}>
              {money(summary.gross_sales_cents)}
            </div>
          </div>

          <div style={cardStyle}>
            <div style={labelStyle}>Commission Owed</div>
            <div style={valueStyle}>
              {money(summary.commission_cents)}
            </div>
          </div>
        </div>
      )}

      {eventId && (
        <>
          <EventTicketSales eventId={eventId} />

          <TicketDoorScanner />

          <div style={{ marginTop: 30 }}>
            <h2>Seller Reports</h2>

            <div style={{ overflowX: "auto" }}>
              <table
                width="100%"
                cellPadding="10"
                style={{ borderCollapse: "collapse" }}
              >
                <thead>
                  <tr>
                    <th align="left">Seller</th>
                    <th>Tickets</th>
                    <th>Gross</th>
                    <th>Commission</th>
                    <th>Reports</th>
                    <th>Ticket Link / QR</th>
                  </tr>
                </thead>

                <tbody>
                  {(summary?.sellers || []).map((seller) => (
                    <tr key={seller.seller_id}>
                      <td>{seller.display_name}</td>

                      <td align="center">
                        {seller.tickets_sold}
                      </td>

                      <td align="center">
                        {money(seller.gross_sales_cents)}
                      </td>

                      <td align="center">
                        <strong>
                          {money(seller.commission_cents)}
                        </strong>
                      </td>

                      <td align="center">
                        <button
                          onClick={() =>
                            downloadReport(
                              `${API_BASE}/api/ticketing/events/${eventId}/sellers/${seller.seller_id}/report.pdf`,
                              `seller_${seller.seller_id}_report.pdf`
                            )
                          }
                        >
                          PDF
                        </button>

                        {" "}

                        <button
                          onClick={() =>
                            downloadReport(
                              `${API_BASE}/api/ticketing/events/${eventId}/sellers/${seller.seller_id}/report.csv`,
                              `seller_${seller.seller_id}_report.csv`
                            )
                          }
                        >
                          CSV
                        </button>
                      </td>

                      <td align="center">
                        <div
                          style={{
                            display: "flex",
                            gap: 6,
                            flexWrap: "wrap",
                            justifyContent: "center",
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => loadSellerQr(seller)}
                          >
                            View QR
                          </button>

                          <button
                            type="button"
                            onClick={() => copySellerLink(seller)}
                          >
                            Copy Link
                          </button>

                          <button
                            type="button"
                            onClick={() =>
                              window.open(
                                sellerTicketUrl(seller),
                                "_blank"
                              )
                            }
                          >
                            Open Page
                          </button>

                          <button
                            type="button"
                            onClick={() => emailSellerLink(seller)}
                          >
                            Email Fighter
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {sellerActionMessage && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "#f5f5f5",
            borderRadius: 8,
          }}
        >
          {sellerActionMessage}
        </div>
      )}

      {sellerQrOpen && sellerQr && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,.55)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 20,
          }}
          onClick={() => setSellerQrOpen(false)}
        >
          <div
            style={{
              background: "white",
              borderRadius: 14,
              padding: 24,
              width: "100%",
              maxWidth: 440,
              textAlign: "center",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0 }}>
              {sellerQr.display_name || sellerQr.name}
            </h2>

            <p>Personal Ticket Sales QR</p>

            {sellerQr.qr_png_base64 && (
              <img
                src={
                  "data:image/png;base64," +
                  sellerQr.qr_png_base64
                }
                alt="Seller ticket QR"
                width="260"
                height="260"
                style={{ maxWidth: "100%" }}
              />
            )}

            <div
              style={{
                marginTop: 12,
                wordBreak: "break-all",
                fontSize: 13,
              }}
            >
              {sellerQr.url}
            </div>

            <div
              style={{
                marginTop: 18,
                display: "flex",
                gap: 8,
                justifyContent: "center",
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() =>
                  navigator.clipboard.writeText(sellerQr.url)
                }
              >
                Copy Link
              </button>

              <button
                type="button"
                onClick={() =>
                  window.open(sellerQr.url, "_blank")
                }
              >
                Open Ticket Page
              </button>

              <button
                type="button"
                onClick={() => setSellerQrOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const cardStyle = {
  border: "1px solid #ddd",
  borderRadius: 10,
  padding: 18,
  background: "#fff",
};

const labelStyle = {
  fontSize: 13,
  color: "#666",
  marginBottom: 6,
};

const valueStyle = {
  fontSize: 28,
  fontWeight: 800,
};
