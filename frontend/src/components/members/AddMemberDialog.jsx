import React, { useState } from "react";
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Stack, TextField, Typography } from "@mui/material";
import { API, authHeaders } from "../../services/api";

const empty = { first_name: "", last_name: "", email: "", phone: "", address: "", city: "", state: "", zip_code: "", notes: "" };
export default function AddMemberDialog({ open, onClose, onCreated }) {
  const [form, setForm] = useState(empty);
  const [invite, setInvite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    let created = null;
    try {
      const response = await fetch(`${API}/api/members`, { method: "POST", headers: { ...authHeaders(), "Content-Type": "application/json" }, body: JSON.stringify(form) });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check the name and contact details.");
      created = data;
      let message = "Profile created. Open the profile to manage membership, payments, and portal access.";
      if (invite && form.email.trim()) {
        try {
          const sent = await fetch(`${API}/api/member/admin/invite`, { method: "POST", headers: { ...authHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ member_id: data.id }) });
          const result = await sent.json();
          if (!sent.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not send the activation email.");
          message = result.email_sent ? "Profile created and portal activation email sent." : "Profile created. A portal activation invitation is already pending.";
        } catch (err) {
          message = `Profile #${data.id} was created, but portal access was not sent: ${err.message} Open the profile to retry; do not create another profile.`;
        }
      }
      setForm(empty); setInvite(false);
      onCreated(created, message);
    } catch (err) { setError(err.message || "Could not create the profile."); }
    finally { setBusy(false); }
  }
  return <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
    <form onSubmit={save}>
      <DialogTitle>Add Member Profile</DialogTitle>
      <DialogContent>
        <Stack spacing={2} pt={1}>
          <Typography color="text.secondary">Create a profile and member number now. Membership stays pending until a payment or membership is recorded.</Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            {["first_name", "last_name"].map(key => <TextField key={key} fullWidth label={key === "first_name" ? "First name" : "Last name"} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} inputProps={{ maxLength: 100 }} disabled={busy} />)}
          </Stack>
          {[['email', 'Email', 'email'], ['phone', 'Phone with area code', 'tel'], ['address', 'Address', 'text'], ['city', 'City', 'text'], ['state', 'State', 'text'], ['zip_code', 'ZIP code', 'text'], ['notes', 'Notes', 'text']].map(([key, label, type]) => <TextField key={key} label={label} type={type} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} multiline={key === 'notes'} minRows={key === 'notes' ? 2 : undefined} disabled={busy} />)}
          <FormControlLabel control={<Checkbox checked={invite} onChange={e => setInvite(e.target.checked)} disabled={busy || !form.email.trim()} />} label="Send portal activation email so the member can choose a password" />
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={onClose} disabled={busy}>Cancel</Button><Button type="submit" variant="contained" color="error" disabled={busy || !(form.first_name.trim() || form.last_name.trim())}>{busy ? "Creating…" : "Create Profile"}</Button></DialogActions>
    </form>
  </Dialog>;
}
