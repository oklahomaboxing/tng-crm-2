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
import MemberCard from "./MemberCard.jsx";
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function MemberProfile({ member, onBack }) {
  const [tab, setTab] = useState("Profile");
  const [memberData, setMemberData] = useState(member);
  const [attendance, setAttendance] = useState(null);
  const [attendanceError, setAttendanceError] = useState("");
  const [payments, setPayments] = useState(null);
  const [paymentError, setPaymentError] = useState("");
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [showCard, setShowCard] = useState(false);
  if (!memberData) return null;

  const fullName = `${memberData.first_name || ""} ${memberData.last_name || ""}`.trim();
  const isActive =
    memberData.membership_status === "active" || memberData.status === "active";

  function photoSrc() {
    if (!memberData.photo_url) return "";
    if (memberData.photo_url.startsWith("http")) return memberData.photo_url;
    return `${API}${memberData.photo_url}`;
  }

  async function loadMember() {
    const res = await fetch(`${API}/api/members/${memberData.id}`, {
      headers: {
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
    });

    const data = await res.json();
    if (res.ok) setMemberData(data);
  }

  async function loadAttendance() {
    try {
      setAttendanceError("");

      const res = await fetch(`${API}/api/members/${memberData.id}/attendance`, {
        headers: {
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not load attendance");

      setAttendance(data);
    } catch (err) {
      setAttendanceError(err.message);
    }
  }

async function loadPayments() {
  try {
    setPaymentError("");

    const res = await fetch(
      `${API}/api/members/${memberData.id}/payments`,
      {
        headers: {
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
      }
    );

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Could not load payments");
    }

    setPayments(data);
  } catch (err) {
    setPaymentError(err.message);
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
          code:
            memberData.barcode ||
            memberData.member_number ||
            memberData.qr_code,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Check-in failed");

      alert(`✅ ${data.member.name} checked in successfully`);

      await loadMember();

      if (tab === "Attendance") {
        await loadAttendance();
      }
    } catch (err) {
      alert(`❌ ${err.message}`);
    }
  }

async function renewMembership() {
  const monthsText = prompt(
    "Renew membership for how many months?\n\nType 1 for 1 month\nType 3 for 3 months"
  );

  if (monthsText !== "1" && monthsText !== "3") {
    return;
  }

  try {
    const res = await fetch(
      `${API}/api/members/${memberData.id}/renew`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
        body: JSON.stringify({
          months: Number(monthsText),
        }),
      }
    );

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Renewal failed");
    }

    await loadMember();

    alert(`✅ ${data.message}`);
  } catch (err) {
    alert(`❌ ${err.message}`);
  }
}

async function uploadPhoto(e) {
  const file = e.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API}/api/members/${memberData.id}/photo`, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + localStorage.getItem("token"),
    },
    body: formData,
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.detail || "Photo upload failed");
    return;
  }

  await loadMember();

  alert("✅ Photo uploaded");
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
    membership_start: memberData.membership_start
      ? memberData.membership_start.slice(0, 10)
      : "",
    membership_end: memberData.membership_end
      ? memberData.membership_end.slice(0, 10)
      : "",
    billing_cycle: memberData.billing_cycle || "",
    monthly_rate: memberData.monthly_rate || "",
    next_billing_date: memberData.next_billing_date
      ? memberData.next_billing_date.slice(0, 10)
      : "",
    billing_status: memberData.billing_status || "",
    notes: memberData.notes || "",
  });

  setEditing(true);
}

async function saveEdit() {
  const res = await fetch(`${API}/api/members/${memberData.id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + localStorage.getItem("token"),
    },
    body: JSON.stringify(editForm),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.detail || "Could not update member");
    return;
  }

  setMemberData(data);
  setEditing(false);
  alert("✅ Member updated");
}

async function deleteMember() {
  const confirmText = prompt(
    `Type DELETE to permanently delete ${fullName || "this member"}`
  );

  if (confirmText !== "DELETE") {
    return;
  }

  const res = await fetch(`${API}/api/members/${memberData.id}`, {
    method: "DELETE",
    headers: {
      Authorization: "Bearer " + localStorage.getItem("token"),
    },
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.detail || "Could not delete member");
    return;
  }

  alert("✅ Member deleted");
  onBack();
}

useEffect(() => {
  setMemberData(member);
}, [member]);

useEffect(() => {
  if (tab === "Attendance") {
    loadAttendance();
  }

  if (tab === "Payments") {
    loadPayments();
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
                  overflow: "hidden",
                }}
              >
                {memberData.photo_url ? (
                  <img
                    src={photoSrc()}
                    alt={fullName}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                ) : (
                  fullName ? fullName[0].toUpperCase() : "?"
                )}
              </Box>

              <Button
                fullWidth
                variant="outlined"
                color="error"
                component="label"
                sx={{ mt: 2 }}
              >
                📸 Upload Photo
                <input
                  hidden
                  type="file"
                  accept="image/*"
                  onChange={uploadPhoto}
                />
              </Button>
            </Grid>

            <Grid item xs={12} md={5}>
              <Typography variant="h4" fontWeight="bold">
                {fullName || "Member"}
              </Typography>

              <Typography color="text.secondary" sx={{ mt: 1 }}>
                Member # {memberData.member_number || "-"}
              </Typography>

              <Typography sx={{ mt: 1 }}>
                {memberData.membership_type || "Clover Customer"}
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Chip
                  color={isActive ? "success" : "warning"}
                  label={
                    isActive
                      ? "ACTIVE MEMBER"
                      : memberData.membership_status ||
                        memberData.status ||
                        "PENDING"
                  }
                  sx={{ fontWeight: "bold" }}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Typography variant="h6" fontWeight="bold" sx={{ mb: 1 }}>
                Quick Actions
              </Typography>

              <Stack spacing={1}>
                <Button
                  fullWidth
                  variant="contained"
                  color="success"
                  onClick={checkInMember}
                >
                  ✅ Check In
                </Button>
                <Button
                  fullWidth
                  variant="contained"
                  color="error"
                  onClick={renewMembership}
                >
                  💳 Renew Membership
                </Button>
                <Button fullWidth variant="outlined" color="error" onClick={() => setShowCard(true)}>
                  🖨 Print Card
                </Button>
                <Button fullWidth variant="outlined" color="error">
                  📷 Show QR Code
                </Button>
                <Button fullWidth variant="outlined" color="error" onClick={startEdit}>
                 ✏ Edit Member
               </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  color="error"
                  onClick={deleteMember}
                >
                  🗑 Delete Member
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
{editing && (
  <Card sx={{ borderRadius: 3, mb: 3 }}>
    <CardContent>
      <Typography variant="h6" fontWeight="bold">
        Edit Member
      </Typography>
      <Divider sx={{ my: 2 }} />

      <Grid container spacing={2}>
        {[
          ["first_name", "First Name"],
          ["last_name", "Last Name"],
          ["email", "Email"],
          ["phone", "Phone"],
          ["membership_type", "Membership Type"],
          ["membership_status", "Membership Status"],
          ["assigned_coach", "Assigned Coach"],
          ["emergency_contact", "Emergency Contact"],
          ["emergency_phone", "Emergency Phone"],
          ["membership_start", "Membership Start"],
          ["membership_end", "Membership Expiration"],
          ["billing_cycle", "Billing Cycle"],
          ["monthly_rate", "Monthly Rate"],
          ["next_billing_date", "Next Billing Date"],
          ["billing_status", "Billing Status"],
          ["notes", "Notes"],
        ].map(([field, label]) => (
          <Grid item xs={12} md={6} key={field}>
            <input
              value={editForm[field] || ""}
              onChange={(e) =>
                setEditForm({ ...editForm, [field]: e.target.value })
              }
              placeholder={label}
              style={{
                width: "100%",
                padding: 12,
                borderRadius: 8,
                border: "1px solid #ccc",
                boxSizing: "border-box",
              }}
            />
          </Grid>
        ))}
      </Grid>

      <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
        <Button variant="contained" color="error" onClick={saveEdit}>
          Save Changes
        </Button>
        <Button variant="outlined" color="error" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </Stack>
    </CardContent>
  </Card>
)}

{showCard && (
  <Card sx={{ borderRadius: 3, mb: 3 }}>
    <CardContent>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Button variant="contained" color="error" onClick={() => window.print()}>
          Print
        </Button>
        <Button variant="outlined" color="error" onClick={() => setShowCard(false)}>
          Close
        </Button>
      </Stack>

      <MemberCard member={memberData} />
    </CardContent>
  </Card>
)}
      {tab === "Profile" && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">
                  Contact
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Email:</b> {memberData.email || "-"}</Typography>
                <Typography><b>Phone:</b> {memberData.phone || "-"}</Typography>
                <Typography><b>Clover ID:</b> {memberData.clover_customer_id || "-"}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">
                  Membership
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Type:</b> {memberData.membership_type || "Clover Customer"}</Typography>
                <Typography><b>Status:</b> {memberData.membership_status || memberData.status || "-"}</Typography>
                <Typography>
                  <b>Total Check-ins:</b> {memberData.total_checkins || 0}
                </Typography>

                <Typography>
                  <b>Last Check-in:</b>{" "}
                  {memberData.last_checkin
                    ? new Date(memberData.last_checkin).toLocaleString()
                    : "-"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold">
                  Member Card Data
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Typography><b>Barcode:</b> {memberData.barcode || "-"}</Typography>
                <Typography><b>QR Code:</b> {memberData.qr_code || "-"}</Typography>
                <Typography><b>Digital Member ID:</b> {memberData.digital_member_id || "-"}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tab === "Attendance" && (
        <Card sx={{ borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="bold">
              Attendance History
            </Typography>
            <Divider sx={{ my: 2 }} />

            {attendanceError && (
              <Typography color="error">{attendanceError}</Typography>
            )}

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} md={4}>
                <Card sx={{ p: 2, background: "#f7f7f7" }}>
                  <Typography color="text.secondary">Total Check-ins</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {attendance?.total_checkins ?? memberData.total_checkins ?? 0}
                  </Typography>
                </Card>
              </Grid>

              <Grid item xs={12} md={8}>
                <Card sx={{ p: 2, background: "#f7f7f7" }}>
                  <Typography color="text.secondary">Last Check-in</Typography>
                  <Typography variant="h6" fontWeight="bold">
                    {attendance?.last_checkin
                      ? new Date(attendance.last_checkin).toLocaleString()
                      : memberData.last_checkin
                      ? new Date(memberData.last_checkin).toLocaleString()
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
                      ✅{" "}
                      {row.checkin_time
                        ? new Date(row.checkin_time).toLocaleString()
                        : "-"}
                    </Typography>
                    <Typography color="text.secondary">
                      Method: {row.method || "barcode"} • Location:{" "}
                      {row.location || "Front Desk"}
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

      {tab === "Payments" && (
  <Card sx={{ borderRadius: 3 }}>
    <CardContent>
      <Typography variant="h6" fontWeight="bold">
        Payment History
      </Typography>
      <Divider sx={{ my: 2 }} />

      {paymentError && (
        <Typography color="error">{paymentError}</Typography>
      )}

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2, background: "#f7f7f7" }}>
            <Typography color="text.secondary">Lifetime Value</Typography>
            <Typography variant="h4" fontWeight="bold">
              ${Number(payments?.lifetime_value || 0).toFixed(2)}
            </Typography>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2, background: "#f7f7f7" }}>
            <Typography color="text.secondary">Total Payments</Typography>
            <Typography variant="h4" fontWeight="bold">
              {payments?.total_payments || 0}
            </Typography>
          </Card>
        </Grid>
      </Grid>

      {payments?.payments?.length > 0 ? (
        <Stack spacing={1}>
          {payments.payments.map((p) => (
            <Card key={p.id} sx={{ p: 2, borderRadius: 2 }}>
              <Typography fontWeight="bold">
                💳 ${Number(p.amount || 0).toFixed(2)}
              </Typography>

              <Typography color="text.secondary">
                {p.membership || "Membership"} • {p.payment_status || "paid"}
              </Typography>

              <Typography color="text.secondary">
                {p.sale_date ? new Date(p.sale_date).toLocaleString() : ""}
              </Typography>

              <Typography variant="caption" color="text.secondary">
                Clover Order: {p.clover_order_id || "-"}
              </Typography>
            </Card>
          ))}
        </Stack>
      ) : (
        <Typography color="text.secondary">
          No payments found for this member.
        </Typography>
      )}
    </CardContent>
  </Card>
)}

{tab === "Membership" && (
  <Card sx={{ borderRadius: 3 }}>
    <CardContent>
      <Typography variant="h6" fontWeight="bold">
        Membership Billing
      </Typography>
      <Divider sx={{ my: 2 }} />

      <Typography><b>Plan:</b> {memberData.membership_type || "-"}</Typography>
      <Typography><b>Status:</b> {memberData.membership_status || "-"}</Typography>

      <Typography>
        <b>Membership Starts:</b>{" "}
        {memberData.membership_start
          ? new Date(memberData.membership_start).toLocaleDateString()
          : "-"}
      </Typography>

      <Typography>
        <b>Membership Expires:</b>{" "}
        {memberData.membership_end
          ? new Date(memberData.membership_end).toLocaleDateString()
          : "-"}
      </Typography>

      <Typography><b>Billing Cycle:</b> {memberData.billing_cycle || "-"}</Typography>

      <Typography>
        <b>Monthly Rate:</b> ${Number(memberData.monthly_rate || 0).toFixed(2)}
      </Typography>

      <Typography>
        <b>Next Billing:</b>{" "}
        {memberData.next_billing_date
          ? new Date(memberData.next_billing_date).toLocaleDateString()
          : "Not Scheduled"}
      </Typography>

      <Typography>
        <b>AutoPay:</b> {memberData.autopay_enabled ? "🟢 Enabled" : "⚪ Disabled"}
      </Typography>
      <Divider sx={{ my: 3 }} />

      <Stack direction="row" spacing={2} flexWrap="wrap">
        <Button
          variant="contained"
          color="success"
          fullWidth
        >
          💳 Enable AutoPay
        </Button>

        <Button
          variant="contained"
          color="error"
          fullWidth
          onClick={renewMembership}
        >
          🔄 Renew Membership
        </Button>

        <Button
          variant="outlined"
          color="warning"
          fullWidth
        >
          ⏸ Pause Membership
        </Button>

        <Button
          variant="outlined"
          color="error"
          fullWidth
        >
          ❌ Cancel Membership
        </Button>
      </Stack>
    </CardContent>
  </Card>
)}

{tab !== "Profile" && tab !== "Attendance" && tab !== "Payments" && tab !== "Membership" && (  <Card sx={{ borderRadius: 3 }}>
    <CardContent>
      <Typography variant="h6" fontWeight="bold">
        {tab}
      </Typography>
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