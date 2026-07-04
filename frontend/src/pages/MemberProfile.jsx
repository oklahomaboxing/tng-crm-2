import React, { useEffect, useState } from "react";
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

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function MemberProfile({ member, onBack }) {
  const [tab, setTab] = useState("Profile");
  const [attendance, setAttendance] = useState(null);
  const [attendanceError, setAttendanceError] = useState("");

  if (!member) return null;

  const fullName = `${member.first_name || ""} ${member.last_name || ""}`.trim();
  const isActive = member.membership_status === "active" || member.status === "active";

  async function loadAttendance() {
    try {
      setAttendanceError("");

      const res = await fetch(`${API}/api/members/${member.id}/attendance`, {
        headers: {
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Could not load attendance");
      }

      setAttendance(data);
    } catch (err) {
      setAttendanceError(err.message);
    }
  }

  async function checkInMember() {
    try {
      const res = await fetch(`${API}/api/checkin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
        body: JSON.stringify({
          code: member.barcode || member.member_number,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Check-in failed");
      }

      alert(`✅ ${data.member.name} checked in successfully`);

      if (tab === "Attendance") {
        loadAttendance();
      }
    } catch (err) {
      alert(`❌ ${err.message}`);
    }
  }

  useEffect(() => {
    if (tab === "Attendance") {
      loadAttendance();
    }
  }, [tab]);

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
                <Button fullWidth variant="contained" color="success" onClick={checkInMember}>
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

      {tab === "Attendance" && (
        <Card sx={{ borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="bold">Attendance History</Typography>
            <Divider sx={{ my: 2 }} />

            {attendanceError && (
              <Typography color="error">{attendanceError}</Typography>
            )}

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} md={4}>
                <Card sx={{ p: 2, background: "#f7f7f7" }}>
                  <Typography color="text.secondary">Total Check-ins</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {attendance?.total_checkins ?? member.total_checkins ?? 0}
                  </Typography>
                </Card>
              </Grid>

              <Grid item xs={12} md={8}>
                <Card sx={{ p: 2, background: "#f7f7f7" }}>
                  <Typography color="text.secondary">Last Check-in</Typography>
                  <Typography variant="h6" fontWeight="bold">
                    {attendance?.last_checkin
                      ? new Date(attendance.last_checkin).toLocaleString()
                      : member.last_checkin
                      ? new Date(member.last_checkin).toLocaleString()
                      : "-"}
                  </Typography>
                </Card>
              </Grid>
            </Grid>

            {attendance?.attendance?.length > 0 ? (
              <Stack spacing={1}>
                {attendance.attendance.map((row) => (
                  <Card key={row.id} sx={{ p: 2, borderRadius: 2 }}>
                    <Typography fontWeight="bold">
                      ✅ {row.checkin_time ? new Date(row.checkin_time).toLocaleString() : "-"}
                    </Typography>
                    <Typography color="text.secondary">
                      Method: {row.method || "barcode"} • Location: {row.location || "Front Desk"}
                    </Typography>
                  </Card>
                ))}
              </Stack>
            ) : (
              <Typography color="text.secondary">
                No attendance records yet.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {tab !== "Profile" && tab !== "Attendance" && (
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