import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, CircularProgress,
  Stack, TextField, Typography
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function MemberActivate() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token") || "", []);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function activate() {
    setError("");
    setMessage("");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (password !== confirm) return setError("Passwords do not match.");
    if (!token) return setError("Activation token is missing.");

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/member/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Unable to activate account");
      setMessage(data.message || "Account activated.");
    } catch (e) {
      setError(e.message || "Unable to activate account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#09090b", display: "grid", placeItems: "center", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 480, borderRadius: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="overline" color="error" fontWeight={900}>TNG BOXING</Typography>
          <Typography variant="h4" fontWeight={900} sx={{ mb: 1 }}>Activate Member Account</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            Create your password to access your membership and InBody information.
          </Typography>
          <Stack spacing={2}>
            {error && <Alert severity="error">{error}</Alert>}
            {message && <Alert severity="success">{message}</Alert>}
            <TextField label="Create password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
            <TextField label="Confirm password" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} />
            <Button variant="contained" size="large" onClick={activate} disabled={loading || Boolean(message)}>
              {loading ? <CircularProgress size={22} /> : "Activate Account"}
            </Button>
            {message && <Button href="/">Go to Login</Button>}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

