import React from "react";

export default function Sidebar({ page, setPage, styles }) {
  const items = ["Dashboard", "Members", "Sales", "Sales Reps", "QR Referrals", "Clover", "Reports"];

  return (
    <aside style={styles.sidebar}>
      <h2>🥊 TNG CRM</h2>
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