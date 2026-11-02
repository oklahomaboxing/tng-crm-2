import { simpleMemberNumber } from "../utils/memberNumber";
import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { API, authHeaders } from "../services/api";
import MemberProfile from "./MemberProfile.jsx";
import { memberDate, membershipCategory, rosterTotals } from "../utils/membershipStatus";
import AddMemberDialog from "../components/members/AddMemberDialog.jsx";

function formatDate(value) {
  if (!value) return "—";
  const date = memberDate(value);
  return date ? date.toLocaleDateString() : "—";
}

function daysRemaining(value) {
  if (!value) return null;
  const end = memberDate(value);
  if (!end) return null;
  return Math.ceil((end.getTime() - Date.now()) / 86400000);
}

function statusFor(member) { return membershipCategory(member); }

function statusChip(member) {
  const status = statusFor(member);
  const map = {
    active: { label: "Active", color: "success" },
    expiring: { label: "Expiring Soon", color: "warning" },
    expired: { label: "Expired", color: "error" },
    inactive: { label: "Inactive", color: "default" },
    contact: { label: "Contact", color: "default" },
    review: { label: "Membership review", color: "warning" },
  };
  return map[status];
}

function portalLabel(member) {
  return ({ active: "Portal active", disabled: "Portal disabled", invited: "Activation email sent", not_invited: "Access not sent", needs_email: "Email needed", needs_review: "Shared contact — review" })[member.portal_status] || "Access not sent";
}

export default function Members({ role, initialMemberId, onOpenMember, onCloseMember }) {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const [addOpen, setAddOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState("");
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("profiles");
  const [sort, setSort] = useState("name");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedMember, setSelectedMember] = useState(null);
  const [bulkAccessLoading, setBulkAccessLoading] = useState(false);

  async function sendAccessToAllMembers() {
    const confirmed = window.confirm(
      "Send TNGOS portal access to every member who has an email and does not already have an active account or pending invitation?\n\nThis includes expired and inactive members."
    );

    if (!confirmed || bulkAccessLoading) return;

    try {
      setBulkAccessLoading(true);

      const response = await fetch(
        `${API}/api/member/admin/invite-all`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not send member portal access."
        );
      }

      window.alert(
        data.message ||
        "Member portal access process completed."
      );
    } catch (err) {
      window.alert(
        err.message ||
        "Could not send member portal access."
      );
    } finally {
      setBulkAccessLoading(false);
    }
  }


  async function syncCloverCustomers() {
    if (syncing) return;
    setSyncing(true); setNotice(""); setError("");
    try {
      const response = await fetch(`${API}/api/clover/sync-customers`, { method: "POST", headers: authHeaders() });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not sync Clover customers.");
      await loadMembers();
      setNotice(`Clover sync complete: ${data.members_created || 0} profiles added, ${data.members_linked || 0} linked, ${data.needs_review || 0} need duplicate review, ${data.skipped || 0} skipped (email and phone required).${data.needs_review ? ` Review Clover customer IDs: ${(data.review_customer_ids || []).join(", ")}.` : ""}`);
    } catch (err) { setError(err.message || "Could not sync Clover customers."); }
    finally { setSyncing(false); }
  }

  async function loadMembers() {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/members`, { headers: authHeaders() });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load members");
      setMembers(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not load members");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMembers();
  }, []);

  useEffect(() => {
    if (!initialMemberId) return;
    const controller = new AbortController();
    (async () => { try {
      const response = await fetch(`${API}/api/members/${initialMemberId}`, { headers: authHeaders(), signal: controller.signal });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Member profile could not be opened.');
      if (!controller.signal.aborted) setSelectedMember(data);
    } catch (err) { if (!controller.signal.aborted) setError(err.message); } })();
    return () => controller.abort();
  }, [initialMemberId]);
  function openMember(member) { setSelectedMember(member); onOpenMember?.(member.id); }

  const visibleMembers = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = members.filter((member) => {
      const searchable = [
        member.first_name,
        member.last_name,
        member.email,
        member.phone,
        member.member_number,
        simpleMemberNumber(member.member_number),
        member.membership_type,
        ...(member.contact_aliases || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch = !query || searchable.includes(query);
      const status = statusFor(member);
      const matchesFilter = filter === "profiles" || (filter === "all" && status !== "contact") || (filter === "active" && ["active","expiring"].includes(status)) || filter === status;
      return matchesSearch && matchesFilter;
    });

    return [...filtered].sort((a, b) => {
      if (sort === "expiration") {
        return new Date(a.membership_end || "2999-12-31") - new Date(b.membership_end || "2999-12-31");
      }
      if (sort === "payment") {
        return new Date(b.last_payment_date || 0) - new Date(a.last_payment_date || 0);
      }
      const nameA = `${a.first_name || ""} ${a.last_name || ""}`.trim();
      const nameB = `${b.first_name || ""} ${b.last_name || ""}`.trim();
      return nameA.localeCompare(nameB);
    });
  }, [members, search, filter, sort]);

  const totals = useMemo(() => rosterTotals(members), [members]);

  async function prepareAccountAccess() {
    if(syncing)return;setSyncing(true);setError('');
    try{const response=await fetch(`${API}/api/members/prepare-accounts`,{method:'POST',headers:authHeaders()});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not connect accounts.');await loadMembers();setNotice(`${data.created} accounts connected, ${data.already_active} already active, ${data.shared_email_review} need contact ownership review. Members can use password setup/reset to sign in.`);}catch(e){setError(e.message);}finally{setSyncing(false);}
  }

  async function consolidateContacts() {
    if (syncing) return;
    setSyncing(true);setError('');setNotice('');
    try {
      const response=await fetch(`${API}/api/duplicates/contacts/consolidate`,{method:'POST',headers:authHeaders()});
      const data=await response.json();
      if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not consolidate contacts.');
      await loadMembers();setNotice(`${data.merged} confirmed duplicate contacts consolidated. Original identifiers and linked histories retained. Conflicting profiles remain in Duplicate Review.`);
    }catch(err){setError(err.message);}finally{setSyncing(false);}
  }


  if (selectedMember) {
    return (
      <MemberProfile
        member={selectedMember}
        onBack={() => {
          setSelectedMember(null);
          onCloseMember?.();
          loadMembers();
        }}
      />
    );
  }

  return (
    <Box>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2} mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={900}>Members</Typography>
          <Typography color="text.secondary">Membership totals and one contact directory, with customer-only contacts kept separate</Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
          {role === "admin" && <>
            <Button variant="contained" color="error" onClick={() => setAddOpen(true)}>Add Member</Button>
            <Button variant="outlined" onClick={prepareAccountAccess} disabled={syncing}>Connect Customer Accounts</Button>
            <Button variant="outlined" onClick={consolidateContacts} disabled={syncing}>Consolidate Contacts</Button>
            <Button variant="outlined" onClick={syncCloverCustomers} disabled={syncing}>{syncing ? "Syncing Clover…" : "Sync Clover Customers"}</Button>
          </>}
          {role === "admin" && <Button
            variant="contained"
            color="error"
            onClick={sendAccessToAllMembers}
            disabled={bulkAccessLoading}
          >
            {bulkAccessLoading
              ? "Sending Access..."
              : "Send Portal Access to All Members"}
          </Button>}
          <Chip label={`${totals.active} Active`} color="success" />
          <Chip label={`${totals.expiring} Expiring`} color="warning" />
          <Chip label={`${totals.expired} Expired`} color="error" />
          <Chip label={`${totals.inactive} Inactive`} />
          <Chip label={`${totals.contact} Contacts`} />
        </Stack>
      </Stack>

      <AddMemberDialog open={addOpen} onClose={() => setAddOpen(false)} onCreated={async (_member, message) => { setAddOpen(false); await loadMembers(); setNotice(message); }} />
      {members.some(member => member.same_name_contact_review) && <Alert severity="warning" sx={{mb:2}} action={role === 'admin' ? <Button component="a" href="#/duplicate-review" color="inherit">Review duplicates</Button> : undefined}>Some profiles have matching names and contact details. They remain separate until identity is confirmed.</Alert>}
      {notice && <Alert severity="info" sx={{ mb: 2 }}>{notice}</Alert>}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Clover customer-directory imports require both an email address and phone number and refresh automatically every ten minutes. Existing profiles are retained. Open a profile to send portal access or record membership. Customer-only contacts are excluded from membership totals. Expiring means an active membership ending within seven days and is included in Active. Expired means its recorded end time has passed. Account access and gym membership are shown separately. Admin-created members start active with their assigned plan and rate.</Typography>
      <Card sx={{ borderRadius: 4, mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              fullWidth
              label="Search name, phone, email, member number, or plan"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <FormControl sx={{ minWidth: 170 }}>
              <InputLabel>Status</InputLabel>
              <Select value={filter} label="Status" onChange={(event) => setFilter(event.target.value)}>
                <MenuItem value="all">All Members ({totals.all})</MenuItem>
                <MenuItem value="active">Active ({totals.active})</MenuItem>
                <MenuItem value="expiring">Expiring ({totals.expiring})</MenuItem>
                <MenuItem value="expired">Expired ({totals.expired})</MenuItem>
                <MenuItem value="inactive">Inactive ({totals.inactive})</MenuItem>
                <MenuItem value="contact">Contacts ({totals.contact})</MenuItem>
                <MenuItem value="review">Membership review ({totals.review})</MenuItem>
                <MenuItem value="profiles">All Contacts & Members ({totals.profiles})</MenuItem>
              </Select>
            </FormControl>
            <FormControl sx={{ minWidth: 170 }}>
              <InputLabel>Sort</InputLabel>
              <Select value={sort} label="Sort" onChange={(event) => setSort(event.target.value)}>
                <MenuItem value="name">Name</MenuItem>
                <MenuItem value="expiration">Expiration</MenuItem>
                <MenuItem value="payment">Last Payment</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" py={8}><CircularProgress color="error" /></Box>
      ) : mobile ? (
        <Stack spacing={2}>
          {visibleMembers.map((member) => {
            const chip = statusChip(member);
            const days = member.membership_days_remaining ?? daysRemaining(member.membership_end);
            const name = `${member.first_name || ""} ${member.last_name || ""}`.trim();
            return (
              <Card key={member.id} sx={{ borderRadius: 4 }}>
                <CardActionArea onClick={() => openMember(member)}>
                  <CardContent>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Avatar src={member.photo_url ? `${API}${member.photo_url}` : undefined} sx={{ width: 58, height: 58, bgcolor: "#111" }}>
                        {name.charAt(0).toUpperCase() || "?"}
                      </Avatar>
                      <Box flex={1} minWidth={0}>
                        <Typography fontWeight={900} noWrap>{name || "Member"}</Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>{simpleMemberNumber(member.member_number) || "No member number"}</Typography>
                        <Typography variant="body2" noWrap>{member.membership_type || (member.member_type === "CUSTOMER" ? "Clover customer" : "No membership recorded")}</Typography>
                      </Box>
                      <Chip size="small" label={chip.label} color={chip.color} />
                    </Stack>
                    <Typography variant="body2" color="text.secondary" mt={1}>{portalLabel(member)}</Typography>
                    <Stack direction="row" justifyContent="space-between" mt={2} spacing={2}>
                      <Box><Typography variant="caption" color="text.secondary">Expires</Typography><Typography fontWeight={700}>{formatDate(member.membership_end)}</Typography></Box>
                      <Box textAlign="center"><Typography variant="caption" color="text.secondary">Days Left</Typography><Typography fontWeight={700}>{days === null ? "—" : days}</Typography></Box>
                      <Box textAlign="right"><Typography variant="caption" color="text.secondary">Check-ins</Typography><Typography fontWeight={700}>{member.total_checkins || 0}</Typography></Box>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            );
          })}
        </Stack>
      ) : (
        <Card sx={{ borderRadius: 4, overflow: "hidden" }}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Member</TableCell>
                  <TableCell>Plan</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Portal Access</TableCell>
                  <TableCell>Join Date</TableCell>
                  <TableCell>Expiration</TableCell>
                  <TableCell>Days Left</TableCell>
                  <TableCell>Last Payment</TableCell>
                  <TableCell align="right">Check-ins</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleMembers.map((member) => {
                  const chip = statusChip(member);
                  const days = member.membership_days_remaining ?? daysRemaining(member.membership_end);
                  const name = `${member.first_name || ""} ${member.last_name || ""}`.trim();
                  return (
                    <TableRow key={member.id} hover onClick={() => openMember(member)} sx={{ cursor: "pointer" }}>
                      <TableCell>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <Avatar src={member.photo_url ? `${API}${member.photo_url}` : undefined} sx={{ bgcolor: "#111" }}>{name.charAt(0).toUpperCase() || "?"}</Avatar>
                          <Box>
                            <Typography fontWeight={800}>{name || "Member"}</Typography>
                            <Typography variant="caption" color="text.secondary">{simpleMemberNumber(member.member_number) || "—"}</Typography>
                          </Box>
                        </Stack>
                      </TableCell>
                      <TableCell>{member.membership_type || (member.member_type === "CUSTOMER" ? "Clover customer" : "No membership recorded")}</TableCell>
                      <TableCell><Chip size="small" label={chip.label} color={chip.color} /></TableCell>
                      <TableCell>{portalLabel(member)}</TableCell>
                      <TableCell>{formatDate(member.membership_start)}</TableCell>
                      <TableCell>{formatDate(member.membership_end)}</TableCell>
                      <TableCell><Typography fontWeight={800} color={days !== null && days < 0 ? "error.main" : days !== null && days <= 7 ? "warning.main" : "text.primary"}>{days === null ? "—" : days}</Typography></TableCell>
                      <TableCell>{formatDate(member.last_payment_date)}</TableCell>
                      <TableCell align="right">{member.total_checkins || 0}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {!loading && visibleMembers.length === 0 && (
        <Card sx={{ mt: 2, borderRadius: 4 }}><CardContent><Typography color="text.secondary">No members match your search or filter.</Typography></CardContent></Card>
      )}
    </Box>
  );
}
