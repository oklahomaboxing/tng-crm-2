import React, { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const emptyForm = {
  submitted_by_role: "boxer",
  submitted_by_name: "",
  submitted_by_phone: "",
  submitted_by_email: "",

  boxrec_id: "",
  legal_name: "",
  pro_record: "",

  available_weight_min: "",
  available_weight_max: "",

  stance: "",
  gym: "",

  city: "",
  state: "",
  country: "USA",

  phone: "",
  email: "",

  instagram: "",
  facebook: "",
  tiktok: "",
  twitter: "",
};

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed) ? parsed : null;
}

export default function FighterRegistration() {
  const [form, setForm] = useState(emptyForm);
  const [working, setWorking] = useState(false);
  const [done, setDone] = useState(false);
  const [message, setMessage] = useState("");

  function set(name, value) {
    setForm((old) => ({
      ...old,
      [name]: value,
    }));
  }

  function openBoxRec() {
    const id = (form.boxrec_id || "").trim();

    if (!id) {
      setMessage("Enter the BoxRec ID first.");
      return;
    }

    const url =
      `https://boxrec.com/en/box-pro/${encodeURIComponent(id)}`;

    const popup = window.open(
      url,
      "tngBoxRec",
      "popup=yes,width=1050,height=800,resizable=yes,scrollbars=yes"
    );

    if (!popup) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }

  async function submit() {
    setMessage("");

    if (!form.legal_name.trim()) {
      setMessage("Fighter name is required.");
      return;
    }

    const low = numberOrNull(form.available_weight_min);
    const high = numberOrNull(form.available_weight_max);

    if (
      low !== null &&
      high !== null &&
      (low < 80 || high > 400)
    ) {
      setMessage("Check the fighter's available weight range.");
      return;
    }

    setWorking(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/register-fighter`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...form,
            boxrec_id: form.boxrec_id.trim(),
            legal_name: form.legal_name.trim(),
            available_weight_min: low,
            available_weight_max: high,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not submit fighter"
        );
      }

      setDone(true);
      setMessage(data.message || "Fighter submitted.");
    } catch (error) {
      setMessage(
        error.message || "Could not submit fighter"
      );
    } finally {
      setWorking(false);
    }
  }

  if (done) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "#09090b",
          display: "grid",
          placeItems: "center",
          p: 2,
        }}
      >
        <Card sx={{ width: "100%", maxWidth: 600 }}>
          <CardContent sx={{ p: 4, textAlign: "center" }}>
            <SportsMmaRoundedIcon
              sx={{ fontSize: 64, color: "#d71920" }}
            />

            <Typography
              variant="h4"
              fontWeight={950}
              sx={{ mt: 1 }}
            >
              Fighter Submitted
            </Typography>

            <Alert severity="success" sx={{ my: 3 }}>
              {message}
            </Alert>

            <Button
              variant="contained"
              onClick={() => {
                setForm(emptyForm);
                setDone(false);
                setMessage("");
              }}
            >
              Register Another Fighter
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#09090b",
        py: 4,
        px: 2,
      }}
    >
      <Card
        sx={{
          width: "100%",
          maxWidth: 800,
          mx: "auto",
        }}
      >
        <CardContent sx={{ p: { xs: 2.5, sm: 4 } }}>
          <Stack spacing={3}>
            <Box>
              <Typography
                variant="h4"
                fontWeight={950}
              >
                TNG Fighter Registration
              </Typography>

              <Typography color="text.secondary">
                Submit a professional fighter for TNG matchmaking.
              </Typography>
            </Box>

            {message && (
              <Alert severity="info">
                {message}
              </Alert>
            )}

            <Box>
              <Typography
                variant="subtitle1"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Who is submitting?
              </Typography>

              <FormControl fullWidth>
                <InputLabel>I am a</InputLabel>

                <Select
                  value={form.submitted_by_role}
                  label="I am a"
                  onChange={(e) =>
                    set("submitted_by_role", e.target.value)
                  }
                >
                  <MenuItem value="boxer">Boxer</MenuItem>
                  <MenuItem value="coach">Coach</MenuItem>
                  <MenuItem value="manager">Manager</MenuItem>
                  <MenuItem value="matchmaker">
                    Matchmaker
                  </MenuItem>
                </Select>
              </FormControl>
            </Box>

            {form.submitted_by_role !== "boxer" && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Your Name"
                    value={form.submitted_by_name}
                    onChange={(e) =>
                      set("submitted_by_name", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Your Phone"
                    value={form.submitted_by_phone}
                    onChange={(e) =>
                      set("submitted_by_phone", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    type="email"
                    label="Your Email"
                    value={form.submitted_by_email}
                    onChange={(e) =>
                      set("submitted_by_email", e.target.value)
                    }
                  />
                </Grid>
              </Grid>
            )}

            <Box>
              <Typography
                variant="subtitle1"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Fighter
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    label="BoxRec ID"
                    helperText="Enter the ID, then open BoxRec to review the athlete."
                    value={form.boxrec_id}
                    onChange={(e) =>
                      set(
                        "boxrec_id",
                        e.target.value.replace(/[^0-9]/g, "")
                      )
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={openBoxRec}
                    disabled={!form.boxrec_id}
                    sx={{ minHeight: 56 }}
                  >
                    Open BoxRec
                  </Button>
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    required
                    label="Fighter Name"
                    value={form.legal_name}
                    onChange={(e) =>
                      set("legal_name", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Pro Record"
                    placeholder="8-2-0"
                    value={form.pro_record}
                    onChange={(e) =>
                      set("pro_record", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Low Weight"
                    value={form.available_weight_min}
                    onChange={(e) =>
                      set(
                        "available_weight_min",
                        e.target.value
                      )
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="High Weight"
                    value={form.available_weight_max}
                    onChange={(e) =>
                      set(
                        "available_weight_max",
                        e.target.value
                      )
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Stance</InputLabel>

                    <Select
                      value={form.stance}
                      label="Stance"
                      onChange={(e) =>
                        set("stance", e.target.value)
                      }
                    >
                      <MenuItem value="">Unknown</MenuItem>
                      <MenuItem value="orthodox">
                        Orthodox
                      </MenuItem>
                      <MenuItem value="southpaw">
                        Southpaw
                      </MenuItem>
                      <MenuItem value="switch">
                        Switch
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Gym"
                    value={form.gym}
                    onChange={(e) =>
                      set("gym", e.target.value)
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Box>
              <Typography
                variant="subtitle1"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Fighter Contact
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={form.phone}
                    onChange={(e) =>
                      set("phone", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="email"
                    label="Email"
                    value={form.email}
                    onChange={(e) =>
                      set("email", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Instagram"
                    placeholder="@fighter"
                    value={form.instagram}
                    onChange={(e) =>
                      set("instagram", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Facebook"
                    value={form.facebook}
                    onChange={(e) =>
                      set("facebook", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="TikTok"
                    placeholder="@fighter"
                    value={form.tiktok}
                    onChange={(e) =>
                      set("tiktok", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="X / Twitter"
                    placeholder="@fighter"
                    value={form.twitter}
                    onChange={(e) =>
                      set("twitter", e.target.value)
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Box>
              <Typography
                variant="subtitle1"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Location
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={5}>
                  <TextField
                    fullWidth
                    label="City"
                    value={form.city}
                    onChange={(e) =>
                      set("city", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="State"
                    value={form.state}
                    onChange={(e) =>
                      set("state", e.target.value)
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={4}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={form.country}
                    onChange={(e) =>
                      set("country", e.target.value)
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Button
              variant="contained"
              size="large"
              disabled={working}
              onClick={submit}
              sx={{
                bgcolor: "#d71920",
                fontWeight: 950,
                minHeight: 54,
              }}
            >
              {working
                ? "Submitting..."
                : "Submit Fighter"}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
