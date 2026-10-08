import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import PersonAddAlt1RoundedIcon from "@mui/icons-material/PersonAddAlt1Rounded";

const API = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

function authHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${localStorage.getItem("token")}`,
    ...extra,
  };
}

function fighterName(fighter) {
  return (
    fighter?.legal_name ||
    fighter?.name ||
    fighter?.fighter_name ||
    [fighter?.first_name, fighter?.last_name]
      .filter(Boolean)
      .join(" ") ||
    `Fighter #${fighter?.id || ""}`
  );
}

const EMPTY_MANAGER = {
  display_name: "",
  company_name: "",
  phone: "",
  email: "",
  license_number: "",
  license_state: "",
  notes: "",
  active: true,
};

export default function PromoterManagersPage({ onBack }) {
  const [managerUsers, setManagerUsers] = useState([]);
  const [managers, setManagers] = useState([]);
  const [fighters, setFighters] = useState([]);

  const [selectedManagerUserId, setSelectedManagerUserId] =
    useState("");
  const [selectedManagerId, setSelectedManagerId] =
    useState("");
  const [selectedFighterId, setSelectedFighterId] =
    useState("");

  const [managerForm, setManagerForm] =
    useState(EMPTY_MANAGER);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedManager = useMemo(
    () =>
      managers.find(
        (row) =>
          Number(row.id) === Number(selectedManagerId)
      ) || null,
    [managers, selectedManagerId]
  );

  const activeManagers = useMemo(
    () =>
      managers.filter((manager) =>
        Boolean(manager.active)
      ).length,
    [managers]
  );

  const assignedFighters = useMemo(
    () =>
      managers.reduce(
        (total, manager) =>
          total +
          (manager.active_fighters?.length || 0),
        0
      ),
    [managers]
  );

  async function request(pathname, options = {}) {
    const response = await fetch(`${API}${pathname}`, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
          data.message ||
          "Request failed"
      );
    }

    return data;
  }

  async function loadData({ silent = false } = {}) {
    if (!silent) setLoading(true);

    setError("");

    try {
      const [managerData, userData, fighterData] =
        await Promise.all([
          request("/api/boxing/manager-admin"),
          request(
            "/api/boxing/manager-admin/eligible-users"
          ),
          request("/api/boxing/fighters"),
        ]);

      setManagers(
        Array.isArray(managerData)
          ? managerData
          : []
      );

      setManagerUsers(
        Array.isArray(userData)
          ? userData
          : []
      );

      setFighters(
        Array.isArray(fighterData)
          ? fighterData
          : []
      );
    } catch (err) {
      setError(
        err.message ||
          "Could not load manager administration data."
      );
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedManager) return;

    setManagerForm({
      display_name:
        selectedManager.display_name || "",
      company_name:
        selectedManager.company_name || "",
      phone: selectedManager.phone || "",
      email: selectedManager.email || "",
      license_number:
        selectedManager.license_number || "",
      license_state:
        selectedManager.license_state || "",
      notes: selectedManager.notes || "",
      active: Boolean(selectedManager.active),
    });

    setSelectedManagerUserId(
      selectedManager.user_id || ""
    );
  }, [selectedManager]);

  function chooseManagerUser(userId) {
    setSelectedManagerUserId(userId);
    setMessage("");
    setError("");

    const existing = managers.find(
      (manager) =>
        Number(manager.user_id) ===
        Number(userId)
    );

    if (existing) {
      setSelectedManagerId(
        String(existing.id)
      );
      return;
    }

    const user = managerUsers.find(
      (row) =>
        Number(row.id) === Number(userId)
    );

    setSelectedManagerId("");

    setManagerForm({
      ...EMPTY_MANAGER,
      display_name: user?.name || "",
      email: user?.email || "",
    });
  }

  async function saveManagerProfile() {
    if (!selectedManagerUserId) {
      setError("Choose a manager user.");
      return;
    }

    setSaving(true);
    setMessage("");
    setError("");

    try {
      const data = await request(
        "/api/boxing/manager-admin",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            user_id: Number(
              selectedManagerUserId
            ),
            ...managerForm,
          }),
        }
      );

      setMessage(
        data.message ||
          "Manager profile saved."
      );

      await loadData({ silent: true });

      if (data.id) {
        setSelectedManagerId(
          String(data.id)
        );
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not save manager profile."
      );
    } finally {
      setSaving(false);
    }
  }

  async function assignFighter() {
    if (!selectedManagerId) {
      setError(
        "Save or select a manager profile first."
      );
      return;
    }

    if (!selectedFighterId) {
      setError("Choose a fighter.");
      return;
    }

    setSaving(true);
    setMessage("");
    setError("");

    try {
      const data = await request(
        `/api/boxing/manager-admin/${selectedManagerId}/fighters/${selectedFighterId}`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({}),
        }
      );

      setMessage(
        data.message ||
          "Fighter assigned."
      );

      setSelectedFighterId("");

      await loadData({ silent: true });
    } catch (err) {
      setError(
        err.message ||
          "Could not assign fighter."
      );
    } finally {
      setSaving(false);
    }
  }

  async function releaseFighter(fighterId) {
    if (!selectedManagerId) return;

    if (
      !window.confirm(
        "Release this fighter from the manager?"
      )
    ) {
      return;
    }

    setSaving(true);
    setMessage("");
    setError("");

    try {
      const data = await request(
        `/api/boxing/manager-admin/${selectedManagerId}/fighters/${fighterId}`,
        {
          method: "DELETE",
        }
      );

      setMessage(
        data.message ||
          "Fighter released."
      );

      await loadData({ silent: true });
    } catch (err) {
      setError(
        err.message ||
          "Could not release fighter."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Box>
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
        sx={{ mb: 3 }}
      >
        <Box>
          <Button
            startIcon={
              <ArrowBackRoundedIcon />
            }
            onClick={onBack}
            sx={{
              px: 0,
              mb: 1,
              color: "text.secondary",
              fontWeight: 850,
            }}
          >
            Promoter Home
          </Button>

          <Typography
            variant="h3"
            fontWeight={950}
            sx={{
              fontSize: {
                xs: 30,
                md: 40,
              },
              letterSpacing: "-0.04em",
            }}
          >
            Managers
          </Typography>

          <Typography
            color="text.secondary"
            sx={{
              mt: 0.5,
              maxWidth: 760,
            }}
          >
            Manage manager profiles,
            licensing information, fighter
            assignments, and active rosters.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={
            <GroupsRoundedIcon />
          }
          onClick={() =>
            loadData({ silent: false })
          }
          sx={{ fontWeight: 850 }}
        >
          Refresh Managers
        </Button>
      </Stack>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
        >
          {error}
        </Alert>
      )}

      {message && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
        >
          {message}
        </Alert>
      )}

      <Grid
        container
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Grid item xs={12} sm={4}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
              >
                Manager Profiles
              </Typography>

              <Typography
                variant="h4"
                fontWeight={950}
              >
                {managers.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
              >
                Active Managers
              </Typography>

              <Typography
                variant="h4"
                fontWeight={950}
              >
                {activeManagers}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
              >
                Fighter Assignments
              </Typography>

              <Typography
                variant="h4"
                fontWeight={950}
              >
                {assignedFighters}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card
        sx={{
          borderRadius: 3.5,
          border: "1px solid",
          borderColor: "divider",
          boxShadow:
            "0 8px 30px rgba(0,0,0,.05)",
        }}
      >
        <CardContent
          sx={{
            p: {
              xs: 2.5,
              md: 3,
            },
          }}
        >
          <Stack
            direction={{
              xs: "column",
              sm: "row",
            }}
            justifyContent="space-between"
            spacing={2}
            sx={{ mb: 2.5 }}
          >
            <Box>
              <Typography
                variant="h5"
                fontWeight={950}
              >
                Manager Administration
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
              >
                Select a manager account,
                maintain the promoter-facing
                profile, and control the
                manager's fighter roster.
              </Typography>
            </Box>

            <Chip
              label={`${managers.length} Profiles`}
              variant="outlined"
              sx={{ fontWeight: 850 }}
            />
          </Stack>

          {loading ? (
            <Typography color="text.secondary">
              Loading manager data...
            </Typography>
          ) : (
            <Stack spacing={2.5}>
              <TextField
                select
                fullWidth
                label="Manager User"
                value={
                  selectedManagerUserId
                }
                onChange={(event) =>
                  chooseManagerUser(
                    event.target.value
                  )
                }
              >
                {managerUsers.map((user) => (
                  <MenuItem
                    key={user.id}
                    value={user.id}
                  >
                    {user.name} - {user.email}
                    {user.manager_profile_exists
                      ? " - Profile Active"
                      : " - Needs Profile"}
                  </MenuItem>
                ))}
              </TextField>

              {!managerUsers.length && (
                <Alert severity="info">
                  No manager-role users are
                  available yet. Create a
                  manager user in User
                  Management first.
                </Alert>
              )}

              <Grid
                container
                spacing={2}
              >
                <Grid
                  item
                  xs={12}
                  sm={6}
                >
                  <TextField
                    label="Display Name"
                    fullWidth
                    value={
                      managerForm.display_name
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        display_name:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={6}
                >
                  <TextField
                    label="Company"
                    fullWidth
                    value={
                      managerForm.company_name
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        company_name:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={6}
                >
                  <TextField
                    label="Phone"
                    fullWidth
                    value={
                      managerForm.phone
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        phone:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={6}
                >
                  <TextField
                    label="Manager Email"
                    fullWidth
                    value={
                      managerForm.email
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        email:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={4}
                >
                  <TextField
                    label="License Number"
                    fullWidth
                    value={
                      managerForm.license_number
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        license_number:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={4}
                >
                  <TextField
                    label="License State"
                    fullWidth
                    value={
                      managerForm.license_state
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        license_state:
                          event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  sm={4}
                >
                  <TextField
                    select
                    label="Status"
                    fullWidth
                    value={
                      managerForm.active
                        ? "active"
                        : "inactive"
                    }
                    onChange={(event) =>
                      setManagerForm({
                        ...managerForm,
                        active:
                          event.target.value ===
                          "active",
                      })
                    }
                  >
                    <MenuItem value="active">
                      Active
                    </MenuItem>

                    <MenuItem value="inactive">
                      Inactive
                    </MenuItem>
                  </TextField>
                </Grid>
              </Grid>

              <TextField
                label="Manager Notes"
                fullWidth
                multiline
                minRows={2}
                value={managerForm.notes}
                onChange={(event) =>
                  setManagerForm({
                    ...managerForm,
                    notes:
                      event.target.value,
                  })
                }
              />

              <Button
                variant="contained"
                color="error"
                startIcon={
                  <PersonAddAlt1RoundedIcon />
                }
                disabled={
                  saving ||
                  !selectedManagerUserId
                }
                onClick={
                  saveManagerProfile
                }
                sx={{
                  alignSelf: "flex-start",
                  fontWeight: 900,
                  px: 2.5,
                }}
              >
                {selectedManager
                  ? "Save Manager Profile"
                  : "Create Manager Profile"}
              </Button>

              {selectedManager && (
                <>
                  <Divider sx={{ my: 1 }} />

                  <Stack
                    direction={{
                      xs: "column",
                      sm: "row",
                    }}
                    justifyContent="space-between"
                    alignItems={{
                      xs: "stretch",
                      sm: "center",
                    }}
                    spacing={1}
                  >
                    <Box>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        Fighter Roster
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        Assign or release
                        fighters represented by
                        this manager.
                      </Typography>
                    </Box>

                    <Chip
                      size="small"
                      label={`${
                        selectedManager
                          .active_fighters
                          ?.length || 0
                      } Fighters`}
                      sx={{ fontWeight: 850 }}
                    />
                  </Stack>

                  <Stack
                    direction={{
                      xs: "column",
                      sm: "row",
                    }}
                    spacing={1}
                  >
                    <TextField
                      select
                      label="Assign Fighter"
                      value={
                        selectedFighterId
                      }
                      onChange={(event) =>
                        setSelectedFighterId(
                          event.target.value
                        )
                      }
                      fullWidth
                    >
                      {fighters.map(
                        (fighter) => (
                          <MenuItem
                            key={fighter.id}
                            value={fighter.id}
                          >
                            {fighterName(
                              fighter
                            )}
                          </MenuItem>
                        )
                      )}
                    </TextField>

                    <Button
                      variant="contained"
                      color="error"
                      disabled={
                        saving ||
                        !selectedFighterId
                      }
                      onClick={
                        assignFighter
                      }
                      sx={{
                        minWidth: 150,
                        fontWeight: 900,
                      }}
                    >
                      Assign
                    </Button>
                  </Stack>

                  {!selectedManager
                    .active_fighters
                    ?.length ? (
                    <Alert severity="info">
                      No fighters are
                      currently assigned to
                      this manager.
                    </Alert>
                  ) : (
                    <Stack spacing={1}>
                      {selectedManager.active_fighters.map(
                        (assignment) => (
                          <Box
                            key={
                              assignment.assignment_id
                            }
                            sx={{
                              display: "flex",
                              alignItems:
                                "center",
                              justifyContent:
                                "space-between",
                              gap: 2,
                              p: 1.5,
                              border:
                                "1px solid",
                              borderColor:
                                "divider",
                              borderRadius: 2.5,
                            }}
                          >
                            <Box>
                              <Typography
                                fontWeight={900}
                              >
                                {fighterName(
                                  assignment.fighter
                                )}
                              </Typography>

                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                Assigned{" "}
                                {assignment.assigned_at
                                  ? new Date(
                                      assignment.assigned_at
                                    ).toLocaleDateString()
                                  : "-"}
                              </Typography>
                            </Box>

                            <Button
                              size="small"
                              color="error"
                              variant="outlined"
                              disabled={saving}
                              onClick={() =>
                                releaseFighter(
                                  assignment.fighter_id
                                )
                              }
                              sx={{
                                fontWeight: 850,
                              }}
                            >
                              Release
                            </Button>
                          </Box>
                        )
                      )}
                    </Stack>
                  )}
                </>
              )}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
