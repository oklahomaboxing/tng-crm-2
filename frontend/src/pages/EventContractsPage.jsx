import React from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  Grid,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

export default function EventContractsPage({
  activeBouts,
  expandedBouts,
  setExpandedBouts,
  setData,
  updateBoutPurse,
  contractWeights,
  setContractWeights,
  contractCommissions,
  setContractCommissions,
  contractTravelValue,
  setContractTravelValue,
  contractTermsSaving,
  saveContractTerms,
  sendContractWithDocuSign,
  syncDocuSignContract,
  viewOfficialContractPdf,
  sendContractEmail,
  uploadSignedContract,
  downloadSignedContract,
  generateContract,
}) {
  return (
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
                    <Box>
                      <Typography
                        variant="overline"
                        sx={{
                          fontWeight: 950,
                          letterSpacing: 1.8,
                          color: "text.secondary",
                        }}
                      >
                        BOUT {bout.bout_order || index + 1}
                      </Typography>

                      <Typography
                        variant="h5"
                        fontWeight={950}
                        sx={{
                          mt: -0.25,
                          lineHeight: 1.15,
                        }}
                      >
                        {bout.red?.legal_name || "Red Corner"}
                        {"  vs  "}
                        {bout.blue?.legal_name || "Blue Corner"}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.5 }}
                      >
                        Contract, purse and fighter logistics
                      </Typography>
                    </Box>


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
                                `RED: ${bout.red?.legal_name || "Fighter"} - First 5 Fight ${bout.red_series.next_fight_number} of ${bout.red_series.target_fights}`
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
                                `BLUE: ${bout.blue?.legal_name || "Fighter"} - First 5 Fight ${bout.blue_series.next_fight_number} of ${bout.blue_series.target_fights}`
                              }
                            />
                          )}
                      </Stack>
                    )}


                  </Stack>

                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    alignItems={{ xs: "stretch", md: "center" }}
                    justifyContent="space-between"
                    sx={{
                      mt: 2,
                      p: 1.5,
                      borderRadius: 2.5,
                      bgcolor: "action.hover",
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Stack
                      direction="row"
                      spacing={1}
                      flexWrap="wrap"
                      useFlexGap
                    >
                      <Chip
                        size="small"
                        label={`${
                          bout.weight_agreed
                            ? `${bout.weight_agreed} LB`
                            : "WEIGHT TBD"
                        }`}
                        sx={{ fontWeight: 900 }}
                      />

                      <Chip
                        size="small"
                        variant="outlined"
                        label={`${bout.rounds || "-"} ROUNDS`}
                        sx={{ fontWeight: 800 }}
                      />

                      <Chip
                        size="small"
                        label={`TOTAL PURSE $${(
                          Number(bout.red_purse || 0) +
                          Number(bout.blue_purse || 0)
                        ).toLocaleString()}`}
                        sx={{ fontWeight: 900 }}
                      />

                      <Chip
                        size="small"
                        variant="outlined"
                        label={`RED: ${
                          bout.red_contract?.status
                            ? String(bout.red_contract.status)
                                .replaceAll("_", " ")
                                .toUpperCase()
                            : "NOT SENT"
                        }`}
                      />

                      <Chip
                        size="small"
                        variant="outlined"
                        label={`BLUE: ${
                          bout.blue_contract?.status
                            ? String(bout.blue_contract.status)
                                .replaceAll("_", " ")
                                .toUpperCase()
                            : "NOT SENT"
                        }`}
                      />
                    </Stack>

                    <Button
                      size="small"
                      variant={
                        expandedBouts[bout.id] ?? (index === 0)
                          ? "contained"
                          : "outlined"
                      }
                      onClick={() =>
                        setExpandedBouts((old) => ({
                          ...old,
                          [bout.id]: !(
                            old[bout.id] ?? (index === 0)
                          ),
                        }))
                      }
                      sx={{
                        minWidth: 140,
                        fontWeight: 900,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {expandedBouts[bout.id] ?? (index === 0)
                        ? "Hide Details"
                        : "Show Details"}
                    </Button>
                  </Stack>

                  <Collapse
                    in={expandedBouts[bout.id] ?? (index === 0)}
                    timeout="auto"
                    unmountOnExit
                  >
                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ mb: 1.5 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight={950}
                    >
                      Bout Financials
                    </Typography>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      Set each fighter's purse and review the total bout cost.
                    </Typography>
                  </Box>

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

                  <Box sx={{ mb: 2 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight={950}
                    >
                      Fighter Contract Details
                    </Typography>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 0.35 }}
                    >
                      Manage final fight weight, ticket commission,
                      travel, hotel, per diem and DocuSign status.
                      Saving either fighter's final weight updates
                      the entire bout.
                    </Typography>
                  </Box>

                  <Grid container spacing={2}>

                    <Grid item xs={12} md={6}>
                      <Card
                        variant="outlined"
                        sx={{
                          height: "100%",
                          borderRadius: 3,
                          borderTop: "5px solid #c62828",
                          background:
                            "linear-gradient(180deg, rgba(198,40,40,.045), rgba(255,255,255,0) 120px)",
                        }}
                      >
                        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
                          <Stack spacing={1.5}>

                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="center"
                              spacing={1}
                            >
                              <Typography
                                fontWeight={950}
                                sx={{
                                  color: "#c62828",
                                  letterSpacing: .6,
                                }}
                              >
                                RED CORNER
                              </Typography>

                              <Chip
                                size="small"
                                variant="outlined"
                                label="CONTRACT"
                                sx={{
                                  fontWeight: 900,
                                  fontSize: 10,
                                }}
                              />
                            </Stack>

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
                              ?.electronic_signature && (
                              <Alert
                                severity="success"
                                sx={{ mb: 1.5 }}
                              >
                                <strong>
                                  ELECTRONICALLY SIGNED
                                </strong>
                                <br />

                                Signed by:{" "}
                                <strong>
                                  {
                                    bout.red_contract
                                      .electronic_signature
                                      .typed_legal_name
                                  }
                                </strong>
                                <br />

                                Signed:{" "}
                                {bout.red_contract
                                  .electronic_signature
                                  .signed_at
                                  ? new Date(
                                      bout.red_contract
                                        .electronic_signature
                                        .signed_at
                                    ).toLocaleString()
                                  : "N/A"}
                                <br />

                                Verification Hash:
                                <br />
                                <span
                                  style={{
                                    fontFamily:
                                      "monospace",
                                    fontSize: 11,
                                    wordBreak:
                                      "break-all",
                                  }}
                                >
                                  {
                                    bout.red_contract
                                      .electronic_signature
                                      .snapshot_sha256
                                  }
                                </span>
                              </Alert>
                            )}

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
                              label="Final Fight Weight"
                              value={
                                contractWeights[bout.id] ??
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
                                    [bout.id]:
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
                              fontWeight={950}
                              sx={{
                                pt: 0.5,
                                letterSpacing: .2,
                              }}
                            >
                              Travel & Fighter Expenses
                            </Typography>

                            <Grid container spacing={1}>

                              <Grid item xs={12}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Ticket Sales Commission"
                                  value={
                                    contractCommissions[
                                      `${bout.id}-red`
                                    ] ??
                                    bout.red_contract
                                      ?.ticket_commission_percent ??
                                    ""
                                  }
                                  inputProps={{
                                    min: 0,
                                    max: 100,
                                    step: 0.1,
                                  }}
                                  onChange={(e) =>
                                    setContractCommissions(
                                      (old) => ({
                                        ...old,
                                        [`${bout.id}-red`]:
                                          e.target.value,
                                      })
                                    )
                                  }
                                  InputProps={{
                                    endAdornment: (
                                      <InputAdornment position="end">
                                        %
                                      </InputAdornment>
                                    ),
                                  }}
                                  helperText="Negotiated ticket commission for this fighter"
                                />
                              </Grid>
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

                            {/* SEND WITH DOCUSIGN - RED */}

                            {bout.red_contract?.id && (
                              <>
                                <Typography
                                  variant="caption"
                                  sx={{
                                    fontWeight: 900,
                                    color:
                                      String(
                                        bout.red_contract
                                          ?.docusign_status || ""
                                      ).toUpperCase() ===
                                      "SIGNED"
                                        ? "success.main"
                                        : "text.secondary",
                                  }}
                                >
                                  DocuSign Status:{" "}
                                  {bout.red_contract
                                    ?.docusign_envelope_id
                                    ? String(
                                        bout.red_contract
                                          ?.docusign_status ||
                                          "SENT"
                                      ).replaceAll("_", " ")
                                    : "Not Sent"}
                                </Typography>

                                <Button
                                  variant="contained"
                                  disabled={
                                    Boolean(
                                      contractTermsSaving[
                                        `${bout.id}-red`
                                      ]
                                    )
                                  }
                                  onClick={() =>
                                    saveContractTerms(
                                      bout,
                                      "red"
                                    )
                                  }
                                  sx={{
                                    alignSelf: "flex-start",
                                    bgcolor: "#111",
                                    color: "#fff",
                                    fontWeight: 900,
                                    "&:hover": {
                                      bgcolor: "#2b2b2b",
                                    },
                                  }}
                                >
                                  {
                                    contractTermsSaving[
                                      `${bout.id}-red`
                                    ]
                                      ? "Saving..."
                                      : "Save Contract Terms"
                                  }
                                </Button>
                              </>
                            )}

                            {!bout.red_contract
                              ?.docusign_envelope_id ? (
                              <Button
                                variant="contained"
                                color="error"
                                disabled={
                                  !bout.red_contract?.id
                                }
                                onClick={() =>
                                  sendContractWithDocuSign(
                                    bout.red_contract?.id,
                                    bout.red?.legal_name ||
                                      "Red Corner"
                                  )
                                }
                              >
                                Send With DocuSign
                              </Button>
                            ) : (
                              <Button
                                variant="outlined"
                                color={
                                  String(
                                    bout.red_contract
                                      ?.docusign_status || ""
                                  ).toLowerCase() ===
                                  "completed"
                                    ? "success"
                                    : "warning"
                                }
                                onClick={() =>
                                  syncDocuSignContract(
                                    bout.red_contract?.id,
                                    bout.red?.legal_name ||
                                      "Red Corner"
                                  )
                                }
                              >
                                Sync Adobe
                              </Button>
                            )}

                            <Button
                              variant="outlined"
                              disabled={
                                !bout.red_contract?.id
                              }
                              onClick={() =>
                                viewOfficialContractPdf(
                                  bout.red_contract?.id
                                )
                              }
                            >
                              View Official PDF
                            </Button>

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
                      <Card
                        variant="outlined"
                        sx={{
                          height: "100%",
                          borderRadius: 3,
                          borderTop: "5px solid #1565c0",
                          background:
                            "linear-gradient(180deg, rgba(21,101,192,.045), rgba(255,255,255,0) 120px)",
                        }}
                      >
                        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
                          <Stack spacing={1.5}>

                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="center"
                              spacing={1}
                            >
                              <Typography
                                fontWeight={950}
                                sx={{
                                  color: "#1565c0",
                                  letterSpacing: .6,
                                }}
                              >
                                BLUE CORNER
                              </Typography>

                              <Chip
                                size="small"
                                variant="outlined"
                                label="CONTRACT"
                                sx={{
                                  fontWeight: 900,
                                  fontSize: 10,
                                }}
                              />
                            </Stack>

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
                              ?.electronic_signature && (
                              <Alert
                                severity="success"
                                sx={{ mb: 1.5 }}
                              >
                                <strong>
                                  ELECTRONICALLY SIGNED
                                </strong>
                                <br />

                                Signed by:{" "}
                                <strong>
                                  {
                                    bout.blue_contract
                                      .electronic_signature
                                      .typed_legal_name
                                  }
                                </strong>
                                <br />

                                Signed:{" "}
                                {bout.blue_contract
                                  .electronic_signature
                                  .signed_at
                                  ? new Date(
                                      bout.blue_contract
                                        .electronic_signature
                                        .signed_at
                                    ).toLocaleString()
                                  : "N/A"}
                                <br />

                                Verification Hash:
                                <br />
                                <span
                                  style={{
                                    fontFamily:
                                      "monospace",
                                    fontSize: 11,
                                    wordBreak:
                                      "break-all",
                                  }}
                                >
                                  {
                                    bout.blue_contract
                                      .electronic_signature
                                      .snapshot_sha256
                                  }
                                </span>
                              </Alert>
                            )}

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
                              label="Final Fight Weight"
                              value={
                                contractWeights[bout.id] ??
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
                                    [bout.id]:
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
                              fontWeight={950}
                              sx={{
                                pt: 0.5,
                                letterSpacing: .2,
                              }}
                            >
                              Travel & Fighter Expenses
                            </Typography>

                            <Grid container spacing={1}>

                              <Grid item xs={12}>
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Ticket Sales Commission"
                                  value={
                                    contractCommissions[
                                      `${bout.id}-blue`
                                    ] ??
                                    bout.blue_contract
                                      ?.ticket_commission_percent ??
                                    ""
                                  }
                                  inputProps={{
                                    min: 0,
                                    max: 100,
                                    step: 0.1,
                                  }}
                                  onChange={(e) =>
                                    setContractCommissions(
                                      (old) => ({
                                        ...old,
                                        [`${bout.id}-blue`]:
                                          e.target.value,
                                      })
                                    )
                                  }
                                  InputProps={{
                                    endAdornment: (
                                      <InputAdornment position="end">
                                        %
                                      </InputAdornment>
                                    ),
                                  }}
                                  helperText="Negotiated ticket commission for this fighter"
                                />
                              </Grid>
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

                            {/* SEND WITH DOCUSIGN - BLUE */}

                            {bout.blue_contract?.id && (
                              <>
                                <Typography
                                  variant="caption"
                                  sx={{
                                    fontWeight: 900,
                                    color:
                                      String(
                                        bout.blue_contract
                                          ?.docusign_status || ""
                                      ).toUpperCase() ===
                                      "SIGNED"
                                        ? "success.main"
                                        : "text.secondary",
                                  }}
                                >
                                  DocuSign Status:{" "}
                                  {bout.blue_contract
                                    ?.docusign_envelope_id
                                    ? String(
                                        bout.blue_contract
                                          ?.docusign_status ||
                                          "SENT"
                                      ).replaceAll("_", " ")
                                    : "Not Sent"}
                                </Typography>

                                <Button
                                  variant="contained"
                                  disabled={
                                    Boolean(
                                      contractTermsSaving[
                                        `${bout.id}-blue`
                                      ]
                                    )
                                  }
                                  onClick={() =>
                                    saveContractTerms(
                                      bout,
                                      "blue"
                                    )
                                  }
                                  sx={{
                                    alignSelf: "flex-start",
                                    bgcolor: "#111",
                                    color: "#fff",
                                    fontWeight: 900,
                                    "&:hover": {
                                      bgcolor: "#2b2b2b",
                                    },
                                  }}
                                >
                                  {
                                    contractTermsSaving[
                                      `${bout.id}-blue`
                                    ]
                                      ? "Saving..."
                                      : "Save Contract Terms"
                                  }
                                </Button>
                              </>
                            )}

                            {!bout.blue_contract
                              ?.docusign_envelope_id ? (
                              <Button
                                variant="contained"
                                color="error"
                                disabled={
                                  !bout.blue_contract?.id
                                }
                                onClick={() =>
                                  sendContractWithDocuSign(
                                    bout.blue_contract?.id,
                                    bout.blue?.legal_name ||
                                      "Blue Corner"
                                  )
                                }
                              >
                                Send With DocuSign
                              </Button>
                            ) : (
                              <Button
                                variant="outlined"
                                color={
                                  String(
                                    bout.blue_contract
                                      ?.docusign_status || ""
                                  ).toLowerCase() ===
                                  "completed"
                                    ? "success"
                                    : "warning"
                                }
                                onClick={() =>
                                  syncDocuSignContract(
                                    bout.blue_contract?.id,
                                    bout.blue?.legal_name ||
                                      "Blue Corner"
                                  )
                                }
                              >
                                Sync Adobe
                              </Button>
                            )}

                            <Button
                              variant="outlined"
                              disabled={
                                !bout.blue_contract?.id
                              }
                              onClick={() =>
                                viewOfficialContractPdf(
                                  bout.blue_contract?.id
                                )
                              }
                            >
                              View Official PDF
                            </Button>

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
                        {bout.red?.boxrec_id || "Not provided"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.red?.phone || "Not provided"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.red?.email || "Not provided"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.red?.manager_name ||
                          "Not provided"}
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
                          "Not provided"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.blue?.phone || "Not provided"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.blue?.email || "Not provided"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.blue?.manager_name ||
                          "Not provided"}
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
                                  </Collapse>
                </CardContent>
              </Card>
            ))}
          </Stack>
  );
}
