import React, { useEffect, useMemo, useState } from "react";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function money(cents) {
  return `$${((Number(cents) || 0) / 100).toFixed(2)}`;
}

export default function PublicTicketCheckout() {
  const match =
    window.location.pathname.match(
      /^\/events\/(\d+)\/tickets\/?$/
    );

  const eventId = match?.[1];

  const params = new URLSearchParams(
    window.location.search
  );

  const sellerCode =
    params.get("seller") || "";

  const paymentStatus =
    params.get("ticket_payment");

  const returnedOrderId =
    params.get("order");

  const [data, setData] = useState(null);

  const [quantities, setQuantities] =
    useState({});

  const [buyerName, setBuyerName] =
    useState("");

  const [buyerEmail, setBuyerEmail] =
    useState("");

  const [buyerPhone, setBuyerPhone] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [submitting, setSubmitting] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [tickets, setTickets] =
    useState([]);

  const [receipt, setReceipt] =
    useState("");

  useEffect(() => {
    if (!eventId) return;

    async function load() {
      try {
        setLoading(true);

        let url =
          `${API}/api/ticketing/public/events/` +
          `${eventId}/tickets`;

        if (sellerCode) {
          url +=
            `?seller=${encodeURIComponent(
              sellerCode
            )}`;
        }

        const response =
          await fetch(url);

        const body =
          await response.json();

        if (!response.ok) {
          throw new Error(
            body.detail ||
            "Could not load event tickets"
          );
        }

        setData(body);

        const initial = {};

        (body.ticket_types || []).forEach(
          (ticket) => {
            initial[ticket.id] = 0;
          }
        );

        setQuantities(initial);
      } catch (error) {
        setMessage(error.message);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [eventId, sellerCode]);

  const total = useMemo(() => {
    if (!data) return 0;

    return (
      data.ticket_types || []
    ).reduce(
      (sum, ticket) =>
        sum +
        (Number(
          quantities[ticket.id]
        ) || 0) *
          Number(ticket.price_cents || 0),
      0
    );
  }, [data, quantities]);

  useEffect(() => {
    if (
      paymentStatus !== "success" ||
      !returnedOrderId
    ) {
      return;
    }

    let cancelled = false;

    async function retrieveTickets() {
      let saved;

      try {
        saved = JSON.parse(
          localStorage.getItem(
            "tngPendingTicketOrder"
          ) || "{}"
        );
      } catch {
        saved = {};
      }

      const email = saved.email;

      if (!email) {
        setMessage(
          "Payment was received. Check your email for your TNG tickets."
        );
        return;
      }

      for (
        let attempt = 0;
        attempt < 8;
        attempt += 1
      ) {
        if (cancelled) return;

        try {
          const response = await fetch(
            `${API}/api/ticketing/public/orders/` +
              `${returnedOrderId}/tickets` +
              `?email=${encodeURIComponent(
                email
              )}`
          );

          const body =
            await response.json();

          if (
            response.ok &&
            body.payment_status === "paid" &&
            body.tickets?.length
          ) {
            setTickets(body.tickets);
            setReceipt(
              body.receipt_number || ""
            );

            setMessage(
              "Payment successful. Your tickets are ready."
            );

            return;
          }
        } catch {
          // Clover webhook may still be processing.
        }

        await new Promise((resolve) =>
          setTimeout(resolve, 2000)
        );
      }

      setMessage(
        "Payment successful. Your tickets are being processed and will also be sent to your email."
      );
    }

    retrieveTickets();

    return () => {
      cancelled = true;
    };
  }, [
    paymentStatus,
    returnedOrderId,
  ]);

  async function purchaseTickets(event) {
    event.preventDefault();

    setMessage("");

    const items = (
      data?.ticket_types || []
    )
      .map((ticket) => ({
        ticket_type_id: ticket.id,
        quantity:
          Number(
            quantities[ticket.id]
          ) || 0,
      }))
      .filter(
        (item) =>
          item.quantity > 0
      );

    if (!items.length) {
      setMessage(
        "Select at least one ticket."
      );
      return;
    }

    if (total <= 0) {
      setMessage(
        "Select at least one paid ticket."
      );
      return;
    }

    if (
      !buyerName.trim() ||
      !buyerEmail.trim()
    ) {
      setMessage(
        "Name and email are required."
      );
      return;
    }

    try {
      setSubmitting(true);

      const orderResponse =
        await fetch(
          `${API}/api/ticketing/public/events/` +
            `${eventId}/orders`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              buyer_name:
                buyerName.trim(),
              buyer_email:
                buyerEmail.trim(),
              buyer_phone:
                buyerPhone.trim() ||
                null,
              seller_code:
                sellerCode || null,
              items,
            }),
          }
        );

      const order =
        await orderResponse.json();

      if (!orderResponse.ok) {
        throw new Error(
          order.detail ||
          "Could not create ticket order"
        );
      }

      localStorage.setItem(
        "tngPendingTicketOrder",
        JSON.stringify({
          orderId: order.order_id,
          email: buyerEmail
            .trim()
            .toLowerCase(),
          eventId,
        })
      );

      const checkoutResponse =
        await fetch(
          `${API}/api/ticketing/public/orders/` +
            `${order.order_id}/checkout`,
          {
            method: "POST",
          }
        );

      const checkout =
        await checkoutResponse.json();

      if (!checkoutResponse.ok) {
        throw new Error(
          checkout.detail ||
          "Could not start Clover checkout"
        );
      }

      if (checkout.status === "paid" && Number(checkout.total_cents) === 0) {
        window.location.href =
          `/events/${eventId}/tickets?ticket_payment=success&order=${order.order_id}`;
        return;
      }

      if (!checkout.checkout_url) {
        throw new Error(
          "Clover did not return a payment link"
        );
      }

      window.location.href =
        checkout.checkout_url;
    } catch (error) {
      setMessage(error.message);
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div style={styles.center}>
        Loading tickets...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={styles.center}>
        {message ||
          "Event tickets unavailable."}
      </div>
    );
  }

  if (tickets.length) {
    return (
      <main style={styles.page}>
        <section style={styles.container}>
          <div style={styles.logo}>
            TNG PROMOTIONS
          </div>

          <h1 style={styles.title}>
            Your Tickets
          </h1>

          <div style={styles.success}>
            Payment Successful
          </div>

          {receipt && (
            <div style={styles.receipt}>
              Receipt: {receipt}
            </div>
          )}

          <div style={styles.ticketGrid}>
            {tickets.map(
              (ticket) => (
                <article
                  key={ticket.id}
                  style={styles.ticket}
                >
                  <h2>
                    {
                      ticket.ticket_number
                    }
                  </h2>

                  <div>
                    {money(
                      ticket.price_cents
                    )}
                  </div>

                  <div
                    style={{
                      margin:
                        "14px 0",
                    }}
                  >
                    {ticket.qr_png_base64 ? (
                      <img
                        src={
                          "data:image/png;base64," +
                          ticket.qr_png_base64
                        }
                        width="240"
                        height="240"
                        alt="Ticket QR"
                      />
                    ) : (
                      <div>
                        QR sent by email
                      </div>
                    )}
                  </div>

                  <strong>
                    {
                      ticket.status
                    }
                  </strong>

                  <p>
                    Show this QR code
                    at the door.
                  </p>
                </article>
              )
            )}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main style={styles.page}>
      <section style={styles.container}>
        <div style={styles.logo}>
          TNG PROMOTIONS
        </div>

        <h1 style={styles.title}>
          {data.event?.name}
        </h1>

        <div style={styles.eventInfo}>
          {data.event?.event_date}
          {data.event?.venue
            ? ` â€¢ ${data.event.venue}`
            : ""}
        </div>

        {data.seller && (
          <div style={styles.seller}>
            Supporting{" "}
            <strong>
              {data.seller.display_name ||
                data.seller.name}
            </strong>
          </div>
        )}

        {paymentStatus ===
          "failure" && (
          <div style={styles.error}>
            Payment was not completed.
            You can try again below.
          </div>
        )}

        {message && (
          <div style={styles.message}>
            {message}
          </div>
        )}

        <form
          onSubmit={purchaseTickets}
        >
          <div
            style={styles.ticketGrid}
          >
            {(
              data.ticket_types || []
            )
              .filter(
                (ticket) =>
                  Number(
                    ticket.price_cents || 0
                  ) > 0
              )
              .map((ticket) => (
              <div
                key={ticket.id}
                style={styles.ticket}
              >
                <h2>{ticket.name}</h2>

                <div
                  style={
                    styles.price
                  }
                >
                  {money(
                    ticket.price_cents
                  )}
                </div>

                <label>
                  Quantity
                </label>

                <select
                  value={
                    quantities[
                      ticket.id
                    ] || 0
                  }
                  onChange={(e) =>
                    setQuantities(
                      (old) => ({
                        ...old,
                        [ticket.id]:
                          Number(
                            e.target
                              .value
                          ),
                      })
                    )
                  }
                  style={
                    styles.input
                  }
                >
                  {[0, 1, 2, 3, 4, 5, 6, 7, 8].map(
                    (qty) => (
                      <option
                        key={qty}
                        value={qty}
                      >
                        {qty}
                      </option>
                    )
                  )}
                </select>
              </div>
            ))}
          </div>

          <div style={styles.form}>
            <h2>
              Buyer Information
            </h2>

            <input
              style={styles.input}
              placeholder="Full name"
              value={buyerName}
              onChange={(e) =>
                setBuyerName(
                  e.target.value
                )
              }
            />

            <input
              style={styles.input}
              type="email"
              placeholder="Email"
              value={buyerEmail}
              onChange={(e) =>
                setBuyerEmail(
                  e.target.value
                )
              }
            />

            <input
              style={styles.input}
              placeholder="Phone"
              value={buyerPhone}
              onChange={(e) =>
                setBuyerPhone(
                  e.target.value
                )
              }
            />

            <div style={styles.total}>
              Total: {money(total)}
            </div>

            <button
              disabled={
                submitting || total <= 0
              }
              style={styles.buyButton}
            >
              {submitting
                ? "Opening Clover..."
                : `Buy Tickets - ${money(total)}`}
            </button>

            <div
              style={
                styles.secureText
              }
            >
              Secure payment powered by
              Clover
            </div>
          </div>
        </form>
      </section>
    </main>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background:
      "linear-gradient(180deg,#050505,#151515)",
    color: "white",
    padding: "24px 14px 60px",
    fontFamily:
      "Inter,Arial,sans-serif",
  },

  container: {
    width: "100%",
    maxWidth: 1000,
    margin: "0 auto",
  },

  center: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    fontFamily:
      "Inter,Arial,sans-serif",
  },

  logo: {
    color: "#e31b23",
    fontWeight: 1000,
    letterSpacing: 2,
    marginBottom: 10,
  },

  title: {
    fontSize: "clamp(32px,7vw,58px)",
    lineHeight: 1,
    margin: "0 0 10px",
  },

  eventInfo: {
    color: "#ccc",
    marginBottom: 20,
  },

  seller: {
    background: "#241214",
    border:
      "1px solid #e31b23",
    borderRadius: 10,
    padding: 12,
    marginBottom: 22,
  },

  ticketGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit,minmax(230px,1fr))",
    gap: 16,
  },

  ticket: {
    background: "white",
    color: "#111",
    borderRadius: 14,
    padding: 20,
    textAlign: "center",
  },

  price: {
    fontSize: 30,
    fontWeight: 900,
    marginBottom: 14,
  },

  form: {
    maxWidth: 620,
    margin: "28px auto 0",
    background: "#1d1d1d",
    padding: 24,
    borderRadius: 14,
  },

  input: {
    width: "100%",
    padding: 13,
    fontSize: 16,
    marginTop: 8,
    marginBottom: 12,
    borderRadius: 8,
    border:
      "1px solid #bbb",
    boxSizing: "border-box",
  },

  total: {
    fontSize: 28,
    fontWeight: 900,
    margin:
      "16px 0",
  },

  buyButton: {
    width: "100%",
    border: 0,
    borderRadius: 10,
    padding: 16,
    background: "#d71920",
    color: "white",
    fontWeight: 900,
    fontSize: 18,
    cursor: "pointer",
  },

  secureText: {
    textAlign: "center",
    color: "#aaa",
    marginTop: 12,
  },

  message: {
    background: "#333",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },

  error: {
    background: "#5b1111",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },

  success: {
    background: "#146c2e",
    padding: 14,
    borderRadius: 8,
    marginBottom: 10,
  },

  receipt: {
    marginBottom: 20,
  },
};

