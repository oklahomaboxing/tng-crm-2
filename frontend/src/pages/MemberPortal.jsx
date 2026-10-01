import { useEffect, useMemo, useState } from "react";

import { QRCodeCanvas } from "qrcode.react";
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

const authHeaders = (token = null) => ({
  Authorization: `Bearer ${token || localStorage.getItem("token")}`,
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

export default function MemberPortal({ onLogout, previewToken = null }) {
  const [data, setData] = useState(null);
  const [memberVideos, setMemberVideos] = useState([]);
  const [memberTransactions, setMemberTransactions] = useState([]);
  const [showMembershipCard, setShowMembershipCard] = useState(false);

  const [profilePhotoUrl, setProfilePhotoUrl] = useState("");
  const [photoWorking, setPhotoWorking] = useState(false);
  const [renewalWorking, setRenewalWorking] = useState(false);
  const [renewalOptions, setRenewalOptions] = useState([]);
  const [scans, setScans] = useState([]);
  const [error, setError] = useState("");
  const [showTrainer, setShowTrainer] = useState(false);
  const [fightVideos, setFightVideos] = useState([]);

  function memberToken() {
    return (
      previewToken ||
      sessionStorage.getItem("memberPreviewToken") ||
      localStorage.getItem("token")
    );
  }


  function memberDate(value) {
    if (!value) return "Not available";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Not available";
    }

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }


  async function renewMembership(productId) {
    if (!productId) {
      window.alert("Select a membership plan.");
      return;
    }

    setRenewalWorking(true);

    try {
      const response = await fetch(
        `${API}/api/member/me/renew-checkout`,
        {
          method: "POST",
          headers: {
            ...authHeaders(memberToken()),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            product_id: productId,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not start membership renewal."
        );
      }

      if (!body.checkout_url) {
        throw new Error(
          "Clover did not return a payment link."
        );
      }

      window.location.href = body.checkout_url;
    } catch (err) {
      window.alert(
        err.message ||
        "Could not start membership renewal."
      );

      setRenewalWorking(false);
    }
  }


  async function loadRenewalOptions() {
    try {
      const response = await fetch(
        `${API}/api/member/me/renewal-options`,
        {
          headers: authHeaders(memberToken()),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load membership options."
        );
      }

      setRenewalOptions(
        Array.isArray(body.options)
          ? body.options
          : []
      );
    } catch (err) {
      console.error(
        "Could not load renewal options:",
        err
      );
      setRenewalOptions([]);
    }
  }


  async function load() {
    setError("");
    try {
      const [profileRes, scansRes] = await Promise.all([
        fetch(`${API}/api/member/me`, { headers: authHeaders(memberToken()) }),
        fetch(`${API}/api/member/inbody/scans`, { headers: authHeaders(memberToken()) }),
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


  async function loadFightVideos() {
    try {
      const response = await fetch(
        `${API}/api/member/me/videos`,
        {
          headers: authHeaders(memberToken()),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load TNG Fight Library."
        );
      }

      setFightVideos(
        Array.isArray(body.videos)
          ? body.videos
          : []
      );
    } catch (err) {
      console.error(
        "Could not load member fight library:",
        err
      );
      setFightVideos([]);
    }
  }


  async function loadMemberProfilePhoto(photoPath) {
    if (!photoPath) {
      setProfilePhotoUrl("");
      return;
    }

    const token = memberToken();

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


  useEffect(() => {
    load();
    loadFightVideos();
    loadRenewalOptions();
  }, []);

  useEffect(() => {
    const photoPath =
      data?.member?.photo_url;

    if (photoPath) {
      loadMemberProfilePhoto(photoPath);
    } else {
      setProfilePhotoUrl("");
    }
  }, [data?.member?.photo_url]);




  async function loadMemberTransactions() {
    try {
      const response = await fetch(
        `${API}/api/member/me/transactions`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not load transaction history."
        );
      }

      setMemberTransactions(
        Array.isArray(body.transactions)
          ? body.transactions
          : []
      );
    } catch (err) {
      console.error(
        "Could not load Member transactions:",
        err
      );
      setMemberTransactions([]);
    }
  }

  useEffect(() => {
    loadMemberTransactions();
  }, []);

  async function loadMemberVideos() {
    try {
      const response = await fetch(
        `${API}/api/member/me/videos`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load TNG Video Library."
        );
      }

      setMemberVideos(
        Array.isArray(body.videos) ? body.videos : []
      );
    } catch (err) {
      console.error(
        "Could not load Member Portal videos:",
        err
      );
      setMemberVideos([]);
    }
  }

  useEffect(() => {
    loadMemberVideos();
  }, []);

  const hasActiveMembership =
    (data?.member?.membership_status || "").toLowerCase() === "active";


  useEffect(() => {
    if (!hasActiveMembership && showTrainer) {
      setShowTrainer(false);
    }
  }, [hasActiveMembership, showTrainer]);

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 5 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={load}>Retry</Button>
        <Button onClick={onLogout}>Sign out</Button>
      </Container>
    );
  }

  if (!data) {
    return <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}><CircularProgress /></Box>;
  }

  const m = data.member;
  const latest = data.inbody?.latest_scan;

  const memberCardCode =
    m.barcode ||
    (m.member_number || "").replaceAll("-", "") ||
    m.qr_code ||
    m.digital_member_id ||
    "";

  const memberCardName =
    `${m.first_name || ""} ${m.last_name || ""}`.trim() ||
    "TNG Member";

  const memberCardNumber =
    m.member_number ||
    m.digital_member_id ||
    m.barcode ||
    "Not assigned";

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
                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Membership"
                      value={
                        m.membership_type ||
                        m.membership_level ||
                        "Member"
                      }
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Membership Ends"
                      value={memberDate(m.membership_end)}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Last Membership Payment"
                      value={memberDate(m.last_payment_date)}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label={
                        m.autopay_enabled
                          ? "Next Billing Date"
                          : "Renewal Date"
                      }
                      value={memberDate(
                        m.next_billing_date ||
                        m.membership_end
                      )}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Total Check-ins"
                      value={m.total_checkins ?? 0}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Member #"
                      value={m.member_number || "?"}
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Waiver"
                      value={
                        m.waiver_signed
                          ? "Complete"
                          : "Needed"
                      }
                    />
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Metric
                      label="Billing Status"
                      value={
                        m.billing_status ||
                        m.membership_status ||
                        "Unknown"
                      }
                    />
                  </Grid>
                </Grid>

                <Divider sx={{ my: 3 }} />

                <Typography
                  variant="h6"
                  fontWeight={900}
                  sx={{ mb: 1.5 }}
                >
                  Choose Membership
                </Typography>

                {renewalOptions.length ? (
                  <Stack spacing={1.25}>
                    {renewalOptions.map((option) => (
                      <Button
                        key={option.id}
                        variant="contained"
                        size="large"
                        fullWidth
                        disabled={renewalWorking}
                        onClick={() =>
                          renewMembership(option.id)
                        }
                        sx={{
                          py: 1.4,
                          fontWeight: 900,
                          justifyContent: "space-between",
                        }}
                      >
                        <span>
                          {option.price === 150
                            ? "Month to Month"
                            : option.price === 300
                              ? "3 Months"
                              : option.price === 999
                                ? "Annual Membership"
                                : option.name}
                        </span>

                        <span>
                          ${Number(option.price).toFixed(0)}
                        </span>
                      </Button>
                    ))}
                  </Stack>
                ) : (
                  <Alert severity="info">
                    No online membership plans are currently
                    available.
                  </Alert>
                )}

                {renewalWorking ? (
                  <Typography
                    variant="body2"
                    sx={{
                      textAlign: "center",
                      mt: 1.25,
                      fontWeight: 700,
                    }}
                  >
                    Opening Clover...
                  </Typography>
                ) : null}

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    display: "block",
                    textAlign: "center",
                    mt: 1.25,
                  }}
                >
                  Secure Clover checkout for your
                  membership only. No registration fee.
                </Typography>

              </CardContent>
            </Card>
          </Grid>

                    <Grid item xs={12} md={5}>
            <Card
              sx={{
                borderRadius: 4,
                height: "100%",
                overflow: "hidden",
                color: "white",
                background:
                  "linear-gradient(135deg, #070707 0%, #171717 58%, #b71c1c 100%)",
                boxShadow: "0 18px 45px rgba(0,0,0,.22)",
                border: "1px solid rgba(255,255,255,.09)",
              }}
            >
              <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  sx={{ mb: 2.5 }}
                >
                  <Box>
                    <Typography
                      sx={{
                        fontWeight: 1000,
                        fontSize: 21,
                        letterSpacing: 1.2,
                        lineHeight: 1,
                      }}
                    >
                      TNG BOXING
                    </Typography>

                    <Typography
                      sx={{
                        mt: 0.45,
                        fontSize: 10,
                        fontWeight: 900,
                        letterSpacing: 2,
                        color: "rgba(255,255,255,.60)",
                      }}
                    >
                      DIGITAL MEMBERSHIP
                    </Typography>
                  </Box>

                  <Box
                    sx={{
                      px: 1.25,
                      py: 0.55,
                      borderRadius: 99,
                      fontSize: 11,
                      fontWeight: 1000,
                      letterSpacing: 1,
                      bgcolor: hasActiveMembership
                        ? "rgba(46,180,80,.22)"
                        : "rgba(239,35,60,.25)",
                      border: hasActiveMembership
                        ? "1px solid rgba(82,220,115,.55)"
                        : "1px solid rgba(255,85,100,.55)",
                    }}
                  >
                    {(m.membership_status || "UNKNOWN").toUpperCase()}
                  </Box>
                </Stack>

                <Stack
                  direction="row"
                  spacing={2}
                  alignItems="center"
                >
                  <Avatar
                    src={profilePhotoUrl || undefined}
                    sx={{
                      width: { xs: 66, sm: 78 },
                      height: { xs: 66, sm: 78 },
                      border: "3px solid rgba(255,255,255,.90)",
                      bgcolor: "#b71c1c",
                      fontWeight: 1000,
                      fontSize: 23,
                    }}
                  >
                    {m.first_name?.[0]}
                    {m.last_name?.[0]}
                  </Avatar>

                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Typography
                      sx={{
                        fontSize: { xs: 19, sm: 22 },
                        fontWeight: 1000,
                        lineHeight: 1.1,
                      }}
                    >
                      {memberCardName}
                    </Typography>

                    <Typography
                      sx={{
                        mt: 0.75,
                        color: "rgba(255,255,255,.70)",
                        fontWeight: 700,
                        fontSize: 13,
                      }}
                    >
                      {m.membership_type ||
                        m.membership_level ||
                        "TNG Member"}
                    </Typography>

                    <Typography
                      sx={{
                        mt: 0.55,
                        color: "rgba(255,255,255,.52)",
                        fontSize: 11,
                        fontWeight: 800,
                      }}
                    >
                      MEMBER #{memberCardNumber}
                    </Typography>
                  </Box>
                </Stack>

                <Box
                  sx={{
                    mt: 2.5,
                    p: 1.5,
                    bgcolor: "white",
                    borderRadius: 2.5,
                    display: "flex",
                    justifyContent: "center",
                  }}
                >
                  {memberCardCode ? (
                    <QRCodeCanvas
                      value={memberCardCode}
                      size={155}
                      level="H"
                      includeMargin
                    />
                  ) : (
                    <Box
                      sx={{
                        height: 155,
                        display: "grid",
                        placeItems: "center",
                        color: "#111",
                        fontWeight: 900,
                      }}
                    >
                      Check-in code not assigned
                    </Box>
                  )}
                </Box>

                <Typography
                  sx={{
                    mt: 1,
                    textAlign: "center",
                    fontSize: 10,
                    letterSpacing: 1.2,
                    fontWeight: 900,
                    color: "rgba(255,255,255,.58)",
                  }}
                >
                  PRESENT AT FRONT DESK FOR CHECK-IN
                </Typography>

                <Button
                  fullWidth
                  variant="contained"
                  disabled={!memberCardCode}
                  onClick={() => setShowMembershipCard(true)}
                  sx={{
                    mt: 2,
                    py: 1.25,
                    bgcolor: "#fff",
                    color: "#080808",
                    fontWeight: 1000,
                    borderRadius: 2,
                    "&:hover": {
                      bgcolor: "#eee",
                    },
                  }}
                >
                  OPEN FULL SCREEN SCAN
                </Button>
              </CardContent>
            </Card>
          </Grid>


          <Grid item xs={12}>
            <Card sx={{ borderRadius: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography
                  variant="h5"
                  fontWeight={900}
                >
                  Recent Transactions
                </Typography>

                <Typography
                  color="text.secondary"
                  sx={{ mt: 0.5, mb: 2.5 }}
                >
                  Payments connected to your TNG Boxing account.
                </Typography>

                {!memberTransactions.length ? (
                  <Box
                    sx={{
                      p: 3,
                      textAlign: "center",
                      border: "2px dashed #ddd",
                      borderRadius: 3,
                      color: "text.secondary",
                    }}
                  >
                    No transactions found.
                  </Box>
                ) : (
                  <Stack spacing={1.5}>
                    {memberTransactions
                      .slice(0, 10)
                      .map((transaction) => {
                        const status = String(
                          transaction.payment_status ||
                          transaction.transaction_status ||
                          "unknown"
                        ).toUpperCase();

                        const paid =
                          status === "PAID" ||
                          status === "APPROVED" ||
                          status === "COMPLETED" ||
                          status === "SUCCESS";

                        return (
                          <Box
                            key={transaction.id}
                            sx={{
                              border: "1px solid #e5e7eb",
                              borderRadius: 3,
                              p: 2,
                              bgcolor: "#fafafa",
                            }}
                          >
                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="flex-start"
                              spacing={2}
                            >
                              <Box sx={{ minWidth: 0 }}>
                                <Typography
                                  fontWeight={900}
                                >
                                  {transaction.product ||
                                    "TNG Payment"}
                                </Typography>

                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{ mt: 0.5 }}
                                >
                                  {transaction.sale_date
                                    ? new Date(
                                        transaction.sale_date
                                      ).toLocaleString()
                                    : "Date unavailable"}
                                </Typography>

                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ display: "block", mt: 0.5 }}
                                >
                                  {String(
                                    transaction.payment_method ||
                                    "Payment"
                                  ).toUpperCase()}
                                </Typography>

                                {transaction.clover_payment_id && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    sx={{ display: "block" }}
                                  >
                                    Ref:{" "}
                                    {String(
                                      transaction.clover_payment_id
                                    ).slice(-8)}
                                  </Typography>
                                )}
                              </Box>

                              <Box
                                sx={{
                                  textAlign: "right",
                                  flexShrink: 0,
                                }}
                              >
                                <Typography
                                  fontWeight={900}
                                  fontSize={18}
                                >
                                  $
                                  {Number(
                                    transaction.amount || 0
                                  ).toFixed(2)}
                                </Typography>

                                <Typography
                                  variant="caption"
                                  sx={{
                                    fontWeight: 900,
                                    color: paid
                                      ? "success.main"
                                      : "warning.main",
                                  }}
                                >
                                  {status}
                                </Typography>
                              </Box>
                            </Stack>
                          </Box>
                        );
                      })}
                  </Stack>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            {!hasActiveMembership ? (
              <Card
                sx={{
                  borderRadius: 4,
                  bgcolor: "#161616",
                  color: "white",
                  border: "1px solid",
                  borderColor: "error.main",
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
                        color="disabled"
                        sx={{ fontSize: 38 }}
                      />

                      <Box>
                        <Typography
                          variant="h5"
                          fontWeight={900}
                        >
                          TNGTrainer Locked
                        </Typography>

                        <Typography
                          sx={{ color: "grey.400" }}
                        >
                          An active TNG Boxing membership
                          is required to use TNGTrainer.
                        </Typography>
                      </Box>
                    </Stack>

                    <Button
                      variant="outlined"
                      color="error"
                      disabled
                      sx={{
                        fontWeight: 900,
                        whiteSpace: "nowrap",
                      }}
                    >
                      Choose a Plan Above
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ) : !showTrainer ? (
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
                      onClick={() =>
                        setShowTrainer(true)
                      }
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
                  onClick={() =>
                    setShowTrainer(false)
                  }
                  sx={{
                    alignSelf: "flex-start",
                  }}
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

      {showMembershipCard && (
        <Box
          onClick={() => setShowMembershipCard(false)}
          sx={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            bgcolor: "#050505",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            p: { xs: 1.5, sm: 3 },
          }}
        >
          <Box
            onClick={(e) => e.stopPropagation()}
            sx={{
              width: "100%",
              maxWidth: 520,
              textAlign: "center",
            }}
          >
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              sx={{ mb: 1.5 }}
            >
              <Box sx={{ textAlign: "left" }}>
                <Typography
                  sx={{
                    color: "white",
                    fontWeight: 1000,
                    fontSize: 20,
                  }}
                >
                  TNG BOXING
                </Typography>

                <Typography
                  sx={{
                    color: "rgba(255,255,255,.55)",
                    fontSize: 11,
                    fontWeight: 900,
                    letterSpacing: 1.5,
                  }}
                >
                  CHECK-IN CARD
                </Typography>
              </Box>

              <Button
                onClick={() => setShowMembershipCard(false)}
                sx={{
                  color: "white",
                  fontWeight: 900,
                }}
              >
                CLOSE
              </Button>
            </Stack>

            <Box
              sx={{
                bgcolor: "white",
                borderRadius: 4,
                px: { xs: 2, sm: 4 },
                py: { xs: 2.5, sm: 4 },
                boxShadow: "0 24px 80px rgba(0,0,0,.55)",
              }}
            >
              <Avatar
                src={profilePhotoUrl || undefined}
                sx={{
                  width: 72,
                  height: 72,
                  mx: "auto",
                  mb: 1.5,
                  bgcolor: "#b71c1c",
                  fontWeight: 1000,
                  fontSize: 23,
                }}
              >
                {m.first_name?.[0]}
                {m.last_name?.[0]}
              </Avatar>

              <Typography
                sx={{
                  fontSize: 24,
                  fontWeight: 1000,
                  color: "#090909",
                  lineHeight: 1.1,
                }}
              >
                {memberCardName}
              </Typography>

              <Typography
                sx={{
                  mt: 0.6,
                  mb: 1.4,
                  color: hasActiveMembership
                    ? "#197a35"
                    : "#b71c1c",
                  fontWeight: 1000,
                  letterSpacing: 1,
                }}
              >
                {(m.membership_status || "UNKNOWN").toUpperCase()}
              </Typography>

              <Box
                sx={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "center",
                  bgcolor: "#fff",
                }}
              >
                <QRCodeCanvas
                  value={memberCardCode}
                  size={340}
                  level="H"
                  includeMargin
                  style={{
                    width: "min(78vw, 340px)",
                    height: "auto",
                  }}
                />
              </Box>

              <Typography
                sx={{
                  mt: 1,
                  color: "#111",
                  fontWeight: 1000,
                  fontSize: 16,
                }}
              >
                MEMBER #{memberCardNumber}
              </Typography>

              <Typography
                sx={{
                  mt: 0.6,
                  color: "#666",
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Hold this screen in front of the check-in scanner
              </Typography>
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  );
}

