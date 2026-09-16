import React, { useEffect, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  LinearProgress,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import {
  ContentCopy,
  Person,
  PhotoCamera,
} from "@mui/icons-material";
import { API, authHeaders } from "../services/api";
import StatCard from "../components/StatCard.jsx";

export default function SalesRepDashboard() {
  const [data, setData] = useState(null);
  const [profile, setProfile] = useState(null);
  const [qr, setQr] = useState(null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [photoUploading, setPhotoUploading] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setError("");

      const [
        dashboardResponse,
        profileResponse,
        qrResponse,
        membersResponse,
      ] = await Promise.all([
        fetch(`${API}/api/my-dashboard`, {
          headers: authHeaders(),
        }),
        fetch(`${API}/api/reps/me`, {
          headers: authHeaders(),
        }),
        fetch(`${API}/api/reps/me/qr`, {
          headers: authHeaders(),
        }),
        fetch(`${API}/api/reps/me/members`, {
          headers: authHeaders(),
        }),
      ]);

      const dashboardJson = await dashboardResponse.json();
      const profileJson = await profileResponse.json();
      const qrJson = await qrResponse.json();
      const membersJson = await membersResponse.json();

      if (!dashboardResponse.ok) {
        throw new Error(
          dashboardJson.detail ||
            "Could not load your sales dashboard."
        );
      }

      if (!profileResponse.ok) {
        throw new Error(
          profileJson.detail ||
            "Could not load your sales profile."
        );
      }

      if (!qrResponse.ok) {
        throw new Error(
          qrJson.detail ||
            "Could not load your QR code."
        );
      }

      if (!membersResponse.ok) {
        throw new Error(
          membersJson.detail ||
            "Could not load your members."
        );
      }

      setData(dashboardJson);
      setProfile(profileJson);
      setQr(qrJson);
      setMembers(
        Array.isArray(membersJson)
          ? membersJson
          : []
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not load your sales profile."
      );
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function uploadPhoto(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    try {
      setPhotoUploading(true);
      setError("");
      setMessage("");

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API}/api/reps/me/photo`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem(
              "token"
            )}`,
          },
          body: formData,
        }
      );

      const json = await response.json();

      if (!response.ok) {
        throw new Error(
          json.detail ||
            "Could not upload profile photo."
        );
      }

      setMessage("Profile photo updated.");

      await load();
    } catch (err) {
      setError(
        err.message ||
          "Could not upload profile photo."
      );
    } finally {
      setPhotoUploading(false);
      event.target.value = "";
    }
  }

  async function copyReferralLink() {
    if (!qr?.url) return;

    try {
      await navigator.clipboard.writeText(qr.url);
      setMessage("Membership referral link copied.");
    } catch {
      setError("Could not copy referral link.");
    }
  }

  if (error && !data) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data || !profile || !qr) {
    return <Typography>Loading your sales profile...</Typography>;
  }

  const rate = Number(data.commission_rate || 0);
  const sales = Number(data.sales_this_month || 0);

  const progress =
    sales >= 20
      ? 100
      : sales >= 10
      ? (sales / 20) * 100
      : (sales / 10) * 100;

  const photoUrl = profile.photo_url
    ? `${API}${profile.photo_url}`
    : "";

  return (
    <Box>
      <Typography
        variant="h4"
        fontWeight="bold"
        sx={{ mb: 1 }}
      >
        My Sales
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mb: 3 }}
      >
        Your personal membership sales and commission dashboard.
      </Typography>

      {message && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setMessage("")}
        >
          {message}
        </Alert>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={() => setError("")}
        >
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ borderRadius: 3, height: "100%" }}>
            <CardContent>
              <Stack
                spacing={2}
                alignItems="center"
                textAlign="center"
              >
                <Avatar
                  src={photoUrl || undefined}
                  sx={{
                    width: 120,
                    height: 120,
                    fontSize: 42,
                  }}
                >
                  {!photoUrl &&
                    profile.name?.charAt(0)?.toUpperCase()}
                </Avatar>

                <Box>
                  <Typography
                    variant="h5"
                    fontWeight="bold"
                  >
                    {profile.name}
                  </Typography>

                  <Typography color="text.secondary">
                    Sales Rep
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    {profile.email}
                  </Typography>
                </Box>

                <Button
                  component="label"
                  variant="outlined"
                  startIcon={<PhotoCamera />}
                  disabled={photoUploading}
                  fullWidth
                >
                  {photoUploading
                    ? "Uploading..."
                    : "Upload Photo"}

                  <input
                    hidden
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={uploadPhoto}
                  />
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card sx={{ borderRadius: 3, height: "100%" }}>
            <CardContent>
              <Typography
                variant="h6"
                fontWeight="bold"
                sx={{ mb: 1 }}
              >
                My Membership QR Code
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Customers can scan this code to purchase a
                membership credited to you.
              </Typography>

              <Stack
                direction={{
                  xs: "column",
                  sm: "row",
                }}
                spacing={3}
                alignItems="center"
              >
                <Box
                  component="img"
                  src={`data:image/png;base64,${qr.qr_png_base64}`}
                  alt="My membership sales QR code"
                  sx={{
                    width: 210,
                    height: 210,
                    objectFit: "contain",
                    bgcolor: "white",
                    p: 1,
                    borderRadius: 2,
                  }}
                />

                <Box sx={{ flex: 1, width: "100%" }}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Referral Code
                  </Typography>

                  <Typography
                    fontWeight="bold"
                    sx={{ mb: 2 }}
                  >
                    {qr.slug}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Your Membership Link
                  </Typography>

                  <Typography
                    sx={{
                      wordBreak: "break-all",
                      mb: 2,
                    }}
                  >
                    {qr.url}
                  </Typography>

                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<ContentCopy />}
                    onClick={copyReferralLink}
                  >
                    Copy Link
                  </Button>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid
        container
        spacing={2}
        sx={{ mt: 1, mb: 3 }}
      >
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Membership Sales"
            value={sales}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Sales Revenue"
            value={`$${Number(
              data.revenue || 0
            ).toFixed(2)}`}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Commission Rate"
            value={`${(rate * 100).toFixed(0)}%`}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Commission Earned"
            value={`$${Number(
              data.commission_earned || 0
            ).toFixed(2)}`}
          />
        </Grid>
      </Grid>

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography
            variant="h6"
            fontWeight="bold"
          >
            Commission Progress
          </Typography>

          <Typography sx={{ mb: 1 }}>
            {data.next_tier}
          </Typography>

          <LinearProgress
            variant="determinate"
            value={Math.min(progress, 100)}
            sx={{
              height: 10,
              borderRadius: 5,
            }}
          />
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="h6"
                fontWeight="bold"
                sx={{ mb: 1 }}
              >
                My Members
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Only members signed up through your sales
                profile are shown here.
              </Typography>

              <Divider />

              <List>
                {members.map((member) => (
                  <ListItem
                    key={member.id}
                    divider
                  >
                    <ListItemAvatar>
                      <Avatar>
                        <Person />
                      </Avatar>
                    </ListItemAvatar>

                    <ListItemText
                      primary={member.name}
                      secondary={
                        <>
                          {member.membership && (
                            <>
                              {member.membership}
                              {" • "}
                            </>
                          )}

                          {member.membership_status ||
                            "Unknown status"}

                          {member.member_number
                            ? ` • ${member.member_number}`
                            : ""}
                        </>
                      }
                    />
                  </ListItem>
                ))}

                {members.length === 0 && (
                  <Typography
                    color="text.secondary"
                    sx={{ py: 3 }}
                  >
                    You have not signed up any members yet.
                  </Typography>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="h6"
                fontWeight="bold"
                sx={{ mb: 1 }}
              >
                My Recent Sales
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                Your most recent commission-eligible
                membership sales.
              </Typography>

              <Divider />

              <List>
                {(data.recent_sales || []).map(
                  (sale, index) => (
                    <ListItem
                      key={`${sale.member}-${index}`}
                      divider
                    >
                      <ListItemText
                        primary={`${sale.member} — ${
                          sale.membership
                        }`}
                        secondary={`$${Number(
                          sale.amount || 0
                        ).toFixed(2)} • ${
                          sale.date
                            ? new Date(
                                sale.date
                              ).toLocaleDateString()
                            : ""
                        }`}
                      />
                    </ListItem>
                  )
                )}

                {(data.recent_sales || []).length ===
                  0 && (
                  <Typography
                    color="text.secondary"
                    sx={{ py: 3 }}
                  >
                    No membership sales yet.
                  </Typography>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
