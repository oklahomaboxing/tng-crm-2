import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { QRCodeCanvas } from "qrcode.react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function MemberProfile({ member, onBack }) {
  const [memberData, setMemberData] = useState(member);
  const [tab, setTab] = useState("Profile");
  const [attendance, setAttendance] = useState(null);
  const [payments, setPayments] = useState(null);
  const [error, setError] = useState("");
  const [showQr, setShowQr] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    setMemberData(member);
  }, [member]);

  useEffect(() => {
    if (tab === "Attendance") loadAttendance();
    if (tab === "Payments") loadPayments();
  }, [tab]);

  if (!memberData) return null;

  const fullName = `${memberData.first_name || ""} ${memberData.last_name || ""}`.trim();
  const isActive =
    memberData.membership_status === "active" || memberData.status === "active";

  const qrValue = useMemo(
    () =>
      memberData.barcode ||
      (memberData.member_number || "").replaceAll("-", "") ||
      String(memberData.id),
    [memberData]
  );

  function photoSrc() {
    if (!memberData.photo_url) return "";
    return memberData.photo_url.startsWith("http")
      ? memberData.photo_url
      : `${API}${memberData.photo_url}`;
  }

  async function loadMember() {
    const response = await fetch(`${API}/api/members/${memberData.id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    const data = await response.json();
    if (response.ok) setMemberData(data);
  }

  async function loadAttendance() {
    setError("");
    const response = await fetch(
      `${API}/api/members/${memberData.id}/attendance`,
      { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } }
    );
    const data = await response.json();
    if (!response.ok) return setError(data.detail || "Could not load attendance");
    setAttendance(data);
  }

  async function loadPayments() {
    setError("");
    const response = await fetch(
      `${API}/api/members/${memberData.id}/payments`,
      { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } }
    );
    const data = await response.json();
    if (!response.ok) return setError(data.detail || "Could not load payments");
    setPayments(data);
  }

  async function checkInMember() {
    const response = await fetch(`${API}/api/checkin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({ code: qrValue }),
    });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Check-in failed");
    alert(`${data.member.name} checked in successfully`);
    loadMember();
  }

  async function uploadPhoto(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API}/api/members/${memberData.id}/photo`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Photo upload failed");
    loadMember();
  }

  function startEdit() {
    setEditForm({
      first_name: memberData.first_name || "",
      last_name: memberData.last_name || "",
      email: memberData.email || "",
      phone: memberData.phone || "",
      membership_type: memberData.membership_type || "",
      membership_status: memberData.membership_status || "active",
      assigned_coach: memberData.assigned_coach || "",
      emergency_contact: memberData.emergency_contact || "",
      emergency_phone: memberData.emergency_phone || "",
      notes: memberData.notes || "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    const response = await fetch(`${API}/api/members/${memberData.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify(editForm),
    });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Could not update member");
    setMemberData(data);
    setEditing(false);
  }

  function downloadQrCode() {
    const canvas = document.getElementById("tng-member-qr");
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `${fullName.replace(/[^a-z0-9]/gi, "-").toLowerCase()}-tng-qr.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  return (
    <Box>
      <Button variant="outlined" color="error" onClick={onBack} sx={{ mb: 2 }}>
        Back to Members
      </Button>

      <Card sx={{ borderRadius: 4, mb: 3, overflow: "hidden" }}>
        <Box sx={{ bgcolor: "#0b0b0f", color: "white", p: 3 }}>
          <Typography variant="h5" fontWeight="bold">MEMBER PROFILE</Typography>
        </Box>

        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={3}>
              <Box sx={{
                width: 170, height: 170, borderRadius: "50%", bgcolor: "#111",
                color: "white", display: "flex", alignItems: "center",
                justifyContent: "center", fontSize: 60, fontWeight: "bold",
                border: "5px solid #d71920", overflow: "hidden",
                mx: { xs: "auto", md: 0 }
              }}>
                {memberData.photo_url ? (
                  <img src={photoSrc()} alt={fullName}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (fullName[0] || "?").toUpperCase()}
              </Box>

              <Button fullWidth variant="outlined" color="error"
                component="label" sx={{ mt: 2 }}>
                Upload Photo
                <input hidden type="file" accept="image/*" onChange={uploadPhoto} />
              </Button>
            </Grid>

            <Grid item xs={12} md={5}>
              <Typography variant="h4" fontWeight="bold">{fullName}</Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                Member # {memberData.member_number || "-"}
              </Typography>
              <Typography sx={{ mt: 1 }}>
                {memberData.membership_type || "Membership"}
              </Typography>
              <Chip sx={{ mt: 2, fontWeight: "bold" }}
                color={isActive ? "success" : "warning"}
                label={isActive ? "ACTIVE MEMBER" : "INACTIVE MEMBER"} />
            </Grid>

            <Grid item xs={12} md={4}>
              <Stack spacing={1}>
                <Button variant="contained" color="success" onClick={checkInMember}>
                  Check In
                </Button>
                <Button variant="contained" color="error" onClick={() => setShowQr(true)}>
                  Show Check-In QR
                </Button>
                <Button variant="outlined" color="error" onClick={startEdit}>
                  Edit Member
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {["Profile", "Attendance", "Payments"].map((item) => (
              <Button key={item} color="error"
                variant={tab === item ? "contained" : "outlined"}
                onClick={() => setTab(item)} sx={{ mb: 1 }}>
                {item}
              </Button>
            ))}
          </Stack>
        </CardContent>
      </Card>

      {editing && (
        <Card sx={{ borderRadius: 3, mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="bold">Edit Member</Typography>
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={2}>
              {[
                ["first_name", "First Name"], ["last_name", "Last Name"],
                ["email", "Email"], ["phone", "Phone"],
                ["membership_type", "Membership Type"],
                ["membership_status", "Membership Status"],
                ["assigned_coach", "Assigned Coach"],
                ["emergency_contact", "Emergency Contact"],
                ["emergency_phone", "Emergency Phone"], ["notes", "Notes"],
              ].map(([field, label]) => (
                <Grid item xs={12} md={6} key={field}>
                  <TextField fullWidth label={label} value={editForm[field] || ""}
                    onChange={(e) => setEditForm({ ...editForm, [field]: e.target.value })} />
                </Grid>
              ))}
            </Grid>
            <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
              <Button variant="contained" color="error" onClick={saveEdit}>Save</Button>
              <Button variant="outlined" onClick={() => setEditing(false)}>Cancel</Button>
            </Stack>
          </CardContent>
        </Card>
      )}

      {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}

      {tab === "Profile" && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <InfoCard title="Contact">
              <Typography><b>Email:</b> {memberData.email || "-"}</Typography>
              <Typography><b>Phone:</b> {memberData.phone || "-"}</Typography>
              <Typography><b>Coach:</b> {memberData.assigned_coach || "-"}</Typography>
              <Typography><b>Emergency:</b> {memberData.emergency_contact || "-"}</Typography>
            </InfoCard>
          </Grid>
          <Grid item xs={12} md={6}>
            <InfoCard title="Membership">
              <Typography><b>Plan:</b> {memberData.membership_type || "-"}</Typography>
              <Typography><b>Status:</b> {memberData.membership_status || "-"}</Typography>
              <Typography><b>Starts:</b> {memberData.membership_start ? new Date(memberData.membership_start).toLocaleDateString() : "-"}</Typography>
              <Typography><b>Expires:</b> {memberData.membership_end ? new Date(memberData.membership_end).toLocaleDateString() : "-"}</Typography>
            </InfoCard>
          </Grid>
        </Grid>
      )}

      {tab === "Attendance" && (
        <InfoCard title="Attendance History">
          <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
            {attendance?.total_checkins ?? memberData.total_checkins ?? 0} Check-ins
          </Typography>
          <Stack spacing={1}>
            {(attendance?.attendance || []).map((row) => (
              <Card key={row.id} sx={{ p: 2 }}>
                {row.checkin_time ? new Date(row.checkin_time).toLocaleString() : "-"}
              </Card>
            ))}
          </Stack>
        </InfoCard>
      )}

      {tab === "Payments" && (
        <InfoCard title="Payment History">
          <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
            ${Number(payments?.lifetime_value || 0).toFixed(2)}
          </Typography>
          <Stack spacing={1}>
            {(payments?.payments || []).map((payment) => (
              <Card key={payment.id} sx={{ p: 2 }}>
                <Typography fontWeight="bold">
                  ${Number(payment.amount || 0).toFixed(2)}
                </Typography>
                <Typography color="text.secondary">
                  {payment.membership || "Membership"} • {payment.sale_date ? new Date(payment.sale_date).toLocaleString() : ""}
                </Typography>
              </Card>
            ))}
          </Stack>
        </InfoCard>
      )}

      <Dialog open={showQr} onClose={() => setShowQr(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ textAlign: "center", bgcolor: "#0b0b0f", color: "white", fontWeight: 900 }}>
          TNG MEMBER CHECK-IN
        </DialogTitle>
        <DialogContent sx={{ textAlign: "center", py: 4 }}>
          <Typography variant="h4" fontWeight="bold">{fullName}</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {memberData.member_number || qrValue}
          </Typography>

          <Box sx={{ display: "inline-flex", p: 2, bgcolor: "white", border: "4px solid #111", borderRadius: 3 }}>
            <QRCodeCanvas id="tng-member-qr" value={qrValue}
              size={300} level="H" includeMargin />
          </Box>

          <Typography sx={{ mt: 3, fontWeight: 700 }}>
            Scan at the front desk tablet to check in.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button fullWidth variant="contained" color="error" onClick={downloadQrCode}>
            Save to Phone
          </Button>
          <Button fullWidth variant="outlined" onClick={() => setShowQr(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function InfoCard({ title, children }) {
  return (
    <Card sx={{ borderRadius: 3 }}>
      <CardContent>
        <Typography variant="h6" fontWeight="bold">{title}</Typography>
        <Divider sx={{ my: 2 }} />
        {children}
      </CardContent>
    </Card>
  );
}