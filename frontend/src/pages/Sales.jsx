import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function Sales() {
  const role = localStorage.getItem("role") || "rep";
  const [sales, setSales] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadSales();
  }, []);

  async function loadSales() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API}/api/sales`, {
        headers: authHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load sales.");
      }

      setSales(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not load sales.");
    } finally {
      setLoading(false);
    }
  }

  async function syncClover() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API}/api/clover/sync-all`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Clover sync failed.");
      }

      await loadSales();
    } catch (err) {
      setError(err.message || "Clover sync failed.");
    } finally {
      setLoading(false);
    }
  }

  const filteredSales = sales.filter((sale) => {
    const query = search.trim().toLowerCase();

    if (!query) return true;

    return [
      sale.member,
      sale.rep,
      sale.membership,
      sale.payment_status,
    ].some((value) => (value || "").toLowerCase().includes(query));
  });

  const totalRevenue = filteredSales.reduce(
    (sum, sale) => sum + Number(sale.amount || 0),
    0
  );

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          justifyContent: "space-between",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h4" fontWeight="bold">
            {role === "rep" ? "My Sales" : "Sales"}
          </Typography>
          <Typography color="text.secondary">
            {filteredSales.length} transactions · ${totalRevenue.toFixed(2)}
          </Typography>
        </Box>

        {role === "admin" && (
          <Button variant="contained" color="error" onClick={syncClover}>
            Sync Clover
          </Button>
        )}
      </Box>

      <TextField
        fullWidth
        label="Search sales"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        sx={{ mb: 3 }}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Card sx={{ borderRadius: 3 }}>
        <CardContent sx={{ p: { xs: 1, sm: 2 } }}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 5 }}>
              <CircularProgress color="error" />
            </Box>
          ) : (
            <TableContainer sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ minWidth: 760 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Member</TableCell>
                    {role !== "rep" && <TableCell>Sales Rep</TableCell>}
                    <TableCell>Membership</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Date</TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {filteredSales.map((sale) => (
                    <TableRow key={sale.id} hover>
                      <TableCell>{sale.member || "-"}</TableCell>
                      {role !== "rep" && <TableCell>{sale.rep || "-"}</TableCell>}
                      <TableCell>{sale.membership || "-"}</TableCell>
                      <TableCell>${Number(sale.amount || 0).toFixed(2)}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={sale.payment_status === "paid" ? "success" : "warning"}
                          label={sale.payment_status || "pending"}
                        />
                      </TableCell>
                      <TableCell>
                        {sale.sale_date
                          ? new Date(sale.sale_date).toLocaleDateString()
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}

                  {filteredSales.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={role === "rep" ? 5 : 6}>
                        No sales found for this account.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
