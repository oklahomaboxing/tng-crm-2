import React, { useMemo, useState } from "react";
import {
  Box,
  Chip,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import TvRoundedIcon from "@mui/icons-material/TvRounded";
import FitnessCenterRoundedIcon from "@mui/icons-material/FitnessCenterRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import TrendingUpRoundedIcon from "@mui/icons-material/TrendingUpRounded";
import PsychologyRoundedIcon from "@mui/icons-material/PsychologyRounded";
import VideoLibraryRoundedIcon from "@mui/icons-material/VideoLibraryRounded";
import AssignmentRoundedIcon from "@mui/icons-material/AssignmentRounded";
import RestaurantRoundedIcon from "@mui/icons-material/RestaurantRounded";
import EmojiEventsRoundedIcon from "@mui/icons-material/EmojiEventsRounded";
import BuildRoundedIcon from "@mui/icons-material/BuildRounded";

import AcademyDashboard from "./AcademyDashboard.jsx";
import AITrainer from "../AITrainer.jsx";
import AIDisplay from "../AIDisplay.jsx";

function ComingSoon({ title, description }) {
  return (
    <Paper variant="outlined" sx={{ p: { xs: 2, md: 4 }, borderRadius: 3 }}>
      <Stack spacing={1.5}>
        <Chip label="Academy 2.0" color="error" sx={{ alignSelf: "flex-start" }} />
        <Typography variant="h4" fontWeight={950}>{title}</Typography>
        <Typography color="text.secondary">{description}</Typography>
        <Typography variant="body2" color="text.secondary">
          This section is reserved and connected to the Academy navigation so it can be developed without adding another main-dashboard page.
        </Typography>
      </Stack>
    </Paper>
  );
}

const academyItems = [
  { key: "overview", label: "Overview", icon: <DashboardRoundedIcon /> },
  { key: "ai-trainer", label: "AI Trainer", icon: <SportsMmaRoundedIcon /> },
  { key: "tv-display", label: "TV Display", icon: <TvRoundedIcon /> },
  { key: "practice-builder", label: "Practice Builder", icon: <BuildRoundedIcon /> },
  { key: "programs", label: "Training Programs", icon: <FitnessCenterRoundedIcon /> },
  { key: "classes", label: "Live Classes", icon: <GroupsRoundedIcon /> },
  { key: "progress", label: "Athlete Progress", icon: <TrendingUpRoundedIcon /> },
  { key: "boxing-iq", label: "Boxing IQ", icon: <PsychologyRoundedIcon /> },
  { key: "videos", label: "Video Library", icon: <VideoLibraryRoundedIcon /> },
  { key: "homework", label: "Homework", icon: <AssignmentRoundedIcon /> },
  { key: "nutrition", label: "Nutrition", icon: <RestaurantRoundedIcon /> },
  { key: "achievements", label: "Achievements", icon: <EmojiEventsRoundedIcon /> },
];

export default function TNGAcademy() {
  const [section, setSection] = useState("overview");

  const content = useMemo(() => {
    switch (section) {
      case "overview":
        return <AcademyDashboard onOpenSection={setSection} />;
      case "ai-trainer":
        return <AITrainer academyMode />;
      case "tv-display":
        return <AIDisplay academyMode />;
      case "practice-builder":
        return <ComingSoon title="Practice Builder" description="Build, save and assign complete practices by level, focus, rounds and class." />;
      case "programs":
        return <ComingSoon title="Training Programs" description="Create multi-week pathways for youth, beginners, competitors and private clients." />;
      case "classes":
        return <ComingSoon title="Live Classes" description="Start classes, attach checked-in athletes and record attendance and results." />;
      case "progress":
        return <ComingSoon title="Athlete Progress" description="Track sessions, skills, attendance, weight, goals and coach evaluations." />;
      case "boxing-iq":
        return <ComingSoon title="Boxing IQ" description="Interactive fight scenarios, defensive decisions, counters and advanced tactical development." />;
      case "videos":
        return <ComingSoon title="Video Library" description="Organize drills, technique lessons, class recordings and athlete film review." />;
      case "homework":
        return <ComingSoon title="Homework" description="Assign drills, videos, conditioning and boxing-IQ work to individual athletes or classes." />;
      case "nutrition":
        return <ComingSoon title="Nutrition" description="Connect athlete goals, weight tracking, meal guidance and NexGen Nutrition support." />;
      case "achievements":
        return <ComingSoon title="Achievements" description="Recognize attendance streaks, skill milestones, program completion and competition results." />;
      default:
        return <AcademyDashboard onOpenSection={setSection} />;
    }
  }, [section]);

  const activeLabel = academyItems.find((item) => item.key === section)?.label || "Overview";

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="h4" fontWeight={950}>TNG Academy</Typography>
        <Typography color="text.secondary">
          The complete training, coaching and athlete-development system inside TNG OS.
        </Typography>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "245px minmax(0, 1fr)" },
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
            <Typography fontWeight={950}>Academy Menu</Typography>
            <Typography variant="caption" color="text.secondary">{activeLabel}</Typography>
          </Box>
          <Divider />
          <List dense sx={{ p: 1 }}>
            {academyItems.map((item) => (
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
                <ListItemIcon sx={{ minWidth: 38, color: "inherit" }}>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontWeight: section === item.key ? 900 : 700 }}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        <Box sx={{ minWidth: 0 }}>{content}</Box>
      </Box>
    </Stack>
  );
}
