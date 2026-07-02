import React, { useEffect, useState } from "react";
import {
  Box, Grid, Card, CardContent, Typography, Button,
  LinearProgress, Alert, List, ListItem, ListItemText
} from "@mui/material";
import { API, authHeaders } from "../services/api";
import StatCard from "../components/StatCard.jsx";

export default function SalesRepDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const res = await fetch(`${API}/api/my-dashboard`, {
        headers: authHeaders(),
      });

      if (!res.ok) throw new Error("Could not load sales rep dashboard");

      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message || "Something went wrong");
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return <Typography>Loading...</Typography>;

  const rate = Number(data.commission_rate || 0);
  const sales = Number(data.sales_this_month || 0);
  const progress = sales >= 20 ? 100 : sales >= 10 ? (sales / 20) * 100 : (sales / 10) * 100;

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 1 }}>
        Welcome, {data.rep_name}
      </Typography>

      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Track your sales, commission, QR referral link, and recent memberships.
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <StatCard title="Sales This Month" value={sales} />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard title="Revenue" value={`$${Number(data.revenue || 0).toFixed(2)}`} />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard title="Commission Rate" value={`${(rate * 100).toFixed(0)}%`} />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatCard title="Commission Earned" value={`$${Number(data.commission_earned || 0).toFixed(2)}`} />
        </Grid>
      </Grid>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="bold">
            Commission Progress
          </Typography>
          <Typography sx={{ mb: 1 }}>{data.next_tier}</Typography>
          <LinearProgress
            variant="determinate"
            value={progress}
            color="error"
            sx={{ height: 12, borderRadius: 10 }}
          />
        </CardContent>
      </Card>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="bold">
            My Referral Link
          </Typography>
          <Typography sx={{ mb: 2 }}>{data.referral_url || "No referral link yet"}</Typography>
          <Button
            variant="contained"
            color="error"
            onClick={() => navigator.clipboard.writeText(data.referral_url || "")}
          >
            Copy Referral Link
          </Button>
        </CardContent>
      </Card>

      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="bold">
            Recent Sales
          </Typography>

          <List>
            {(data.recent_sales || []).map((sale, index) => (
              <ListItem key={index} divider>
                <ListItemText
                  primary={`${sale.member} — ${sale.membership}`}
                  secondary={`$${Number(sale.amount || 0).toFixed(2)} • ${
                    sale.date ? new Date(sale.date).toLocaleDateString() : ""
                  }`}
                />
              </ListItem>
            ))}

            {(data.recent_sales || []).length === 0 && (
              <Typography color="text.secondary">No recent sales yet.</Typography>
            )}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
}