import React from "react";
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

export default function Members() {
  const members = [
    {
      id: 1,
      name: "John Smith",
      membership: "Unlimited Boxing",
      status: "Active",
      coach: "Coach Maurice",
      rep: "Mike",
      renewal: "08/01/2026"
    },
    {
      id: 2,
      name: "Sarah Johnson",
      membership: "Youth Boxing",
      status: "Pending",
      coach: "Coach Dora",
      rep: "Ashley",
      renewal: "07/15/2026"
    }
  ];

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          mb: 3
        }}
      >
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
                <TableCell>Membership</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Coach</TableCell>
                <TableCell>Sales Rep</TableCell>
                <TableCell>Renewal</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {members.map((member) => (
                <TableRow key={member.id}>
                  <TableCell>{member.name}</TableCell>
                  <TableCell>{member.membership}</TableCell>

                  <TableCell>
                    <Chip
                      color={member.status === "Active" ? "success" : "warning"}
                      label={member.status}
                    />
                  </TableCell>

                  <TableCell>{member.coach}</TableCell>
                  <TableCell>{member.rep}</TableCell>
                  <TableCell>{member.renewal}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
}