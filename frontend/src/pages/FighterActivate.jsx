import { useMemo, useState } from "react";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export default function FighterActivate() {
  const token = useMemo(
    () => new URLSearchParams(window.location.search).get("token") || "",
    []
  );

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);
  const [success, setSuccess] = useState(false);

  async function activate(e) {
    e.preventDefault();

    if (!token) {
      setMessage("Activation token is missing.");
      return;
    }

    if (password.length < 8) {
      setMessage("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    try {
      setWorking(true);
      setMessage("");

      const response = await fetch(
        `${API}/api/fighter/activate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            password,
            confirm_password: confirmPassword,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not activate fighter account"
        );
      }

      setSuccess(true);
      setMessage(data.message || "Fighter account activated.");
    } catch (err) {
      setMessage(err.message || "Activation failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#111",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 460,
          background: "#fff",
          borderRadius: 14,
          padding: 28,
        }}
      >
        <div
          style={{
            fontSize: 14,
            fontWeight: 900,
            color: "#d71920",
            marginBottom: 4,
          }}
        >
          TNG BOXING
        </div>

        <h1 style={{ marginTop: 0 }}>
          Fighter Portal Activation
        </h1>

        {!success ? (
          <form onSubmit={activate}>
            <p>
              Create your password to activate your TNG Fighter Portal.
            </p>

            <label
              style={{
                display: "block",
                fontWeight: 700,
                marginBottom: 5,
              }}
            >
              Password
            </label>

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: 12,
                marginBottom: 16,
              }}
            />

            <label
              style={{
                display: "block",
                fontWeight: 700,
                marginBottom: 5,
              }}
            >
              Confirm Password
            </label>

            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: 12,
                marginBottom: 18,
              }}
            />

            <button
              type="submit"
              disabled={working}
              style={{
                width: "100%",
                padding: 13,
                background: "#d71920",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              {working
                ? "Activating..."
                : "Activate Fighter Portal"}
            </button>
          </form>
        ) : (
          <div>
            <h2>Account Activated</h2>

            <p>
              Your Fighter Portal login is ready.
            </p>

            <button
              type="button"
              onClick={() => {
                window.location.href = "/";
              }}
              style={{
                width: "100%",
                padding: 13,
                background: "#111",
                color: "#fff",
                border: 0,
                borderRadius: 8,
                fontWeight: 900,
              }}
            >
              Sign In to TNGOS
            </button>
          </div>
        )}

        {message && (
          <div
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 8,
              background: success ? "#e8f5e9" : "#fff3f3",
            }}
          >
            {message}
          </div>
        )}

        <div
          style={{
            marginTop: 24,
            fontSize: 13,
            color: "#666",
          }}
        >
          TNG Boxing - Earned Not Given
        </div>
      </div>
    </div>
  );
}
