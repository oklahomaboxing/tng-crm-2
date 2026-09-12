import { useEffect, useState } from "react";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function statusBadge(value) {
  const text = String(value || "missing").replaceAll("_", " ");

  const good = [
    "active",
    "approved",
    "complete",
    "completed",
    "valid",
    "current",
  ].includes(String(value || "").toLowerCase());

  return (
    <span
      style={{
        display: "inline-block",
        padding: "5px 9px",
        borderRadius: 20,
        fontSize: 12,
        fontWeight: 800,
        background: good ? "#e8f5e9" : "#fff3e0",
        color: good ? "#176b2c" : "#8a4b00",
        textTransform: "capitalize",
      }}
    >
      {text}
    </span>
  );
}

function money(cents) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format((Number(cents) || 0) / 100);
}

export default function FighterPortal({ onLogout }) {
  const [data, setData] = useState(null);
  const [ticketSales, setTicketSales] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setLoading(true);
      setMessage("");

      const token = localStorage.getItem("token");

      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [profileResponse, ticketResponse] =
        await Promise.all([
          fetch(
            `${API}/api/fighter/me`,
            { headers }
          ),
          fetch(
            `${API}/api/fighter/me/ticket-sales`,
            { headers }
          ),
        ]);

      const profileBody =
        await profileResponse.json();

      const ticketBody =
        await ticketResponse.json();

      if (!profileResponse.ok) {
        throw new Error(
          profileBody.detail ||
          "Could not load Fighter Portal"
        );
      }

      if (!ticketResponse.ok) {
        throw new Error(
          ticketBody.detail ||
          "Could not load ticket sales"
        );
      }

      setData(profileBody);
      setTicketSales(ticketBody);
    } catch (err) {
      setMessage(
        err.message || "Could not load Fighter Portal"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 30, fontFamily: "Arial" }}>
        Loading Fighter Portal...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 30, fontFamily: "Arial" }}>
        <h2>Fighter Portal</h2>
        <p>{message}</p>

        <button onClick={onLogout}>
          Sign Out
        </button>
      </div>
    );
  }

  const fighter = data.fighter || {};

  const cards = [
    {
      title: "Fight Offers",
      value: "No pending offers",
      note: "View, accept or decline fight offers.",
    },
    {
      title: "Contracts",
      value: "Coming next",
      note: "Review and electronically sign bout agreements.",
    },
    {
      title: "Medical Documents",
      value: fighter.bloodwork_status || "Missing",
      note: fighter.bloodwork_expires
        ? `Bloodwork expires ${fighter.bloodwork_expires}`
        : "Upload bloodwork, physicals and medical documents.",
    },
    {
      title: "Ticket Sales",
      value: `${
        ticketSales?.summary?.tickets_sold || 0
      } tickets`,
      note: `Commission earned: ${money(
        ticketSales?.summary?.commission_cents || 0
      )}`,
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f4f4f5",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <header
        style={{
          background: "#111",
          color: "#fff",
          padding: "18px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 15,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              color: "#e31b23",
              fontWeight: 900,
              fontSize: 13,
            }}
          >
            TNG BOXING
          </div>

          <div
            style={{
              fontSize: 24,
              fontWeight: 900,
            }}
          >
            Fighter Portal
          </div>
        </div>

        <button
          onClick={onLogout}
          style={{
            border: "1px solid #555",
            color: "#fff",
            background: "transparent",
            borderRadius: 8,
            padding: "9px 15px",
            cursor: "pointer",
          }}
        >
          Sign Out
        </button>
      </header>

      <main
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: 24,
        }}
      >
        <section
          style={{
            background: "#fff",
            borderRadius: 14,
            padding: 22,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 20,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div
                style={{
                  color: "#777",
                  fontSize: 13,
                  fontWeight: 700,
                }}
              >
                WELCOME
              </div>

              <h1
                style={{
                  margin: "5px 0 8px",
                }}
              >
                {fighter.legal_name}
              </h1>

              <div style={{ color: "#666" }}>
                {fighter.pro_record
                  ? `Professional Record: ${fighter.pro_record}`
                  : fighter.amateur_record
                  ? `Amateur Record: ${fighter.amateur_record}`
                  : "TNG Fighter"}
              </div>
            </div>

            <div>
              <div
                style={{
                  fontSize: 12,
                  color: "#777",
                  marginBottom: 5,
                }}
              >
                BOXREC ID
              </div>

              <strong>
                {fighter.boxrec_id || "Not added"}
              </strong>
            </div>
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 14,
            marginBottom: 20,
          }}
        >
          {cards.map((card) => (
            <div
              key={card.title}
              style={{
                background: "#fff",
                borderRadius: 12,
                padding: 18,
                minHeight: 125,
              }}
            >
              <div
                style={{
                  color: "#777",
                  fontSize: 12,
                  fontWeight: 800,
                  textTransform: "uppercase",
                }}
              >
                {card.title}
              </div>

              <div
                style={{
                  fontSize: 21,
                  fontWeight: 900,
                  margin: "9px 0",
                  textTransform: "capitalize",
                }}
              >
                {card.value}
              </div>

              <div
                style={{
                  color: "#666",
                  fontSize: 13,
                  lineHeight: 1.4,
                }}
              >
                {card.note}
              </div>
            </div>
          ))}
        </section>

        <section
          style={{
            background: "#fff",
            borderRadius: 14,
            padding: 22,
            marginBottom: 20,
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            Fight Requirements
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(190px, 1fr))",
              gap: 16,
            }}
          >
            <div>
              <strong>Bloodwork</strong>
              <div style={{ marginTop: 7 }}>
                {statusBadge(
                  fighter.bloodwork_status
                )}
              </div>
            </div>

            <div>
              <strong>OK License</strong>
              <div style={{ marginTop: 7 }}>
                {statusBadge(
                  fighter.ok_license_status
                )}
              </div>
            </div>

            <div>
              <strong>Federal ID</strong>
              <div style={{ marginTop: 7 }}>
                {statusBadge(
                  fighter.federal_id_status
                )}
              </div>
            </div>

            <div>
              <strong>Contract</strong>
              <div style={{ marginTop: 7 }}>
                {statusBadge("pending")}
              </div>
            </div>
          </div>
        </section>

        <section
          style={{
            background: "#fff",
            borderRadius: 14,
            padding: 22,
            marginBottom: 20,
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            Ticket Sales & Commission
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(170px, 1fr))",
              gap: 12,
              marginBottom: 22,
            }}
          >
            <div>
              <small>Tickets Sold</small>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 900,
                  marginTop: 4,
                }}
              >
                {ticketSales?.summary?.tickets_sold || 0}
              </div>
            </div>

            <div>
              <small>Gross Sales</small>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 900,
                  marginTop: 4,
                }}
              >
                {money(
                  ticketSales?.summary
                    ?.gross_sales_cents || 0
                )}
              </div>
            </div>

            <div>
              <small>Commission Earned</small>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 900,
                  marginTop: 4,
                }}
              >
                {money(
                  ticketSales?.summary
                    ?.commission_cents || 0
                )}
              </div>
            </div>

            <div>
              <small>Commission Paid</small>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 900,
                  marginTop: 4,
                }}
              >
                {money(
                  ticketSales?.summary
                    ?.amount_paid_cents || 0
                )}
              </div>
            </div>

            <div>
              <small>Balance Due</small>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 900,
                  marginTop: 4,
                }}
              >
                {money(
                  ticketSales?.summary
                    ?.balance_due_cents || 0
                )}
              </div>
            </div>
          </div>

          {!ticketSales?.events?.length ? (
            <div
              style={{
                color: "#666",
                padding: "12px 0",
              }}
            >
              You have not been assigned ticket sales
              for an event yet.
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: 14,
              }}
            >
              {ticketSales.events.map((event) => (
                <div
                  key={event.seller_id}
                  style={{
                    border: "1px solid #ddd",
                    borderRadius: 12,
                    padding: 16,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: 18,
                          fontWeight: 900,
                        }}
                      >
                        {event.event_name}
                      </div>

                      <div
                        style={{
                          color: "#666",
                          fontSize: 13,
                          marginTop: 3,
                        }}
                      >
                        {[
                          event.event_date,
                          event.venue,
                        ]
                          .filter(Boolean)
                          .join(" - ")}
                      </div>
                    </div>

                    <span
                      style={{
                        textTransform: "capitalize",
                        fontWeight: 800,
                      }}
                    >
                      {event.payout_status}
                    </span>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(130px, 1fr))",
                      gap: 10,
                      marginTop: 15,
                    }}
                  >
                    <div>
                      <small>Tickets</small>
                      <div>
                        <strong>
                          {event.tickets_sold}
                        </strong>
                      </div>
                    </div>

                    <div>
                      <small>Gross</small>
                      <div>
                        <strong>
                          {money(
                            event.gross_sales_cents
                          )}
                        </strong>
                      </div>
                    </div>

                    <div>
                      <small>Commission</small>
                      <div>
                        <strong>
                          {money(
                            event.commission_cents
                          )}
                        </strong>
                      </div>
                    </div>

                    <div>
                      <small>Balance Due</small>
                      <div>
                        <strong>
                          {money(
                            event.balance_due_cents
                          )}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      flexWrap: "wrap",
                      marginTop: 16,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        window.open(
                          event.ticket_url,
                          "_blank"
                        );
                      }}
                      style={{
                        padding: "10px 14px",
                        background: "#d71920",
                        color: "#fff",
                        border: 0,
                        borderRadius: 8,
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      Open My Ticket Page
                    </button>

                    <button
                      type="button"
                      onClick={async () => {
                        await navigator.clipboard.writeText(
                          event.ticket_url
                        );
                        setMessage(
                          "Ticket link copied."
                        );
                      }}
                      style={{
                        padding: "10px 14px",
                        background: "#fff",
                        color: "#111",
                        border: "1px solid #bbb",
                        borderRadius: 8,
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      Copy My Link
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section
          style={{
            background: "#fff",
            borderRadius: 14,
            padding: 22,
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            Fighter Profile
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 18,
            }}
          >
            <div>
              <small>Email</small>
              <div>
                <strong>
                  {fighter.email || "-"}
                </strong>
              </div>
            </div>

            <div>
              <small>Phone</small>
              <div>
                <strong>
                  {fighter.phone || "-"}
                </strong>
              </div>
            </div>

            <div>
              <small>Gym</small>
              <div>
                <strong>
                  {fighter.gym || "-"}
                </strong>
              </div>
            </div>

            <div>
              <small>Coach</small>
              <div>
                <strong>
                  {fighter.coach || "-"}
                </strong>
              </div>
            </div>

            <div>
              <small>Manager</small>
              <div>
                <strong>
                  {fighter.manager_name || "-"}
                </strong>
              </div>
            </div>

            <div>
              <small>Fight Weight</small>
              <div>
                <strong>
                  {fighter.fight_weight
                    ? `${fighter.fight_weight} lbs`
                    : "-"}
                </strong>
              </div>
            </div>
          </div>
        </section>

        <div
          style={{
            textAlign: "center",
            color: "#777",
            marginTop: 25,
            paddingBottom: 30,
            fontSize: 13,
          }}
        >
          TNG Boxing - Earned Not Given
        </div>
      </main>
    </div>
  );
}
