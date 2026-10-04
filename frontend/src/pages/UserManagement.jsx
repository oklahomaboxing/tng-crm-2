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

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

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
    [fighter?.first_name, fighter?.last_name].filter(Boolean).join(" ") ||
    `Fighter #${fighter?.id || ""}`
  );
}

export default function UserManagement() {
  const [role, setRole] = useState("staff");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [referralSlug, setReferralSlug] = useState("");

  const [managerUsers, setManagerUsers] = useState([]);
  const [managers, setManagers] = useState([]);
  const [fighters, setFighters] = useState([]);

  const [selectedManagerUserId, setSelectedManagerUserId] = useState("");
  const [selectedManagerId, setSelectedManagerId] = useState("");
  const [selectedFighterId, setSelectedFighterId] = useState("");

  const [managerForm, setManagerForm] = useState({
    display_name: "",
    company_name: "",
    phone: "",
    email: "",
    license_number: "",
    license_state: "",
    notes: "",
    active: true,
  });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingManagers, setLoadingManagers] = useState(false);

  const selectedManager = useMemo(
    () =>
      managers.find(
        (row) => Number(row.id) === Number(selectedManagerId)
      ) || null,
    [managers, selectedManagerId]
  );

  async function request(pathname, options = {}) {
    const response = await fetch(`${API}${pathname}`, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        data.message ||
        "Request failed"
      );
    }

    return data;
  }

  async function loadManagerData({ silent = false } = {}) {
    if (!silent) setLoadingManagers(true);

    try {
      const [managerData, userData, fighterData] =
        await Promise.all([
          request("/api/boxing/manager-admin"),
          request("/api/boxing/manager-admin/eligible-users"),
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
      if (!silent) setLoadingManagers(false);
    }
  }

  useEffect(() => {
    loadManagerData();
  }, []);

  useEffect(() => {
    if (!selectedManager) return;

    setManagerForm({
      display_name:
        selectedManager.display_name || "",
      company_name:
        selectedManager.company_name || "",
      phone:
        selectedManager.phone || "",
      email:
        selectedManager.email || "",
      license_number:
        selectedManager.license_number || "",
      license_state:
        selectedManager.license_state || "",
      notes:
        selectedManager.notes || "",
      active:
        Boolean(selectedManager.active),
    });

    setSelectedManagerUserId(
      selectedManager.user_id || ""
    );
  }, [selectedManager]);

  async function createUser() {
    setMessage("");
    setError("");

    if (!name.trim() || !email.trim() || !password) {
      setError(
        "Name, email, and password are required."
      );
      return;
    }

    if (
      role === "rep" &&
      !referralSlug.trim()
    ) {
      setError(
        "Referral slug is required for sales reps."
      );
      return;
    }

    setSaving(true);

    try {
      const body = {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
        phone: "",
        referral_slug:
          role === "rep"
            ? referralSlug.trim().toLowerCase()
            : "",
      };

      const data = await request("/api/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const roleLabels = {
        staff: "Staff member",
        rep: "Sales rep",
        manager: "Manager",
        matchmaker: "Matchmaker",
      };

      setMessage(
        `${roleLabels[role] || "User"} ${
          data.name || name
        } created successfully.`
      );

      setName("");
      setEmail("");
      setPassword("");
      setReferralSlug("");

      if (role === "manager") {
        await loadManagerData({ silent: true });
      }
    } catch (err) {
      setError(
        err.message ||
        "Could not create user."
      );
    } finally {
      setSaving(false);
    }
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
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_id:
              Number(selectedManagerUserId),
            ...managerForm,
          }),
        }
      );

      setMessage(
        data.message ||
        "Manager profile saved."
      );

      await loadManagerData({
        silent: true,
      });

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

  function chooseManagerUser(userId) {
    setSelectedManagerUserId(userId);

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
      display_name:
        user?.name || "",
      company_name: "",
      phone: "",
      email:
        user?.email || "",
      license_number: "",
      license_state: "",
      notes: "",
      active: true,
    });
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
            "Content-Type": "application/json",
          },
          body: JSON.stringify({}),
        }
      );

      setMessage(
        data.message ||
        "Fighter assigned."
      );

      setSelectedFighterId("");

      await loadManagerData({
        silent: true,
      });
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

      await loadManagerData({
        silent: true,
      });
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
      <Typography
        variant="h4"
        fontWeight="bold"
        sx={{ mb: 3 }}
      >
        User Management
      </Typography>

      {message && (
        <Alert
          severity="success"
          onClose={() => setMessage("")}
          sx={{ mb: 2 }}
        >
          {message}
        </Alert>
      )}

      {error && (
        <Alert
          severity="error"
          onClose={() => setError("")}
          sx={{ mb: 2 }}
        >
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} lg={5}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography
                variant="h6"
                fontWeight={900}
                sx={{ mb: 2 }}
              >
                Create User
              </Typography>

              <Stack spacing={2}>
                <TextField
                  select
                  label="User Role"
                  value={role}
                  onChange={(event) =>
                    setRole(event.target.value)
                  }
                  fullWidth
                >
                  <MenuItem value="staff">
                    Staff
                  </MenuItem>

                  <MenuItem value="rep">
                    Sales Rep
                  </MenuItem>

                  <MenuItem value="manager">
                    Manager
                  </MenuItem>

                  <MenuItem value="matchmaker">
                    Matchmaker
                  </MenuItem>
                </TextField>

                <TextField
                  label="Full Name"
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  fullWidth
                />

                <TextField
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  fullWidth
                />

                <TextField
                  label="Temporary Password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  fullWidth
                />

                {role === "rep" && (
                  <TextField
                    label="Referral Slug"
                    helperText="Example: john-smith"
                    value={referralSlug}
                    onChange={(event) =>
                      setReferralSlug(
                        event.target.value
                      )
                    }
                    fullWidth
                  />
                )}

                <Button
                  variant="contained"
                  color="error"
                  onClick={createUser}
                  disabled={saving}
                  sx={{ py: 1.5 }}
                >
                  {saving
                    ? "Creating..."
                    : "Create User"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Stack
                direction={{
                  xs: "column",
                  sm: "row",
                }}
                justifyContent="space-between"
                spacing={2}
                sx={{ mb: 2 }}
              >
                <Box>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Manager Administration
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Link manager users to fighter profiles and manage their roster.
                  </Typography>
                </Box>

                <Chip
                  label={`${managers.length} Manager Profiles`}
                  color="primary"
                  variant="outlined"
                />
              </Stack>

              {loadingManagers ? (
                <Typography color="text.secondary">
                  Loading manager data...
                </Typography>
              ) : (
                <Stack spacing={2}>
                  <TextField
                    select
                    label="Manager User"
                    value={
                      selectedManagerUserId
                    }
                    onChange={(event) =>
                      chooseManagerUser(
                        event.target.value
                      )
                    }
                    fullWidth
                  >
                    {managerUsers.map(
                      (user) => (
                        <MenuItem
                          key={user.id}
                          value={user.id}
                        >
                          {user.name} ? {user.email}
                          {user.manager_profile_exists
                            ? " ? Profile Active"
                            : " ? Needs Profile"}
                        </MenuItem>
                      )
                    )}
                  </TextField>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
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

                    <Grid item xs={12} sm={6}>
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

                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Phone"
                        fullWidth
                        value={managerForm.phone}
                        onChange={(event) =>
                          setManagerForm({
                            ...managerForm,
                            phone:
                              event.target.value,
                          })
                        }
                      />
                    </Grid>

                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Manager Email"
                        fullWidth
                        value={managerForm.email}
                        onChange={(event) =>
                          setManagerForm({
                            ...managerForm,
                            email:
                              event.target.value,
                          })
                        }
                      />
                    </Grid>

                    <Grid item xs={12} sm={6}>
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

                    <Grid item xs={12} sm={6}>
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
                    disabled={
                      saving ||
                      !selectedManagerUserId
                    }
                    onClick={saveManagerProfile}
                  >
                    {selectedManager
                      ? "Save Manager Profile"
                      : "Create Manager Profile"}
                  </Button>

                  {selectedManager && (
                    <>
                      <Divider sx={{ my: 1 }} />

                      <Typography
                        fontWeight={900}
                      >
                        Fighter Roster
                      </Typography>

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
                          disabled={
                            saving ||
                            !selectedFighterId
                          }
                          onClick={assignFighter}
                          sx={{
                            minWidth: 150,
                          }}
                        >
                          Assign
                        </Button>
                      </Stack>

                      {!selectedManager
                        .active_fighters
                        ?.length ? (
                        <Alert severity="info">
                          No fighters are currently assigned to this manager.
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
                                  borderRadius: 2,
                                }}
                              >
                                <Box>
                                  <Typography
                                    fontWeight={
                                      850
                                    }
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
        </Grid>
      </Grid>
    </Box>
  );
}
