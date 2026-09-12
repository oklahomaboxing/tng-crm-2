import React, { useMemo, useState } from "react";
import {
  Box,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import TvRoundedIcon from "@mui/icons-material/TvRounded";

import AITrainer from "../AITrainer.jsx";
import AIDisplay from "../AIDisplay.jsx";

const trainerItems = [
  {
    key: "ai-trainer",
    label: "AI Trainer",
    icon: <SportsMmaRoundedIcon />,
  },
  {
    key: "tv-display",
    label: "TV Display",
    icon: <TvRoundedIcon />,
  },
];

export default function TNGAcademy() {
  const [section, setSection] = useState("ai-trainer");

  const content = useMemo(() => {
    switch (section) {
      case "tv-display":
        return <AIDisplay academyMode />;

      case "ai-trainer":
      default:
        return <AITrainer academyMode />;
    }
  }, [section]);

  const activeLabel =
    trainerItems.find((item) => item.key === section)?.label ||
    "AI Trainer";

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="h4" fontWeight={950}>
          TNGTrainer
        </Typography>

        <Typography color="text.secondary">
          AI-powered boxing training and live TV display.
        </Typography>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            lg: "220px minmax(0, 1fr)",
          },
          gap: 2.5,
          alignItems: "start",
        }}
      >
        <Paper
          variant="outlined"
          sx={{
            borderRadius: 3,
            overflow: "hidden",
            position: { lg: "sticky" },
            top: { lg: 16 },
          }}
        >
          <Box sx={{ px: 2, py: 1.75 }}>
            <Typography fontWeight={950}>
              TNGTrainer
            </Typography>

            <Typography
              variant="caption"
              color="text.secondary"
            >
              {activeLabel}
            </Typography>
          </Box>

          <Divider />

          <List dense sx={{ p: 1 }}>
            {trainerItems.map((item) => (
              <ListItemButton
                key={item.key}
                selected={section === item.key}
                onClick={() => setSection(item.key)}
                sx={{
                  borderRadius: 2,
                  mb: 0.35,
                  "&.Mui-selected": {
                    bgcolor: "rgba(215,25,32,.10)",
                    color: "error.main",
                  },
                  "&.Mui-selected:hover": {
                    bgcolor: "rgba(215,25,32,.14)",
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 38,
                    color: "inherit",
                  }}
                >
                  {item.icon}
                </ListItemIcon>

                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontWeight:
                      section === item.key ? 900 : 700,
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        <Box sx={{ minWidth: 0 }}>
          {content}
        </Box>
      </Box>
    </Stack>
  );
}
