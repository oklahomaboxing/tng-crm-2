import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
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
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [view, setView] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    customer_name: "",
    customer_email: "",
    customer_phone: "",
    product_id: "",
    quantity: 1,
    payment_status: "paid",
    payment_method: "clover",
  });

  useEffect(() => {
    Promise.all([loadSales(), loadProducts()]);
  }, []);

  async function loadSales() {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API}/api/sales`, { headers: authHeaders() });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load sales.");
      setSales(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not load sales.");
    } finally {
      setLoading(false);
    }
  }

  async function loadProducts() {
    try {
      const response = await fetch(`${API}/api/products`, { headers: authHeaders() });
      const data = await response.json();
      if (response.ok) setProducts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Could not load merchandise products", err);
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
      if (!response.ok) throw new Error(data.detail || "Clover sync failed.");
      await Promise.all([loadSales(), loadProducts()]);
    } catch (err) {
      setError(err.message || "Clover sync failed.");
    } finally {
      setLoading(false);
    }
  }

  const merchandiseProducts = useMemo(
    () => products.filter((product) => product.active && product.category === "merchandise"),
    [products]
  );

  const selectedProduct = merchandiseProducts.find(
    (product) => Number(product.id) === Number(form.product_id)
  );

  const checkoutTotal = Number(selectedProduct?.price || 0) * Number(form.quantity || 1);

  async function recordMerchandiseSale() {
    if (!form.customer_name.trim()) return setError("Customer name is required.");
    if (!form.product_id) return setError("Select a merchandise product.");
    if (Number(form.quantity) < 1) return setError("Quantity must be at least 1.");

    try {
      setSaving(true);
      setError("");
      const response = await fetch(`${API}/api/merchandise-sales`, {
        method: "POST",
        headers: {
          ...authHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...form,
          product_id: Number(form.product_id),
          quantity: Number(form.quantity),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not record merchandise sale.");

      setCheckoutOpen(false);
      setForm({
        customer_name: "",
        customer_email: "",
        customer_phone: "",
        product_id: "",
        quantity: 1,
        payment_status: "paid",
        payment_method: "clover",
      });
      await Promise.all([loadSales(), loadProducts()]);
    } catch (err) {
      setError(err.message || "Could not record merchandise sale.");
    } finally {
      setSaving(false);
    }
  }

  const filteredSales = sales.filter((sale) => {
    if (view === "merchandise" && sale.category !== "merchandise") return false;
    if (view === "memberships" && sale.category === "merchandise") return false;

    const query = search.trim().toLowerCase();
    if (!query) return true;

    return [sale.member, sale.rep, sale.product, sale.membership, sale.category, sale.payment_status]
      .some((value) => String(value || "").toLowerCase().includes(query));
  });

  const totalRevenue = filteredSales.reduce(
    (sum, sale) => sum + Number(sale.amount || 0), 0
  );

  return (
    <Box>
      <Box sx={{ display: "flex", flexDirection: { xs: "column", sm: "row" }, justifyContent: "space-between", gap: 2, mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            {role === "rep" ? "My Sales" : "Sales"}
          </Typography>
          <Typography color="text.secondary">
            {filteredSales.length} transactions · ${totalRevenue.toFixed(2)}
          </Typography>
        </Box>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button variant="contained" color="error" onClick={() => setCheckoutOpen(true)}>
            Sell Merchandise
          </Button>
          {role === "admin" && (
            <Button variant="outlined" color="error" onClick={syncClover}>
              Sync Clover
            </Button>
          )}
        </Stack>
      </Box>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Tabs value={view} onChange={(_, value) => setView(value)} variant="scrollable">
            <Tab value="all" label="All Sales" />
            <Tab value="memberships" label="Memberships" />
            <Tab value="merchandise" label="Merchandise" />
          </Tabs>
        </CardContent>
      </Card>

      <TextField fullWidth label="Search sales" value={search}
        onChange={(event) => setSearch(event.target.value)} sx={{ mb: 3 }} />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ borderRadius: 3 }}>
        <CardContent sx={{ p: { xs: 1, sm: 2 } }}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 5 }}>
              <CircularProgress color="error" />
            </Box>
          ) : (
            <TableContainer sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ minWidth: 860 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Customer</TableCell>
                    {role !== "rep" && <TableCell>Sales Rep</TableCell>}
                    <TableCell>Product</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Qty</TableCell>
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
                      <TableCell>{sale.product || sale.membership || "-"}</TableCell>
                      <TableCell>
                        <Chip size="small" color={sale.category === "merchandise" ? "error" : "default"}
                          label={sale.category === "merchandise" ? "Merchandise" : "Membership"} />
                      </TableCell>
                      <TableCell>{sale.quantity || 1}</TableCell>
                      <TableCell>${Number(sale.amount || 0).toFixed(2)}</TableCell>
                      <TableCell>
                        <Chip size="small" color={sale.payment_status === "paid" ? "success" : "warning"}
                          label={sale.payment_status || "pending"} />
                      </TableCell>
                      <TableCell>{sale.sale_date ? new Date(sale.sale_date).toLocaleDateString() : "-"}</TableCell>
                    </TableRow>
                  ))}
                  {filteredSales.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={role === "rep" ? 7 : 8}>No sales found for this account.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <Dialog open={checkoutOpen} onClose={() => !saving && setCheckoutOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle fontWeight="bold">Sell Merchandise</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Customer Name" fullWidth value={form.customer_name}
              onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
            <TextField label="Customer Email (optional)" type="email" fullWidth value={form.customer_email}
              onChange={(e) => setForm({ ...form, customer_email: e.target.value })} />
            <TextField label="Customer Phone (optional)" fullWidth value={form.customer_phone}
              onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} />

            <FormControl fullWidth>
              <InputLabel>Merchandise Product</InputLabel>
              <Select label="Merchandise Product" value={form.product_id}
                onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
                {merchandiseProducts.map((product) => (
                  <MenuItem key={product.id} value={product.id}
                    disabled={product.track_inventory && Number(product.stock_quantity || 0) <= 0}>
                    {product.name} — ${Number(product.price || 0).toFixed(2)}
                    {product.track_inventory ? ` (${product.stock_quantity || 0} in stock)` : ""}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField label="Quantity" type="number" inputProps={{ min: 1 }} fullWidth
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: Math.max(1, Number(e.target.value)) })} />

            <FormControl fullWidth>
              <InputLabel>Payment Method</InputLabel>
              <Select label="Payment Method" value={form.payment_method}
                onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
                <MenuItem value="clover">Clover</MenuItem>
                <MenuItem value="cash">Cash</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>

            <Typography variant="h5" fontWeight="bold">
              Total: ${checkoutTotal.toFixed(2)}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setCheckoutOpen(false)} disabled={saving}>Cancel</Button>
          <Button variant="contained" color="error" onClick={recordMerchandiseSale} disabled={saving}>
            {saving ? "Saving..." : "Complete Sale"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
