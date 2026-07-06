import Dashboard from "./pages/Dashboard.jsx";
import AIDisplay from "./pages/AIDisplay.jsx";
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import Sidebar from "./components/Sidebar.jsx";
import Members from "./pages/Members.jsx";
import Sales from "./pages/Sales.jsx";
import SalesRepDashboard from "./pages/SalesRepDashboard.jsx";
import JoinPage from "./pages/JoinPage.jsx";
import Leads from "./pages/Leads.jsx";
import FrontDesk from "./pages/FrontDesk.jsx";
import Products from "./pages/Products.jsx";
import DuplicateReview from "./pages/DuplicateReview.jsx";
import AITrainer from "./pages/AITrainer.jsx";
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {

  const [email, setEmail] = useState("admin@tngboxinggym.com");
  const [password, setPassword] = useState("admin123");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [page, setPage] = useState("Dashboard");
  const [dash, setDash] = useState(null);
  const [reps, setReps] = useState([]);
  const [leader, setLeader] = useState([]);
  const [msg, setMsg] = useState("");
  const [qrCodes, setQrCodes] = useState({});const params = new URLSearchParams(window.location.search);
const paymentStatus = params.get("payment");

if (paymentStatus === "success") {
  return (
    <main style={styles.paymentPage}>
      <div style={styles.paymentCard}>
        <h1>🥊 Payment Successful!</h1>
        <p>Welcome to TNG Boxing. Your membership payment was processed successfully.</p>
        <p>Our team will follow up with your next steps.</p>
        <button style={styles.primaryBtn} onClick={() => window.location.href = "/"}>
          Go to TNG CRM
        </button>
      </div>
    </main>
  );
}

if (paymentStatus === "cancelled") {
  return (
    <main style={styles.paymentPage}>
      <div style={styles.paymentCard}>
        <h1>Payment Cancelled</h1>
        <p>Your checkout was cancelled. You can restart your signup anytime.</p>
      </div>
    </main>
  );
}

if (paymentStatus === "failed") {
  return (
    <main style={styles.paymentPage}>
      <div style={styles.paymentCard}>
        <h1>Payment Failed</h1>
        <p>Something went wrong with the payment. Please try again or contact TNG Boxing.</p>
      </div>
    </main>
  );
}

if (params.has("join")) {
  return <JoinPage />;
}

  async function login() {
    const r = await fetch(`${API}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const j = await r.json();

    if (j.token) {
      localStorage.setItem("token", j.token);
      setToken(j.token);
      setMsg("Logged in");
      setTimeout(load, 300);
    } else {
      setMsg(j.detail || "Login failed");
    }
  }

  async function load() {
    const h = { Authorization: "Bearer " + localStorage.getItem("token") };
    setDash(await (await fetch(`${API}/api/dashboard`, { headers: h })).json());
    setReps(await (await fetch(`${API}/api/reps`, { headers: h })).json().catch(() => []));
    setLeader(await (await fetch(`${API}/api/leaderboard`, { headers: h })).json().catch(() => []));
  }
async function loadQr(repId) {
  const h = { Authorization: "Bearer " + localStorage.getItem("token") };

  const r = await fetch(`${API}/api/reps/${repId}/qr`, { headers: h });
  const j = await r.json();

  setQrCodes((old) => ({ ...old, [repId]: j }));
}

async function syncTngOS() {
  const r = await fetch(`${API}/api/clover/sync-all`, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + localStorage.getItem("token"),
    },
  });

  const j = await r.json();

  if (!r.ok) {
    alert(j.detail || "TNG OS Sync failed");
    return;
  }

  alert(
`✅ TNG OS Sync Complete

Products Synced: ${j.products?.synced || 0}

Customers Added: ${j.customers?.synced || 0}

Customers Updated: ${j.customers?.updated || 0}

Sales Imported: ${j.sales?.synced || 0}

Sales Skipped: ${j.sales?.skipped || 0}`
  );

  load();
}

  async function addRep() {
    const name = prompt("Rep name?");
    const repEmail = prompt("Rep email?");
    const slug = prompt("Referral slug? Example: mike");
    const clover = prompt("Clover link?");
    if (!name || !repEmail || !slug) return;

    const r = await fetch(`${API}/api/reps`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({
        name,
        email: repEmail,
        referral_slug: slug,
        clover_link: clover || "",
        password: "TNG12345",
      }),
    });

    setMsg(JSON.stringify(await r.json()));
    load();
  }

  if (!token) {
    return (
      <main style={styles.loginPage}>
        <div style={styles.loginCard}>
          <h1>🥊 TNG CRM</h1>
          <p style={styles.sub}>Sales • Members • Commissions • Clover</p>
          <input style={styles.input} value={email} onChange={(e) => setEmail(e.target.value)} />
          <input style={styles.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button style={styles.primaryBtn} onClick={login}>Login</button>
          <p>{msg}</p>
        </div>
      </main>
    );
  }

  return (
    <div style={styles.app}>
     <Sidebar page={page} setPage={setPage} styles={styles} />

      <main style={styles.main}>
        <header style={styles.header}>
          <div>
            <h1>{page}</h1>
            <p>TNG Boxing sales and commission command center</p>
          </div>
          <div>
            <button style={styles.secondaryBtn} onClick={load}>Refresh</button>
<button
  style={{
    ...styles.primaryBtnSmall,
    background: "#111",
  }}
  onClick={syncTngOS}
>
  🔄 TNG OS Sync
</button>            <button style={styles.primaryBtnSmall} onClick={addRep}>Add Rep</button>
            <button style={styles.logoutBtn} onClick={() => { localStorage.clear(); setToken(""); }}>Logout</button>
          </div>
        </header>

        {msg && <p style={styles.notice}>{msg}</p>}

        {page === "Dashboard" && (
  <Dashboard
    dash={dash}
    leader={leader}
    load={load}
  />
)}
     

      {page === "Members" && (
  <Members />
)}

{page === "Front Desk" && (
  <FrontDesk />
)}

{page === "Sales" && (
  <Sales />
)}

{page === "Products" && (
  <Products />
)}

{page === "Duplicate Review" && (
  <DuplicateReview />
)}

{page === "Leads" && (
  <Leads />
)}       {page === "Sales Reps" && (
  <SalesRepDashboard />
)}

{page === "AI Trainer" && (
  <AITrainer />
)}


      {page === "QR Referrals" && (
  <section style={styles.panel}>
    <h2>QR Referrals</h2>
    <p>Each sales rep has their own referral page and QR code.</p>

    {Array.isArray(reps) &&
      reps.map((r) => (
        <div key={r.id} style={styles.repCard}>
          <h3>{r.name}</h3>

          <p>
            <b>Referral:</b> /join/{r.slug}
          </p>

          <p>
            {r.clover_link ? "✅ Clover Connected" : "❌ Clover Not Connected"}
          </p>

          <button
            style={styles.secondaryBtn}
            onClick={() => loadQr(r.id)}
          >
            Generate QR Code
          </button>

          {qrCodes[r.id] && (
            <>
              <p>
                <b>Referral URL</b>
              </p>

              <a
                href={qrCodes[r.id].url}
                target="_blank"
                rel="noreferrer"
              >
                {qrCodes[r.id].url}
              </a>

              <br />
              <br />

              <img
                src={`data:image/png;base64,${qrCodes[r.id].qr_png_base64}`}
                alt="QR Code"
                style={{
                  width: 180,
                  border: "1px solid #ddd",
                  borderRadius: 10,
                }}
              />
            </>
          )}
        </div>
      ))}
  </section>
)}
        {page === "Clover" && (
          <section style={styles.panel}>
            <h2>Clover Integration</h2>
            <p>Backend webhook is ready at:</p>
            <code>{API}/api/clover/webhook</code>
            <p>Next step: add Clover webhook secret and match payments to sales reps.</p>
          </section>
        )}

        {page === "Reports" && (
          <section style={styles.panel}>
            <h2>Leaderboard</h2>
            {Array.isArray(leader) && leader.map((r, i) => (
              <div key={r.rep_id} style={styles.row}>
                <b>#{i + 1} {r.name}</b>
                <span>{r.sales} sales</span>
                <span>${Number(r.revenue || 0).toFixed(2)}</span>
                <span>{Number((r.rate || 0) * 100).toFixed(0)}%</span>
              </div>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div style={styles.card}>
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}

const styles = {
  loginPage: {
    minHeight: "100vh",
    background: "#0b0b0f",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "Arial",
  },
paymentPage: {
  minHeight: "100vh",
  background: "#0b0b0f",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  fontFamily: "Arial",
  padding: 20,
},

paymentCard: {
  background: "white",
  padding: 36,
  borderRadius: 18,
  maxWidth: 520,
  textAlign: "center",
  boxShadow: "0 20px 50px rgba(0,0,0,.3)",
},
  loginCard: {
    background: "white",
    padding: 32,
    borderRadius: 18,
    width: 380,
    boxShadow: "0 20px 50px rgba(0,0,0,.3)",
  },
  sub: { color: "#666", marginBottom: 20 },
  input: {
    width: "100%",
    padding: 14,
    marginBottom: 12,
    borderRadius: 10,
    border: "1px solid #ddd",
    boxSizing: "border-box",
  },
  primaryBtn: {
    width: "100%",
    padding: 14,
    background: "#d71920",
    color: "white",
    border: 0,
    borderRadius: 10,
    fontWeight: "bold",
    cursor: "pointer",
  },
  app: { display: "flex", minHeight: "100vh", fontFamily: "Arial", background: "#f5f5f7" },
  sidebar: {
    width: 230,
    background: "#0b0b0f",
    color: "white",
    padding: 24,
  },
  navBtn: {
    display: "block",
    width: "100%",
    padding: "12px",
    marginBottom: "8px",
    border: 0,
    borderRadius: 10,
    color: "white",
    textAlign: "left",
    cursor: "pointer",
    fontWeight: "bold",
  },
  main: { flex: 1, padding: 28 },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  secondaryBtn: {
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #ccc",
    marginRight: 8,
    cursor: "pointer",
  },
  primaryBtnSmall: {
    padding: "10px 14px",
    borderRadius: 10,
    border: 0,
    background: "#d71920",
    color: "white",
    marginRight: 8,
    cursor: "pointer",
  },
  logoutBtn: {
    padding: "10px 14px",
    borderRadius: 10,
    border: 0,
    background: "#111",
    color: "white",
    cursor: "pointer",
  },
  notice: {
    background: "#fff3cd",
    padding: 12,
    borderRadius: 10,
  },
  grid4: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 16,
    marginBottom: 24,
  },
  card: {
    background: "white",
    padding: 22,
    borderRadius: 16,
    boxShadow: "0 8px 20px rgba(0,0,0,.06)",
  },
  panel: {
    background: "white",
    padding: 22,
    borderRadius: 16,
    marginBottom: 24,
    boxShadow: "0 8px 20px rgba(0,0,0,.06)",
  },
  repGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: 14,
  },
  repCard: {
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 16,
    background: "#fafafa",
  },
  row: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr 1fr 1fr",
    padding: 12,
    borderBottom: "1px solid #eee",
  },
};

const host = window.location.hostname.toLowerCase();

if (host === "display.tngboxinggym.com") {
  createRoot(document.getElementById("root")).render(<AIDisplay />);
} else {
  createRoot(document.getElementById("root")).render(<App />);
}