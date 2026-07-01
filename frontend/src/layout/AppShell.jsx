import React from "react";
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Typography,
  AppBar,
  Toolbar,
  Button,
} from "@mui/material";

const pages = ["Dashboard", "Members", "Sales", "Sales Reps", "QR Referrals", "Clover", "Reports"];

export default function AppShell({ page, setPage, children, onLogout }) {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#f5f5f7" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: 240,
          "& .MuiDrawer-paper": {
            width: 240,
            bgcolor: "#0b0b0f",
            color: "white",
            p: 2,
          },
        }}
      >
        <Typography variant="h5" fontWeight="bold" sx={{ mb: 3 }}>
          🥊 TNG CRM
        </Typography>

        <List>
          {pages.map((item) => (
            <ListItemButton
              key={item}
              onClick={() => setPage(item)}
              sx={{
                borderRadius: 2,
                mb: 1,
                bgcolor: page === item ? "#d71920" : "transparent",
                "&:hover": { bgcolor: "#d71920" },
              }}
            >
              <ListItemText primary={item} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box sx={{ flex: 1 }}>
        <AppBar position="static" elevation={0} sx={{ bgcolor: "white", color: "#111" }}>
          <Toolbar sx={{ justifyContent: "space-between" }}>
            <Box>
              <Typography variant="h5" fontWeight="bold">
                {page}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                TNG Boxing sales and commission command center
              </Typography>
            </Box>

            <Button variant="contained" color="error" onClick={onLogout}>
              Logout
            </Button>
          </Toolbar>
        </AppBar>

        <Box sx={{ p: 3 }}>{children}</Box>
      </Box>
    </Box>
  );
}