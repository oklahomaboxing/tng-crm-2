import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { API, authHeaders } from "../services/api";
import MemberCard from "./MemberCard.jsx";

function formatDate(value, includeTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return includeTime ? date.toLocaleString() : date.toLocaleDateString();
}

function daysRemaining(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.ceil((date.getTime() - Date.now()) / 86400000);
}

export default function MemberProfile({ member, onBack }) {
  const [memberData, setMemberData] = useState(member);
  const [tab, setTab] = useState("overview");
  const [payments, setPayments] = useState(null);
  const [attendance, setAttendance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const [form, setForm] = useState({});

  const fullName = useMemo(() => `${memberData?.first_name || ""} ${memberData?.last_name || ""}`.trim(), [memberData]);
  const days = daysRemaining(memberData?.membership_end);
  const isActive = memberData?.membership_status === "active" && (days === null || days >= 0);

  async function loadMember() {
    try {
      setError("");
      const response = await fetch(`${API}/api/members/${member.id}`, { headers: authHeaders() });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load member");
      setMemberData(data);
    } catch (err) {
      setError(err.message || "Could not load member");
    } finally {
      setLoading(false);
    }
  }

  async function loadPayments() {
    const response = await fetch(`${API}/api/members/${member.id}/payments`, { headers: authHeaders() });
    const data = await response.json();
    if (response.ok) setPayments(data);
  }

  async function loadAttendance() {
    const response = await fetch(`${API}/api/members/${member.id}/attendance`, { headers: authHeaders() });
    const data = await response.json();
    if (response.ok) setAttendance(data);
  }

  useEffect(() => {
    loadMember();
    loadPayments();
    loadAttendance();
  }, [member.id]);

  async function checkIn() {
    const response = await fetch(`${API}/api/checkin`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ code: memberData.barcode || memberData.member_number || memberData.qr_code }),
    });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Check-in failed");
    await Promise.all([loadMember(), loadAttendance()]);
    alert(`${data.member.name} checked in successfully`);
  }

  async function uploadPhoto(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const response = await fetch(`${API}/api/members/${member.id}/photo`, { method: "POST", headers: authHeaders(), body });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Photo upload failed");
    await loadMember();
  }

  function startEdit() {
    setForm({
      first_name: memberData.first_name || "",
      last_name: memberData.last_name || "",
      email: memberData.email || "",
      phone: memberData.phone || "",
      assigned_coach: memberData.assigned_coach || "",
      emergency_contact: memberData.emergency_contact || "",
      emergency_phone: memberData.emergency_phone || "",
      notes: memberData.notes || "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    const response = await fetch(`${API}/api/members/${member.id}`, {
      method: "PUT",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const data = await response.json();
    if (!response.ok) return alert(data.detail || "Could not save member");
    setEditing(false);
    await loadMember();
  }

  if (loading) return <Box display="flex" justifyContent="center" py={8}><CircularProgress color="error" /></Box>;

  return (
    <Box>
      <Button variant="outlined" color="error" onClick={onBack} sx={{ mb: 2 }}>← Back to Members</Button>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ borderRadius: 4, mb: 3, overflow: "hidden" }}>
        <Box sx={{ background: "linear-gradient(135deg,#09090b,#1d1d24)", color: "white", p: { xs: 2.5, md: 4 } }}>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md="auto">
              <Avatar src={memberData.photo_url ? `${API}${memberData.photo_url}` : undefined} sx={{ width: { xs: 96, md: 132 }, height: { xs: 96, md: 132 }, border: "4px solid #d71920", bgcolor: "#222", fontSize: 44 }}>
                {fullName.charAt(0).toUpperCase() || "?"}
              </Avatar>
            </Grid>
            <Grid item xs={12} md>
              <Typography variant="h4" fontWeight={900}>{fullName || "Member"}</Typography>
              <Typography sx={{ opacity: 0.7 }}>{memberData.member_number || "No member number"}</Typography>
              <Stack direction="row" spacing={1} mt={2} flexWrap="wrap">
                <Chip label={isActive ? "ACTIVE" : "INACTIVE"} color={isActive ? "success" : "error"} />
                <Chip label={memberData.membership_type || "Membership"} sx={{ color: "white", borderColor: "rgba(255,255,255,.35)" }} variant="outlined" />
                {days !== null && <Chip label={days >= 0 ? `${days} days left` : `${Math.abs(days)} days expired`} color={days >= 0 ? "warning" : "error"} />}
              </Stack>
            </Grid>
            <Grid item xs={12} md="auto">
              <Stack spacing={1} minWidth={{ md: 210 }}>
                <Button variant="contained" color="success" onClick={checkIn}>Check In</Button>
                <Button variant="contained" color="error" onClick={startEdit}>Edit Member</Button>
                <Button variant="outlined" component="label" sx={{ color: "white", borderColor: "rgba(255,255,255,.5)" }}>Upload Photo<input hidden type="file" accept="image/*" onChange={uploadPhoto} /></Button>
                <Button variant="outlined" onClick={() => setShowCard((value) => !value)} sx={{ color: "white", borderColor: "rgba(255,255,255,.5)" }}>Membership Card</Button>
              </Stack>
            </Grid>
          </Grid>
        </Box>
      </Card>

      {showCard && <Card sx={{ mb: 3, borderRadius: 4 }}><CardContent><Stack direction="row" justifyContent="flex-end" mb={2}><Button onClick={() => window.print()} variant="contained" color="error">Print</Button></Stack><MemberCard member={memberData} /></CardContent></Card>}

      {editing && (
        <Card sx={{ borderRadius: 4, mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={900}>Edit Member</Typography>
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={2}>
              {[
                ["first_name", "First Name"], ["last_name", "Last Name"], ["email", "Email"], ["phone", "Phone"],
                ["assigned_coach", "Assigned Coach"], ["emergency_contact", "Emergency Contact"], ["emergency_phone", "Emergency Phone"], ["notes", "Notes"],
              ].map(([field, label]) => (
                <Grid item xs={12} md={field === "notes" ? 12 : 6} key={field}>
                  <TextField fullWidth multiline={field === "notes"} minRows={field === "notes" ? 3 : undefined} label={label} value={form[field] || ""} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />
                </Grid>
              ))}
            </Grid>
            <Stack direction="row" spacing={1} mt={2}><Button variant="contained" color="error" onClick={saveEdit}>Save</Button><Button variant="outlined" onClick={() => setEditing(false)}>Cancel</Button></Stack>
          </CardContent>
        </Card>
      )}

      <Card sx={{ borderRadius: 4 }}>
        <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto">
          <Tab value="overview" label="Overview" /><Tab value="membership" label="Membership" /><Tab value="payments" label="Payments" /><Tab value="attendance" label="Attendance" /><Tab value="notes" label="Notes" />
        </Tabs>
        <Divider />
        <CardContent>
          {tab === "overview" && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}><InfoCard title="Contact" rows={[["Email", memberData.email], ["Phone", memberData.phone], ["Emergency Contact", memberData.emergency_contact], ["Emergency Phone", memberData.emergency_phone]]} /></Grid>
              <Grid item xs={12} md={6}><InfoCard title="Gym Profile" rows={[["Assigned Coach", memberData.assigned_coach], ["Total Check-ins", memberData.total_checkins || 0], ["Last Check-in", formatDate(memberData.last_checkin, true)], ["Clover ID", memberData.clover_customer_id]]} /></Grid>
            </Grid>
          )}
          {tab === "membership" && <InfoCard title="Membership Billing" rows={[["Plan", memberData.membership_type], ["Status", memberData.membership_status], ["Join Date", formatDate(memberData.membership_start)], ["Expiration", formatDate(memberData.membership_end)], ["Last Payment", formatDate(memberData.last_payment_date)], ["Next Billing", formatDate(memberData.next_billing_date)], ["Monthly Rate", `$${Number(memberData.monthly_rate || 0).toFixed(2)}`], ["Billing Status", memberData.billing_status]]} />}
          {tab === "payments" && (
            <Stack spacing={2}>
              <Grid container spacing={2}><Grid item xs={6}><Metric label="Lifetime Value" value={`$${Number(payments?.lifetime_value || 0).toFixed(2)}`} /></Grid><Grid item xs={6}><Metric label="Payments" value={payments?.total_payments || 0} /></Grid></Grid>
              {(payments?.payments || []).map((payment) => <Card key={payment.id} variant="outlined"><CardContent><Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between"><Box><Typography fontWeight={900}>{payment.membership || "Membership"}</Typography><Typography color="text.secondary">{formatDate(payment.sale_date, true)}</Typography></Box><Typography variant="h6" fontWeight={900}>${Number(payment.amount || 0).toFixed(2)}</Typography></Stack></CardContent></Card>)}
              {!payments?.payments?.length && <Typography color="text.secondary">No payments found.</Typography>}
            </Stack>
          )}
          {tab === "attendance" && (
            <Stack spacing={2}>
              <Grid container spacing={2}><Grid item xs={6}><Metric label="Total Check-ins" value={attendance?.total_checkins || 0} /></Grid><Grid item xs={6}><Metric label="Last Check-in" value={formatDate(attendance?.last_checkin, true)} /></Grid></Grid>
              {(attendance?.attendance || []).map((row) => <Card key={row.id} variant="outlined"><CardContent><Typography fontWeight={800}>{formatDate(row.checkin_time, true)}</Typography><Typography color="text.secondary">{row.method || "barcode"} • {row.location || "Front Desk"}</Typography></CardContent></Card>)}
              {!attendance?.attendance?.length && <Typography color="text.secondary">No attendance records found.</Typography>}
            </Stack>
          )}
          {tab === "notes" && <Typography sx={{ whiteSpace: "pre-wrap" }}>{memberData.notes || "No notes saved."}</Typography>}
        </CardContent>
      </Card>
    </Box>
  );
}

function InfoCard({ title, rows }) {
  return <Card variant="outlined" sx={{ borderRadius: 3, height: "100%" }}><CardContent><Typography fontWeight={900}>{title}</Typography><Divider sx={{ my: 2 }} />{rows.map(([label, value]) => <Stack key={label} direction="row" justifyContent="space-between" spacing={2} py={0.75}><Typography color="text.secondary">{label}</Typography><Typography fontWeight={700} textAlign="right">{value || "—"}</Typography></Stack>)}</CardContent></Card>;
}

function Metric({ label, value }) {
  return <Card sx={{ borderRadius: 3, bgcolor: "#f6f6f8" }}><CardContent><Typography color="text.secondary">{label}</Typography><Typography variant="h5" fontWeight={900}>{value}</Typography></CardContent></Card>;
}
