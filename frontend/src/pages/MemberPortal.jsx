import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import FitnessCenterRoundedIcon from "@mui/icons-material/FitnessCenterRounded";
import QrCode2RoundedIcon from "@mui/icons-material/QrCode2Rounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import MemberHomeTrainer from "./MemberHomeTrainer.jsx";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
});

function Metric({ label, value, suffix = "" }) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 3 }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="h5" fontWeight={800}>
          {value ?? "â€”"}{value !== null && value !== undefined && value !== "" ? suffix : ""}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function MemberPortal({ onLogout }) {
  const [data, setData] = useState(null);

  const [profilePhotoUrl, setProfilePhotoUrl] = useState("");
  const [photoWorking, setPhotoWorking] = useState(false);
  const [scans, setScans] = useState([]);
  const [error, setError] = useState("");
  const [showTrainer, setShowTrainer] = useState(false);

  async function load() {
    setError("");
    try {
      const [profileRes, scansRes] = await Promise.all([
        fetch(`${API}/api/member/me`, { headers: authHeaders() }),
        fetch(`${API}/api/member/inbody/scans`, { headers: authHeaders() }),
      ]);
      const profile = await profileRes.json();
      const scanData = await scansRes.json();
      if (!profileRes.ok) throw new Error(profile.detail || "Unable to load member profile");
      if (!scansRes.ok) throw new Error(scanData.detail || "Unable to load InBody scans");
      setData(profile);
      setScans(Array.isArray(scanData) ? scanData : []);
    } catch (e) {
      setError(e.message || "Unable to load member portal");
    }
  }


  async function loadMemberProfilePhoto(photoPath) {
    if (!photoPath) {
      setProfilePhotoUrl("");
      return;
    }

    const token =
      localStorage.getItem("token");

    try {
      const response = await fetch(
        photoPath.startsWith("http")
          ? photoPath
          : `${API}${photoPath}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) return;

      const blob = await response.blob();
      const objectUrl =
        URL.createObjectURL(blob);

      setProfilePhotoUrl((current) => {
        if (current) {
          try {
            URL.revokeObjectURL(current);
          } catch (_) {}
        }

        return objectUrl;
      });
    } catch (err) {
      console.error(
        "Could not load member profile photo:",
        err
      );
    }
  }


  async function uploadMemberProfilePhoto(file) {
    if (!file) return;

    if (
      ![
        "image/jpeg",
        "image/png",
        "image/webp",
      ].includes(file.type)
    ) {
      window.alert(
        "Please choose a JPG, PNG, or WEBP image."
      );
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      window.alert(
        "Profile photo must be 5 MB or smaller."
      );
      return;
    }

    setPhotoWorking(true);

    try {
      const token =
        localStorage.getItem("token");

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API}/api/member/me/photo`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not upload profile photo."
        );
      }

      await loadMemberProfilePhoto(
        "/api/member/me/photo"
      );

      setData((current) => ({
        ...current,
        member: {
          ...current.member,
          photo_url:
            "/api/member/me/photo",
        },
      }));
    } catch (err) {
      window.alert(
        err.message ||
          "Could not upload profile photo."
      );
    } finally {
      setPhotoWorking(false);
    }
  }


  async function removeMemberProfilePhoto() {
    const confirmed =
      window.confirm(
        "Remove your profile photo?"
      );

    if (!confirmed) return;

    setPhotoWorking(true);

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/member/me/photo`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not remove profile photo."
        );
      }

      setProfilePhotoUrl((current) => {
        if (current) {
          try {
            URL.revokeObjectURL(current);
          } catch (_) {}
        }

        return "";
      });

      setData((current) => ({
        ...current,
        member: {
          ...current.member,
          photo_url: null,
        },
      }));
    } catch (err) {
      window.alert(
        err.message ||
          "Could not remove profile photo."
      );
    } finally {
      setPhotoWorking(false);
    }
  }


  useEffect(() => { load(); }, []);

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 5 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  useEffect(() => {
    const photoPath =
      data?.member?.photo_url;

    if (photoPath) {
      loadMemberProfilePhoto(photoPath);
    } else {
      setProfilePhotoUrl("");
    }
  }, [data?.member?.photo_url]);


  if (!data) {
    return <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}><CircularProgress /></Box>;
  }

  const m = data.member;
  const latest = data.inbody?.latest_scan;

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f6f7f9", pb: 8 }}>
      <Box sx={{ bgcolor: "#09090b", color: "white", py: 2 }}>
        <Container maxWidth="lg">
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Stack direction="row" spacing={2} alignItems="center">
              <Box sx={{ position: "relative" }}>
                <label
                  title="Change profile photo"
                  style={{
                    cursor: photoWorking
                      ? "not-allowed"
                      : "pointer",
                  }}
                >
                  <Avatar
                    src={profilePhotoUrl || undefined}
                    sx={{
                      width: 54,
                      height: 54,
                      border:
                        "2px solid rgba(255,255,255,.35)",
                    }}
                  >
                    {m.first_name?.[0]}
                    {m.last_name?.[0]}
                  </Avatar>

                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    disabled={photoWorking}
                    onChange={(e) => {
                      const file =
                        e.target.files?.[0];

                      if (file) {
                        uploadMemberProfilePhoto(
                          file
                        );
                      }

                      e.target.value = "";
                    }}
                    style={{
                      display: "none",
                    }}
                  />
                </label>

                {profilePhotoUrl && (
                  <button
                    type="button"
                    title="Remove profile photo"
                    disabled={photoWorking}
                    onClick={
                      removeMemberProfilePhoto
                    }
                    style={{
                      position: "absolute",
                      right: -6,
                      bottom: -5,
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      border:
                        "2px solid #09090b",
                      background: "#d71920",
                      color: "#fff",
                      fontSize: 14,
                      fontWeight: 900,
                      cursor: "pointer",
                    }}
                  >
                    ?
                  </button>
                )}
              </Box>
              <Box>
                <Typography fontWeight={900}>TNG MEMBER</Typography>
                <Typography variant="body2" sx={{ opacity: .75 }}>
                  {m.first_name} {m.last_name}
                </Typography>
              </Box>
            </Stack>
            <Button
              startIcon={<LogoutRoundedIcon />}
              color="inherit"
              onClick={() => {
                localStorage.removeItem("token");
                localStorage.removeItem("role");
                localStorage.removeItem("name");
                if (onLogout) onLogout();
                else window.location.reload();
              }}
            >
              Sign out
            </Button>
          </Stack>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ pt: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={7}>
            <Card sx={{ borderRadius: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
                  <Box>
                    <Typography variant="h4" fontWeight={900}>Welcome, {m.first_name}</Typography>
                    <Typography color="text.secondary">Your TNG Boxing member account</Typography>
                  </Box>
                  <Chip
                    label={(m.membership_status || "unknown").toUpperCase()}
                    color={m.membership_status === "active" ? "success" : "default"}
                    sx={{ fontWeight: 800 }}
                  />
                </Stack>
                <Divider sx={{ my: 3 }} />
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}><Metric label="Membership" value={m.membership_type || m.membership_level || "Member"} /></Grid>
                  <Grid item xs={12} sm={6}><Metric label="Total Check-ins" value={m.total_checkins ?? 0} /></Grid>
                  <Grid item xs={12} sm={6}><Metric label="Member #" value={m.member_number || "â€”"} /></Grid>
                  <Grid item xs={12} sm={6}><Metric label="Waiver" value={m.waiver_signed ? "Complete" : "Needed"} /></Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={5}>
            <Card sx={{ borderRadius: 4, height: "100%" }}>
              <CardContent sx={{ p: 3, textAlign: "center" }}>
                <QrCode2RoundedIcon sx={{ fontSize: 56 }} />
                <Typography variant="h6" fontWeight={900}>Digital Membership Card</Typography>
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                  Use your TNG member ID at check-in.
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {m.digital_member_id || m.barcode || m.member_number || "Not assigned"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            {!showTrainer ? (
              <Card
                sx={{
                  borderRadius: 4,
                  bgcolor: "#09090b",
                  color: "white",
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Stack
                    direction={{
                      xs: "column",
                      sm: "row",
                    }}
                    spacing={2}
                    alignItems={{
                      xs: "flex-start",
                      sm: "center",
                    }}
                    justifyContent="space-between"
                  >
                    <Stack
                      direction="row"
                      spacing={1.5}
                      alignItems="center"
                    >
                      <SportsMmaRoundedIcon
                        color="error"
                        sx={{ fontSize: 38 }}
                      />

                      <Box>
                        <Typography
                          variant="h5"
                          fontWeight={900}
                        >
                          Train at Home
                        </Typography>

                        <Typography
                          sx={{ color: "grey.400" }}
                        >
                          Simple TNGTrainer workouts for
                          shadowboxing, conditioning and
                          footwork.
                        </Typography>
                      </Box>
                    </Stack>

                    <Button
                      variant="contained"
                      color="error"
                      onClick={() => setShowTrainer(true)}
                      sx={{
                        fontWeight: 900,
                        whiteSpace: "nowrap",
                      }}
                    >
                      Open Trainer
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ) : (
              <Stack spacing={1.5}>
                <Button
                  onClick={() => setShowTrainer(false)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  Back to Member Account
                </Button>

                <MemberHomeTrainer />
              </Stack>
            )}
          </Grid>

          <Grid item xs={12}>
            <Card sx={{ borderRadius: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                  <FitnessCenterRoundedIcon color="error" />
                  <Typography variant="h5" fontWeight={900}>InBody</Typography>
                  <Chip
                    size="small"
                    label={data.inbody?.linked ? "CONNECTED" : "NOT CONNECTED"}
                    color={data.inbody?.linked ? "success" : "default"}
                  />
                </Stack>

                {!latest ? (
                  <Alert severity="info">
                    No InBody scans are attached to your TNG account yet.
                  </Alert>
                ) : (
                  <>
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      Latest scan: {new Date(latest.scan_date).toLocaleDateString()}
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} md={3}><Metric label="Weight" value={latest.weight} suffix=" lb" /></Grid>
                      <Grid item xs={6} md={3}><Metric label="Muscle Mass" value={latest.skeletal_muscle_mass} suffix=" lb" /></Grid>
                      <Grid item xs={6} md={3}><Metric label="Body Fat" value={latest.percent_body_fat} suffix="%" /></Grid>
                      <Grid item xs={6} md={3}><Metric label="InBody Score" value={latest.inbody_score} /></Grid>
                    </Grid>
                  </>
                )}

                {scans.length > 1 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    {scans.length} scans available. Progress charts are the next portal upgrade.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

