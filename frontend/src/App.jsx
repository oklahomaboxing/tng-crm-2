import React, { useState } from "react";
import { createRoot } from "react-dom/client";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [email, setEmail] = useState("admin@tngboxinggym.com");
  const [password, setPassword] = useState("admin123");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [dash, setDash] = useState(null);
  const [reps, setReps] = useState([]);
  const [leader, setLeader] = useState([]);
  const [msg, setMsg] = useState("");
  const [page, setPage] = useState("Dashboard");
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
    } else setMsg(j.detail || "Login failed");
  }

  async function load() {
    const h = { Authorization: "Bearer " + localStorage.getItem("token") };
    setDash(await (await fetch(`${API}/api/dashboard`, { headers: h })).json());
    setReps(await (await fetch(`${API}/api/reps`, { headers: h })).json().catch(() => []));
    setLeader(await (await fetch(`${API}/api/leaderboard`, { headers: h })).json().catch(() => []));
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
          <h1 style={styles.logo}>🥊 TNG CRM</h1>
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
      <aside style={styles.sidebar}>
  <h2>🥊 TNG CRM</h2>
  {["Dashboard", "Members", "Sales", "Sales Reps", "QR Referrals", "Clover", "Reports"].map((item) => (
    <button
      key={item}
      onClick={() => setPage(item)}
      style={{
        ...styles.navBtn,
        background: page === item ? "#d71920" : "transparent",
      }}
    >
      {item}
    </button>
  ))}
</aside>

      <main style={styles.main}>
        <header style={styles.header}>
          <div>
            <h1>Dashboard</h1>
            <p>TNG Boxing sales and commission command center</p>
          </div>
          <div>
            <button style={styles.secondaryBtn} onClick={load}>Refresh</button>
            <button style={styles.primaryBtnSmall} onClick={addRep}>Add Rep</button>
            <button style={styles.logoutBtn} onClick={() => { localStorage.clear(); setToken(""); }}>Logout</button>
          </div>
        </header>

        {msg && <p style={styles.notice}>{msg}</p>}

        {dash && (
          <section style={styles.grid4}>
            <Card title="Sales This Month" value={dash.sales_this_month} />
            <Card title="Revenue This Month" value={`$${Number(dash.revenue_this_month || 0).toFixed(2)}`} />
            <Card title="Commission Rate" value={`${Number((dash.commission_rate || 0) * 100).toFixed(0)}%`} />
            <Card title="Commission Earned" value={`$${Number(dash.commission_earned || 0).toFixed(2)}`} />
          </section>
        )}

        <section style={styles.panel}>
          <h2>Sales Reps</h2>
          <div style={styles.repGrid}>
            {Array.isArray(reps) && reps.map((r) => (
              <div key={r.id} style={styles.repCard}>
                <h3>{r.name}</h3>
                <p>{r.email}</p>
                <p><b>Referral:</b> /join/{r.slug}</p>
                <p><b>Clover:</b> {r.clover_link ? "Connected" : "Not Added"}</p>
              </div>
            ))}
          </div>
        </section>

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

  loginPage: {
    minHeight: "100vh",
    background: "#0b0b0f",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "Arial",
  },
  loginCard: {
    background: "white",
    padding: 32,
    borderRadius: 18,
    width: 380,
    boxShadow: "0 20px 50px rgba(0,0,0,.3)",
  },
  logo: { marginBottom: 4 },
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

createRoot(document.getElementById("root")).render(<App />);