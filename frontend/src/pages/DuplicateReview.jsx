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
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function DuplicateReview() {
  const [duplicates, setDuplicates] = useState([]);

  async function loadDuplicates() {
    const res = await fetch(`${API}/api/duplicates/members`, {
      headers: {
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
    });

    const data = await res.json();

    if (Array.isArray(data)) {
      setDuplicates(data);
    } else {
      setDuplicates([]);
    }
  }

  async function mergeMembers(keepId, mergeId) {
    if (!window.confirm("Merge these members?")) return;

    const res = await fetch(`${API}/api/duplicates/members/merge`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
      body: JSON.stringify({
        keep_id: keepId,
        merge_id: mergeId,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Merge failed");
      return;
    }

    alert("✅ Members merged successfully");

    loadDuplicates();
  }

  useEffect(() => {
    loadDuplicates();
  }, []);

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
        Duplicate Review
      </Typography>

      <Card>
        <CardContent>
          {duplicates.length === 0 ? (
            <Typography>No duplicate members found.</Typography>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Member A</TableCell>
                  <TableCell>Member B</TableCell>
                  <TableCell>Reason</TableCell>
                  <TableCell>Confidence</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {duplicates.map((d, index) => (
                  <TableRow key={index}>
                    <TableCell>{d.member_a.name}</TableCell>

                    <TableCell>{d.member_b.name}</TableCell>

                    <TableCell>{d.reasons.join(", ")}</TableCell>

                    <TableCell>{d.confidence}%</TableCell>

                    <TableCell>
                      <Button
                        variant="contained"
                        color="error"
                        onClick={() =>
                          mergeMembers(
                            d.member_a.id,
                            d.member_b.id
                          )
                        }
                      >
                        Merge
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}