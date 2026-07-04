import React from "react";
import { Card, CardContent, Typography, Box, Chip } from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function MemberCard({ member }) {
  if (!member) return null;

  const photo =
    member.photo_url
      ? (member.photo_url.startsWith("http")
          ? member.photo_url
          : `${API}${member.photo_url}`)
      : null;

  return (
    <Card
      sx={{
        width: 430,
        borderRadius: 4,
        background: "#111",
        color: "white",
        overflow: "hidden",
        border: "3px solid #d71920",
      }}
    >
      <Box
        sx={{
          background: "#d71920",
          p: 2,
          textAlign: "center",
        }}
      >
        <Typography variant="h5" fontWeight="bold">
          TNG BOXING
        </Typography>

        <Typography>
          THE NEXT GENERATION
        </Typography>
      </Box>

      <CardContent>
        <Box
          sx={{
            display: "flex",
            gap: 3,
            alignItems: "center",
          }}
        >
          <Box
            sx={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              overflow: "hidden",
              background: "#333",
            }}
          >
            {photo ? (
              <img
                src={photo}
                alt=""
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                }}
              />
            ) : null}
          </Box>

          <Box>
            <Typography variant="h5" fontWeight="bold">
              {member.first_name} {member.last_name}
            </Typography>

            <Typography>
              {member.member_number}
            </Typography>

            <Typography>
              {member.membership_type}
            </Typography>

            <Chip
              color="success"
              label={member.membership_status || "ACTIVE"}
              sx={{ mt: 1 }}
            />
          </Box>
        </Box>

        <Box sx={{ mt: 4 }}>
          <Typography fontWeight="bold">
            {member.barcode}
          </Typography>

          <Typography>
            {member.qr_code}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}