import React from "react";
import { Box, Typography, Button } from "@mui/material";

export default function PageHeader({
  title,
  subtitle,
  buttonText,
  onButtonClick,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        mb: 3,
      }}
    >
      <Box>
        <Typography variant="h4" fontWeight="bold">
          {title}
        </Typography>

        {subtitle && (
          <Typography color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </Box>

      {buttonText && (
        <Button
          variant="contained"
          color="error"
          onClick={onButtonClick}
        >
          {buttonText}
        </Button>
      )}
    </Box>
  );
}