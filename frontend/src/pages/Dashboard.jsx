import React from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

export default function Dashboard({ dash, leader, load }) {
  const revenueThisMonth =
    "$" + Number(dash?.revenue_this_month || 0).toFixed(2);

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h4" fontWeight="bold">
            TNG Command Center
          </Typography>

          <Typography color="text.secondary">
            Gym, sales, attendance, and member overview
          </Typography>
        </Box>

        <Button
          variant="contained"
          color="error"
          onClick={load}
        >
          Refresh Dashboard
        </Button>
      </Box>

      <Grid container spacing={2}>
        <Stat
          title="Total Members"
          value={dash?.total_members || 0}
        />

        <Stat
          title="Active Members"
          value={dash?.active_members || 0}
        />

        <Stat
          title="Today's Check-ins"
          value={dash?.today_checkins || 0}
        />

        <Stat
          title="Leads"
          value={dash?.total_leads || 0}
        />

        <Stat
          title="Sales This Month"
          value={dash?.sales_this_month || 0}
        />

        <Stat
          title="Revenue This Month"
          value={revenueThisMonth}
        />
      </Grid>

      <Grid
        container
        spacing={3}
        sx={{ mt: 1 }}
      >
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Recent Check-ins
              </Typography>

              <Stack spacing={1} sx={{ mt: 2 }}>
                {dash?.recent_checkins?.length ? (
                  dash.recent_checkins.map((checkin, index) => (
                    <Box
                      key={
                        String(checkin.member || "member") +
                        "-" +
                        String(checkin.time || "time") +
                        "-" +
                        index
                      }
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        background: "#f7f7f7",
                      }}
                    >
                      <Typography fontWeight="bold">
                        {checkin.member}
                      </Typography>

                      <Typography color="text.secondary">
                        {checkin.time
                          ? new Date(checkin.time).toLocaleString()
                          : ""}
                        {" - "}
                        {checkin.method || "barcode"}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography color="text.secondary">
                    No check-ins yet.
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Sales Leaderboard
              </Typography>

              {Array.isArray(leader) && leader.length > 0 ? (
                leader.map((rep, index) => (
                  <Box
                    key={
                      rep.rep_id ||
                      String(rep.name || "rep") + "-" + index
                    }
                    sx={{
                      display: "grid",
                      gridTemplateColumns: {
                        xs: "1fr",
                        sm: "2fr 1fr 1fr 1fr",
                      },
                      gap: 1,
                      py: 1.25,
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    <Typography fontWeight="bold">
                      #{index + 1} {rep.name}
                    </Typography>

                    <Typography>
                      {rep.sales || 0} sales
                    </Typography>

                    <Typography>
                      {"$" + Number(rep.revenue || 0).toFixed(2)}
                    </Typography>

                    <Typography>
                      {Number((rep.rate || 0) * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                ))
              ) : (
                <Typography
                  color="text.secondary"
                  sx={{ mt: 2 }}
                >
                  No sales leaderboard data available.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

function Stat({ title, value }) {
  return (
    <Grid size={{ xs: 12, sm: 6, md: 4 }}>
      <Card
        sx={{
          borderRadius: 3,
          height: "100%",
        }}
      >
        <CardContent>
          <Typography color="text.secondary">
            {title}
          </Typography>

          <Typography variant="h4" fontWeight="bold">
            {value}
          </Typography>
        </CardContent>
      </Card>
    </Grid>
  );
}
