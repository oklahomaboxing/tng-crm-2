import React, { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Typography, Button, Table, TableHead,
  TableRow, TableCell, TableBody, Chip, TextField, CircularProgress, Alert
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function Sales() {
  const [sales, setSales] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSales() {
    try {
      setLoading(true);
      setError("");

      const res = await fetch(`${API}/api/sales`, { headers: authHeaders() });

      if (!res.ok) throw new Error("Could not load sales");

      const data = await res.json();
      setSales(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Something went wrong loading sales");
    } finally {
      setLoading(false);
    }
  }
async function syncCloverSales() {
  try {
    setLoading(true);
    setError("");

    const res = await fetch(`${API}/api/clover/sync-sales`, {
      method: "POST",
      headers: authHeaders(),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Could not sync Clover sales");
    }

    alert(`${data.message}\nSynced: ${data.synced}\nSkipped: ${data.skipped}`);
    await loadSales();
  } catch (err) {
    setError(err.message || "Something went wrong syncing sales");
  } finally {
    setLoading(false);
  }
}
  useEffect(() => {
    loadSales();
  }, []);

  const filteredSales = sales.filter((sale) => {
    const q = search.toLowerCase();
    return (
      (sale.member || "").toLowerCase().includes(q) ||
      (sale.rep || "").toLowerCase().includes(q) ||
      (sale.membership || "").toLowerCase().includes(q) ||
      (sale.payment_status || "").toLowerCase().includes(q)
    );
  });

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">Sales</Typography>
        <Button variant="contained" color="error" onClick={syncCloverSales}>
          Sync Clover Sales
        </Button>
      </Box>

      <TextField
        fullWidth
        label="Search sales by member, rep, membership, or status"
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
                  <TableCell>Member</TableCell>
                  <TableCell>Sales Rep</TableCell>
                  <TableCell>Membership</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Date</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {filteredSales.map((sale) => (
                  <TableRow key={sale.id}>
                    <TableCell>{sale.member}</TableCell>
                    <TableCell>{sale.rep}</TableCell>
                    <TableCell>{sale.membership}</TableCell>
                    <TableCell>${Number(sale.amount || 0).toFixed(2)}</TableCell>
                    <TableCell>
                      <Chip
                        color={sale.payment_status === "paid" ? "success" : "warning"}
                        label={sale.payment_status || "pending"}
                      />
                    </TableCell>
                    <TableCell>
                      {sale.sale_date ? new Date(sale.sale_date).toLocaleDateString() : ""}
                    </TableCell>
                  </TableRow>
                ))}

                {filteredSales.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6}>No sales found.</TableCell>
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