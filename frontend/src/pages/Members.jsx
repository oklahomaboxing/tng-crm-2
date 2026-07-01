import React, { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  TextField,
  CircularProgress,
  Alert,
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function Members() {
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadMembers() {
    try {
      setLoading(true);
      setError("");

      const res = await fetch(`${API}/api/members`, {
        headers: authHeaders(),
      });

      if (!res.ok) {
        throw new Error("Could not load members");
      }

      const data = await res.json();
      setMembers(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Something went wrong loading members");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMembers();
  }, []);

  const filteredMembers = members.filter((member) => {
    const fullName = `${member.first_name || ""} ${member.last_name || ""}`.toLowerCase();
    const email = (member.email || "").toLowerCase();
    const phone = (member.phone || "").toLowerCase();
    const q = search.toLowerCase();

    return fullName.includes(q) || email.includes(q) || phone.includes(q);
  });

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          Members
        </Typography>

        <Button variant="contained" color="error">
          Add Member
        </Button>
      </Box>

      <TextField
        fullWidth
        label="Search members by name, email, or phone"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 3 }}
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress color="error" />
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {filteredMembers.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell>
                      {member.first_name} {member.last_name}
                    </TableCell>
                    <TableCell>{member.email}</TableCell>
                    <TableCell>{member.phone}</TableCell>
                    <TableCell>
                      <Chip
                        color={member.status === "active" ? "success" : "warning"}
                        label={member.status || "pending"}
                      />
                    </TableCell>
                    <TableCell>
                      {member.created_at
                        ? new Date(member.created_at).toLocaleDateString()
                        : ""}
                    </TableCell>
                  </TableRow>
                ))}

                {filteredMembers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      No members found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}