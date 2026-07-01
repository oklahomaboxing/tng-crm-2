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

export default function Members() {
  const [members, setMembers] = useState([]);

  async function loadMembers() {
    const res = await fetch(`${API}/api/members`, {
      headers: authHeaders()
    });
    const data = await res.json();
    setMembers(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    loadMembers();
  }, []);

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

      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
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
              {members.map((member) => (
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

              {members.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>
                    No members yet. Create a sale or add a member next.
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