import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Products() {
  const [products, setProducts] = useState([]);
  const [error, setError] = useState("");
  const [newProductOpen, setNewProductOpen] = useState(false);
  const [newProduct, setNewProduct] = useState({
    name: "",
    price: 0,
    category: "merchandise",
    sku: "",
    stock_quantity: 0,
    track_inventory: true,
    active: true,
  });

  async function loadProducts() {
    const res = await fetch(`${API}/api/products`, {
      headers: { Authorization: "Bearer " + localStorage.getItem("token") },
    });
    const data = await res.json();
    if (!res.ok) return setError(data.detail || "Could not load products");
    setProducts(Array.isArray(data) ? data : []);
  }

  async function saveProduct(product) {
    const res = await fetch(`${API}/api/products/${product.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
      body: JSON.stringify(product),
    });
    const data = await res.json();
    if (!res.ok) return setError(data.detail || "Could not save product");
    await loadProducts();
  }

  async function createProduct() {
    const res = await fetch(`${API}/api/products`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
      body: JSON.stringify(newProduct),
    });
    const data = await res.json();
    if (!res.ok) return setError(data.detail || "Could not create product");

    setNewProductOpen(false);
    setNewProduct({
      name: "", price: 0, category: "merchandise", sku: "",
      stock_quantity: 0, track_inventory: true, active: true,
    });
    await loadProducts();
  }

  function updateProduct(id, field, value) {
    setProducts((old) => old.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  }

  useEffect(() => { loadProducts(); }, []);

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 2, mb: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Products Manager</Typography>
          <Typography color="text.secondary">Memberships, tickets, nutrition, and merchandise inventory</Typography>
        </Box>
        <Button variant="contained" color="error" onClick={() => setNewProductOpen(true)}>
          Add Product
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ borderRadius: 3 }}>
        <CardContent sx={{ p: { xs: 1, sm: 2 } }}>
          <TableContainer sx={{ overflowX: "auto" }}>
            <Table size="small" sx={{ minWidth: 1250 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Product</TableCell>
                  <TableCell>Price</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>SKU</TableCell>
                  <TableCell>Stock</TableCell>
                  <TableCell>Track</TableCell>
                  <TableCell>Membership</TableCell>
                  <TableCell>Months</TableCell>
                  <TableCell>Renews</TableCell>
                  <TableCell>AutoPay</TableCell>
                  <TableCell>Active</TableCell>
                  <TableCell>Save</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {products.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell><TextField size="small" value={p.name || ""} onChange={(e) => updateProduct(p.id, "name", e.target.value)} /></TableCell>
                    <TableCell><TextField size="small" type="number" value={p.price || 0} onChange={(e) => updateProduct(p.id, "price", Number(e.target.value))} /></TableCell>
                    <TableCell>
                      <Select size="small" value={p.category || "other"} onChange={(e) => updateProduct(p.id, "category", e.target.value)}>
                        <MenuItem value="membership">Membership</MenuItem>
                        <MenuItem value="event_ticket">Event Ticket</MenuItem>
                        <MenuItem value="nutrition">Nutrition</MenuItem>
                        <MenuItem value="merchandise">Merchandise</MenuItem>
                        <MenuItem value="private_lessons">Private Lessons</MenuItem>
                        <MenuItem value="registration">Registration</MenuItem>
                        <MenuItem value="other">Other</MenuItem>
                      </Select>
                    </TableCell>
                    <TableCell><TextField size="small" value={p.sku || ""} onChange={(e) => updateProduct(p.id, "sku", e.target.value)} /></TableCell>
                    <TableCell><TextField size="small" type="number" value={p.stock_quantity ?? 0} onChange={(e) => updateProduct(p.id, "stock_quantity", Number(e.target.value))} disabled={!p.track_inventory} /></TableCell>
                    <TableCell><Checkbox checked={Boolean(p.track_inventory)} onChange={(e) => updateProduct(p.id, "track_inventory", e.target.checked)} /></TableCell>
                    <TableCell><Checkbox checked={Boolean(p.is_membership)} onChange={(e) => updateProduct(p.id, "is_membership", e.target.checked)} /></TableCell>
                    <TableCell><TextField size="small" type="number" value={p.default_membership_months || 1} onChange={(e) => updateProduct(p.id, "default_membership_months", Number(e.target.value))} /></TableCell>
                    <TableCell><Checkbox checked={Boolean(p.renews_monthly)} onChange={(e) => updateProduct(p.id, "renews_monthly", e.target.checked)} /></TableCell>
                    <TableCell><Checkbox checked={Boolean(p.autopay_allowed)} onChange={(e) => updateProduct(p.id, "autopay_allowed", e.target.checked)} /></TableCell>
                    <TableCell><Checkbox checked={Boolean(p.active)} onChange={(e) => updateProduct(p.id, "active", e.target.checked)} /></TableCell>
                    <TableCell><Button variant="contained" color="error" onClick={() => saveProduct(p)}>Save</Button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={newProductOpen} onClose={() => setNewProductOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle fontWeight="bold">Add Product</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Product Name" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} />
            <TextField label="Price" type="number" value={newProduct.price} onChange={(e) => setNewProduct({ ...newProduct, price: Number(e.target.value) })} />
            <Select value={newProduct.category} onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}>
              <MenuItem value="merchandise">Merchandise</MenuItem>
              <MenuItem value="membership">Membership</MenuItem>
              <MenuItem value="nutrition">Nutrition</MenuItem>
              <MenuItem value="private_lessons">Private Lessons</MenuItem>
              <MenuItem value="registration">Registration</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </Select>
            <TextField label="SKU (optional)" value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} />
            <TextField label="Starting Stock" type="number" value={newProduct.stock_quantity} onChange={(e) => setNewProduct({ ...newProduct, stock_quantity: Number(e.target.value) })} />
            <Box><Checkbox checked={newProduct.track_inventory} onChange={(e) => setNewProduct({ ...newProduct, track_inventory: e.target.checked })} /> Track inventory</Box>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setNewProductOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={createProduct}>Create Product</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
