import React from "react";
import { Grid, Card, CardContent, Typography, Button, Box, Stack } from "@mui/material";

export default function Dashboard({ dash, leader, load }) {
  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            TNG Command Center
          </Typography>
          <Typography color="text.secondary">
            Gym, sales, attendance, and member overview
          </Typography>
        </Box>

        <Button variant="contained" color="error" onClick={load}>
          Refresh Dashboard
        </Button>
      </Box>

      <Grid container spacing={2}>
        <Stat title="Total Members" value={dash?.total_members || 0} />
        <Stat title="Active Members" value={dash?.active_members || 0} />
        <Stat title="Today's Check-ins" value={dash?.today_checkins || 0} />
        <Stat title="Leads" value={dash?.total_leads || 0} />
        <Stat title="Sales This Month" value={dash?.sales_this_month || 0} />
        <Stat title="Revenue This Month" value={`$${Number(dash?.revenue_this_month || 0).toFixed(2)}`} />
      </Grid>

      <Grid container spacing={3} sx={{ mt: 1 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Recent Check-ins
              </Typography>

              <Stack spacing={1} sx={{ mt: 2 }}>
                {dash?.recent_checkins?.length ? (
                  dash.recent_checkins.map((c, i) => (
                    <Box
                      key={i}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        background: "#f7f7f7",
                      }}
                    >
                      <Typography fontWeight="bold">🥊 {c.member}</Typography>
                      <Typography color="text.secondary">
                        {c.time ? new Date(c.time).toLocaleString() : ""} • {c.method || "barcode"}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography color="text.secondary">No check-ins yet.</Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Sales Leaderboard
              </Typography>

              {Array.isArray(leader) && leader.map((r, i) => (
                <Box
                  key={r.rep_id}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr",
                    py: 1,
                    borderBottom: "1px solid #eee",
                  }}
                >
                  <b>#{i + 1} {r.name}</b>
                  <span>{r.sales} sales</span>
                  <span>${Number(r.revenue || 0).toFixed(2)}</span>
                  <span>{Number((r.rate || 0) * 100).toFixed(0)}%</span>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

function Stat({ title, value }) {
  return (
    <Grid item xs={12} sm={6} md={4}>
      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Typography color="text.secondary">{title}</Typography>
          <Typography variant="h4" fontWeight="bold">{value}</Typography>
        </CardContent>
      </Card>
    </Grid>
  );
}