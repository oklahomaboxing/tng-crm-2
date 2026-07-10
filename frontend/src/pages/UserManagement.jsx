import React, { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function UserManagement() {
  const [role, setRole] = useState("staff");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [referralSlug, setReferralSlug] = useState("");
  const [cloverLink, setCloverLink] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function createUser() {
    setMessage("");
    setError("");

    if (!name.trim() || !email.trim() || !password) {
      setError("Name, email, and password are required.");
      return;
    }

    if (role === "rep" && !referralSlug.trim()) {
      setError("Referral slug is required for sales reps.");
      return;
    }

    setSaving(true);

    try {
      const endpoint = role === "rep" ? "/api/reps" : "/api/staff";

      const body =
        role === "rep"
          ? {
              name: name.trim(),
              email: email.trim().toLowerCase(),
              password,
              phone: "",
              referral_slug: referralSlug.trim().toLowerCase(),
              clover_link: cloverLink.trim(),
            }
          : {
              name: name.trim(),
              email: email.trim().toLowerCase(),
              password,
            };

      const response = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not create user.");
      }

      setMessage(
        role === "rep"
          ? `Sales rep ${data.name || name} created successfully.`
          : `Staff member ${data.name || name} created successfully.`
      );

      setName("");
      setEmail("");
      setPassword("");
      setReferralSlug("");
      setCloverLink("");
    } catch (err) {
      setError(err.message || "Could not create user.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 3 }}>
        User Management
      </Typography>

      <Card sx={{ borderRadius: 3, maxWidth: 700 }}>
        <CardContent>
          <Stack spacing={2}>
            {message && <Alert severity="success">{message}</Alert>}
            {error && <Alert severity="error">{error}</Alert>}

            <TextField
              select
              label="User Role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              fullWidth
            >
              <MenuItem value="staff">Staff</MenuItem>
              <MenuItem value="rep">Sales Rep</MenuItem>
            </TextField>

            <TextField
              label="Full Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              fullWidth
            />

            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              fullWidth
            />

            <TextField
              label="Temporary Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              fullWidth
            />

            {role === "rep" && (
              <>
                <TextField
                  label="Referral Slug"
                  helperText="Example: john-smith"
                  value={referralSlug}
                  onChange={(event) => setReferralSlug(event.target.value)}
                  fullWidth
                />

                <TextField
                  label="Clover Link"
                  value={cloverLink}
                  onChange={(event) => setCloverLink(event.target.value)}
                  fullWidth
                />
              </>
            )}

            <Button
              variant="contained"
              color="error"
              onClick={createUser}
              disabled={saving}
              sx={{ py: 1.5 }}
            >
              {saving ? "Creating..." : "Create User"}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}