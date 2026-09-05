import React, {
  useState,
} from "react";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function headers() {
  return {
    Authorization:
      `Bearer ${localStorage.getItem(
        "token"
      )}`,
  };
}

export default function TicketSellerControls({
  eventId,
  fighterId,
}) {
  const [seller, setSeller] =
    useState(null);

  const [qr, setQr] =
    useState(null);

  const [message, setMessage] =
    useState("");

  const [working, setWorking] =
    useState(false);

  async function enableSales() {
    if (!eventId) {
      setMessage(
        "Select an event first."
      );
      return;
    }

    if (!fighterId) {
      setMessage(
        "Select a fighter first."
      );
      return;
    }

    try {
      setWorking(true);
      setMessage("");

      const response =
        await fetch(
          `${API}/api/ticketing/events/` +
            `${eventId}/fighters/` +
            `${fighterId}/enable-ticket-sales`,
          {
            method: "POST",
            headers: headers(),
          }
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not enable ticket sales"
        );
      }

      const sellerData =
        body.seller || body;

      setSeller(sellerData);

      setMessage(
        "Ticket sales enabled for this fighter."
      );

      const sellerId =
        sellerData.id ||
        sellerData.seller_id;

      if (sellerId) {
        await loadQr(sellerId);
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setWorking(false);
    }
  }

  async function loadQr(
    sellerId
  ) {
    try {
      const response =
        await fetch(
          `${API}/api/ticketing/events/` +
            `${eventId}/sellers/` +
            `${sellerId}/qr`,
          {
            headers: headers(),
          }
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load seller QR"
        );
      }

      setQr(body);
    } catch (err) {
      setMessage(err.message);
    }
  }

  function copyLink() {
    const url =
      qr?.url ||
      qr?.ticket_url ||
      qr?.seller_url;

    if (!url) return;

    navigator.clipboard
      ?.writeText(url);

    setMessage(
      "Seller ticket link copied."
    );
  }

  const qrImage =
    qr?.qr_png_base64 ||
    qr?.qr_base64 ||
    qr?.qr;

  const sellerUrl =
    qr?.url ||
    qr?.ticket_url ||
    qr?.seller_url;

  return (
    <div
      style={{
        marginTop: 16,
        marginBottom: 16,
        padding: 16,
        border:
          "1px solid #ddd",
        borderRadius: 10,
        background: "#fafafa",
      }}
    >
      <div
        style={{
          fontWeight: 900,
          marginBottom: 8,
        }}
      >
        Fighter Ticket Sales
      </div>

      <div
        style={{
          color: "#666",
          fontSize: 14,
          marginBottom: 10,
        }}
      >
        Select a fighter and an
        event, then create their
        personal ticket sales QR
        and link.
      </div>

      <button
        type="button"
        disabled={
          working ||
          !fighterId ||
          !eventId
        }
        onClick={enableSales}
        style={{
          background: "#d71920",
          color: "white",
          border: 0,
          borderRadius: 8,
          padding:
            "10px 15px",
          fontWeight: 800,
          cursor: "pointer",
        }}
      >
        {working
          ? "Working..."
          : "Enable Ticket Sales / Get QR"}
      </button>

      {message && (
        <div
          style={{
            marginTop: 10,
          }}
        >
          {message}
        </div>
      )}

      {seller && (
        <div
          style={{
            marginTop: 10,
          }}
        >
          Seller code:{" "}
          <strong>
            {
              seller.public_code
            }
          </strong>
        </div>
      )}

      {qrImage && (
        <div
          style={{
            marginTop: 15,
          }}
        >
          <img
            src={
              "data:image/png;base64," +
              qrImage
            }
            width="190"
            height="190"
            alt="Fighter ticket seller QR"
          />
        </div>
      )}

      {sellerUrl && (
        <div
          style={{
            marginTop: 10,
          }}
        >
          <button
            type="button"
            onClick={copyLink}
          >
            Copy Ticket Link
          </button>

          {" "}

          <button
            type="button"
            onClick={() =>
              window.open(
                sellerUrl,
                "_blank"
              )
            }
          >
            Open Ticket Page
          </button>
        </div>
      )}
    </div>
  );
}
