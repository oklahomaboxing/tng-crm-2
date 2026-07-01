import React from "react";
import { Grid, Card, CardContent, Typography, Button, Box } from "@mui/material";

export default function Dashboard({ dash, leader, load }) {
  return (
    <Box>
      <Button variant="contained" color="error" onClick={load} sx={{ mb: 3 }}>
        Refresh Dashboard
      </Button>

      <Grid container spacing={2}>
        <Stat title="Sales This Month" value={dash?.sales_this_month || 0} />
        <Stat title="Revenue This Month" value={`$${Number(dash?.revenue_this_month || 0).toFixed(2)}`} />
        <Stat title="Commission Rate" value={`${Number((dash?.commission_rate || 0) * 100).toFixed(0)}%`} />
        <Stat title="Commission Earned" value={`$${Number(dash?.commission_earned || 0).toFixed(2)}`} />
      </Grid>

      <Card sx={{ mt: 3, borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="bold">Leaderboard</Typography>
          {Array.isArray(leader) && leader.map((r, i) => (
            <Box key={r.rep_id} sx={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", py: 1, borderBottom: "1px solid #eee" }}>
              <b>#{i + 1} {r.name}</b>
              <span>{r.sales} sales</span>
              <span>${Number(r.revenue || 0).toFixed(2)}</span>
              <span>{Number((r.rate || 0) * 100).toFixed(0)}%</span>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}

function Stat({ title, value }) {
  return (
    <Grid item xs={12} sm={6} md={3}>
      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Typography color="text.secondary">{title}</Typography>
          <Typography variant="h4" fontWeight="bold">{value}</Typography>
        </CardContent>
      </Card>
    </Grid>
  );
}