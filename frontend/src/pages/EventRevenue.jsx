import { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "https://sea-lion-app-2-gxyfr.ondigitalocean.app";

function money(value) {
  const num = Number(value || 0);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(num);
}

function ScoreBadge({ score }) {
  const value = Number(score || 0);

  let label = "Low";

  if (value >= 85) label = "Hot";
  else if (value >= 70) label = "Strong";
  else if (value >= 50) label = "Developing";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 10px",
        borderRadius: 999,
        background: "#17171d",
        border: "1px solid #34343d",
        fontWeight: 700,
        fontSize: 12,
      }}
    >
      {value}/100 · {label}
    </span>
  );
}

function MetricCard({ label, value, subtext }) {
  return (
    <div
      style={{
        background: "#111116",
        border: "1px solid #27272f",
        borderRadius: 16,
        padding: 18,
        minHeight: 110,
      }}
    >
      <div
        style={{
          color: "#9999a5",
          fontSize: 12,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 0.6,
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: 30,
          fontWeight: 900,
          marginTop: 8,
        }}
      >
        {value}
      </div>

      {subtext ? (
        <div
          style={{
            color: "#777783",
            fontSize: 12,
            marginTop: 6,
          }}
        >
          {subtext}
        </div>
      ) : null}
    </div>
  );
}

export default function EventRevenue({ eventId = 1 }) {
  const [tab, setTab] = useState("SPONSOR");

  const [dashboard, setDashboard] = useState({
    prospects: 0,
    high_intent_prospects: 0,
    pipeline_value: 0,
    committed: 0,
    collected: 0,
  });

  const [prospects, setProspects] = useState([]);
  const [packages, setPackages] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchJson(path) {
    const response = await fetch(`${API_BASE}${path}`);

    if (!response.ok) {
      const text = await response.text();

      throw new Error(
        `Request failed ${response.status}: ${text || response.statusText}`
      );
    }

    return response.json();
  }

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [dashboardData, prospectData, packageData] = await Promise.all([
        fetchJson(`/api/events/${eventId}/revenue/dashboard`),

        fetchJson(
          `/api/events/${eventId}/revenue/prospects?prospect_type=${tab}`
        ),

        fetchJson(
          `/api/events/${eventId}/revenue/packages?package_type=${tab}`
        ),
      ]);

      setDashboard(dashboardData || {});
      setProspects(Array.isArray(prospectData) ? prospectData : []);
      setPackages(Array.isArray(packageData) ? packageData : []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load revenue data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [eventId, tab]);

  const tabPipeline = useMemo(() => {
    return prospects.reduce((total, prospect) => {
      return total + Number(prospect.recommended_ask || 0);
    }, 0);
  }, [prospects]);

  const highIntentCount = useMemo(() => {
    return prospects.filter(
      (prospect) => Number(prospect.fit_score || 0) >= 80
    ).length;
  }, [prospects]);

  function openPlaceholder(type) {
    alert(
      `${type} Scout is the next build step. This button will search for real businesses, rank them, and add qualified leads into this event.`
    );
  }

  return (
    <div
      style={{
        minHeight: "100%",
        color: "#f5f5f7",
        padding: 24,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 12,
              color: "#e6202d",
              fontWeight: 900,
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            TNG Promotions
          </div>

          <h1
            style={{
              fontSize: 32,
              margin: "5px 0 6px",
              fontWeight: 900,
            }}
          >
            Event Revenue Engine
          </h1>

          <p
            style={{
              margin: 0,
              color: "#9999a5",
              maxWidth: 650,
            }}
          >
            Find, rank, contact, close, and collect revenue from sponsors and
            vendors for this event.
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            openPlaceholder(tab === "SPONSOR" ? "Sponsor" : "Vendor")
          }
          style={{
            border: 0,
            background: "#e6202d",
            color: "white",
            borderRadius: 10,
            padding: "12px 18px",
            fontWeight: 900,
            cursor: "pointer",
          }}
        >
          {tab === "SPONSOR" ? "Find Sponsors" : "Find Vendors"}
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 26,
          marginBottom: 18,
        }}
      >
        {[
          ["SPONSOR", "Sponsors"],
          ["VENDOR", "Vendors"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            style={{
              border:
                tab === value
                  ? "1px solid #e6202d"
                  : "1px solid #2a2a32",
              background: tab === value ? "#241014" : "#111116",
              color: "white",
              borderRadius: 10,
              padding: "10px 16px",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <div
          style={{
            background: "#2a1114",
            border: "1px solid #6f2028",
            color: "#ffb4ba",
            padding: 14,
            borderRadius: 12,
            marginBottom: 18,
          }}
        >
          {error}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        <MetricCard
          label="Prospects"
          value={prospects.length}
          subtext={`${tab === "SPONSOR" ? "Sponsor" : "Vendor"} pipeline`}
        />

        <MetricCard
          label="High Intent"
          value={highIntentCount}
          subtext="Fit score 80+"
        />

        <MetricCard
          label="Pipeline"
          value={money(tabPipeline)}
          subtext="Current tab"
        />

        <MetricCard
          label="Committed"
          value={money(dashboard.committed)}
          subtext="All event revenue"
        />

        <MetricCard
          label="Collected"
          value={money(dashboard.collected)}
          subtext="Paid revenue"
        />
      </div>

      <div
        style={{
          marginTop: 26,
          background: "#0f0f14",
          border: "1px solid #27272f",
          borderRadius: 16,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "18px 20px",
            borderBottom: "1px solid #27272f",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: 20,
              }}
            >
              {tab === "SPONSOR"
                ? "Sponsor Pipeline"
                : "Vendor Pipeline"}
            </h2>

            <div
              style={{
                color: "#81818d",
                fontSize: 13,
                marginTop: 4,
              }}
            >
              Highest-fit prospects appear first.
            </div>
          </div>

          <div
            style={{
              color: "#9999a5",
              fontSize: 13,
            }}
          >
            Packages: {packages.length}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 28 }}>Loading revenue data...</div>
        ) : prospects.length === 0 ? (
          <div
            style={{
              padding: 36,
              textAlign: "center",
              color: "#8f8f99",
            }}
          >
            <div
              style={{
                fontSize: 18,
                fontWeight: 800,
                color: "#eeeeef",
                marginBottom: 8,
              }}
            >
              No {tab === "SPONSOR" ? "sponsors" : "vendors"} yet
            </div>

            <div>
              Use{" "}
              <strong>
                {tab === "SPONSOR" ? "Find Sponsors" : "Find Vendors"}
              </strong>{" "}
              or add a lead manually.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 900,
              }}
            >
              <thead>
                <tr
                  style={{
                    background: "#15151b",
                    color: "#9696a2",
                    fontSize: 12,
                    textTransform: "uppercase",
                  }}
                >
                  <th style={thStyle}>Business</th>
                  <th style={thStyle}>Fit</th>
                  <th style={thStyle}>Industry</th>
                  <th style={thStyle}>Distance</th>
                  <th style={thStyle}>Suggested Ask</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>

              <tbody>
                {prospects.map((prospect) => (
                  <tr
                    key={prospect.id}
                    style={{
                      borderTop: "1px solid #24242b",
                    }}
                  >
                    <td style={tdStyle}>
                      <div
                        style={{
                          fontWeight: 900,
                          color: "#ffffff",
                        }}
                      >
                        {prospect.business_name || "Unnamed Business"}
                      </div>

                      <div
                        style={{
                          color: "#777783",
                          fontSize: 12,
                          marginTop: 3,
                        }}
                      >
                        {prospect.email || prospect.phone || "No contact yet"}
                      </div>
                    </td>

                    <td style={tdStyle}>
                      <ScoreBadge score={prospect.fit_score} />
                    </td>

                    <td style={tdStyle}>
                      {prospect.industry || "—"}
                    </td>

                    <td style={tdStyle}>
                      {prospect.distance_miles !== null &&
                      prospect.distance_miles !== undefined
                        ? `${prospect.distance_miles} mi`
                        : "—"}
                    </td>

                    <td style={tdStyle}>
                      <strong>
                        {prospect.recommended_ask
                          ? money(prospect.recommended_ask)
                          : "—"}
                      </strong>
                    </td>

                    <td style={tdStyle}>
                      {prospect.status || "NEW"}
                    </td>

                    <td style={tdStyle}>
                      <div
                        style={{
                          display: "flex",
                          gap: 6,
                          flexWrap: "wrap",
                        }}
                      >
                        <button
                          type="button"
                          style={smallButtonStyle}
                        >
                          View
                        </button>

                        <button
                          type="button"
                          style={smallButtonStyle}
                        >
                          Proposal
                        </button>

                        <button
                          type="button"
                          style={smallButtonStyle}
                        >
                          Email
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "12px 16px",
  fontWeight: 800,
};

const tdStyle = {
  padding: "15px 16px",
  verticalAlign: "middle",
};

const smallButtonStyle = {
  background: "#18181f",
  border: "1px solid #33333c",
  color: "#f1f1f3",
  borderRadius: 8,
  padding: "7px 10px",
  fontSize: 12,
  fontWeight: 800,
  cursor: "pointer",
};

