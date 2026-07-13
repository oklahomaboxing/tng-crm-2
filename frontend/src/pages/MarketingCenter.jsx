import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import {
  CloudUpload,
  Email,
  Group,
  Search,
  Send,
  Sms,
} from "@mui/icons-material";

const API =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const CAMPAIGN_PRESETS = [
  {
    id: "youth-boxing",
    name: "Youth Boxing",
    prompt:
      "Create a marketing campaign promoting TNG Youth Boxing for children ages 8 through 14. Focus on confidence, discipline, fitness, self-defense, and positive coaching. Include the TNG Boxing slogan Earned Not Given.",
  },
  {
    id: "adult-boxing",
    name: "Adult Boxing",
    prompt:
      "Create a marketing campaign promoting TNG adult boxing classes. Focus on fitness, boxing skills, stress relief, discipline, weight loss, and beginner-friendly training. Include the slogan Earned Not Given.",
  },
  {
    id: "fight-night",
    name: "Fight Night",
    prompt:
      "Create an exciting marketing campaign promoting an upcoming TNG Boxing fight night. Encourage people to purchase tickets, bring friends and family, and support local fighters. Make the message exciting and professional.",
  },
  {
    id: "membership",
    name: "Membership Special",
    prompt:
      "Create a marketing campaign promoting a limited-time TNG Boxing membership special. Emphasize professional coaching, boxing classes, fitness, youth programs, and the slogan Earned Not Given.",
  },
  {
    id: "grand-opening",
    name: "Grand Opening",
    prompt:
      "Create a marketing campaign promoting the TNG Boxing grand opening at 8416 NW Expressway in Oklahoma City, next to Crunch Fitness. Invite families, athletes, beginners, and community supporters. Include the slogan Earned Not Given.",
  },
  {
    id: "sponsorship",
    name: "Sponsorship",
    prompt:
      "Create a professional sponsorship campaign for TNG Boxing. Explain that sponsors support youth development, amateur and professional boxing, community programs, uniforms, equipment, and events. Include a strong call to action for local businesses.",
  },
  {
    id: "nexgen-nutrition",
    name: "NexGen Nutrition",
    prompt:
      "Create a marketing campaign promoting NexGen Nutrition inside TNG Boxing. Promote healthy shakes, energizing teas, fitness support, and convenient service next to Crunch Fitness.",
  },
];

export default function MarketingCenter() {
  const [tab, setTab] = useState(0);
  const [contacts, setContacts] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [emailDialogOpen, setEmailDialogOpen] =
    useState(false);

  const [smsDialogOpen, setSmsDialogOpen] =
    useState(false);

  const [emailCampaign, setEmailCampaign] = useState({
    name: "",
    subject: "",
    body: "",
  });

  const [smsCampaign, setSmsCampaign] = useState({
    name: "",
    message: "",
  });

  const [aiLoading, setAiLoading] = useState(false);
  const [generatedSubject, setGeneratedSubject] = useState("");
  const [aiPrompt, setAiPrompt] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [generatedEmail, setGeneratedEmail] = useState("");

  const [generatedSms, setGeneratedSms] = useState("");

  const [generatedSocial, setGeneratedSocial] = useState("");


  const token = localStorage.getItem("token");

  async function loadContacts() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/marketing/contacts`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Contacts could not be loaded."
        );
      }

      setContacts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Contacts could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadContacts();
  }, []);


  const availableTags = useMemo(() => {
    const tags = new Set();

    contacts.forEach((contact) => {
      if (Array.isArray(contact.tags)) {
        contact.tags.forEach((tag) => tags.add(tag));
      }
    });

    return Array.from(tags).sort();
  }, [contacts]);

  const filteredContacts = useMemo(() => {
    const term = search.trim().toLowerCase();

    return contacts.filter((contact) => {
      const contactTags = Array.isArray(contact.tags)
        ? contact.tags
        : [];

      const matchesTag =
        tagFilter === "all" ||
        contactTags.includes(tagFilter);

      const searchableText = [
        contact.first_name,
        contact.last_name,
        contact.email,
        contact.phone,
        contact.company,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !term || searchableText.includes(term);

      return matchesTag && matchesSearch;
    });
  }, [contacts, search, tagFilter]);

  const emailContactCount = contacts.filter(
    (contact) => contact.email
  ).length;

  const phoneContactCount = contacts.filter(
    (contact) => contact.phone
  ).length;

  const selectedContacts = contacts.filter((contact) =>
    selectedIds.includes(contact.id)
  );

  function toggleContact(contactId) {
    setSelectedIds((current) =>
      current.includes(contactId)
        ? current.filter((id) => id !== contactId)
        : [...current, contactId]
    );
  }

  function toggleAllVisible() {
    const visibleIds = filteredContacts.map(
      (contact) => contact.id
    );

    const allVisibleSelected =
      visibleIds.length > 0 &&
      visibleIds.every((id) =>
        selectedIds.includes(id)
      );

    if (allVisibleSelected) {
      setSelectedIds((current) =>
        current.filter(
          (id) => !visibleIds.includes(id)
        )
      );
    } else {
      setSelectedIds((current) => [
        ...new Set([...current, ...visibleIds]),
      ]);
    }
  }

  async function importContacts(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setNotice("");
    setError("");

    try {
      const response = await fetch(
        `${API}/api/marketing/contacts/import`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Contact import failed."
        );
      }

      setNotice(
        `${data.imported || 0} contacts imported, ${
          data.updated || 0
        } updated, and ${data.skipped || 0} skipped.`
      );

      await loadContacts();
    } catch (err) {
      console.error(err);
      setError(err.message || "Contact import failed.");
    } finally {
      event.target.value = "";
      setLoading(false);
    }
  }

  function saveEmailDraft() {
    setNotice(
      `Email draft "${emailCampaign.name || "Untitled"}" prepared for ${selectedContacts.length} selected contacts.`
    );

    setEmailDialogOpen(false);
  }

  function saveSmsDraft() {
    setNotice(
      `Text draft "${smsCampaign.name || "Untitled"}" prepared for ${selectedContacts.length} selected contacts.`
    );

    setSmsDialogOpen(false);
  }

  function selectCampaignPreset(presetId) {
  const preset = CAMPAIGN_PRESETS.find(
    (item) => item.id === presetId
  );

  setSelectedPreset(presetId);

  if (preset) {
    setAiPrompt(preset.prompt);
  }
}

 async function generateCampaign() {
    if (!aiPrompt.trim()) {
      setError("Describe the campaign you want to create.");
      return;
    }

    setAiLoading(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API}/api/marketing/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            prompt: aiPrompt,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "AI campaign generation failed."
        );
      }

      setGeneratedSubject(data.subject || "");
      setGeneratedEmail(data.email || "");
      setGeneratedSms(data.sms || "");
      setGeneratedSocial(data.social || "");

      setEmailCampaign((current) => ({
        ...current,
        subject: data.subject || "",
        body: data.email || "",
      }));

      setSmsCampaign((current) => ({
        ...current,
        message: data.sms || "",
      }));

      setNotice("AI campaign generated successfully.");
    } catch (err) {
      setError(
        err.message || "AI campaign generation failed."
      );
    } finally {
      setAiLoading(false);
    }
  }
  return (
    <Box>
      <Typography variant="h4" fontWeight={900}>
        TNG Marketing Center
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mt: 0.5 }}
      >
        Import contacts and prepare mass email and text
        campaigns.
      </Typography>

      {notice && (
        <Alert
          severity="success"
          sx={{ mt: 2 }}
          onClose={() => setNotice("")}
        >
          {notice}
        </Alert>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ mt: 2 }}
          onClose={() => setError("")}
        >
          {error}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            lg: "repeat(4, 1fr)",
          },
          gap: 2,
          mt: 3,
        }}
      >
        <StatCard
          title="Total Contacts"
          value={contacts.length}
          icon={<Group />}
        />

        <StatCard
          title="Email Contacts"
          value={emailContactCount}
          icon={<Email />}
        />

        <StatCard
          title="Phone Contacts"
          value={phoneContactCount}
          icon={<Sms />}
        />

        <StatCard
          title="Selected"
          value={selectedIds.length}
          icon={<Send />}
        />
      </Box>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1.5,
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Box
              sx={{
                display: "flex",
                gap: 1,
                flexWrap: "wrap",
              }}
            >
              <Button
                variant="contained"
                component="label"
                startIcon={<CloudUpload />}
                disabled={loading}
              >
                Import Contacts

                <input
                  hidden
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={importContacts}
                />
              </Button>

              <Button
                variant="outlined"
                startIcon={<Email />}
                onClick={() => setEmailDialogOpen(true)}
              >
                New Email
              </Button>

              <Button
                variant="outlined"
                startIcon={<Sms />}
                onClick={() => setSmsDialogOpen(true)}
              >
                New Text
              </Button>
            </Box>

            <Typography color="text.secondary">
              {selectedIds.length} selected
            </Typography>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mt: 3 }}>
<Tabs
  value={tab}
  onChange={(_, value) => setTab(value)}
  variant="scrollable"
  scrollButtons="auto"
>
  <Tab label="Contacts" />
  <Tab label="AI Generator" />
  <Tab label="Email" />
  <Tab label="Text" />
  <Tab label="Templates" />
  <Tab label="History" />
  <Tab label="Analytics" />
</Tabs>

        <Divider />

        <CardContent>
          {tab === 0 && (
            <>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    md: "2fr 1fr",
                  },
                  gap: 2,
                  mb: 2,
                }}
              >
                <TextField
                  label="Search contacts"
                  value={search}
                  onChange={(event) =>
                    setSearch(event.target.value)
                  }
                  InputProps={{
                    startAdornment: (
                      <Search sx={{ mr: 1 }} />
                    ),
                  }}
                />

                <FormControl size="small">
                  <InputLabel>Filter by tag</InputLabel>

                  <Select
                    value={tagFilter}
                    label="Filter by tag"
                    onChange={(event) =>
                      setTagFilter(event.target.value)
                    }
                  >
                    <MenuItem value="all">
                      All tags
                    </MenuItem>

                    {availableTags.map((tag) => (
                      <MenuItem
                        key={tag}
                        value={tag}
                      >
                        {tag}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>

              {loading ? (
                <Box
                  sx={{
                    minHeight: 240,
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <CircularProgress />
                </Box>
              ) : (
                <Box
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    overflowX: "auto",
                  }}
                >
                  <Box sx={{ minWidth: 900 }}>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "60px 1.4fr 1.7fr 1.1fr 1fr",
                        gap: 1,
                        px: 1.5,
                        py: 1,
                        bgcolor: "action.hover",
                        alignItems: "center",
                        fontWeight: 800,
                      }}
                    >
                      <Checkbox
                        checked={
                          filteredContacts.length > 0 &&
                          filteredContacts.every(
                            (contact) =>
                              selectedIds.includes(
                                contact.id
                              )
                          )
                        }
                        onChange={toggleAllVisible}
                      />

                      <span>Name</span>
                      <span>Email</span>
                      <span>Phone</span>
                      <span>Tags</span>
                    </Box>

                    {filteredContacts.length === 0 ? (
                      <Box
                        sx={{
                          p: 5,
                          textAlign: "center",
                        }}
                      >
                        <Typography
                          variant="h6"
                          fontWeight={800}
                        >
                          No contacts found
                        </Typography>

                        <Typography color="text.secondary">
                          Import your merged contact
                          spreadsheet to begin.
                        </Typography>
                      </Box>
                    ) : (
                      filteredContacts.map(
                        (contact) => (
                          <Box
                            key={contact.id}
                            sx={{
                              display: "grid",
                              gridTemplateColumns:
                                "60px 1.4fr 1.7fr 1.1fr 1fr",
                              gap: 1,
                              px: 1.5,
                              py: 1.25,
                              alignItems: "center",
                              borderTop: "1px solid",
                              borderColor: "divider",
                            }}
                          >
                            <Checkbox
                              checked={selectedIds.includes(
                                contact.id
                              )}
                              onChange={() =>
                                toggleContact(contact.id)
                              }
                            />

                            <Typography>
                              {[
                                contact.first_name,
                                contact.last_name,
                              ]
                                .filter(Boolean)
                                .join(" ") ||
                                "Unnamed Contact"}
                            </Typography>

                            <Typography>
                              {contact.email || "—"}
                            </Typography>

                            <Typography>
                              {contact.phone || "—"}
                            </Typography>

                            <Box
                              sx={{
                                display: "flex",
                                gap: 0.5,
                                flexWrap: "wrap",
                              }}
                            >
                              {(contact.tags || []).map(
                                (tag) => (
                                  <Chip
                                    key={tag}
                                    label={tag}
                                    size="small"
                                  />
                                )
                              )}
                            </Box>
                          </Box>
                        )
                      )
                    )}
                  </Box>
                </Box>
              )}
            </>
          )}

         {tab === 1 && (
  <Card>
    <CardContent>

      <Typography variant="h5" fontWeight="bold">
        TNG AI Marketing Assistant
      </Typography>

      <Typography sx={{ mb: 3 }}>
  Choose a campaign type or describe your own campaign.
</Typography>

<FormControl fullWidth sx={{ mb: 3 }}>
  <InputLabel>Campaign Type</InputLabel>

  <Select
    value={selectedPreset}
    label="Campaign Type"
    onChange={(event) =>
      selectCampaignPreset(event.target.value)
    }
  >
    <MenuItem value="">
      Custom Campaign
    </MenuItem>

    {CAMPAIGN_PRESETS.map((preset) => (
      <MenuItem
        key={preset.id}
        value={preset.id}
      >
        {preset.name}
      </MenuItem>
    ))}
  </Select>
</FormControl>

<TextField
  fullWidth
  multiline
  minRows={5}
  label="Describe the campaign"
  value={aiPrompt}
  onChange={(event) => {
    setAiPrompt(event.target.value);
    setSelectedPreset("");
  }}
/>

      <Button
        sx={{ mt: 3 }}
        variant="contained"
        color="error"
        onClick={generateCampaign}
        disabled={aiLoading || !aiPrompt.trim()}
      >
        {aiLoading ? "Generating..." : "Generate Campaign"}
      </Button>

      <Divider sx={{ my: 4 }} />

      <TextField
        fullWidth
        label="Subject"
        value={generatedSubject}
        onChange={(event) =>
          setGeneratedSubject(event.target.value)
        }
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        multiline
        minRows={8}
        label="Email"
        value={generatedEmail}
        onChange={(event) =>
          setGeneratedEmail(event.target.value)
        }
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        multiline
        minRows={4}
        label="SMS"
        value={generatedSms}
        onChange={(event) =>
          setGeneratedSms(event.target.value)
        }
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        multiline
        minRows={5}
        label="Social Post"
        value={generatedSocial}
        onChange={(event) =>
          setGeneratedSocial(event.target.value)
        }
      />

    </CardContent>
  </Card>
)}
        </CardContent>
      </Card>

      <Dialog
        open={emailDialogOpen}
        onClose={() => setEmailDialogOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          Create Email Campaign
        </DialogTitle>

        <DialogContent>
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
          >
            Sending will remain disabled until an email
            provider, unsubscribe handling, and bounce
            processing are connected.
          </Alert>

          <Typography sx={{ mb: 2 }}>
            Selected recipients:{" "}
            <strong>
              {selectedContacts.length}
            </strong>
          </Typography>

          <TextField
            fullWidth
            label="Campaign name"
            value={emailCampaign.name}
            onChange={(event) =>
              setEmailCampaign((current) => ({
                ...current,
                name: event.target.value,
              }))
            }
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            label="Subject"
            value={emailCampaign.subject}
            onChange={(event) =>
              setEmailCampaign((current) => ({
                ...current,
                subject: event.target.value,
              }))
            }
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            multiline
            minRows={10}
            label="Email message"
            value={emailCampaign.body}
            onChange={(event) =>
              setEmailCampaign((current) => ({
                ...current,
                body: event.target.value,
              }))
            }
            helperText="Use {{first_name}} for personalization later."
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() =>
              setEmailDialogOpen(false)
            }
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            onClick={saveEmailDraft}
            disabled={
              !emailCampaign.subject.trim() ||
              !emailCampaign.body.trim()
            }
          >
            Save Draft
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={smsDialogOpen}
        onClose={() => setSmsDialogOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          Create Text Campaign
        </DialogTitle>

        <DialogContent>
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
          >
            Marketing texts may only be sent to contacts
            with documented SMS consent. STOP and HELP
            handling will be added before sending is
            enabled.
          </Alert>

          <Typography sx={{ mb: 2 }}>
            Selected recipients:{" "}
            <strong>
              {selectedContacts.length}
            </strong>
          </Typography>

          <TextField
            fullWidth
            label="Campaign name"
            value={smsCampaign.name}
            onChange={(event) =>
              setSmsCampaign((current) => ({
                ...current,
                name: event.target.value,
              }))
            }
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            multiline
            minRows={6}
            label="Text message"
            value={smsCampaign.message}
            onChange={(event) =>
              setSmsCampaign((current) => ({
                ...current,
                message: event.target.value,
              }))
            }
            helperText={`${smsCampaign.message.length} characters`}
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() =>
              setSmsDialogOpen(false)
            }
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            onClick={saveSmsDraft}
            disabled={!smsCampaign.message.trim()}
          >
            Save Draft
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function StatCard({ title, value, icon }) {
  return (
    <Card>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box>
            <Typography color="text.secondary">
              {title}
            </Typography>

            <Typography
              variant="h4"
              fontWeight={900}
            >
              {value}
            </Typography>
          </Box>

          <Box
            sx={{
              width: 48,
              height: 48,
              display: "grid",
              placeItems: "center",
              borderRadius: 2,
              bgcolor: "action.hover",
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

function EmptyState({
  title,
  text,
  buttonText,
  onClick,
}) {
  return (
    <Box sx={{ py: 7, textAlign: "center" }}>
      <Typography
        variant="h6"
        fontWeight={900}
      >
        {title}
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mt: 1, mb: 2 }}
      >
        {text}
      </Typography>

      {buttonText && (
        <Button
          variant="contained"
          onClick={onClick}
        >
          {buttonText}
        </Button>
      )}
    </Box>
  );
}
 