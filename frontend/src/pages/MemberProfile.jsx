import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Grid,
  Divider,
  Stack,
} from "@mui/material";

export default function MemberProfile({ member, onBack }) {
  const [tab, setTab] = useState("Profile");
  if (!member) return null;

  const fullName = `${member.first_name || ""} ${member.last_name || ""}`.trim();
  const isActive = member.membership_status === "active" || member.status === "active";

  return (
    <Box>
      <Button variant="outlined" color="error" onClick={onBack} sx={{ mb: 2 }}>
        ← Back to Members
      </Button>

      <Card sx={{ borderRadius: 4, mb: 3, overflow: "hidden" }}>
        <Box sx={{ background: "#0b0b0f", color: "white", p: 3 }}>
          <Typography variant="h5" fontWeight="bold">
            👤 MEMBER PROFILE
          </Typography>
        </Box>

        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={3}>
              <Box
                sx={{
                  width: 180,
                  height: 180,
                  borderRadius: "50%",
                  background: "#111",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 60,
                  fontWeight: "bold",
                  border: "5px solid #d71920",
                }}
              >
                {fullName ? fullName[0].toUpperCase() : "?"}
              </Box>
            </Grid>

            <Grid item xs={12} md={5}>
              <Typography variant="h4" fontWeight="bold">
                {fullName || "Member"}
              </Typography>

              <Typography color="text.secondary" sx={{ mt: 1 }}>
                Member # {member.member_number || "-"}
              </Typography>

              <Typography sx={{ mt: 1 }}>
                {member.membership_type || "Clover Customer"}
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Chip
                  color={isActive ? "success" : "warning"}
                  label={isActive ? "ACTIVE MEMBER" : member.membership_status || member.status || "PENDING"}
                  sx={{ fontWeight: "bold" }}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Typography variant="h6" fontWeight="bold" sx={{ mb: 1 }}>
                Quick Actions
              </Typography>

              <Stack spacing={1}>
                <Button fullWidth variant="contained" color="success">
                  ✅ Check In
                </Button>
                <Button fullWidth variant="contained" color="error">
                  💳 Renew Membership
                </Button>
                <Button fullWidth variant="outlined" color="error">
                  🖨 Print Card
                </Button>
                <Button fullWidth variant="outlined" color="error">
                  📷 Show QR Code
                </Button>
                <Button fullWidth variant="outlined" color="error">
                  ✏ Edit Member
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {["Profile", "Attendance", "Payments", "Membership", "Documents", "Notes"].map((item) => (
              <Button
                key={item}
                variant={tab === item ? "contained" : "outlined"}
                color="error"
                onClick={() => setTab(item)}
                sx={{ mb: 1 }}
              >
                {item}
              </Button>
            ))}
          </Stack>
        </CardContent>
      </Card>

      {tab === "Profile" && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">Contact</Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Email:</b> {member.email || "-"}</Typography>
                <Typography><b>Phone:</b> {member.phone || "-"}</Typography>
                <Typography><b>Clover ID:</b> {member.clover_customer_id || "-"}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">Membership</Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Type:</b> {member.membership_type || "Clover Customer"}</Typography>
                <Typography><b>Status:</b> {member.membership_status || member.status || "-"}</Typography>
                <Typography><b>Total Check-ins:</b> {member.total_checkins || 0}</Typography>
                <Typography>
                  <b>Last Check-in:</b>{" "}
                  {member.last_checkin ? new Date(member.last_checkin).toLocaleString() : "-"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">Member Card Data</Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Barcode:</b> {member.barcode || "-"}</Typography>
                <Typography><b>QR Code:</b> {member.qr_code || "-"}</Typography>
                <Typography><b>Digital Member ID:</b> {member.digital_member_id || "-"}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tab !== "Profile" && (
        <Card sx={{ borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="bold">{tab}</Typography>
            <Divider sx={{ my: 2 }} />
            <Typography color="text.secondary">
              {tab} details coming next.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}