import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  InputAdornment,
  Typography,
} from "@mui/material";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import BloodtypeRoundedIcon from "@mui/icons-material/BloodtypeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import { buildOfficialContractHtml } from "../utils/officialContract";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const REQUEST_A_TEST_URL =
  "https://requestatest.com/combative";

const statusLabels = {
  not_started: "Not Started",
  in_progress: "In Progress",
  submitted: "Submitted",
  complete: "Complete",
  needs_attention: "Needs Attention",
};

function statusColor(status) {
  if (status === "complete") return "success";
  if (status === "needs_attention") return "error";
  if (status === "submitted") return "info";
  if (status === "in_progress") return "warning";
  return "default";
}

function fighterLocation(fighter) {
  return [
    fighter?.city,
    fighter?.state,
    fighter?.country,
  ]
    .filter(Boolean)
    .join(", ");
}

export default function EventWorkspace({
  eventId,
  onBack,
}) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState(0);
  const [cancelBoutOpen, setCancelBoutOpen] = useState(false);
  const [cancelBout, setCancelBout] = useState(null);
  const [cancelBoutNotes, setCancelBoutNotes] = useState("");
  const [cancelBoutWorking, setCancelBoutWorking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [contractWeights, setContractWeights] = useState({});
  const [contractTravel, setContractTravel] = useState({});
  const [promoImage, setPromoImage] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);


  async function load() {
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/workspace`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load event workspace"
        );
      }

      setData(body);
    } catch (error) {
      setMessage(
        error.message ||
          "Could not load event workspace"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [eventId]);

  async function updateBloodwork(fighter, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${fighter.id}/bloodwork`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update bloodwork"
        );
      }

      setData((old) => ({
        ...old,
        fighters: old.fighters.map((row) =>
          row.id === fighter.id
            ? { ...row, ...body }
            : row
        ),
      }));

      setMessage(`${fighter.legal_name} bloodwork updated.`);
    } catch (error) {
      setMessage(
        error.message || "Could not update bloodwork"
      );
    }
  }

  async function updateFee(fee, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/fees/${fee.id}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update fee"
        );
      }

      setData((old) => ({
        ...old,
        fees: old.fees.map((row) =>
          row.id === fee.id
            ? { ...row, ...body }
            : row
        ),
      }));
    } catch (error) {
      setMessage(
        error.message || "Could not update fee"
      );
    }
  }


  async function updateChecklist(item, changes) {
    const response = await fetch(
      `${API}/api/boxing/events/${eventId}/checklist/${item.id}`,
      {
        method: "PATCH",
        headers: authHeaders({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(changes),
      }
    );

    const body = await response.json();

    if (!response.ok) {
      setMessage(
        body.detail || "Could not update checklist"
      );
      return;
    }

    setData((old) => ({
      ...old,
      checklist: old.checklist.map((row) =>
        row.id === item.id
          ? { ...row, ...body }
          : row
      ),
    }));
  }

  function contractTravelValue(
    boutId,
    corner,
    field,
    fallback = ""
  ) {
    const key = `${boutId}-${corner}`;

    return (
      contractTravel[key]?.[field] ??
      fallback
    );
  }

  function setContractTravelValue(
    boutId,
    corner,
    field,
    value
  ) {
    const key = `${boutId}-${corner}`;

    setContractTravel((old) => ({
      ...old,
      [key]: {
        ...(old[key] || {}),
        [field]: value,
      },
    }));
  }

  async function uploadSignedContract(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/pdf,.pdf";

    input.onchange = async () => {
      const file = input.files?.[0];

      if (!file) return;

      if (
        file.type &&
        file.type !== "application/pdf"
      ) {
        window.alert(
          "Please select a PDF contract."
        );
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      try {
        const token =
          localStorage.getItem("token");

        const response = await fetch(
          `${API}/api/boxing/contracts/${contractId}/signed-upload`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: formData,
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(
            body.detail ||
              "Could not upload signed contract."
          );
        }

        const notice =
          body.message ||
          `${fighterName} signed contract uploaded.`;

        setMessage(notice);
        window.alert(notice);

        await load();
      } catch (error) {
        const notice =
          error.message ||
          "Could not upload signed contract.";

        setMessage(notice);
        window.alert(notice);
      }
    };

    input.click();
  }


  async function downloadSignedContract(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/signed-file`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        let detail =
          "No signed contract is available yet.";

        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {
          // response may not be JSON
        }

        throw new Error(detail);
      }

      const blob = await response.blob();

      const disposition =
        response.headers.get(
          "Content-Disposition"
        ) || "";

      const match =
        disposition.match(
          /filename="([^"]+)"/i
        );

      const fallbackName =
        `${fighterName || "fighter"}-signed-contract.pdf`
          .replace(/[^a-z0-9._-]+/gi, "-");

      const fileName =
        match?.[1] || fallbackName;

      const url =
        window.URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;
      link.download = fileName;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setMessage(
        `Downloaded signed contract for ${fighterName}.`
      );
    } catch (error) {
      const notice =
        error.message ||
        "Could not download signed contract.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function sendContractEmail(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first, then send it."
      );
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/send-email`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not send contract email."
        );
      }

      setMessage(body.message);
      window.alert(body.message);
    } catch (error) {
      const notice =
        error.message ||
        "Could not send contract email.";

      setMessage(notice);
      window.alert(notice);
    }
  }

  async function generateContract(bout, corner) {
    const printWindow = window.open(
      "",
      "_blank",
      "width=900,height=1000,scrollbars=yes"
    );

    if (!printWindow) {
      setMessage(
        "Your browser blocked the contract window. Allow popups for TNG."
      );
      return;
    }

    printWindow.document.write(
      "<p style='font-family:Arial;padding:30px'>Generating contract...</p>"
    );

    try {
      const travelKey = `${bout.id}-${corner}`;
      const travel =
        contractTravel[travelKey] || {};

      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/contracts/${corner}`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            maximum_weight:
              contractWeights[
                `${bout.id}-${corner}`
              ] ??
              bout.weight_agreed ??
              "",

            travel_type:
              travel.travel_type || "",

            travel_paid_by:
              travel.travel_paid_by || "",

            travel_expense:
              travel.travel_expense || 0,

            hotel_provided:
              travel.hotel_provided || "",

            hotel_name:
              travel.hotel_name || "",

            hotel_nights:
              travel.hotel_nights || 0,

            per_diem_daily:
              travel.per_diem_daily || 0,

            per_diem_days:
              travel.per_diem_days || 0,
          }),
        }
      );

      const contract = await response.json();

      if (!response.ok) {
        throw new Error(
          contract.detail || "Could not generate contract"
        );
      }

      const html =
        buildOfficialContractHtml(contract);

      printWindow.document.open();
      printWindow.document.write(html);
      printWindow.document.close();

      setMessage(
        `${contract.boxer_name} contract generated.`
      );

      await load();

    } catch (error) {
      printWindow.close();

      setMessage(
        error.message ||
        "Could not generate contract"
      );
    }
  }


  async function updateBoutPurse(bout, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/purse`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update purse"
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts.map((row) =>
          row.id === bout.id
            ? {
                ...row,
                red_purse: body.red_purse,
                blue_purse: body.blue_purse,
              }
            : row
        ),
      }));

      setMessage("Fight purse updated.");
    } catch (error) {
      setMessage(
        error.message || "Could not update purse"
      );
    }
  }


  async function updateBoutOrder(bout, value) {
    const order = Number(value);

    if (!Number.isInteger(order) || order < 1) {
      setMessage("Bout order must be 1 or higher.");
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/order`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            bout_order: order,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update bout order"
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts
          .map((row) =>
            row.id === bout.id
              ? { ...row, bout_order: order }
              : row
          )
          .sort(
            (a, b) =>
              Number(a.bout_order || 999) -
              Number(b.bout_order || 999)
          ),
      }));

      setMessage(`Bout moved to #${order}`);
    } catch (error) {
      setMessage(
        error.message || "Could not update bout order"
      );
    }
  }

  async function generateEventPromo() {
    setPromoLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/generate-promo`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not generate event promo"
        );
      }

      setPromoImage(body.image);

      setMessage(
        "Event promo generated from the current fight card."
      );

    } catch (error) {

      setMessage(
        error.message ||
        "Could not generate event promo"
      );

    } finally {
      setPromoLoading(false);
    }
  }


  const promoterItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "promoter"
      ),
    [data]
  );

  const matchmakerItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "matchmaker"
      ),
    [data]
  );

  const completed = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.status === "complete"
      ).length,
    [data]
  );

  const bloodworkVerified = useMemo(
    () =>
      (data?.fighters || []).filter(
        (x) => x.bloodwork_status === "verified"
      ).length,
    [data]
  );

  if (loading) {
    return (
      <Box sx={{ p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          {message || "Event could not be loaded."}
        </Alert>

        <Button
          sx={{ mt: 2 }}
          onClick={onBack}
        >
          Back
        </Button>
      </Box>
    );
  }

  const event = data.event;
  const bouts = data.bouts || [];

  const activeBouts = bouts.filter(
    (bout) =>
      bout.status !== "cancelled" &&
      bout.status !== "void"
  );

  const cancelledBouts = bouts.filter(
    (bout) =>
      bout.status === "cancelled" ||
      bout.status === "void"
  );

  const fighters = data.fighters || [];
  const totalChecklist =
    data.checklist?.length || 0;

  function ChecklistSection({ items }) {
    return (
      <Stack spacing={1.5}>
        {items.map((item) => (
          <Card key={item.id}>
            <CardContent>
              <Stack spacing={1.5}>
                <Stack
                  direction={{
                    xs: "column",
                    md: "row",
                  }}
                  spacing={1}
                  justifyContent="space-between"
                >
                  <Typography fontWeight={850}>
                    {item.label}
                  </Typography>

                  <Chip
                    size="small"
                    label={
                      statusLabels[item.status] ||
                      item.status
                    }
                    color={statusColor(item.status)}
                  />
                </Stack>

                <Grid container spacing={1.5}>
                  <Grid item xs={12} md={3}>
                    <Select
                      fullWidth
                      size="small"
                      value={item.status}
                      onChange={(e) =>
                        updateChecklist(item, {
                          status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="not_started">
                        Not Started
                      </MenuItem>

                      <MenuItem value="in_progress">
                        In Progress
                      </MenuItem>

                      <MenuItem value="submitted">
                        Submitted
                      </MenuItem>

                      <MenuItem value="complete">
                        Complete
                      </MenuItem>

                      <MenuItem value="needs_attention">
                        Needs Attention
                      </MenuItem>
                    </Select>
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      type="date"
                      label="Due Date"
                      InputLabelProps={{
                        shrink: true,
                      }}
                      value={item.due_date || ""}
                      onChange={(e) =>
                        updateChecklist(item, {
                          due_date: e.target.value,
                        })
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Assigned To"
                      value={item.assigned_to || ""}
                      onBlur={(e) =>
                        updateChecklist(item, {
                          assigned_to:
                            e.target.value,
                        })
                      }
                      onChange={(e) => {
                        const value =
                          e.target.value;

                        setData((old) => ({
                          ...old,
                          checklist:
                            old.checklist.map(
                              (row) =>
                                row.id === item.id
                                  ? {
                                      ...row,
                                      assigned_to:
                                        value,
                                    }
                                  : row
                            ),
                        }));
                      }}
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Notes"
                      value={item.notes || ""}
                      onBlur={(e) =>
                        updateChecklist(item, {
                          notes: e.target.value,
                        })
                      }
                      onChange={(e) => {
                        const value =
                          e.target.value;

                        setData((old) => ({
                          ...old,
                          checklist:
                            old.checklist.map(
                              (row) =>
                                row.id === item.id
                                  ? {
                                      ...row,
                                      notes: value,
                                    }
                                  : row
                            ),
                        }));
                      }}
                    />
                  </Grid>
                </Grid>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
    );
  }


  async function submitBoutCancellation() {
    if (!cancelBout) return;

    const notes = cancelBoutNotes.trim();

    if (!notes) {
      alert("Please enter a reason for removing this bout.");
      return;
    }

    setCancelBoutWorking(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${cancelBout.id}/cancel`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            notes,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail || "Could not remove bout."
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts.map((bout) =>
          bout.id === cancelBout.id
            ? {
                ...bout,
                status: "cancelled",
                notes: result.notes || bout.notes,
              }
            : bout
        ),
      }));

      setCancelBoutOpen(false);
      setCancelBout(null);
      setCancelBoutNotes("");
    } catch (error) {
      alert(error.message || "Could not remove bout.");
    } finally {
      setCancelBoutWorking(false);
    }
  }


  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={2.5}>
        <Stack
          direction={{
            xs: "column",
            md: "row",
          }}
          spacing={2}
          justifyContent="space-between"
        >
          <Box>
            <Button
              startIcon={<ArrowBackRoundedIcon />}
              onClick={onBack}
              sx={{ mb: 1 }}
            >
              Back to Matchmaker
            </Button>

            <Typography
              variant="h4"
              fontWeight={950}
            >
              {event.name}
            </Typography>

            <Typography color="text.secondary">
              {event.event_date || "No date"}
              {event.venue
                ? ` • ${event.venue}`
                : ""}
            </Typography>

            {event.venue_address && (
              <Typography
                variant="body2"
                color="text.secondary"
              >
                {event.venue_address}
              </Typography>
            )}
          </Box>

          <Chip
            label={event.status || "planning"}
            sx={{
              alignSelf: {
                xs: "flex-start",
                md: "center",
              },
            }}
          />
        </Stack>

        {message && (
          <Alert
            severity="info"
            onClose={() => setMessage("")}
          >
            {message}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Bouts
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {activeBouts.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Fighters
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {fighters.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Bloodwork
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {bloodworkVerified}/{fighters.length}
                </Typography>

                <Typography variant="caption">
                  verified
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Checklist
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {completed}/{totalChecklist}
                </Typography>

                <Typography variant="caption">
                  complete
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card>
          <Card
          sx={{
            mb: 2,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <CardContent>
            <Stack spacing={2}>
              <Stack
                direction={{
                  xs: "column",
                  md: "row",
                }}
                justifyContent="space-between"
                alignItems={{
                  xs: "stretch",
                  md: "center",
                }}
                spacing={2}
              >
                <Box>
                  <Typography
                    variant="h6"
                    fontWeight={950}
                  >
                    AI Event Promo
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Generate artwork from this event
                    and the saved bout order.
                  </Typography>
                </Box>

                <Button
                  variant="contained"
                  onClick={generateEventPromo}
                  disabled={promoLoading}
                >
                  {promoLoading
                    ? "Generating..."
                    : promoImage
                    ? "Regenerate Promo"
                    : "Generate AI Event Promo"}
                </Button>
              </Stack>

              {promoImage && (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                  }}
                >
                  <Box
                    component="img"
                    src={promoImage}
                    alt="Generated event promo"
                    sx={{
                      width: "100%",
                      maxWidth: 600,
                      borderRadius: 2,
                      boxShadow: 3,
                    }}
                  />
                </Box>
              )}
            </Stack>
          </CardContent>
        </Card>

        <Tabs
            value={tab}
            onChange={(_, value) =>
              setTab(value)
            }
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Overview" />
            <Tab label="Bout Sheet" />
            <Tab label="Contracts" />
            <Tab label="Promoter Checklist" />
            <Tab label="Matchmaker Checklist" />
            <Tab label="Bloodwork" />
            <Tab label="Fees" />
          </Tabs>
        </Card>

        {/* OVERVIEW */}
        {tab === 0 && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Fight Card
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  {!activeBouts.length && (
                    <Typography color="text.secondary">
                      No bouts have been built for
                      this event yet.
                    </Typography>
                  )}

                  <Stack spacing={1}>
                    {activeBouts.map((bout, index) => (
                      <Box
                        key={bout.id}
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: "#fafafa",
                        }}
                      >
                        <Typography
                          fontWeight={900}
                        >
                          Bout {index + 1}
                        </Typography>

                        <Typography>
                          {bout.red?.legal_name}
                          {" vs "}
                          {bout.blue?.legal_name}
                        </Typography>

                        <Typography
                          variant="caption"
                          color="text.secondary"
                        >
                          {bout.weight_agreed
                            ? `${bout.weight_agreed} lb`
                            : "Weight TBD"}
                          {" • "}
                          {bout.rounds} rounds
                          {" • "}
                          {bout.status}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={5}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Needs Attention
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  <Stack spacing={1}>
                    {fighters
                      .filter(
                        (fighter) =>
                          fighter.bloodwork_status !==
                          "verified"
                      )
                      .map((fighter) => (
                        <Alert
                          severity="warning"
                          key={fighter.id}
                        >
                          {fighter.legal_name}: bloodwork{" "}
                          {fighter.bloodwork_status ||
                            "missing"}
                        </Alert>
                      ))}

                    {data.checklist
                      .filter(
                        (item) =>
                          item.status ===
                          "needs_attention"
                      )
                      .map((item) => (
                        <Alert
                          severity="error"
                          key={item.id}
                        >
                          {item.label}
                        </Alert>
                      ))}

                    {!fighters.some(
                      (f) =>
                        f.bloodwork_status !==
                        "verified"
                    ) &&
                      !data.checklist.some(
                        (x) =>
                          x.status ===
                          "needs_attention"
                      ) && (
                        <Alert severity="success">
                          No current attention flags.
                        </Alert>
                      )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* FIGHT CARD */}
        {tab === 1 && (
          <Stack spacing={2}>
            {activeBouts.map((bout, index) => (
              <Card key={bout.id}>
                <CardContent>
                  <Grid
                    container
                    spacing={2}
                    alignItems="center"
                  >
                    <Grid item xs={12} md={2}>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        Bout {index + 1}
                      </Typography>

                      <Chip
                        size="small"
                        label={bout.status}
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <Typography
                        fontWeight={950}
                      >
                        RED:{" "}
                        {bout.red?.legal_name}
                      </Typography>

                      <Typography variant="body2">
                        {bout.red?.pro_record ||
                          "Record N/A"}
                      </Typography>


                      {bout.red_series &&
                        bout.red_series.status !==
                          "released" && (
                          <Chip
                            size="small"
                            color="primary"
                            sx={{ mt: 0.75 }}
                            label={
                              bout.red_series.status ===
                              "graduated"
                                ? "FIRST 5 FIGHTS SERIES — GRADUATED"
                                : `FIRST 5 FIGHTS SERIES — FIGHT ${bout.red_series.next_fight_number} OF ${bout.red_series.target_fights}`
                            }
                          />
                        )}

                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        {fighterLocation(
                          bout.red
                        )}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <Typography
                        fontWeight={950}
                      >
                        BLUE:{" "}
                        {bout.blue?.legal_name}
                      </Typography>

                      <Typography variant="body2">
                        {bout.blue?.pro_record ||
                          "Record N/A"}
                      </Typography>


                      {bout.blue_series &&
                        bout.blue_series.status !==
                          "released" && (
                          <Chip
                            size="small"
                            color="primary"
                            sx={{ mt: 0.75 }}
                            label={
                              bout.blue_series.status ===
                              "graduated"
                                ? "FIRST 5 FIGHTS SERIES — GRADUATED"
                                : `FIRST 5 FIGHTS SERIES — FIGHT ${bout.blue_series.next_fight_number} OF ${bout.blue_series.target_fights}`
                            }
                          />
                        )}

                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        {fighterLocation(
                          bout.blue
                        )}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={2}>
                      <TextField
                        fullWidth
                        type="number"
                        size="small"
                        label="Bout Order"
                        value={bout.bout_order ?? ""}
                        inputProps={{ min: 1 }}
                        onChange={(e) => {
                          const value = e.target.value;

                          setData((old) => ({
                            ...old,
                            bouts: old.bouts.map((row) =>
                              row.id === bout.id
                                ? {
                                    ...row,
                                    bout_order: value,
                                  }
                                : row
                            ),
                          }));
                        }}
                        onBlur={(e) =>
                          updateBoutOrder(
                            bout,
                            e.target.value
                          )
                        }
                        sx={{ mb: 1 }}
                      />


                      <Typography fontWeight={850}>
                        {bout.weight_agreed
                          ? `${bout.weight_agreed} lb`
                          : "TBD"}
                      </Typography>

                      <Typography variant="body2">
                        {bout.rounds} rounds
                      </Typography>

                      {bout.status !== "cancelled" ? (
                        <Button
                          size="small"
                          color="error"
                          variant="outlined"
                          sx={{ mt: 1 }}
                          onClick={() => {
                            setCancelBout(bout);
                            setCancelBoutNotes("");
                            setCancelBoutOpen(true);
                          }}
                        >
                          Remove Bout
                        </Button>
                      ) : (
                        <Chip
                          size="small"
                          color="default"
                          label="Removed / Cancelled"
                          sx={{ mt: 1 }}
                        />
                      )}
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}

            {!activeBouts.length && (
              <Alert severity="info">
                No active bouts are currently assigned to this event.
              </Alert>
            )}

            {cancelledBouts.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />

                <Typography
                  variant="h6"
                  fontWeight={950}
                >
                  Cancelled Bout History
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 1 }}
                >
                  These bouts remain in TNGOS for records but are
                  no longer part of the active fight card.
                </Typography>

                <Stack spacing={1}>
                  {cancelledBouts.map((bout) => (
                    <Card
                      key={bout.id}
                      variant="outlined"
                      sx={{
                        opacity: 0.78,
                        borderStyle: "dashed",
                      }}
                    >
                      <CardContent>
                        <Stack
                          direction={{
                            xs: "column",
                            md: "row",
                          }}
                          justifyContent="space-between"
                          spacing={2}
                        >
                          <Box>
                            <Typography fontWeight={950}>
                              {bout.red?.legal_name || "Red Corner"}
                              {" vs "}
                              {bout.blue?.legal_name || "Blue Corner"}
                            </Typography>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                            >
                              {bout.weight_agreed
                                ? `${bout.weight_agreed} lb`
                                : "Weight TBD"}
                              {" ? "}
                              {bout.rounds} rounds
                            </Typography>

                            {bout.notes && (
                              <Typography
                                variant="body2"
                                sx={{
                                  mt: 1,
                                  whiteSpace: "pre-line",
                                }}
                              >
                                {bout.notes}
                              </Typography>
                            )}
                          </Box>

                          <Chip
                            label={
                              bout.status === "void"
                                ? "Void"
                                : "Cancelled"
                            }
                          />
                        </Stack>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </>
            )}
          </Stack>
        )}

        {/* BOUT SHEETS */}
        {tab === 2 && (
          <Stack spacing={2}>
            {activeBouts.map((bout, index) => (
              <Card key={bout.id}>
                <CardContent>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={2}
                    alignItems={{ xs: "flex-start", sm: "center" }}
                    justifyContent="space-between"
                  >
                    <Typography
                      variant="h5"
                      fontWeight={950}
                    >
                      Bout Contract {bout.bout_order || index + 1}
                    </Typography>


                    {(bout.red_series ||
                      bout.blue_series) && (
                      <Stack
                        direction={{
                          xs: "column",
                          sm: "row",
                        }}
                        spacing={1}
                      >
                        {bout.red_series &&
                          bout.red_series.status !==
                            "released" && (
                            <Chip
                              size="small"
                              color="primary"
                              label={
                                `RED: ${bout.red?.legal_name || "Fighter"} — First 5 Fight ${bout.red_series.next_fight_number} of ${bout.red_series.target_fights}`
                              }
                            />
                          )}

                        {bout.blue_series &&
                          bout.blue_series.status !==
                            "released" && (
                            <Chip
                              size="small"
                              color="primary"
                              label={
                                `BLUE: ${bout.blue?.legal_name || "Fighter"} — First 5 Fight ${bout.blue_series.next_fight_number} of ${bout.blue_series.target_fights}`
                              }
                            />
                          )}
                      </Stack>
                    )}

                    
                  </Stack>

                  <Divider sx={{ my: 2 }} />

                  <Typography
                    variant="subtitle1"
                    fontWeight={950}
                    sx={{ mb: 1 }}
                  >
                    Fight Offer / Purse
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        type="number"
                        label="Red Corner Purse"
                        value={bout.red_purse ?? 0}
                        inputProps={{
                          min: 0,
                          step: 50,
                        }}
                        onChange={(e) => {
                          const value = e.target.value;

                          setData((old) => ({
                            ...old,
                            bouts: old.bouts.map((row) =>
                              row.id === bout.id
                                ? {
                                    ...row,
                                    red_purse: value,
                                  }
                                : row
                            ),
                          }));
                        }}
                        onBlur={(e) =>
                          updateBoutPurse(bout, {
                            red_purse:
                              e.target.value,
                          })
                        }
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              $
                            </InputAdornment>
                          ),
                        }}
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        type="number"
                        label="Blue Corner Purse"
                        value={bout.blue_purse ?? 0}
                        inputProps={{
                          min: 0,
                          step: 50,
                        }}
                        onChange={(e) => {
                          const value = e.target.value;

                          setData((old) => ({
                            ...old,
                            bouts: old.bouts.map((row) =>
                              row.id === bout.id
                                ? {
                                    ...row,
                                    blue_purse: value,
                                  }
                                : row
                            ),
                          }));
                        }}
                        onBlur={(e) =>
                          updateBoutPurse(bout, {
                            blue_purse:
                              e.target.value,
                          })
                        }
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              $
                            </InputAdornment>
                          ),
                        }}
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Total Bout Purse"
                        value={
                          `$${(
                            Number(bout.red_purse || 0) +
                            Number(bout.blue_purse || 0)
                          ).toLocaleString()}`
                        }
                        InputProps={{
                          readOnly: true,
                        }}
                      />
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  <Typography
                    variant="subtitle1"
                    fontWeight={950}
                    sx={{ mb: 1 }}
                  >
                    Fighter Contracts
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Enter the final contracted maximum
                    weight before generating each fighter's
                    agreement.
                  </Typography>

                  <Grid container spacing={2}>

                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Stack spacing={1.5}>

                            <Typography
                              fontWeight={950}
                            >
                              Red Corner Contract
                            </Typography>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                            >
                              {bout.red?.legal_name ||
                                "Red Corner"}
                            </Typography>

                            <Stack
                              direction="row"
                              spacing={1}
                              alignItems="center"
                              flexWrap="wrap"
                            >
                              <Typography
                                variant="body2"
                                fontWeight={800}
                              >
                                Fighter Response:
                              </Typography>

                              <Chip
                                size="small"
                                label={
                                  bout.red_contract?.status
                                    ? String(
                                        bout.red_contract.status
                                      )
                                        .replaceAll("_", " ")
                                        .toUpperCase()
                                    : "NOT SENT"
                                }
                                color={
                                  bout.red_contract?.status ===
                                    "accepted" ||
                                  bout.red_contract?.status ===
                                    "signed"
                                    ? "success"
                                    : bout.red_contract?.status ===
                                        "declined"
                                      ? "error"
                                      : bout.red_contract?.status ===
                                          "change_requested"
                                        ? "warning"
                                        : "default"
                                }
                              />
                            </Stack>

                            {bout.red_contract
                              ?.change_request && (
                              <Alert severity="warning">
                                <strong>
                                  Fighter requested:
                                </strong>{" "}
                                {
                                  bout.red_contract
                                    .change_request
                                }
                              </Alert>
                            )}

                            <TextField
                              fullWidth
                              type="number"
                              label="Final Contract Weight"
                              value={
                                contractWeights[
                                  `${bout.id}-red`
                                ] ??
                                bout.weight_agreed ??
                                ""
                              }
                              inputProps={{
                                min: 0,
                                step: 0.1,
                              }}
                              onChange={(e) =>
                                setContractWeights(
                                  (old) => ({
                                    ...old,
                                    [`${bout.id}-red`]:
                                      e.target.value,
                                  })
                                )
                              }
                              InputProps={{
                                endAdornment: (
                                  <InputAdornment
                                    position="end"
                                  >
                                    lb
                                  </InputAdornment>
                                ),
                              }}
                            />

                            <Divider />

                            <Typography
                              variant="body2"
                              fontWeight={900}
                            >
                              Travel / Hotel / Per Diem
                            </Typography>

                            <Grid container spacing={1}>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Travel Type"
                                  placeholder="Airfare, ground, other"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "travel_type"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "travel_type",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Travel Paid By"
                                  placeholder="Promoter / fighter / reimbursement"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "travel_paid_by"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "travel_paid_by",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Travel Amount"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "travel_expense",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "travel_expense",
                                      e.target.value
                                    )
                                  }
                                  InputProps={{
                                    startAdornment: (
                                      <InputAdornment position="start">
                                        $
                                      </InputAdornment>
                                    ),
                                  }}
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Hotel Provided"
                                  placeholder="Yes / No"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "hotel_provided"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "hotel_provided",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={8}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Hotel Name"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "hotel_name"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "hotel_name",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={4}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Hotel Nights"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "hotel_nights",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "hotel_nights",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Per Diem / Day"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "per_diem_daily",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "per_diem_daily",
                                      e.target.value
                                    )
                                  }
                                  InputProps={{
                                    startAdornment: (
                                      <InputAdornment position="start">
                                        $
                                      </InputAdornment>
                                    ),
                                  }}
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Per Diem Days"
                                  value={contractTravelValue(
                                    bout.id,
                                    "red",
                                    "per_diem_days",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "red",
                                      "per_diem_days",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>
                            </Grid>

                            <Button
                              variant="outlined"
                              disabled={!bout.red_contract?.id}
                              onClick={() =>
                                sendContractEmail(
                                  bout.red_contract?.id,
                                  bout.red?.legal_name ||
                                    "Red Corner"
                                )
                              }
                            >
                              Send Contract Email
                            </Button>

                            <Button
                              variant="outlined"
                              disabled={!bout.red_contract?.id}
                              onClick={() =>
                                uploadSignedContract(
                                  bout.red_contract?.id,
                                  bout.red?.legal_name ||
                                    "Red Corner"
                                )
                              }
                            >
                              Upload Signed PDF
                            </Button>

                            <Button
                              variant="text"
                              disabled={!bout.red_contract?.id}
                              onClick={() =>
                                downloadSignedContract(
                                  bout.red_contract?.id,
                                  bout.red?.legal_name ||
                                    "Red Corner"
                                )
                              }
                            >
                              Download Signed PDF
                            </Button>

                            <Button
                              variant="contained"
                              onClick={() =>
                                generateContract(
                                  bout,
                                  "red"
                                )
                              }
                            >
                              Generate Red Contract
                            </Button>

                          </Stack>
                        </CardContent>
                      </Card>
                    </Grid>


                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Stack spacing={1.5}>

                            <Typography
                              fontWeight={950}
                            >
                              Blue Corner Contract
                            </Typography>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                            >
                              {bout.blue?.legal_name ||
                                "Blue Corner"}
                            </Typography>

                            <Stack
                              direction="row"
                              spacing={1}
                              alignItems="center"
                              flexWrap="wrap"
                            >
                              <Typography
                                variant="body2"
                                fontWeight={800}
                              >
                                Fighter Response:
                              </Typography>

                              <Chip
                                size="small"
                                label={
                                  bout.blue_contract?.status
                                    ? String(
                                        bout.blue_contract.status
                                      )
                                        .replaceAll("_", " ")
                                        .toUpperCase()
                                    : "NOT SENT"
                                }
                                color={
                                  bout.blue_contract?.status ===
                                    "accepted" ||
                                  bout.blue_contract?.status ===
                                    "signed"
                                    ? "success"
                                    : bout.blue_contract?.status ===
                                        "declined"
                                      ? "error"
                                      : bout.blue_contract?.status ===
                                          "change_requested"
                                        ? "warning"
                                        : "default"
                                }
                              />
                            </Stack>

                            {bout.blue_contract
                              ?.change_request && (
                              <Alert severity="warning">
                                <strong>
                                  Fighter requested:
                                </strong>{" "}
                                {
                                  bout.blue_contract
                                    .change_request
                                }
                              </Alert>
                            )}

                            <TextField
                              fullWidth
                              type="number"
                              label="Final Contract Weight"
                              value={
                                contractWeights[
                                  `${bout.id}-blue`
                                ] ??
                                bout.weight_agreed ??
                                ""
                              }
                              inputProps={{
                                min: 0,
                                step: 0.1,
                              }}
                              onChange={(e) =>
                                setContractWeights(
                                  (old) => ({
                                    ...old,
                                    [`${bout.id}-blue`]:
                                      e.target.value,
                                  })
                                )
                              }
                              InputProps={{
                                endAdornment: (
                                  <InputAdornment
                                    position="end"
                                  >
                                    lb
                                  </InputAdornment>
                                ),
                              }}
                            />

                            <Divider />

                            <Typography
                              variant="body2"
                              fontWeight={900}
                            >
                              Travel / Hotel / Per Diem
                            </Typography>

                            <Grid container spacing={1}>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Travel Type"
                                  placeholder="Airfare, ground, other"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "travel_type"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "travel_type",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Travel Paid By"
                                  placeholder="Promoter / fighter / reimbursement"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "travel_paid_by"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "travel_paid_by",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Travel Amount"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "travel_expense",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "travel_expense",
                                      e.target.value
                                    )
                                  }
                                  InputProps={{
                                    startAdornment: (
                                      <InputAdornment position="start">
                                        $
                                      </InputAdornment>
                                    ),
                                  }}
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Hotel Provided"
                                  placeholder="Yes / No"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "hotel_provided"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "hotel_provided",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={8}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  label="Hotel Name"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "hotel_name"
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "hotel_name",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={4}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Hotel Nights"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "hotel_nights",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "hotel_nights",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Per Diem / Day"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "per_diem_daily",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "per_diem_daily",
                                      e.target.value
                                    )
                                  }
                                  InputProps={{
                                    startAdornment: (
                                      <InputAdornment position="start">
                                        $
                                      </InputAdornment>
                                    ),
                                  }}
                                />
                              </Grid>

                              <Grid item xs={12} sm={6}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Per Diem Days"
                                  value={contractTravelValue(
                                    bout.id,
                                    "blue",
                                    "per_diem_days",
                                    0
                                  )}
                                  onChange={(e) =>
                                    setContractTravelValue(
                                      bout.id,
                                      "blue",
                                      "per_diem_days",
                                      e.target.value
                                    )
                                  }
                                />
                              </Grid>
                            </Grid>

                            <Button
                              variant="outlined"
                              disabled={!bout.blue_contract?.id}
                              onClick={() =>
                                sendContractEmail(
                                  bout.blue_contract?.id,
                                  bout.blue?.legal_name ||
                                    "Blue Corner"
                                )
                              }
                            >
                              Send Contract Email
                            </Button>

                            <Button
                              variant="outlined"
                              disabled={!bout.blue_contract?.id}
                              onClick={() =>
                                uploadSignedContract(
                                  bout.blue_contract?.id,
                                  bout.blue?.legal_name ||
                                    "Blue Corner"
                                )
                              }
                            >
                              Upload Signed PDF
                            </Button>

                            <Button
                              variant="text"
                              disabled={!bout.blue_contract?.id}
                              onClick={() =>
                                downloadSignedContract(
                                  bout.blue_contract?.id,
                                  bout.blue?.legal_name ||
                                    "Blue Corner"
                                )
                              }
                            >
                              Download Signed PDF
                            </Button>

                            <Button
                              variant="contained"
                              onClick={() =>
                                generateContract(
                                  bout,
                                  "blue"
                                )
                              }
                            >
                              Generate Blue Contract
                            </Button>

                          </Stack>
                        </CardContent>
                      </Card>
                    </Grid>

                  </Grid>



                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography
                        color="error"
                        fontWeight={900}
                      >
                        RED CORNER
                      </Typography>

                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {bout.red?.legal_name}
                      </Typography>

                      <Typography>
                        {bout.red?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography>
                        BoxRec #
                        {bout.red?.boxrec_id || "—"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.red?.phone || "—"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.red?.email || "—"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.red?.manager_name ||
                          "—"}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography
                        fontWeight={900}
                      >
                        BLUE CORNER
                      </Typography>

                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {bout.blue?.legal_name}
                      </Typography>

                      <Typography>
                        {bout.blue?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography>
                        BoxRec #
                        {bout.blue?.boxrec_id ||
                          "—"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.blue?.phone || "—"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.blue?.email || "—"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.blue?.manager_name ||
                          "—"}
                      </Typography>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        WEIGHT
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        {bout.weight_agreed
                          ? `${bout.weight_agreed} lb`
                          : "TBD"}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        ROUNDS
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        {bout.rounds}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        RED PURSE
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        ${Number(
                          bout.red_purse || 0
                        ).toFixed(2)}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        BLUE PURSE
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        ${Number(
                          bout.blue_purse || 0
                        ).toFixed(2)}
                      </Typography>
                    </Grid>
                  </Grid>

                  {bout.notes && (
                    <>
                      <Divider sx={{ my: 2 }} />

                      <Typography
                        fontWeight={850}
                      >
                        Notes
                      </Typography>

                      <Typography>
                        {bout.notes}
                      </Typography>
                    </>
                  )}
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}

        {/* PROMOTER */}
        {tab === 3 && (
          <Box>
            <Typography
              variant="h5"
              fontWeight={950}
              sx={{ mb: 0.5 }}
            >
              Promoter Responsibilities
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Track every Commission and event
              operations requirement.
            </Typography>

            <ChecklistSection
              items={promoterItems}
            />
          </Box>
        )}

        {/* MATCHMAKER */}
        {tab === 4 && (
          <Box>
            <Typography
              variant="h5"
              fontWeight={950}
              sx={{ mb: 0.5 }}
            >
              Matchmaker Responsibilities
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Bout submission, contracts, bloodwork
              and special fighter requirements.
            </Typography>

            <ChecklistSection
              items={matchmakerItems}
            />
          </Box>
        )}

        {/* BLOODWORK */}
        {tab === 5 && (
          <Stack spacing={2}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              spacing={1}
            >
              <Box>
                <Typography variant="h5" fontWeight={950}>
                  Fighter Bloodwork
                </Typography>

                <Typography color="text.secondary">
                  Update bloodwork status for each fighter on this card.
                </Typography>
              </Box>

              <Button
                variant="outlined"
                startIcon={<BloodtypeRoundedIcon />}
                onClick={() =>
                  window.open(
                    REQUEST_A_TEST_URL,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Open Request A Test
              </Button>
            </Stack>

            {fighters.map((fighter) => (
              <Card key={fighter.id}>
                <CardContent>
                  <Stack spacing={2}>
                    <Box>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {fighter.legal_name}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {fighter.pro_record || "Record N/A"}
                        {" • "}
                        {fighter.fight_weight
                          ? `${fighter.fight_weight} lb`
                          : "Weight N/A"}
                      </Typography>
                    </Box>

                    <Grid container spacing={2}>
                      <Grid item xs={12} md={3}>
                        <Select
                          fullWidth
                          value={
                            fighter.bloodwork_status ||
                            "missing"
                          }
                          onChange={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_status:
                                e.target.value,
                            })
                          }
                        >
                          <MenuItem value="missing">
                            Missing
                          </MenuItem>

                          <MenuItem value="requested">
                            Requested
                          </MenuItem>

                          <MenuItem value="pending">
                            Pending
                          </MenuItem>

                          <MenuItem value="verified">
                            Verified
                          </MenuItem>

                          <MenuItem value="expired">
                            Expired
                          </MenuItem>
                        </Select>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          label="Provider"
                          defaultValue={
                            fighter.bloodwork_provider || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_provider:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Requested"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_requested_date ||
                            ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_requested_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Completed"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_completed_date ||
                            ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_completed_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Expires"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_expires || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_expires:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={7}>
                        <TextField
                          fullWidth
                          label="Notes"
                          defaultValue={
                            fighter.bloodwork_notes || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_notes:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={2}>
                        <Button
                          fullWidth
                          variant="outlined"
                          sx={{ minHeight: 56 }}
                          onClick={() =>
                            window.open(
                              REQUEST_A_TEST_URL,
                              "_blank",
                              "noopener,noreferrer"
                            )
                          }
                        >
                          Request Test
                        </Button>
                      </Grid>
                    </Grid>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}

        {/* FEES */}
        {tab === 6 && (
          <Stack spacing={2}>
            <Box>
              <Typography variant="h5" fontWeight={950}>
                Event Fees & Assessments
              </Typography>

              <Typography color="text.secondary">
                Track estimated and actual costs for this event.
              </Typography>
            </Box>

            {(data.fees || []).map((fee) => (
              <Card key={fee.id}>
                <CardContent>
                  <Stack spacing={2}>
                    <Stack
                      direction={{
                        xs: "column",
                        md: "row",
                      }}
                      justifyContent="space-between"
                      spacing={1}
                    >
                      <Box>
                        <Typography fontWeight={950}>
                          {fee.name}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                        >
                          Estimate: {fee.estimate}
                        </Typography>
                      </Box>

                      <Chip
                        label={
                          fee.paid ? "Paid" : "Unpaid"
                        }
                        color={
                          fee.paid
                            ? "success"
                            : "warning"
                        }
                      />
                    </Stack>

                    <Grid container spacing={2}>
                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="number"
                          label="Actual Amount"
                          defaultValue={
                            fee.actual_amount ?? ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              actual_amount:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={2}>
                        <Select
                          fullWidth
                          value={
                            fee.paid ? "paid" : "unpaid"
                          }
                          onChange={(e) =>
                            updateFee(fee, {
                              paid:
                                e.target.value === "paid",
                            })
                          }
                        >
                          <MenuItem value="unpaid">
                            Unpaid
                          </MenuItem>

                          <MenuItem value="paid">
                            Paid
                          </MenuItem>
                        </Select>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Due Date"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fee.due_date || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              due_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Payee"
                          defaultValue={
                            fee.payee || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              payee: e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          multiline
                          minRows={2}
                          label="Notes"
                          defaultValue={
                            fee.notes || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              notes: e.target.value,
                            })
                          }
                        />
                      </Grid>
                    </Grid>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}

      </Stack>
      <Dialog
        open={cancelBoutOpen}
        onClose={() => {
          if (!cancelBoutWorking) {
            setCancelBoutOpen(false);
          }
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          Remove Bout
        </DialogTitle>

        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will remove the bout from the active fight card,
            but it will remain in TNGOS records as cancelled.
          </Alert>

          {cancelBout && (
            <Typography fontWeight={900} sx={{ mb: 2 }}>
              {cancelBout.red?.legal_name || "Red Corner"}
              {" vs "}
              {cancelBout.blue?.legal_name || "Blue Corner"}
            </Typography>
          )}

          <TextField
            autoFocus
            required
            fullWidth
            multiline
            minRows={4}
            label="Reason / Notes"
            placeholder="Example: Opponent withdrew, purse disagreement, medical issue, weight issue..."
            value={cancelBoutNotes}
            onChange={(e) =>
              setCancelBoutNotes(e.target.value)
            }
            helperText="Required. This note will stay with the bout record."
          />
        </DialogContent>

        <DialogActions>
          <Button
            disabled={cancelBoutWorking}
            onClick={() => {
              setCancelBoutOpen(false);
              setCancelBout(null);
              setCancelBoutNotes("");
            }}
          >
            Keep Bout
          </Button>

          <Button
            variant="contained"
            color="error"
            disabled={
              cancelBoutWorking ||
              !cancelBoutNotes.trim()
            }
            onClick={submitBoutCancellation}
          >
            {cancelBoutWorking
              ? "Removing..."
              : "Remove Bout"}
          </Button>
        </DialogActions>
      </Dialog>


    </Box>
  );
}
