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
  Chip
} from "@mui/material";
import { API, authHeaders } from "../services/api";

export default function Sales() {
  const [sales, setSales] = useState([]);

  async function loadSales() {
    const res = await fetch(`${API}/api/sales`, {
      headers: authHeaders(),
    });

    const data = await res.json();
    setSales(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    loadSales();
  }, []);

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          mb: 3,
        }}
      >
        <Typography variant="h4" fontWeight="bold">
          Sales
        </Typography>

        <Button variant="contained" color="error">
          Add Sale
        </Button>
      </Box>

      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
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
              {sales.map((sale) => (
                <TableRow key={sale.id}>
                  <TableCell>{sale.member}</TableCell>
                  <TableCell>{sale.rep}</TableCell>
                  <TableCell>{sale.membership}</TableCell>
                  <TableCell>${Number(sale.amount).toFixed(2)}</TableCell>

                  <TableCell>
                    <Chip
                      color={
                        sale.payment_status === "paid"
                          ? "success"
                          : "warning"
                      }
                      label={sale.payment_status}
                    />
                  </TableCell>

                  <TableCell>
                    {sale.sale_date
                      ? new Date(sale.sale_date).toLocaleDateString()
                      : ""}
                  </TableCell>
                </TableRow>
              ))}

              {sales.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6}>
                    No sales have been recorded yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
}