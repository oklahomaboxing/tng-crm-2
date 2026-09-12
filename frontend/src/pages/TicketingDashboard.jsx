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
  const [ticketTypes, setTicketTypes] = useState([]);
  const [ticketPriceMessage, setTicketPriceMessage] = useState("");
  const [savingTicketTypeId, setSavingTicketTypeId] = useState(null);

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

  async function loadTicketTypes(selectedEventId = eventId) {
    if (!selectedEventId) {
      setTicketTypes([]);
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/ticketing/events/${selectedEventId}/ticket-types`,
        {
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not load ticket prices"
        );
      }

      setTicketTypes(
        (Array.isArray(data) ? data : []).map((ticket) => ({
          ...ticket,
          price_display: (
            (Number(ticket.price_cents) || 0) / 100
          ).toFixed(2),
          inventory_display:
            ticket.inventory === null ||
            ticket.inventory === undefined
              ? ""
              : String(ticket.inventory),
        }))
      );
    } catch (error) {
      setTicketPriceMessage(error.message);
    }
  }

  function updateTicketTypeField(ticketId, field, value) {
    setTicketTypes((current) =>
      current.map((ticket) =>
        ticket.id === ticketId
          ? {
              ...ticket,
              [field]: value,
            }
          : ticket
      )
    );
  }

  async function saveTicketType(ticket) {
    if (!eventId) return;

    const price = Number(ticket.price_display);

    if (!Number.isFinite(price) || price < 0) {
      setTicketPriceMessage(
        `Enter a valid price for ${ticket.name}.`
      );
      return;
    }

    const inventoryText = String(
      ticket.inventory_display ?? ""
    ).trim();

    let inventory = null;

    if (inventoryText !== "") {
      inventory = Number(inventoryText);

      if (
        !Number.isInteger(inventory) ||
        inventory < 0
      ) {
        setTicketPriceMessage(
          `Enter a valid inventory for ${ticket.name}.`
        );
        return;
      }
    }

    try {
      setSavingTicketTypeId(ticket.id);
      setTicketPriceMessage("");

      const response = await fetch(
        `${API}/api/ticketing/events/${eventId}/ticket-types/${ticket.id}`,
        {
          method: "PATCH",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            price_cents: Math.round(price * 100),
            inventory,
            active: Boolean(ticket.active),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not update ticket type"
        );
      }

      setTicketPriceMessage(
        `${ticket.name} updated successfully.`
      );

      await loadTicketTypes(eventId);
    } catch (error) {
      setTicketPriceMessage(error.message);
    } finally {
      setSavingTicketTypeId(null);
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
      loadTicketTypes(eventId);
    } else {
      setTicketTypes([]);
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

      {eventId && (
        <div
          style={{
            marginTop: 22,
            marginBottom: 24,
            padding: 20,
            border: "1px solid #ddd",
            borderRadius: 12,
            background: "#fafafa",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
              marginBottom: 16,
            }}
          >
            <div>
              <h2 style={{ margin: 0 }}>
                Ticket Prices
              </h2>

              <div
                style={{
                  marginTop: 4,
                  color: "#666",
                  fontSize: 14,
                }}
              >
                Changes apply to new ticket purchases.
                Previously sold tickets keep their original price.
              </div>
            </div>

            <button
              type="button"
              onClick={() => loadTicketTypes(eventId)}
              disabled={!eventId}
            >
              Refresh Prices
            </button>
          </div>

          {ticketPriceMessage && (
            <div
              style={{
                marginBottom: 14,
                padding: 10,
                borderRadius: 8,
                background: "#fff",
                border: "1px solid #ddd",
              }}
            >
              {ticketPriceMessage}
            </div>
          )}

          {ticketTypes.length === 0 ? (
            <div style={{ color: "#666" }}>
              No ticket types have been created for this event yet.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                width="100%"
                cellPadding="10"
                style={{
                  borderCollapse: "collapse",
                  background: "#fff",
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid #ddd",
                    }}
                  >
                    <th align="left">
                      Ticket Type
                    </th>

                    <th align="left">
                      Price
                    </th>

                    <th align="left">
                      Inventory
                    </th>

                    <th align="center">
                      On Sale
                    </th>

                    <th align="center">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {ticketTypes.map((ticket) => (
                    <tr
                      key={ticket.id}
                      style={{
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      <td>
                        <strong>
                          {ticket.name}
                        </strong>

                        <div
                          style={{
                            fontSize: 12,
                            color: "#777",
                            marginTop: 3,
                          }}
                        >
                          Commission:{" "}
                          {ticket.commission_type === "percent"
                            ? `${ticket.commission_value}%`
                            : ticket.commission_type === "flat"
                            ? `$${Number(
                                ticket.commission_value || 0
                              ).toFixed(2)}`
                            : "None"}
                        </div>
                      </td>

                      <td>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <span>$</span>

                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={
                              ticket.price_display
                            }
                            onChange={(e) =>
                              updateTicketTypeField(
                                ticket.id,
                                "price_display",
                                e.target.value
                              )
                            }
                            style={{
                              width: 95,
                              padding: 8,
                            }}
                          />
                        </div>
                      </td>

                      <td>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          placeholder="Unlimited"
                          value={
                            ticket.inventory_display
                          }
                          onChange={(e) =>
                            updateTicketTypeField(
                              ticket.id,
                              "inventory_display",
                              e.target.value
                            )
                          }
                          style={{
                            width: 110,
                            padding: 8,
                          }}
                        />

                        <div
                          style={{
                            fontSize: 11,
                            color: "#777",
                            marginTop: 3,
                          }}
                        >
                          Blank = unlimited
                        </div>
                      </td>

                      <td align="center">
                        <label
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            cursor: "pointer",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={Boolean(
                              ticket.active
                            )}
                            onChange={(e) =>
                              updateTicketTypeField(
                                ticket.id,
                                "active",
                                e.target.checked
                              )
                            }
                          />

                          {ticket.active
                            ? "Active"
                            : "Off"}
                        </label>
                      </td>

                      <td align="center">
                        <button
                          type="button"
                          disabled={
                            savingTicketTypeId ===
                            ticket.id
                          }
                          onClick={() =>
                            saveTicketType(ticket)
                          }
                          style={{
                            background: "#d71920",
                            color: "#fff",
                            border: 0,
                            borderRadius: 7,
                            padding: "9px 14px",
                            fontWeight: 700,
                            cursor: "pointer",
                          }}
                        >
                          {savingTicketTypeId ===
                          ticket.id
                            ? "Saving..."
                            : "Save"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

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
