import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DescriptionRoundedIcon from "@mui/icons-material/DescriptionRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import PublishRoundedIcon from "@mui/icons-material/PublishRounded";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000")
  .replace(/\/$/, "");

const headers = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const labels = {
  bout_terms: "Bout Information / Participation",
  release: "Release of Liability",
  failure_to_appear: "Failure to Appear",
  other_event_restriction: "Other Event Restriction",
  cancellation: "Cancellation / Opponent No-Show",
};

export default function ContractTemplateManager() {
  const [data, setData] = useState(null);
  const [sections, setSections] = useState({});
  const [applyTo, setApplyTo] = useState("future");
  const [open, setOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: headers(options.headers || {}),
    });

    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        body.detail ||
        body.message ||
        "Request failed"
      );
    }

    return body;
  }

  async function load() {
    try {
      setError("");

      const body = await request(
        "/api/boxing/contract-templates/bout-agreement"
      );

      setData(body);

      setSections(
        body.draft?.sections ||
        body.active?.sections ||
        {}
      );
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function saveDraft() {
    setWorking(true);
    setMessage("");
    setError("");

    try {
      await request(
        "/api/boxing/contract-templates/bout-agreement/draft",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ sections }),
        }
      );

      setMessage("Contract template draft saved.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setWorking(false);
    }
  }

  async function publish() {
    setWorking(true);
    setMessage("");
    setError("");

    try {
      const body = await request(
        "/api/boxing/contract-templates/bout-agreement/publish",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            sections,
            apply_to: applyTo,
          }),
        }
      );

      setMessage(
        `Version ${body.published?.version} published. ` +
        `${body.contracts_updated || 0} unsigned contract(s) updated. ` +
        `${body.signed_contracts_preserved || 0} signed contract(s) preserved.`
      );

      setOpen(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setWorking(false);
    }
  }

  async function restore(versionId) {
    setWorking(true);
    setMessage("");
    setError("");

    try {
      const body = await request(
        `/api/boxing/contract-templates/bout-agreement/restore/${versionId}`,
        { method: "POST" }
      );

      setMessage(
        `Version ${body.published?.version} published from history.`
      );

      setHistoryOpen(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setWorking(false);
    }
  }

  function insertField(field) {
    navigator.clipboard
      ?.writeText(field)
      .catch(() => {});

    setMessage(
      `${field} copied. Paste it into any contract section.`
    );
  }

  return (
    <Card
      sx={{
        mb: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <CardContent>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", md: "center" }}
        >
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <DescriptionRoundedIcon color="error" />

              <Typography variant="h5" fontWeight={950}>
                Contract Management
              </Typography>
            </Stack>

            <Typography color="text.secondary" sx={{ mt: 0.5 }}>
              Edit your Bout Agreement wording without changing code.
            </Typography>
          </Box>

          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              startIcon={<HistoryRoundedIcon />}
              onClick={() => setHistoryOpen(true)}
            >
              Versions
            </Button>

            <Button
              variant="contained"
              onClick={() => setOpen(true)}
            >
              Edit Template
            </Button>
          </Stack>
        </Stack>

        <Divider sx={{ my: 2 }} />

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {message && (
          <Alert
            severity="success"
            onClose={() => setMessage("")}
            sx={{ mb: 2 }}
          >
            {message}
          </Alert>
        )}

        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          flexWrap="wrap"
        >
          <Chip
            color="success"
            label={`Active Version: ${
              data?.active?.version || "-"
            }`}
          />

          {data?.draft && (
            <Chip
              color="warning"
              label={`Draft Version: ${data.draft.version}`}
            />
          )}

          <Chip
            variant="outlined"
            label="Signed contracts are frozen"
          />
        </Stack>
      </CardContent>

      <Dialog
        open={open}
        onClose={() => !working && setOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          Edit Professional Boxing Bout Agreement
        </DialogTitle>

        <DialogContent dividers>
          <Alert severity="info" sx={{ mb: 2 }}>
            Edit the wording below. Contract amounts, fighter names,
            bout information, signatures, and DocuSign placement remain
            controlled by TNGOS.
          </Alert>

          <Typography fontWeight={900} sx={{ mb: 1 }}>
            Insert Merge Field
          </Typography>

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            flexWrap="wrap"
            sx={{ mb: 3 }}
          >
            {(data?.merge_fields || []).map((field) => (
              <Chip
                key={field}
                label={field}
                clickable
                onClick={() => insertField(field)}
              />
            ))}
          </Stack>

          <Stack spacing={3}>
            {Object.entries(labels).map(([key, label]) => (
              <Box key={key}>
                <Typography
                  fontWeight={900}
                  sx={{ mb: 1 }}
                >
                  {label}
                </Typography>

                <TextField
                  multiline
                  minRows={4}
                  fullWidth
                  value={sections[key] || ""}
                  onChange={(event) =>
                    setSections((current) => ({
                      ...current,
                      [key]: event.target.value,
                    }))
                  }
                />
              </Box>
            ))}
          </Stack>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" fontWeight={950}>
            Preview Wording
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 2 }}
          >
            Merge fields will be filled automatically when each contract
            is generated.
          </Typography>

          <Stack spacing={2}>
            {Object.entries(labels).map(([key, label]) => (
              <Box
                key={key}
                sx={{
                  p: 2,
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                }}
              >
                <Typography fontWeight={900}>
                  {label}
                </Typography>

                <Typography
                  sx={{
                    mt: 1,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {sections[key] || ""}
                </Typography>
              </Box>
            ))}
          </Stack>

          <Divider sx={{ my: 3 }} />

          <FormControl fullWidth>
            <InputLabel>Apply Published Changes To</InputLabel>

            <Select
              value={applyTo}
              label="Apply Published Changes To"
              onChange={(event) =>
                setApplyTo(event.target.value)
              }
            >
              <MenuItem value="future">
                New contracts only
              </MenuItem>

              <MenuItem value="unsigned">
                All unsigned contracts
              </MenuItem>
            </Select>
          </FormControl>

          {applyTo === "unsigned" && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              TNGOS will update every unsigned Bout Agreement to this
              version. Signed contracts and completed DocuSign/Adobe
              agreements will not be changed.
            </Alert>
          )}
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setOpen(false)}
            disabled={working}
          >
            Cancel
          </Button>

          <Button
            startIcon={<SaveRoundedIcon />}
            onClick={saveDraft}
            disabled={working}
          >
            Save Draft
          </Button>

          <Button
            variant="contained"
            color="error"
            startIcon={<PublishRoundedIcon />}
            onClick={publish}
            disabled={working}
          >
            Publish Changes
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={historyOpen}
        onClose={() => !working && setHistoryOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Contract Version History</DialogTitle>

        <DialogContent dividers>
          <Stack spacing={2}>
            {(data?.versions || []).map((version) => (
              <Card key={version.id} variant="outlined">
                <CardContent>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    spacing={2}
                  >
                    <Box>
                      <Typography fontWeight={950}>
                        Version {version.version}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {version.status}
                      </Typography>
                    </Box>

                    <Stack direction="row" spacing={1}>
                      {version.is_active && (
                        <Chip
                          size="small"
                          color="success"
                          label="Active"
                        />
                      )}

                      {version.status === "published" &&
                        !version.is_active && (
                          <Button
                            size="small"
                            onClick={() =>
                              restore(version.id)
                            }
                            disabled={working}
                          >
                            Restore
                          </Button>
                        )}
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}
