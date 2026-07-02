import React from "react";
import { Card, CardContent, Typography } from "@mui/material";

export default function StatCard({
  title,
  value,
  subtitle = "",
  color = "inherit",
}) {
  return (
    <Card
      sx={{
        borderRadius: 3,
        boxShadow: "0 8px 20px rgba(0,0,0,.08)",
        height: "100%",
      }}
    >
      <CardContent>
        <Typography
          variant="body2"
          color="text.secondary"
          gutterBottom
        >
          {title}
        </Typography>

        <Typography
          variant="h4"
          fontWeight="bold"
          color={color}
        >
          {value}
        </Typography>

        {subtitle && (
          <Typography
            variant="caption"
            color="text.secondary"
          >
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}