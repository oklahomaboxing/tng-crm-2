import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
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

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
}

function daysRemaining(value) {
  if (!value) return null;
  const end = new Date(value);
  if (Number.isNaN(end.getTime())) return null;
  return Math.ceil((end.getTime() - Date.now()) / 86400000);
}

function statusFor(member) {
  const days = daysRemaining(member.membership_end);
  if (member.membership_status === "inactive" || (days !== null && days < 0)) return "inactive";
  if (days !== null && days <= 7) return "expiring";
  return member.membership_status === "active" ? "active" : "pending";
}

function statusChip(member) {
  const status = statusFor(member);
  const map = {
    active: { label: "Active", color: "success" },
    expiring: { label: "Expiring Soon", color: "warning" },
    inactive: { label: "Inactive", color: "error" },
    pending: { label: "Pending", color: "default" },
  };
  return map[status];
}

export default function Members() {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("name");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedMember, setSelectedMember] = useState(null);

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

  const visibleMembers = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = members.filter((member) => {
      const searchable = [
        member.first_name,
        member.last_name,
        member.email,
        member.phone,
        member.member_number,
        member.membership_type,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch = !query || searchable.includes(query);
      const status = statusFor(member);
      const matchesFilter = filter === "all" || filter === status;
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

  const totals = useMemo(() => ({
    all: members.length,
    active: members.filter((m) => statusFor(m) === "active").length,
    expiring: members.filter((m) => statusFor(m) === "expiring").length,
    inactive: members.filter((m) => statusFor(m) === "inactive").length,
  }), [members]);

  if (selectedMember) {
    return (
      <MemberProfile
        member={selectedMember}
        onBack={() => {
          setSelectedMember(null);
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
          <Typography color="text.secondary">Membership, billing, attendance, and renewals</Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip label={`${totals.active} Active`} color="success" />
          <Chip label={`${totals.expiring} Expiring`} color="warning" />
          <Chip label={`${totals.inactive} Inactive`} color="error" />
        </Stack>
      </Stack>

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
                <MenuItem value="all">All ({totals.all})</MenuItem>
                <MenuItem value="active">Active ({totals.active})</MenuItem>
                <MenuItem value="expiring">Expiring ({totals.expiring})</MenuItem>
                <MenuItem value="inactive">Inactive ({totals.inactive})</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
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
            const days = daysRemaining(member.membership_end);
            const name = `${member.first_name || ""} ${member.last_name || ""}`.trim();
            return (
              <Card key={member.id} sx={{ borderRadius: 4 }}>
                <CardActionArea onClick={() => setSelectedMember(member)}>
                  <CardContent>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Avatar src={member.photo_url ? `${API}${member.photo_url}` : undefined} sx={{ width: 58, height: 58, bgcolor: "#111" }}>
                        {name.charAt(0).toUpperCase() || "?"}
                      </Avatar>
                      <Box flex={1} minWidth={0}>
                        <Typography fontWeight={900} noWrap>{name || "Member"}</Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>{member.member_number || "No member number"}</Typography>
                        <Typography variant="body2" noWrap>{member.membership_type || "Membership"}</Typography>
                      </Box>
                      <Chip size="small" label={chip.label} color={chip.color} />
                    </Stack>
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
                  const days = daysRemaining(member.membership_end);
                  const name = `${member.first_name || ""} ${member.last_name || ""}`.trim();
                  return (
                    <TableRow key={member.id} hover onClick={() => setSelectedMember(member)} sx={{ cursor: "pointer" }}>
                      <TableCell>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <Avatar src={member.photo_url ? `${API}${member.photo_url}` : undefined} sx={{ bgcolor: "#111" }}>{name.charAt(0).toUpperCase() || "?"}</Avatar>
                          <Box>
                            <Typography fontWeight={800}>{name || "Member"}</Typography>
                            <Typography variant="caption" color="text.secondary">{member.member_number || "—"}</Typography>
                          </Box>
                        </Stack>
                      </TableCell>
                      <TableCell>{member.membership_type || "—"}</TableCell>
                      <TableCell><Chip size="small" label={chip.label} color={chip.color} /></TableCell>
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
