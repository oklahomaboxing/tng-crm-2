import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function QRReferrals() {
  const role = localStorage.getItem("role") || "rep";
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [myQr, setMyQr] = useState(null);
  const [reps, setReps] = useState([]);
  const [qrCodes, setQrCodes] = useState({});

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setLoading(true);
      setError("");

      if (role === "rep") {
        const response = await fetch(`${API}/api/reps/me/qr`, {
          headers: authHeaders(),
        });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Could not load your QR code.");
        }

        setMyQr(data);
        return;
      }

      const response = await fetch(`${API}/api/reps`, {
        headers: authHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load sales reps.");
      }

      setReps(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not load QR referrals.");
    } finally {
      setLoading(false);
    }
  }

  async function loadQr(repId) {
    try {
      setError("");

      const response = await fetch(`${API}/api/reps/${repId}/qr`, {
        headers: authHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not generate QR code.");
      }

      setQrCodes((current) => ({ ...current, [repId]: data }));
    } catch (err) {
      setError(err.message || "Could not generate QR code.");
    }
  }

  function downloadQr(data, filename) {
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${data.qr_png_base64}`;
    link.download = filename;
    link.click();
  }

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress color="error" />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 1 }}>
        {role === "rep" ? "My QR Code" : "QR Referrals"}
      </Typography>

      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {role === "rep"
          ? "Share this code or link. Leads and sales from it are assigned to your account."
          : "View and generate each sales rep's referral QR code."}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {role === "rep" && myQr && (
        <Card sx={{ maxWidth: 560, borderRadius: 4 }}>
          <CardContent sx={{ p: { xs: 2.5, sm: 4 }, textAlign: "center" }}>
            <Typography variant="h5" fontWeight="bold">
              {myQr.name}
            </Typography>

            <Typography color="text.secondary" sx={{ mb: 3 }}>
              Personal TNG referral code
            </Typography>

            <Box
              component="img"
              src={`data:image/png;base64,${myQr.qr_png_base64}`}
              alt="My referral QR code"
              sx={{
                width: "100%",
                maxWidth: 280,
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 3,
                p: 1,
                backgroundColor: "white",
              }}
            />

            <Typography
              sx={{
                mt: 3,
                wordBreak: "break-all",
                fontSize: { xs: 13, sm: 15 },
              }}
            >
              {myQr.url}
            </Typography>

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.5}
              justifyContent="center"
              sx={{ mt: 3 }}
            >
              <Button
                variant="contained"
                color="error"
                onClick={() => navigator.clipboard.writeText(myQr.url)}
              >
                Copy Referral Link
              </Button>

              <Button
                variant="outlined"
                onClick={() => downloadQr(myQr, "tng-my-referral-qr.png")}
              >
                Save QR Code
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}

      {role !== "rep" && (
        <Grid container spacing={2}>
          {reps.map((rep) => {
            const qr = qrCodes[rep.id];

            return (
              <Grid item xs={12} md={6} lg={4} key={rep.id}>
                <Card sx={{ height: "100%", borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight="bold">
                      {rep.name}
                    </Typography>

                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      /join/{rep.slug}
                    </Typography>

                    {!qr ? (
                      <Button
                        variant="contained"
                        color="error"
                        onClick={() => loadQr(rep.id)}
                      >
                        Show QR Code
                      </Button>
                    ) : (
                      <Stack spacing={2} alignItems="center">
                        <Box
                          component="img"
                          src={`data:image/png;base64,${qr.qr_png_base64}`}
                          alt={`${rep.name} QR code`}
                          sx={{ width: 220, maxWidth: "100%" }}
                        />

                        <Typography sx={{ wordBreak: "break-all", fontSize: 13 }}>
                          {qr.url}
                        </Typography>
                      </Stack>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
}
