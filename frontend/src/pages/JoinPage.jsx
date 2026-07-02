import React, { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Typography, TextField, Button,
  Grid, Alert, MenuItem
} from "@mui/material";
import { API } from "../services/api";

export default function JoinPage() {
  const slug = window.location.pathname.split("/join/")[1] || "";
  const [data, setData] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
  });
  const [message, setMessage] = useState("");

  async function loadJoinData() {
    const res = await fetch(`${API}/api/join/${slug}`);
    const json = await res.json();
    setData(json);

    if (json.products?.length) {
      setSelectedProduct(json.products[0].id);
    }
  }

  useEffect(() => {
    loadJoinData();
  }, []);

  function update(field, value) {
    setForm((old) => ({ ...old, [field]: value }));
  }

  async function continueToPayment() {
    try {
      const leadResponse = await fetch(`${API}/api/leads`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          phone: form.phone,
          product_id: selectedProduct,
          referral_slug: slug,
        }),
      });

      const lead = await leadResponse.json();

      if (!leadResponse.ok) {
        throw new Error(lead.detail || "Could not create lead");
      }

      const checkoutResponse = await fetch(
        `${API}/api/clover/create-checkout/${lead.id}`,
        { method: "POST" }
      );

      const checkout = await checkoutResponse.json();

      if (!checkoutResponse.ok) {
        throw new Error(checkout.detail || "Could not create Clover checkout");
      }

      window.location.href = checkout.checkout_url;
    } catch (err) {
      setMessage(err.message);
    }
  }

  if (!data) return <Box sx={{ p: 4 }}>Loading...</Box>;

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#0b0b0f", p: 3 }}>
      <Card sx={{ maxWidth: 720, mx: "auto", borderRadius: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h3" fontWeight="bold">
            🥊 Join TNG Boxing
          </Typography>

          <Typography color="text.secondary" sx={{ mb: 3 }}>
            Referred by {data.rep_name}
          </Typography>

          {message && <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert>}

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="First Name" value={form.first_name} onChange={(e) => update("first_name", e.target.value)} />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Last Name" value={form.last_name} onChange={(e) => update("last_name", e.target.value)} />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Phone" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
            </Grid>

            <Grid item xs={12}>
              <TextField select fullWidth label="Choose Membership" value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}>
                {(data.products || []).map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name} — ${Number(p.price || 0).toFixed(2)}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <Button fullWidth variant="contained" color="error" size="large" onClick={continueToPayment}>
                Continue to Payment
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}