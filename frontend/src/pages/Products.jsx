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
  TextField,
  Select,
  MenuItem,
  Checkbox,
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Products() {
  const [products, setProducts] = useState([]);

  async function loadProducts() {
    const res = await fetch(`${API}/api/products`, {
      headers: {
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
    });

    const data = await res.json();
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

    if (!res.ok) {
      alert(data.detail || "Could not save product");
      return;
    }

    alert("✅ Product saved");
    loadProducts();
  }

  function updateProduct(id, field, value) {
    setProducts((old) =>
      old.map((p) =>
        p.id === id ? { ...p, [field]: value } : p
      )
    );
  }

  useEffect(() => {
    loadProducts();
  }, []);

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
        Products Manager
      </Typography>

      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Product</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>Category</TableCell>
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
                  <TableCell>
                    <TextField
                      size="small"
                      value={p.name || ""}
                      onChange={(e) =>
                        updateProduct(p.id, "name", e.target.value)
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <TextField
                      size="small"
                      type="number"
                      value={p.price || 0}
                      onChange={(e) =>
                        updateProduct(p.id, "price", Number(e.target.value))
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <Select
                      size="small"
                      value={p.category || "other"}
                      onChange={(e) =>
                        updateProduct(p.id, "category", e.target.value)
                      }
                    >
                      <MenuItem value="membership">Membership</MenuItem>
                      <MenuItem value="event_ticket">Event Ticket</MenuItem>
                      <MenuItem value="nutrition">Nutrition</MenuItem>
                      <MenuItem value="merchandise">Merchandise</MenuItem>
                      <MenuItem value="private_lessons">Private Lessons</MenuItem>
                      <MenuItem value="registration">Registration</MenuItem>
                      <MenuItem value="other">Other</MenuItem>
                    </Select>
                  </TableCell>

                  <TableCell>
                    <Checkbox
                      checked={Boolean(p.is_membership)}
                      onChange={(e) =>
                        updateProduct(p.id, "is_membership", e.target.checked)
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <TextField
                      size="small"
                      type="number"
                      value={p.default_membership_months || 1}
                      onChange={(e) =>
                        updateProduct(
                          p.id,
                          "default_membership_months",
                          Number(e.target.value)
                        )
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <Checkbox
                      checked={Boolean(p.renews_monthly)}
                      onChange={(e) =>
                        updateProduct(p.id, "renews_monthly", e.target.checked)
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <Checkbox
                      checked={Boolean(p.autopay_allowed)}
                      onChange={(e) =>
                        updateProduct(p.id, "autopay_allowed", e.target.checked)
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <Checkbox
                      checked={Boolean(p.active)}
                      onChange={(e) =>
                        updateProduct(p.id, "active", e.target.checked)
                      }
                    />
                  </TableCell>

                  <TableCell>
                    <Button
                      variant="contained"
                      color="error"
                      onClick={() => saveProduct(p)}
                    >
                      💾 Save
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
}