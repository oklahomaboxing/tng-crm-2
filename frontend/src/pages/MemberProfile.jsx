import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Grid,
  Divider,
} from "@mui/material";

export default function MemberProfile({ member, onBack }) {
  if (!member) return null;

  const fullName = `${member.first_name || ""} ${member.last_name || ""}`.trim();

  return (
    <Box>
      <Button variant="outlined" color="error" onClick={onBack} sx={{ mb: 2 }}>
        ← Back to Members
      </Button>

      <Card sx={{ borderRadius: 4, mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={3}>
              <Box
                sx={{
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  background: "#111",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 52,
                  fontWeight: "bold",
                }}
              >
                {fullName ? fullName[0].toUpperCase() : "?"}
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h4" fontWeight="bold">
                {fullName || "Member"}
              </Typography>

              <Typography color="text.secondary" sx={{ mt: 1 }}>
                Member # {member.member_number || "-"}
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Chip
                  color={
                    member.membership_status === "active" || member.status === "active"
                      ? "success"
                      : "warning"
                  }
                  label={member.membership_status || member.status || "pending"}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={3}>
              <Button fullWidth variant="contained" color="error" sx={{ mb: 1 }}>
                Check In
              </Button>
              <Button fullWidth variant="outlined" color="error" sx={{ mb: 1 }}>
                Print Card
              </Button>
              <Button fullWidth variant="outlined" color="error">
                Show QR Code
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

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
              <Typography><b>Last Check-in:</b> {member.last_checkin ? new Date(member.last_checkin).toLocaleString() : "-"}</Typography>
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
    </Box>
  );
}