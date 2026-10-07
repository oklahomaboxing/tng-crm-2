import React from "react";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import BloodtypeRoundedIcon from "@mui/icons-material/BloodtypeRounded";
import ConfirmationNumberRoundedIcon from "@mui/icons-material/ConfirmationNumberRounded";
import StorefrontRoundedIcon from "@mui/icons-material/StorefrontRounded";
import PaymentsRoundedIcon from "@mui/icons-material/PaymentsRounded";
import FactCheckRoundedIcon from "@mui/icons-material/FactCheckRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import StadiumRoundedIcon from "@mui/icons-material/StadiumRounded";

const pages = [
  {
    label: "Fight Card",
    description: "Official bouts, bout order and fighter details.",
    tab: 1,
    icon: SportsMmaRoundedIcon,
    group: "Competition",
  },
  {
    label: "Matchmaking",
    description: "Auto-Match, manual matches and fight offers.",
    tab: 10,
    icon: AutoAwesomeRoundedIcon,
    group: "Competition",
  },
  {
    label: "Contracts",
    description: "Generate, send, track and manage fighter contracts.",
    tab: 2,
    icon: DescriptionRoundedIcon,
    group: "Competition",
  },
  {
    label: "Fighters",
    description: "Event roster, fighter readiness and logistics.",
    tab: 11,
    icon: GroupsRoundedIcon,
    group: "Operations",
  },
  {
    label: "Medicals",
    description: "Bloodwork and medical readiness.",
    tab: 5,
    icon: BloodtypeRoundedIcon,
    group: "Operations",
  },
  {
    label: "Compliance",
    description: "Promoter and matchmaker requirements.",
    tab: 3,
    icon: FactCheckRoundedIcon,
    group: "Operations",
  },
  {
    label: "Tickets",
    description: "Ticket prices, sellers, links, QR codes and sales.",
    tab: 9,
    icon: ConfirmationNumberRoundedIcon,
    group: "Revenue",
  },
  {
    label: "Sponsors & Vendors",
    description: "Sponsor pipeline, vendors and event revenue.",
    tab: 7,
    icon: StorefrontRoundedIcon,
    group: "Revenue",
  },
  {
    label: "Expenses",
    description: "Event fees, assessments and actual costs.",
    tab: 6,
    icon: PaymentsRoundedIcon,
    group: "Finance",
  },
  {
    label: "Fight Night",
    description: "Bout order, readiness and event-day operations.",
    tab: 12,
    icon: StadiumRoundedIcon,
    group: "Event Day",
  },
  {
    label: "Event Settings",
    description: "Venue, address and event configuration.",
    tab: 8,
    icon: SettingsRoundedIcon,
    group: "Settings",
  },
];

export default function EventHomeNavigation({ setTab }) {
  return (
    <Box>
      <Stack spacing={0.5} sx={{ mb: 2.5 }}>
        <Typography variant="h5" fontWeight={950}>
          Event Operations
        </Typography>

        <Typography color="text.secondary">
          Choose one area to work on. Each section opens as its own focused page.
        </Typography>
      </Stack>

      <Grid container spacing={2}>
        {pages.map((page) => {
          const Icon = page.icon;

          return (
            <Grid item xs={12} sm={6} lg={4} key={page.label}>
              <Card
                sx={{
                  height: "100%",
                  borderRadius: 4,
                  border: "1px solid",
                  borderColor: "divider",
                  boxShadow: "0 10px 30px rgba(15,23,42,.05)",
                  transition: "transform .18s ease, box-shadow .18s ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 16px 40px rgba(15,23,42,.09)",
                  },
                }}
              >
                <CardActionArea
                  onClick={() => setTab(page.tab)}
                  sx={{ height: "100%" }}
                >
                  <CardContent sx={{ p: 2.5, height: "100%" }}>
                    <Stack spacing={2} height="100%">
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="flex-start"
                        spacing={1}
                      >
                        <Box
                          sx={{
                            width: 48,
                            height: 48,
                            borderRadius: 3,
                            display: "grid",
                            placeItems: "center",
                            bgcolor: "rgba(215,25,32,.08)",
                            color: "error.main",
                          }}
                        >
                          <Icon />
                        </Box>

                        <Chip
                          size="small"
                          label={page.group}
                          variant="outlined"
                        />
                      </Stack>

                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" fontWeight={950}>
                          {page.label}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mt: 0.75 }}
                        >
                          {page.description}
                        </Typography>
                      </Box>

                      <Typography
                        variant="body2"
                        fontWeight={900}
                        color="error.main"
                      >
                        Open {page.label} ?
                      </Typography>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}
