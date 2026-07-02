import React, { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Typography, Table, TableHead,
  TableRow, TableCell, TableBody, Chip, TextField,
  CircularProgress, Alert
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadLeads() {
    try {
      setLoading(true);
      setError("");

      const res = await fetch(`${API}/api/leads`, {
        headers: authHeaders(),
      });

      if (!res.ok) throw new Error("Could not load leads");

      const data = await res.json();
      setLeads(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Something went wrong loading leads");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLeads();
  }, []);

  const filtered = leads.filter((lead) => {
    const q = search.toLowerCase();
    return (
      `${lead.first_name || ""} ${lead.last_name || ""}`.toLowerCase().includes(q) ||
      (lead.email || "").toLowerCase().includes(q) ||
      (lead.phone || "").toLowerCase().includes(q) ||
      (lead.rep || "").toLowerCase().includes(q) ||
      (lead.membership || "").toLowerCase().includes(q)
    );
  });

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 3 }}>
        Leads
      </Typography>

      <TextField
        fullWidth
        label="Search leads by name, email, phone, rep, or membership"
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
                  <TableCell>Phone</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Membership</TableCell>
                  <TableCell>Rep</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {filtered.map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell>{lead.first_name} {lead.last_name}</TableCell>
                    <TableCell>{lead.phone}</TableCell>
                    <TableCell>{lead.email}</TableCell>
                    <TableCell>{lead.membership}</TableCell>
                    <TableCell>{lead.rep}</TableCell>
                    <TableCell>
                      <Chip
                        color={lead.status === "new" ? "warning" : "success"}
                        label={lead.status || "new"}
                      />
                    </TableCell>
                    <TableCell>
                      {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : ""}
                    </TableCell>
                  </TableRow>
                ))}

                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7}>No leads found.</TableCell>
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