import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  CssBaseline,
  Link,
  Stack,
  TextField,
  ThemeProvider,
  Typography,
  createTheme,
} from "@mui/material";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import SecurityCenter from "./pages/SecurityCenter";
import AppShell from "./layout/AppShell.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import AIDisplay from "./pages/AIDisplay.jsx";
import Members from "./pages/Members.jsx";
import Sales from "./pages/Sales.jsx";
import SalesRepDashboard from "./pages/SalesRepDashboard.jsx";
import JoinPage from "./pages/JoinPage.jsx";
import Leads from "./pages/Leads.jsx";
import FrontDesk from "./pages/FrontDesk.jsx";
import Products from "./pages/Products.jsx";
import DuplicateReview from "./pages/DuplicateReview.jsx";
import AITrainer from "./pages/AITrainer.jsx";
import UserManagement from "./pages/UserManagement.jsx";
import QRReferrals from "./pages/QRReferrals.jsx";
import MarketingCenter from "./pages/MarketingCenter.jsx";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#d71920" },
    error: { main: "#d71920" },
    background: {
      default: "#f5f6f8",
      paper: "#ffffff",
    },
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
    button: { textTransform: "none", fontWeight: 800 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 10, minHeight: 42 },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #e8e9ed",
          boxShadow: "0 8px 30px rgba(16,24,40,.05)",
        },
      },
    },
    MuiTextField: {
      defaultProps: { size: "small" },
    },
  },
});

function landingPageForRole(role) {
  if (role === "rep") return "Sales";
  if (role === "staff") return "Front Desk";
  return "Dashboard";
}

function PaymentMessage({ status }) {
  const content = {
    success: {
      title: "Payment Successful",
      text: "Welcome to TNG Boxing. Your membership payment was processed successfully.",
      severity: "success",
    },
    cancelled: {
      title: "Payment Cancelled",
      text: "Your checkout was cancelled. You can restart your signup anytime.",
      severity: "warning",
    },
    failed: {
      title: "Payment Failed",
      text: "Something went wrong with the payment. Please try again or contact TNG Boxing.",
      severity: "error",
    },
  }[status];
  if (!content) return null;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#09090b",
        display: "grid",
        placeItems: "center",
        p: 2,
      }}
    >
      <Card sx={{ width: "100%", maxWidth: 520, borderRadius: 4 }}>
        <CardContent sx={{ p: { xs: 3, sm: 5 }, textAlign: "center" }}>
          <SportsMmaRoundedIcon color="error" sx={{ fontSize: 58, mb: 1 }} />
          <Typography variant="h4" fontWeight={900} gutterBottom>
            {content.title}
          </Typography>
          <Alert severity={content.severity} sx={{ my: 3, textAlign: "left" }}>
            {content.text}
          </Alert>
          <Button variant="contained" fullWidth onClick={() => (window.location.href = "/")}>
            Go to TNG OS
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}

function App() {
  const params = new URLSearchParams(window.location.search);
  const paymentStatus = params.get("payment");
  const passwordResetToken = params.get("token");
  const isResetPasswordPage =
    window.location.pathname === "/reset-password" &&
    Boolean(passwordResetToken);
  const [authView, setAuthView] = useState("login");
  const [resetEmail, setResetEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [role, setRole] = useState(localStorage.getItem("role") || "");
  const [userName, setUserName] = useState(localStorage.getItem("name") || "");
  const [page, setPage] = useState(() =>
    landingPageForRole(localStorage.getItem("role") || "")
  );
  const [dash, setDash] = useState(null);
  const [reps, setReps] = useState([]);
  const [leader, setLeader] = useState([]);
  const [msg, setMsg] = useState("");
  const [qrCodes, setQrCodes] = useState({});
  const [loginLoading, setLoginLoading] = useState(false);

  async function login() {
    setLoginLoading(true);
    setMsg("");

    try {
      const response = await fetch(`${API}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok || !data.token) {
        setMsg(data.detail || "Login failed");
        return;
      }

      const loggedInRole = data.user?.role || "rep";
      const loggedInName = data.user?.name || "";

      localStorage.setItem("token", data.token);
      localStorage.setItem("role", loggedInRole);
      localStorage.setItem("name", loggedInName);

      setToken(data.token);
      setRole(loggedInRole);
      setUserName(loggedInName);
      setPage(landingPageForRole(loggedInRole));
      setMsg("");
    } catch (error) {
      setMsg(error.message || "Login failed");
    } finally {
      setLoginLoading(false);
    }
  }
async function requestPasswordReset() {
  setAuthLoading(true);
  setAuthMessage("");
  setAuthError("");

  try {
    const response = await fetch(`${API}/api/auth/forgot-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: resetEmail.trim(),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      setAuthError(
        data.detail || "Unable to send the password reset email."
      );
      return;
    }

    setAuthMessage(
      data.message ||
        "If an account exists for that email, a password reset link has been sent."
    );
  } catch (error) {
    setAuthError(
      error.message || "Unable to send the password reset email."
    );
  } finally {
    setAuthLoading(false);
  }
}

async function submitPasswordReset() {
  setAuthLoading(true);
  setAuthMessage("");
  setAuthError("");

  if (newPassword !== confirmPassword) {
    setAuthError("Passwords do not match.");
    setAuthLoading(false);
    return;
  }

  try {
    const response = await fetch(`${API}/api/auth/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: resetToken,
        password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      setAuthError(
        data.detail || "Unable to reset your password."
      );
      return;
    }

    setAuthMessage(
      data.message ||
        "Your password was reset successfully."
    );

    setNewPassword("");
    setConfirmPassword("");

    window.history.replaceState({}, "", "/");

    setTimeout(() => {
      setAuthView("login");
      setAuthMessage("");
      setEmail(resetEmail);
    }, 1500);
  } catch (error) {
    setAuthError(
      error.message || "Unable to reset your password."
    );
  } finally {
    setAuthLoading(false);
  }
}

  async function load() {
    const headers = { Authorization: `Bearer ${localStorage.getItem("token")}` };

    try {
      if (role !== "rep") {
        const dashboardResponse = await fetch(`${API}/api/dashboard`, { headers });
        if (dashboardResponse.ok) setDash(await dashboardResponse.json());
      }

      if (role === "admin") {
        const [repsResponse, leaderResponse] = await Promise.all([
          fetch(`${API}/api/reps`, { headers }),
          fetch(`${API}/api/leaderboard`, { headers }),
        ]);

        if (repsResponse.ok) setReps(await repsResponse.json());
        if (leaderResponse.ok) setLeader(await leaderResponse.json());
      }
    } catch (error) {
      console.error("Load failed", error);
    }
  }

  async function loadQr(repId) {
    const response = await fetch(`${API}/api/reps/${repId}/qr`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    const data = await response.json();

    if (!response.ok) {
      setMsg(data.detail || "Could not load QR code");
      return;
    }

    setQrCodes((old) => ({ ...old, [repId]: data }));
  }

  async function syncTngOS() {
    if (role !== "admin") return;

    const response = await fetch(`${API}/api/clover/sync-all`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    const data = await response.json();

    if (!response.ok) {
      setMsg(data.detail || "TNG OS sync failed");
      return;
    }

setMsg(
  `TNG OS is up to date. ${data.sales?.synced || 0} sales imported and ${
    data.customers?.synced || 0
  } customers added.`
);
  }

  function logout() {
    localStorage.clear();

    setEmail("");
    setPassword("");
    setToken("");
    setRole("");
    setUserName("");
    setPage("Dashboard");
    setDash(null);
    setReps([]);
    setLeader([]);
    setQrCodes({});
    setMsg("");
  }

  useEffect(() => {
    if (!token) return;

    if (role === "admin") {
      syncTngOS();
    } else {
      load();
    }
  }, [token, role]);

  useEffect(() => {
    if (isResetPasswordPage) {
      setResetToken(passwordResetToken);
      setAuthView("reset");
    }
  }, [isResetPasswordPage, passwordResetToken]);

  if (paymentStatus) return <PaymentMessage status={paymentStatus} />;
if (params.has("join")) return <JoinPage />;
if (window.location.pathname === "/register") return <JoinPage />;
  if (!token) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "#09090b",
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1.1fr .9fr" },
        }}
      >
        <Box
          sx={{
            display: { xs: "none", md: "flex" },
            flexDirection: "column",
            justifyContent: "space-between",
            p: 6,
            color: "white",
            background: "radial-gradient(circle at 30% 20%, #471015 0, #09090b 48%)",
          }}
        >
          <Typography variant="h4" fontWeight={900}>
            TNG <Box component="span" sx={{ color: "#e31b23" }}>OS</Box>
          </Typography>
          <Box>
            <Typography variant="h2" fontWeight={950} sx={{ maxWidth: 650, lineHeight: 1 }}>
              Run the gym. Build champions.
            </Typography>
            <Typography sx={{ mt: 3, color: "rgba(255,255,255,.7)", maxWidth: 580 }}>
              Members, sales, attendance, staff, Clover, and AI training in one operating system.
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,.45)" }}>
            Earned Not Given
          </Typography>
        </Box>

        <Box sx={{ display: "grid", placeItems: "center", p: 2 }}>
          <Card sx={{ width: "100%", maxWidth: 440, borderRadius: 4 }}>
            <CardContent sx={{ p: { xs: 3, sm: 5 } }}>
{authView === "login" && (
  <>
    <Typography variant="h4" fontWeight={900}>
      Sign in
    </Typography>

    <Typography color="text.secondary" sx={{ mb: 3 }}>
      Access TNG Boxing operations.
    </Typography>

    <form
      autoComplete="on"
      onSubmit={(event) => {
        event.preventDefault();
        login();
      }}
    >
      <Stack spacing={2}>
        {msg && <Alert severity="error">{msg}</Alert>}

        {authMessage && (
          <Alert severity="success">{authMessage}</Alert>
        )}

        <TextField
          id="tng-login-email"
          name="username"
          label="Email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="username"
          fullWidth
          required
          inputProps={{
            spellCheck: false,
            autoCapitalize: "none",
          }}
        />

        <TextField
          id="tng-login-password"
          name="password"
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          fullWidth
          required
        />

        <Button
          type="submit"
          variant="contained"
          size="large"
          disabled={loginLoading}
          fullWidth
        >
          {loginLoading ? (
            <CircularProgress size={24} color="inherit" />
          ) : (
            "Login"
          )}
        </Button>

        <Button
          type="button"
          variant="text"
          onClick={() => {
            setResetEmail(email);
            setAuthView("forgot");
            setMsg("");
            setAuthMessage("");
            setAuthError("");
          }}
        >
          Forgot your password?
        </Button>
      </Stack>
    </form>
  </>
)}

{authView === "forgot" && (
  <>
    <Typography variant="h4" fontWeight={900}>
      Reset password
    </Typography>

    <Typography color="text.secondary" sx={{ mb: 3 }}>
      Enter your account email and we will send you a secure
      password reset link.
    </Typography>

    <form
      onSubmit={(event) => {
        event.preventDefault();
        requestPasswordReset();
      }}
    >
      <Stack spacing={2}>
        {authError && (
          <Alert severity="error">{authError}</Alert>
        )}

        {authMessage && (
          <Alert severity="success">{authMessage}</Alert>
        )}

        <TextField
          label="Email"
          type="email"
          value={resetEmail}
          onChange={(event) =>
            setResetEmail(event.target.value)
          }
          autoComplete="email"
          fullWidth
          required
        />

        <Button
          type="submit"
          variant="contained"
          size="large"
          disabled={authLoading}
          fullWidth
        >
          {authLoading ? (
            <CircularProgress size={24} color="inherit" />
          ) : (
            "Send Reset Link"
          )}
        </Button>

        <Button
          type="button"
          variant="text"
          onClick={() => {
            setAuthView("login");
            setAuthMessage("");
            setAuthError("");
          }}
        >
          Back to login
        </Button>
      </Stack>
    </form>
  </>
)}

{authView === "reset" && (
  <>
    <Typography variant="h4" fontWeight={900}>
      Choose new password
    </Typography>

    <Typography color="text.secondary" sx={{ mb: 3 }}>
      Use at least 12 characters with uppercase, lowercase,
      a number, and a symbol.
    </Typography>

    <form
      onSubmit={(event) => {
        event.preventDefault();
        submitPasswordReset();
      }}
    >
      <Stack spacing={2}>
        {authError && (
          <Alert severity="error">{authError}</Alert>
        )}

        {authMessage && (
          <Alert severity="success">{authMessage}</Alert>
        )}

        <TextField
          label="New Password"
          type="password"
          value={newPassword}
          onChange={(event) =>
            setNewPassword(event.target.value)
          }
          autoComplete="new-password"
          fullWidth
          required
        />

        <TextField
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={(event) =>
            setConfirmPassword(event.target.value)
          }
          autoComplete="new-password"
          fullWidth
          required
        />

        <Button
          type="submit"
          variant="contained"
          size="large"
          disabled={authLoading}
          fullWidth
        >
          {authLoading ? (
            <CircularProgress size={24} color="inherit" />
          ) : (
            "Reset Password"
          )}
        </Button>
      </Stack>
    </form>
  </>
)}
            </CardContent>
          </Card>
        </Box>
      </Box>
    );
  }

  return (
    <AppShell
      role={role}
      page={page}
      setPage={setPage}
      userName={userName}
      onRefresh={load}
      onSync={syncTngOS}
      onLogout={logout}
    >
      {msg && (
        <Alert severity="info" onClose={() => setMsg("")} sx={{ mb: 2 }}>
          {msg}
        </Alert>
      )}

      {page === "Dashboard" && role !== "rep" && (
        <Dashboard dash={dash} leader={leader} load={load} />
      )}
      {page === "Members" && role !== "rep" && <Members />}
      {page === "Front Desk" && role !== "rep" && <FrontDesk />}
      {page === "Sales" && <Sales />}
      {page === "Products" && role === "admin" && <Products />}
      {page === "Duplicate Review" && role === "admin" && <DuplicateReview />}
      {page === "Leads" && <Leads />}
      {page === "Sales Reps" && role === "admin" && <SalesRepDashboard />}
      {page === "AI Trainer" && role !== "rep" && <AITrainer />}
      {page === "User Management" && role === "admin" && <UserManagement />}
      {page === "Security Center" && role === "admin" && <SecurityCenter />}
      {page === "QR Referrals" && <QRReferrals />}

      {page === "Marketing Center" && role === "admin" && (
        <MarketingCenter />
      )}

      {page === "Clover" && role === "admin" && (
        <Card>
          <CardContent sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="h5" fontWeight={900}>Clover Integration</Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>
              Payment synchronization and webhook configuration.
            </Typography>
            <Typography component="code" sx={{ display: "block", p: 2, bgcolor: "#f4f4f5", borderRadius: 2, overflowWrap: "anywhere" }}>
              {API}/api/clover/webhook
            </Typography>
          </CardContent>
        </Card>
      )}

      {page === "Reports" && role === "admin" && (
        <Card>
          <CardContent sx={{ p: { xs: 2, md: 3 } }}>
            <Typography variant="h5" fontWeight={900} sx={{ mb: 2 }}>Sales Leaderboard</Typography>
            <Stack spacing={1}>
              {Array.isArray(leader) && leader.map((item, index) => (
                <Box
                  key={item.rep_id}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr auto", md: "2fr 1fr 1fr 1fr" },
                    gap: 1,
                    p: 1.5,
                    borderRadius: 2,
                    bgcolor: index === 0 ? "#fff4f4" : "#fafafa",
                  }}
                >
                  <Typography fontWeight={850}>#{index + 1} {item.name}</Typography>
                  <Typography>{item.sales} sales</Typography>
                  <Typography sx={{ display: { xs: "none", md: "block" } }}>${Number(item.revenue || 0).toFixed(2)}</Typography>
                  <Typography sx={{ display: { xs: "none", md: "block" } }}>{Number((item.rate || 0) * 100).toFixed(0)}%</Typography>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}
    </AppShell>
  );
}

const host = window.location.hostname.toLowerCase();
const root = createRoot(document.getElementById("root"));

root.render(
  <ThemeProvider theme={theme}>
    <CssBaseline />
    {host === "display.tngboxinggym.com" ? <AIDisplay /> : <App />}
  </ThemeProvider>
);


