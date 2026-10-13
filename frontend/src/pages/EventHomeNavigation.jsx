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
  const groups = ["Competition", "Operations", "Revenue", "Finance", "Event Day", "Settings"];
  return <Box>
    <Typography component="h2" variant="h5" sx={{ mb: 1 }}>Your event, end to end.</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>Build the card, prepare the roster, manage the business and run fight night.</Typography>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0,1fr))", xl: "repeat(3,minmax(0,1fr))" }, gap: 2 }}>
      {groups.map(group => <Card key={group} sx={{ p: 2.5 }}>
        <Typography variant="overline" sx={{ fontWeight: 850, letterSpacing: ".12em", color: "text.secondary" }}>{group}</Typography>
        {pages.filter(page => page.group === group).map(page => {
          const Icon = page.icon;
          return <CardActionArea key={page.tab} onClick={() => setTab(page.tab)} sx={{ borderRadius: 2, mt: 1, p: 1.5 }}>
            <Stack direction="row" spacing={2} alignItems="center"><Icon sx={{ color: "primary.main" }} /><Box><Typography fontWeight={800}>{page.label}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>{page.description}</Typography></Box></Stack>
          </CardActionArea>;
        })}
      </Card>)}
    </Box>
  </Box>;
}
