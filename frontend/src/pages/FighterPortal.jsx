import { openOfficialContract } from "../utils/officialContract";
﻿import { useEffect, useState } from "react";

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
  const [fightOffers, setFightOffers] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [contractWorkingId, setContractWorkingId] =
    useState(null);
  const [signatureNames, setSignatureNames] = useState({});
  const [signatureAgreements, setSignatureAgreements] =
    useState({});
  const [offerWorkingId, setOfferWorkingId] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const [fighterPhotos, setFighterPhotos] = useState([]);
  const [fighterPhotoUrls, setFighterPhotoUrls] = useState({});
  const [photoType, setPhotoType] = useState("headshot");
  const [photoWorking, setPhotoWorking] = useState(false);

  async function load() {
    try {
      setLoading(true);
      setMessage("");

      const token = localStorage.getItem("token");

      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [
        profileResponse,
        ticketResponse,
        offersResponse,
      ] = await Promise.all([
        fetch(
          `${API}/api/fighter/me`,
          { headers }
        ),
        fetch(
          `${API}/api/fighter/me/ticket-sales`,
          { headers }
        ),
        fetch(
          `${API}/api/fighter/me/fight-offers`,
          { headers }
        ),
      ]);

      const profileBody =
        await profileResponse.json();

      const ticketBody =
        await ticketResponse.json();

      const offersBody =
        await offersResponse.json();

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

      if (!offersResponse.ok) {
        throw new Error(
          offersBody.detail ||
          "Could not load fight offers"
        );
      }

      setData(profileBody);
      setTicketSales(ticketBody);
      setFightOffers(
        Array.isArray(offersBody.offers)
          ? offersBody.offers
          : []
      );
    } catch (err) {
      setMessage(
        err.message || "Could not load Fighter Portal"
      );
    } finally {
      setLoading(false);
    }
  }


  async function loadFighterPhotos() {
    const token = localStorage.getItem("token");

    try {
      const response = await fetch(
        `${API}/api/fighter/me/photos`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load fighter photos."
        );
      }

      const photos = Array.isArray(body.photos)
        ? body.photos
        : [];

      setFighterPhotos(photos);

      const nextUrls = {};

      await Promise.all(
        photos.map(async (photo) => {
          try {
            const imageResponse = await fetch(
              `${API}${photo.image_url}`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            if (!imageResponse.ok) {
              return;
            }

            const blob = await imageResponse.blob();

            nextUrls[photo.id] =
              URL.createObjectURL(blob);
          } catch (err) {
            console.error(
              "Could not load fighter photo:",
              err
            );
          }
        })
      );

      setFighterPhotoUrls((current) => {
        Object.values(current).forEach((url) => {
          try {
            URL.revokeObjectURL(url);
          } catch (_) {}
        });

        return nextUrls;
      });
    } catch (err) {
      console.error(
        "Could not load fighter photos:",
        err
      );
    }
  }


  async function uploadFighterPhoto(file) {
    if (!file) return;

    if (
      ![
        "image/jpeg",
        "image/png",
        "image/webp",
      ].includes(file.type)
    ) {
      window.alert(
        "Please select a JPG, PNG, or WEBP image."
      );
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      window.alert(
        "Fighter photos must be 5 MB or smaller."
      );
      return;
    }

    setPhotoWorking(true);
    setMessage("");

    try {
      const token =
        localStorage.getItem("token");

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API}/api/fighter/me/photos?photo_type=${encodeURIComponent(
          photoType
        )}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not upload fighter photo."
        );
      }

      setMessage(
        body.message ||
          "Fighter photo uploaded."
      );

      await loadFighterPhotos();
    } catch (err) {
      const notice =
        err.message ||
        "Could not upload fighter photo.";

      setMessage(notice);
      window.alert(notice);
    } finally {
      setPhotoWorking(false);
    }
  }


  async function setPrimaryFighterPhoto(photoId) {
    setPhotoWorking(true);

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/photos/${photoId}/primary`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not update primary photo."
        );
      }

      setMessage(
        body.message ||
          "Primary flyer photo updated."
      );

      await loadFighterPhotos();
    } catch (err) {
      const notice =
        err.message ||
        "Could not update primary photo.";

      setMessage(notice);
      window.alert(notice);
    } finally {
      setPhotoWorking(false);
    }
  }


  async function deleteFighterPhoto(photoId) {
    const confirmed = window.confirm(
      "Delete this fighter photo?"
    );

    if (!confirmed) return;

    setPhotoWorking(true);

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/photos/${photoId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not delete fighter photo."
        );
      }

      setMessage(
        body.message || "Fighter photo deleted."
      );

      await loadFighterPhotos();
    } catch (err) {
      const notice =
        err.message ||
        "Could not delete fighter photo.";

      setMessage(notice);
      window.alert(notice);
    } finally {
      setPhotoWorking(false);
    }
  }


  async function loadContracts() {
    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/contracts`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load contracts."
        );
      }

      setContracts(
        Array.isArray(body.contracts)
          ? body.contracts
          : []
      );
    } catch (err) {
      console.error(
        "Could not load fighter contracts:",
        err
      );
    }
  }


  async function electronicallySignContract(
    contract
  ) {
    const contractId = contract.contract_id;

    const typedName = String(
      signatureNames[contractId] || ""
    ).trim();

    const agreed =
      signatureAgreements[contractId] === true;

    if (!typedName) {
      window.alert(
        "Type your full legal name before signing."
      );
      return;
    }

    if (!agreed) {
      window.alert(
        "You must agree to the contract before signing."
      );
      return;
    }

    const confirmed = window.confirm(
      "By selecting OK, you confirm that you have reviewed the official contract and intend to electronically sign it."
    );

    if (!confirmed) return;

    setContractWorkingId(contractId);
    setMessage("");

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/contracts/${contractId}/esign`,
        {
          method: "POST",
          headers: {
            Authorization:
              `Bearer ${token}`,
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            typed_legal_name: typedName,
            agreed: true,
          }),
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not electronically sign contract."
        );
      }

      setMessage(
        body.message ||
        "Contract electronically signed."
      );

      window.alert(
        body.message ||
        "Contract electronically signed."
      );

      setContracts((current) =>
        current.map((item) =>
          item.contract_id === contractId
            ? {
                ...item,
                status: "signed",
              }
            : item
        )
      );

      setFightOffers((current) =>
        current.map((offer) =>
          offer.contract_id === contractId
            ? {
                ...offer,
                status: "signed",
              }
            : offer
        )
      );

    } catch (err) {
      const notice =
        err.message ||
        "Could not electronically sign contract.";

      setMessage(notice);
      window.alert(notice);

    } finally {
      setContractWorkingId(null);
    }
  }


  async function uploadMySignedContract(
    contractId
  ) {
    const input =
      document.createElement("input");

    input.type = "file";
    input.accept = "application/pdf,.pdf";

    input.onchange = async () => {
      const file = input.files?.[0];

      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      setContractWorkingId(contractId);

      try {
        const token =
          localStorage.getItem("token");

        const response = await fetch(
          `${API}/api/fighter/me/contracts/${contractId}/signed-upload`,
          {
            method: "POST",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
            body: formData,
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(
            body.detail ||
            "Could not upload signed contract."
          );
        }

        setMessage(
          body.message ||
          "Signed contract uploaded."
        );

        window.alert(
          body.message ||
          "Signed contract uploaded."
        );

        await loadContracts();

        setFightOffers((current) =>
          current.map((offer) =>
            offer.contract_id === contractId
              ? {
                  ...offer,
                  status: "signed",
                }
              : offer
          )
        );
      } catch (err) {
        const notice =
          err.message ||
          "Could not upload signed contract.";

        setMessage(notice);
        window.alert(notice);
      } finally {
        setContractWorkingId(null);
      }
    };

    input.click();
  }


  async function openAdobeSigning(contract) {
    const contractId = contract.contract_id;

    // Open the tab immediately so mobile/browser
    // popup blockers do not block Adobe after fetch.
    const signingWindow = window.open(
      "",
      "_blank"
    );

    if (!signingWindow) {
      window.alert(
        "Please allow popups for TNGOS, then try again."
      );
      return;
    }

    signingWindow.document.write(
      `
        <html>
          <body style="
            margin:0;
            background:#080808;
            color:white;
            font-family:Arial,sans-serif;
            display:flex;
            align-items:center;
            justify-content:center;
            min-height:100vh;
            text-align:center;
          ">
            <div>
              <div style="
                color:#ef233c;
                font-size:14px;
                font-weight:900;
                letter-spacing:2px;
              ">
                TNG BOXING
              </div>
              <h2>Opening Adobe Acrobat Sign...</h2>
              <p style="color:#aaa;">
                Secure contract signature
              </p>
            </div>
          </body>
        </html>
      `
    );

    setContractWorkingId(contractId);
    setMessage("");

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/contracts/${contractId}/adobe-signing-url`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not open Adobe Acrobat Sign."
        );
      }

      if (!body.signing_url) {
        throw new Error(
          "Adobe signing link is not available yet."
        );
      }

      signingWindow.location.replace(
        body.signing_url
      );

    } catch (err) {
      try {
        signingWindow.close();
      } catch (_) {}

      const notice =
        err.message ||
        "Could not open Adobe Acrobat Sign.";

      setMessage(notice);
      window.alert(notice);

    } finally {
      setContractWorkingId(null);
    }
  }


  function downloadMyFullContract(contract) {
    try {
      // Uses the exact same official contract
      // renderer as Event Workspace.
      // autoPrint=true opens the browser's
      // Print / Save as PDF dialog.
      openOfficialContract(
        contract,
        true
      );
    } catch (err) {
      const notice =
        err.message ||
        "Could not download contract.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function downloadMySignedContract(
    contractId,
    eventName
  ) {
    setContractWorkingId(contractId);

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/contracts/${contractId}/signed-file`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        let detail =
          "Signed contract is not available.";

        try {
          const body =
            await response.json();

          detail =
            body.detail || detail;
        } catch {
          // Non-JSON error.
        }

        throw new Error(detail);
      }

      const blob = await response.blob();

      const url =
        URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;
      link.download =
        `${eventName || "TNG"}-signed-contract.pdf`
          .replace(
            /[^a-z0-9._-]+/gi,
            "-"
          );

      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(url);
    } catch (err) {
      const notice =
        err.message ||
        "Could not download signed contract.";

      setMessage(notice);
      window.alert(notice);
    } finally {
      setContractWorkingId(null);
    }
  }


  async function respondToOffer(
    contractId,
    action,
    responseMessage = ""
  ) {
    setOfferWorkingId(contractId);
    setMessage("");

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/fighter/me/fight-offers/${contractId}/respond`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            action,
            message: responseMessage,
          }),
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not update fight offer"
        );
      }

      setFightOffers((current) =>
        current.map((offer) =>
          offer.contract_id === contractId
            ? {
                ...offer,
                status: body.status,
              }
            : offer
        )
      );

      setMessage(body.message || "Offer updated.");
      window.alert(
        body.message || "Offer updated."
      );
    } catch (err) {
      const notice =
        err.message ||
        "Could not update fight offer";

      setMessage(notice);
      window.alert(notice);
    } finally {
      setOfferWorkingId(null);
    }
  }

  useEffect(() => {
    load();
    loadContracts();
    loadFighterPhotos();

    return () => {
      Object.values(fighterPhotoUrls).forEach((url) => {
        try {
          URL.revokeObjectURL(url);
        } catch (_) {}
      });
    };
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
      value: `${
        fightOffers.filter((offer) =>
          ![
            "accepted",
            "declined",
            "change_requested",
            "signed",
            "completed",
            "cancelled",
          ].includes(
            String(
              offer.status || ""
            ).toLowerCase()
          )
        ).length
      } pending`,
      note:
        "View, accept or decline fight offers.",
    },
    {
      title: "Contracts",
      value: `${contracts.length} contract${
        contracts.length === 1 ? "" : "s"
      }`,
      note:
        contracts.length > 0
          ? "Review and manage your bout agreements."
          : "No bout contracts assigned yet.",
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
        background:
          "radial-gradient(circle at top right, rgba(215,25,32,.24), transparent 28%), linear-gradient(180deg, #080808 0%, #111114 48%, #090909 100%)",
        color: "#fff",
        fontFamily: "Inter, Arial, sans-serif",
      }}
    >
      <header
        style={{
          background: "rgba(7,7,8,.94)",
          color: "#fff",
          padding: "18px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 15,
          flexWrap: "wrap",
          borderBottom: "1px solid rgba(255,255,255,.08)",
          position: "sticky",
          top: 0,
          zIndex: 20,
          backdropFilter: "blur(16px)",
        }}
      >
        <div>
          <div
            style={{
              color: "#ff3038",
              fontWeight: 950,
              fontSize: 12,
              letterSpacing: "2.5px",
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
          maxWidth: 1180,
          margin: "0 auto",
          padding: "26px 18px 60px",
        }}
      >
        <section
          style={{
            background:
              "linear-gradient(135deg, rgba(215,25,32,.94) 0%, rgba(92,5,10,.96) 42%, rgba(13,13,15,.98) 100%)",
            borderRadius: 24,
            padding: "30px 28px",
            marginBottom: 22,
            border: "1px solid rgba(255,255,255,.12)",
            boxShadow: "0 24px 60px rgba(0,0,0,.34)",
            position: "relative",
            overflow: "hidden",
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
                  color: "rgba(255,255,255,.68)",
                  fontSize: 11,
                  fontWeight: 900,
                  letterSpacing: "2px",
                }}
              >
                WELCOME
              </div>

              <h1
                style={{
                  margin: "6px 0 8px",
                  fontSize: "clamp(30px, 6vw, 52px)",
                  lineHeight: .95,
                  letterSpacing: "-1.8px",
                  textTransform: "uppercase",
                  fontWeight: 950,
                  textShadow: "0 8px 26px rgba(0,0,0,.35)",
                }}
              >
                {fighter.legal_name}
              </h1>

              <div
                style={{
                  color: "rgba(255,255,255,.78)",
                  fontWeight: 700,
                  fontSize: 15,
                }}
              >
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
                  fontSize: 10,
                  color: "rgba(255,255,255,.60)",
                  marginBottom: 6,
                  fontWeight: 900,
                  letterSpacing: "1.5px",
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
              "repeat(auto-fit, minmax(210px, 1fr))",
            gap: 14,
            marginBottom: 24,
          }}
        >
          {cards.map((card) => (
            <div
              key={card.title}
              style={{
                background:
                  "linear-gradient(145deg, rgba(28,28,31,.98), rgba(14,14,16,.98))",
                color: "#fff",
                borderRadius: 20,
                padding: 20,
                minHeight: 140,
                border: "1px solid rgba(255,255,255,.08)",
                boxShadow: "0 14px 30px rgba(0,0,0,.22)",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  color: "#ff3c43",
                  fontSize: 10,
                  fontWeight: 950,
                  textTransform: "uppercase",
                  letterSpacing: "1.7px",
                }}
              >
                {card.title}
              </div>

              <div
                style={{
                  fontSize: 28,
                  fontWeight: 950,
                  margin: "12px 0 8px",
                  textTransform: "capitalize",
                  letterSpacing: "-.8px",
                }}
              >
                {card.value}
              </div>

              <div
                style={{
                  color: "rgba(255,255,255,.58)",
                  fontSize: 12,
                  lineHeight: 1.5,
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
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 16,
              flexWrap: "wrap",
              marginBottom: 18,
            }}
          >
            <div>
              <h2 style={{ margin: "0 0 5px" }}>
                My Photos
              </h2>

              <div
                style={{
                  color: "#666",
                  maxWidth: 650,
                  lineHeight: 1.5,
                }}
              >
                Upload promotional photos that TNG
                Promotions can use for your fight flyers
                and event graphics. Choose your best
                photo as your Primary Flyer Photo.
              </div>
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <select
                value={photoType}
                onChange={(e) =>
                  setPhotoType(e.target.value)
                }
                disabled={photoWorking}
                style={{
                  padding: "10px 12px",
                  border: "1px solid #ccc",
                  borderRadius: 8,
                  background: "#fff",
                }}
              >
                <option value="headshot">
                  Headshot
                </option>

                <option value="fight_pose">
                  Fight Pose
                </option>

                <option value="action_shot">
                  Action Shot
                </option>
              </select>

              <label
                style={{
                  display: "inline-block",
                  padding: "10px 15px",
                  background: "#d71920",
                  color: "#fff",
                  borderRadius: 8,
                  fontWeight: 800,
                  cursor: photoWorking
                    ? "not-allowed"
                    : "pointer",
                  opacity: photoWorking ? 0.6 : 1,
                }}
              >
                {photoWorking
                  ? "Working..."
                  : "Upload Photo"}

                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={photoWorking}
                  onChange={(e) => {
                    const file =
                      e.target.files?.[0];

                    if (file) {
                      uploadFighterPhoto(file);
                    }

                    e.target.value = "";
                  }}
                  style={{
                    display: "none",
                  }}
                />
              </label>
            </div>
          </div>

          <div
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              background: "#f7f7f7",
              color: "#555",
              fontSize: 13,
              marginBottom: 18,
            }}
          >
            JPG, PNG or WEBP ? Maximum 5 MB ?
            Up to 5 photos
          </div>

          {!fighterPhotos.length ? (
            <div
              style={{
                border: "2px dashed #ddd",
                borderRadius: 12,
                padding: 30,
                textAlign: "center",
                color: "#666",
              }}
            >
              <div
                style={{
                  fontSize: 36,
                  marginBottom: 8,
                }}
              >
                ??
              </div>

              <strong>
                Add your first promotional photo
              </strong>

              <div
                style={{
                  marginTop: 6,
                  fontSize: 14,
                }}
              >
                Your first upload automatically becomes
                your Primary Flyer Photo.
              </div>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(190px, 1fr))",
                gap: 16,
              }}
            >
              {fighterPhotos.map((photo) => (
                <div
                  key={photo.id}
                  style={{
                    border: photo.is_primary
                      ? "2px solid #d71920"
                      : "1px solid #ddd",
                    borderRadius: 12,
                    overflow: "hidden",
                    background: "#fff",
                  }}
                >
                  <div
                    style={{
                      position: "relative",
                      height: 230,
                      background: "#eee",
                    }}
                  >
                    {fighterPhotoUrls[photo.id] ? (
                      <img
                        src={
                          fighterPhotoUrls[photo.id]
                        }
                        alt={
                          photo.file_name ||
                          "Fighter photo"
                        }
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          objectPosition: "center top",
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          height: "100%",
                          display: "grid",
                          placeItems: "center",
                          color: "#777",
                        }}
                      >
                        Loading photo...
                      </div>
                    )}

                    {photo.is_primary && (
                      <div
                        style={{
                          position: "absolute",
                          top: 10,
                          left: 10,
                          background: "#d71920",
                          color: "#fff",
                          padding: "6px 9px",
                          borderRadius: 20,
                          fontSize: 11,
                          fontWeight: 900,
                        }}
                      >
                        PRIMARY FLYER PHOTO
                      </div>
                    )}
                  </div>

                  <div style={{ padding: 13 }}>
                    <div
                      style={{
                        textTransform: "capitalize",
                        fontWeight: 800,
                        marginBottom: 3,
                      }}
                    >
                      {String(
                        photo.photo_type ||
                          "headshot"
                      ).replaceAll("_", " ")}
                    </div>

                    <div
                      style={{
                        color: "#777",
                        fontSize: 12,
                        marginBottom: 12,
                      }}
                    >
                      {photo.file_name}
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gap: 8,
                      }}
                    >
                      {!photo.is_primary && (
                        <button
                          type="button"
                          disabled={photoWorking}
                          onClick={() =>
                            setPrimaryFighterPhoto(
                              photo.id
                            )
                          }
                          style={{
                            padding: "9px 10px",
                            border: 0,
                            borderRadius: 7,
                            background: "#111",
                            color: "#fff",
                            fontWeight: 800,
                            cursor: "pointer",
                          }}
                        >
                          Set as Primary Flyer Photo
                        </button>
                      )}

                      <button
                        type="button"
                        disabled={photoWorking}
                        onClick={() =>
                          deleteFighterPhoto(
                            photo.id
                          )
                        }
                        style={{
                          padding: "9px 10px",
                          border: "1px solid #ddd",
                          borderRadius: 7,
                          background: "#fff",
                          color: "#a00",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        Delete Photo
                      </button>
                    </div>
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
            marginBottom: 20,
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            Fight Offers
          </h2>

          {!fightOffers.length ? (
            <div
              style={{
                color: "#666",
                padding: "10px 0",
              }}
            >
              You do not have any fight offers yet.
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: 14,
              }}
            >
              {fightOffers.map((offer) => {
                const status = String(
                  offer.status || "draft"
                ).toLowerCase();

                const canRespond = ![
                  "accepted",
                  "declined",
                  "change_requested",
                  "signed",
                  "completed",
                  "cancelled",
                ].includes(status);

                return (
                  <div
                    key={offer.contract_id}
                    style={{
                      border: "1px solid #ddd",
                      borderRadius: 12,
                      padding: 18,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent:
                          "space-between",
                        gap: 12,
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: 20,
                            fontWeight: 900,
                          }}
                        >
                          vs{" "}
                          {offer.opponent?.name ||
                            "Opponent TBD"}
                        </div>

                        <div
                          style={{
                            color: "#666",
                            marginTop: 4,
                          }}
                        >
                          {offer.opponent?.record
                            ? `Record: ${offer.opponent.record}`
                            : ""}
                        </div>
                      </div>

                      <div>
                        {statusBadge(status)}
                      </div>
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fit, minmax(150px, 1fr))",
                        gap: 12,
                        marginTop: 18,
                      }}
                    >
                      <div>
                        <small>Event</small>
                        <div>
                          <strong>
                            {offer.event?.name ||
                              "Event TBD"}
                          </strong>
                        </div>
                      </div>

                      <div>
                        <small>Date</small>
                        <div>
                          <strong>
                            {offer.event?.date ||
                              "TBD"}
                          </strong>
                        </div>
                      </div>

                      <div>
                        <small>Weight</small>
                        <div>
                          <strong>
                            {offer.weight
                              ? `${offer.weight} lb`
                              : "TBD"}
                          </strong>
                        </div>
                      </div>

                      <div>
                        <small>Rounds</small>
                        <div>
                          <strong>
                            {offer.rounds || 4}
                          </strong>
                        </div>
                      </div>

                      <div>
                        <small>Purse</small>
                        <div>
                          <strong>
                            {new Intl.NumberFormat(
                              "en-US",
                              {
                                style: "currency",
                                currency: "USD",
                              }
                            ).format(
                              Number(
                                offer.purse || 0
                              )
                            )}
                          </strong>
                        </div>
                      </div>

                      <div>
                        <small>Travel</small>
                        <div>
                          <strong>
                            {new Intl.NumberFormat(
                              "en-US",
                              {
                                style: "currency",
                                currency: "USD",
                              }
                            ).format(
                              Number(
                                offer.travel_expense ||
                                  0
                              )
                            )}
                          </strong>
                        </div>
                      </div>
                    </div>

                    {offer.additional_terms && (
                      <div
                        style={{
                          marginTop: 16,
                          padding: 12,
                          background: "#f7f7f7",
                          borderRadius: 8,
                        }}
                      >
                        <strong>
                          Additional Terms
                        </strong>
                        <div
                          style={{
                            marginTop: 5,
                            color: "#555",
                          }}
                        >
                          {offer.additional_terms}
                        </div>
                      </div>
                    )}

                    {canRespond && (
                      <div
                        style={{
                          display: "flex",
                          gap: 10,
                          flexWrap: "wrap",
                          marginTop: 18,
                        }}
                      >
                        <button
                          type="button"
                          disabled={
                            offerWorkingId ===
                            offer.contract_id
                          }
                          onClick={() =>
                            respondToOffer(
                              offer.contract_id,
                              "accept"
                            )
                          }
                          style={{
                            border: 0,
                            borderRadius: 8,
                            padding:
                              "11px 18px",
                            background:
                              "#176b2c",
                            color: "#fff",
                            fontWeight: 900,
                            cursor: "pointer",
                          }}
                        >
                          {offerWorkingId ===
                          offer.contract_id
                            ? "Updating..."
                            : "Accept Fight"}
                        </button>

                        <button
                          type="button"
                          disabled={
                            offerWorkingId ===
                            offer.contract_id
                          }
                          onClick={() => {
                            const request =
                              window.prompt(
                                "What would you like changed? Example: purse, weight, rounds, travel, opponent, or other terms."
                              );

                            if (
                              request &&
                              request.trim()
                            ) {
                              respondToOffer(
                                offer.contract_id,
                                "request_change",
                                request.trim()
                              );
                            }
                          }}
                          style={{
                            border:
                              "1px solid #c98b00",
                            borderRadius: 8,
                            padding:
                              "11px 18px",
                            background: "#fff",
                            color: "#8a5a00",
                            fontWeight: 900,
                            cursor: "pointer",
                          }}
                        >
                          Request Change
                        </button>

                        <button
                          type="button"
                          disabled={
                            offerWorkingId ===
                            offer.contract_id
                          }
                          onClick={() => {
                            if (
                              window.confirm(
                                "Decline this fight offer?"
                              )
                            ) {
                              respondToOffer(
                                offer.contract_id,
                                "decline"
                              );
                            }
                          }}
                          style={{
                            border:
                              "1px solid #c62828",
                            borderRadius: 8,
                            padding:
                              "11px 18px",
                            background: "#fff",
                            color: "#c62828",
                            fontWeight: 900,
                            cursor: "pointer",
                          }}
                        >
                          Decline
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
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
            My Contracts
          </h2>

          {contracts.length === 0 ? (
            <p style={{ color: "#666" }}>
              No contracts are available yet.
            </p>
          ) : (
            <div
              style={{
                display: "grid",
                gap: 14,
              }}
            >
              {contracts.map((contract) => (
                <div
                  key={contract.contract_id}
                  style={{
                    border:
                      "1px solid rgba(255,255,255,.12)",
                    borderRadius: 18,
                    padding: 18,
                    background:
                      "linear-gradient(145deg, #17171a 0%, #0d0d0f 100%)",
                    color: "#fff",
                    boxShadow:
                      "0 16px 34px rgba(0,0,0,.28)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent:
                        "space-between",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontWeight: 900,
                          fontSize: 18,
                        }}
                      >
                        {contract.event_name ||
                          "Fight Contract"}
                      </div>

                      <div
                        style={{
                          color:
                            "rgba(255,255,255,.62)",
                          marginTop: 4,
                        }}
                      >
                        vs.{" "}
                        {contract.opponent_name ||
                          "Opponent TBD"}
                      </div>
                    </div>

                    {statusBadge(
                      contract.status ||
                      "generated"
                    )}
                  </div>

                  <div
                    style={{
                      marginTop: 12,
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(160px, 1fr))",
                      gap: 8,
                      fontSize: 14,
                    }}
                  >
                    <div>
                      <strong>Date:</strong>{" "}
                      {contract.event_date ||
                        "TBD"}
                    </div>

                    <div>
                      <strong>Weight:</strong>{" "}
                      {contract.maximum_weight ||
                        "TBD"}{" "}
                      lb
                    </div>

                    <div>
                      <strong>Purse:</strong>{" "}
                      $
                      {Number(
                        contract.gross_purse || 0
                      ).toFixed(2)}
                    </div>

                    <div>
                      <strong>Signed PDF:</strong>{" "}
                      {contract.signed_document
                        ? "Uploaded"
                        : "Not uploaded"}
                    </div>
                  </div>

                  <div
                    style={{
                      marginTop: 12,
                      padding: 12,
                      background: "#f7f7f7",
                      borderRadius: 8,
                      fontSize: 14,
                    }}
                  >
                    <strong>
                      Travel / Hotel / Per Diem
                    </strong>

                    <div>
                      Travel:{" "}
                      {contract.travel_type ||
                        "N/A"}
                    </div>

                    <div>
                      Travel paid by:{" "}
                      {contract.travel_paid_by ||
                        "N/A"}
                    </div>

                    <div>
                      Travel amount: $
                      {Number(
                        contract.travel_expense ||
                          0
                      ).toFixed(2)}
                    </div>

                    <div>
                      Hotel:{" "}
                      {contract.hotel_provided ||
                        "N/A"}
                      {contract.hotel_name
                        ? ` - ${contract.hotel_name}`
                        : ""}
                    </div>

                    <div>
                      Hotel nights:{" "}
                      {contract.hotel_nights || 0}
                    </div>

                    <div>
                      Per diem: $
                      {Number(
                        contract.per_diem_daily ||
                          0
                      ).toFixed(2)}
                      /day ?{" "}
                      {contract.per_diem_days || 0}
                      {" = $"}
                      {Number(
                        contract.per_diem_total ||
                          0
                      ).toFixed(2)}
                    </div>
                  </div>

                  {contract.additional_terms && (
                    <div
                      style={{
                        marginTop: 12,
                        fontSize: 14,
                      }}
                    >
                      <strong>
                        Additional Terms:
                      </strong>{" "}
                      {contract.additional_terms}
                    </div>
                  )}

                  {String(
                    contract.adobe_status || ""
                  ).toUpperCase() === "SIGNED" ? (
                    <div
                      style={{
                        marginTop: 18,
                        padding: 20,
                        border:
                          "1px solid rgba(38,208,124,.55)",
                        borderRadius: 16,
                        background:
                          "linear-gradient(135deg, rgba(12,54,36,.96), rgba(7,18,14,.98))",
                        boxShadow:
                          "0 12px 34px rgba(0,0,0,.28)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          color: "#4ade80",
                          fontWeight: 950,
                          fontSize: 19,
                          letterSpacing: 0.5,
                        }}
                      >
                        <span
                          style={{
                            display: "inline-flex",
                            width: 30,
                            height: 30,
                            borderRadius: "50%",
                            alignItems: "center",
                            justifyContent: "center",
                            background:
                              "rgba(74,222,128,.15)",
                            border:
                              "1px solid rgba(74,222,128,.45)",
                          }}
                        >
                          ?
                        </span>

                        CONTRACT SIGNED
                      </div>

                      <div
                        style={{
                          color: "#fff",
                          marginTop: 10,
                          fontWeight: 800,
                        }}
                      >
                        Adobe Acrobat Sign
                      </div>

                      {contract.adobe_signed_at && (
                        <div
                          style={{
                            color:
                              "rgba(255,255,255,.62)",
                            marginTop: 5,
                            fontSize: 13,
                          }}
                        >
                          Completed{" "}
                          {new Date(
                            contract.adobe_signed_at
                          ).toLocaleString()}
                        </div>
                      )}

                      {contract.signed_document && (
                        <button
                          type="button"
                          disabled={
                            contractWorkingId ===
                            contract.contract_id
                          }
                          onClick={() =>
                            downloadMySignedContract(
                              contract.contract_id,
                              contract.event_name
                            )
                          }
                          style={{
                            marginTop: 16,
                            width: "100%",
                            border:
                              "1px solid rgba(74,222,128,.5)",
                            borderRadius: 10,
                            padding: "13px 16px",
                            background:
                              "rgba(74,222,128,.12)",
                            color: "#fff",
                            fontWeight: 950,
                            fontSize: 14,
                            cursor: "pointer",
                          }}
                        >
                          DOWNLOAD SIGNED CONTRACT
                        </button>
                      )}
                    </div>
                  ) : contract.adobe_signing_available ? (
                    <div
                      style={{
                        marginTop: 18,
                        padding: 20,
                        border:
                          "1px solid rgba(239,35,60,.45)",
                        borderRadius: 18,
                        background:
                          "linear-gradient(145deg, #161619 0%, #0b0b0d 100%)",
                        boxShadow:
                          "0 16px 38px rgba(0,0,0,.34)",
                        color: "#fff",
                      }}
                    >
                      <div
                        style={{
                          color: "#ef233c",
                          fontSize: 12,
                          fontWeight: 950,
                          letterSpacing: 2,
                        }}
                      >
                        ADOBE SIGN
                      </div>

                      <div
                        style={{
                          marginTop: 7,
                          fontSize: 21,
                          fontWeight: 950,
                        }}
                      >
                        CONTRACT READY
                      </div>

                      <div
                        style={{
                          marginTop: 8,
                          color:
                            "rgba(255,255,255,.66)",
                          fontSize: 13,
                        }}
                      >
                        Secure electronic signature
                        through Adobe Acrobat Sign.
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns:
                            "repeat(auto-fit, minmax(120px, 1fr))",
                          gap: 9,
                          marginTop: 16,
                        }}
                      >
                        <div
                          style={{
                            padding: 11,
                            background:
                              "rgba(255,255,255,.05)",
                            borderRadius: 10,
                          }}
                        >
                          <div
                            style={{
                              fontSize: 10,
                              color:
                                "rgba(255,255,255,.5)",
                              fontWeight: 900,
                              letterSpacing: 1,
                            }}
                          >
                            PURSE
                          </div>

                          <div
                            style={{
                              marginTop: 4,
                              fontWeight: 950,
                              fontSize: 17,
                            }}
                          >
                            $
                            {Number(
                              contract.gross_purse ||
                                0
                            ).toFixed(2)}
                          </div>
                        </div>

                        <div
                          style={{
                            padding: 11,
                            background:
                              "rgba(255,255,255,.05)",
                            borderRadius: 10,
                          }}
                        >
                          <div
                            style={{
                              fontSize: 10,
                              color:
                                "rgba(255,255,255,.5)",
                              fontWeight: 900,
                              letterSpacing: 1,
                            }}
                          >
                            OPPONENT
                          </div>

                          <div
                            style={{
                              marginTop: 4,
                              fontWeight: 900,
                              fontSize: 14,
                            }}
                          >
                            {contract.opponent_name ||
                              "TBD"}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        disabled={
                          contractWorkingId ===
                          contract.contract_id
                        }
                        onClick={() =>
                          openAdobeSigning(contract)
                        }
                        style={{
                          marginTop: 18,
                          width: "100%",
                          border: 0,
                          borderRadius: 11,
                          padding: "15px 18px",
                          background:
                            "linear-gradient(135deg, #ef233c, #c1121f)",
                          color: "#fff",
                          fontWeight: 950,
                          fontSize: 15,
                          letterSpacing: 0.5,
                          cursor:
                            contractWorkingId ===
                            contract.contract_id
                              ? "wait"
                              : "pointer",
                          boxShadow:
                            "0 10px 24px rgba(239,35,60,.28)",
                        }}
                      >
                        {contractWorkingId ===
                        contract.contract_id
                          ? "OPENING ADOBE..."
                          : "REVIEW & SIGN WITH ADOBE"}
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          loadContracts()
                        }
                        style={{
                          marginTop: 9,
                          width: "100%",
                          border:
                            "1px solid rgba(255,255,255,.16)",
                          borderRadius: 9,
                          padding: "10px 14px",
                          background: "transparent",
                          color:
                            "rgba(255,255,255,.75)",
                          fontWeight: 800,
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                      >
                        REFRESH CONTRACT STATUS
                      </button>

                      <div
                        style={{
                          textAlign: "center",
                          marginTop: 10,
                          color:
                            "rgba(255,255,255,.42)",
                          fontSize: 11,
                        }}
                      >
                        After signing in Adobe,
                        return here and refresh status.
                      </div>
                    </div>
                  ) : null}

                  {![
                    "signed",
                    "declined",
                    "cancelled",
                    "completed",
                  ].includes(
                    String(
                      contract.status || ""
                    ).toLowerCase()
                  ) && (
                    <div
                      style={{
                        marginTop: 16,
                        padding: 16,
                        border: "2px solid #111",
                        borderRadius: 10,
                        background: "#fafafa",
                      }}
                    >
                      <div
                        style={{
                          fontSize: 17,
                          fontWeight: 900,
                          marginBottom: 8,
                        }}
                      >
                        {contract.adobe_agreement_id
                          ? "Other Signing Option"
                          : "Electronic Signature"}
                      </div>

                      <div
                        style={{
                          fontSize: 13,
                          color: "#555",
                          marginBottom: 12,
                        }}
                      >
                        {contract.adobe_agreement_id
                          ? "If you cannot use Adobe, you may use the TNGOS electronic signature below."
                          : "Review and download the official contract before signing."}
                      </div>

                      <label
                        style={{
                          display: "block",
                          fontWeight: 800,
                          fontSize: 13,
                          marginBottom: 6,
                        }}
                      >
                        Type Your Full Legal Name
                      </label>

                      <input
                        type="text"
                        value={
                          signatureNames[
                            contract.contract_id
                          ] || ""
                        }
                        onChange={(e) =>
                          setSignatureNames(
                            (current) => ({
                              ...current,
                              [contract.contract_id]:
                                e.target.value,
                            })
                          )
                        }
                        placeholder={
                          fighter.legal_name ||
                          "Full legal name"
                        }
                        style={{
                          width: "100%",
                          boxSizing: "border-box",
                          padding: 11,
                          border: "1px solid #aaa",
                          borderRadius: 7,
                          fontSize: 15,
                        }}
                      />

                      <label
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 9,
                          marginTop: 13,
                          fontSize: 13,
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={
                            signatureAgreements[
                              contract.contract_id
                            ] === true
                          }
                          onChange={(e) =>
                            setSignatureAgreements(
                              (current) => ({
                                ...current,
                                [contract.contract_id]:
                                  e.target.checked,
                              })
                            )
                          }
                          style={{
                            marginTop: 3,
                          }}
                        />

                        <span>
                          I have reviewed the official
                          professional boxing contract,
                          agree to its terms, and intend
                          my typed legal name to serve as
                          my electronic signature.
                        </span>
                      </label>

                      <button
                        type="button"
                        disabled={
                          contractWorkingId ===
                            contract.contract_id ||
                          !String(
                            signatureNames[
                              contract.contract_id
                            ] || ""
                          ).trim() ||
                          signatureAgreements[
                            contract.contract_id
                          ] !== true
                        }
                        onClick={() =>
                          electronicallySignContract(
                            contract
                          )
                        }
                        style={{
                          marginTop: 14,
                          width: "100%",
                          border: 0,
                          borderRadius: 8,
                          padding: "12px 16px",
                          background: "#b71c1c",
                          color: "#fff",
                          fontWeight: 900,
                          fontSize: 15,
                          cursor: "pointer",
                        }}
                      >
                        {contractWorkingId ===
                        contract.contract_id
                          ? "Signing..."
                          : "Sign Contract Electronically"}
                      </button>
                    </div>
                  )}

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      flexWrap: "wrap",
                      marginTop: 14,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        downloadMyFullContract(
                          contract
                        )
                      }
                      style={{
                        border: 0,
                        borderRadius: 8,
                        padding: "11px 16px",
                        background: "#111",
                        color: "#fff",
                        fontWeight: 900,
                        cursor: "pointer",
                      }}
                    >
                      Download Contract PDF
                    </button>

                    

                    <button
                      type="button"
                      disabled={
                        contractWorkingId ===
                        contract.contract_id
                      }
                      onClick={() =>
                        uploadMySignedContract(
                          contract.contract_id
                        )
                      }
                      style={{
                        border: 0,
                        borderRadius: 8,
                        padding: "11px 16px",
                        background: "#111",
                        color: "#fff",
                        fontWeight: 900,
                        cursor: "pointer",
                      }}
                    >
                      {contract.signed_document
                        ? "Replace Signed PDF"
                        : "Upload Signed PDF"}
                    </button>

                    {contract.signed_document && (
                      <button
                        type="button"
                        disabled={
                          contractWorkingId ===
                          contract.contract_id
                        }
                        onClick={() =>
                          downloadMySignedContract(
                            contract.contract_id,
                            contract.event_name
                          )
                        }
                        style={{
                          border:
                            "1px solid #111",
                          borderRadius: 8,
                          padding:
                            "11px 16px",
                          background: "#fff",
                          color: "#111",
                          fontWeight: 900,
                          cursor: "pointer",
                        }}
                      >
                        Download Signed PDF
                      </button>
                    )}
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

                  {event.qr_png_base64 && (
                    <div
                      style={{
                        marginTop: 18,
                        padding: 16,
                        background: "#f7f7f7",
                        borderRadius: 12,
                        textAlign: "center",
                      }}
                    >
                      <div
                        style={{
                          fontWeight: 900,
                          marginBottom: 10,
                        }}
                      >
                        MY TICKET QR
                      </div>

                      <img
                        src={`data:image/png;base64,${event.qr_png_base64}`}
                        alt={`${event.event_name} ticket sales QR`}
                        style={{
                          width: 220,
                          maxWidth: "100%",
                          background: "#fff",
                          padding: 10,
                          borderRadius: 10,
                        }}
                      />

                      <div
                        style={{
                          marginTop: 10,
                          color: "#666",
                          fontSize: 12,
                        }}
                      >
                        Scan this QR to purchase tickets
                        through your fighter sales link.
                      </div>
                    </div>
                  )}

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
