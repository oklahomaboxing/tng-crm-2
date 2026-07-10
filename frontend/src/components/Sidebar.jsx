import React from "react";

export default function Sidebar({ role = "admin", page, setPage, styles }) {
  const menus = {
    admin: [
      "Dashboard",
      "Members",
      "Products",
      "Front Desk",
      "Sales",
      "Leads",
      "Sales Reps",
      "QR Referrals",
      "Clover",
      "Duplicate Review",
      "AI Trainer",
      "Reports",
    ],

    staff: [
      "Front Desk",
      "Members",
      "Sales",
      "Leads",
      "QR Referrals",
      "AI Trainer",
    ],

    rep: [
      "Sales",
      "Leads",
      "QR Referrals",
    ],
  };

  const items = menus[role] || menus.rep;

  return (
    <aside style={styles.sidebar}>
      <h2>🥊 TNG OS</h2>

      <div
        style={{
          color: "#999",
          fontSize: 12,
          marginBottom: 20,
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        {role}
      </div>

      {items.map((item) => (
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
  );
}