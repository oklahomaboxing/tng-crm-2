import React, { useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization:
    `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

export default function FighterPortalVideos() {
  const [videos, setVideos] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  const [form, setForm] = useState({
    youtube_url: "",
    title: "",
    category: "fight",
    event_name: "",
    fighter_names: "",
  });

  async function load() {
    setError("");

    try {
      const response = await fetch(
        `${API}/api/fighter/admin/videos`,
        {
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not load Fighter Portal videos."
        );
      }

      setVideos(
        Array.isArray(data.videos)
          ? data.videos
          : []
      );
    } catch (err) {
      setError(
        err.message ||
        "Could not load Fighter Portal videos."
      );
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function addVideo() {
    if (!form.youtube_url.trim()) {
      setError("Paste a YouTube video link.");
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/api/fighter/admin/videos`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(form),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not add video."
        );
      }

      setForm({
        youtube_url: "",
        title: "",
        category: "fight",
        event_name: "",
        fighter_names: "",
      });

      setMessage(
        "Video added. Approve it when you want fighters to see it."
      );

      await load();
    } catch (err) {
      setError(
        err.message || "Could not add video."
      );
    } finally {
      setWorking(false);
    }
  }

  async function updateVideo(video, updates) {
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/api/fighter/admin/videos/${video.id}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(updates),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not update video."
        );
      }

      setVideos((current) =>
        current.map((item) =>
          item.id === video.id
            ? { ...item, ...updates }
            : item
        )
      );
    } catch (err) {
      setError(
        err.message || "Could not update video."
      );
    }
  }

  async function deleteVideo(video) {
    if (
      !window.confirm(
        `Remove "${video.title}" from TNGOS?`
      )
    ) {
      return;
    }

    const response = await fetch(
      `${API}/api/fighter/admin/videos/${video.id}`,
      {
        method: "DELETE",
        headers: authHeaders(),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      setError(
        data.detail ||
        "Could not remove video."
      );
      return;
    }

    setVideos((current) =>
      current.filter(
        (item) => item.id !== video.id
      )
    );
  }

  return (
    <Box>
      <Typography
        variant="h4"
        fontWeight={950}
      >
        Fighter Portal Videos
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mt: 0.5, mb: 3 }}
      >
        Control which TNG Boxing YouTube videos
        fighters can watch inside their portal.
      </Typography>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={() => setError("")}
        >
          {error}
        </Alert>
      )}

      {message && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setMessage("")}
        >
          {message}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography
            variant="h6"
            fontWeight={900}
            sx={{ mb: 2 }}
          >
            Add YouTube Video
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="YouTube Video URL"
                placeholder="https://youtube.com/watch?v=..."
                value={form.youtube_url}
                onChange={(e) =>
                  setForm({
                    ...form,
                    youtube_url:
                      e.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Title"
                placeholder="Fall Brawl 5 - Smith vs Jones"
                value={form.title}
                onChange={(e) =>
                  setForm({
                    ...form,
                    title: e.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>
                  Category
                </InputLabel>

                <Select
                  label="Category"
                  value={form.category}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      category:
                        e.target.value,
                    })
                  }
                >
                  <MenuItem value="fight">
                    Fight
                  </MenuItem>
                  <MenuItem value="fall_brawl">
                    Fall Brawl
                  </MenuItem>
                  <MenuItem value="amateur">
                    Amateur
                  </MenuItem>
                  <MenuItem value="pro">
                    Professional
                  </MenuItem>
                  <MenuItem value="training">
                    Training
                  </MenuItem>
                  <MenuItem value="other">
                    Other
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Event"
                placeholder="Fall Brawl 6"
                value={form.event_name}
                onChange={(e) =>
                  setForm({
                    ...form,
                    event_name:
                      e.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} md={5}>
              <TextField
                fullWidth
                label="Fighters"
                placeholder="Rocky Hernandez vs Bryan Cox"
                value={form.fighter_names}
                onChange={(e) =>
                  setForm({
                    ...form,
                    fighter_names:
                      e.target.value,
                  })
                }
              />
            </Grid>
          </Grid>

          <Button
            variant="contained"
            disabled={working}
            onClick={addVideo}
            sx={{
              mt: 2,
              bgcolor: "#d71920",
              fontWeight: 900,
            }}
          >
            {working
              ? "Adding..."
              : "Add to Video Library"}
          </Button>
        </CardContent>
      </Card>

      <Stack spacing={2}>
        {videos.map((video) => (
          <Card key={video.id}>
            <CardContent>
              <Grid
                container
                spacing={2}
                alignItems="center"
              >
                <Grid
                  item
                  xs={12}
                  md={3}
                >
                  <Box
                    component="img"
                    src={
                      video.thumbnail_url
                    }
                    alt={video.title}
                    sx={{
                      width: "100%",
                      maxWidth: 280,
                      borderRadius: 2,
                    }}
                  />
                </Grid>

                <Grid
                  item
                  xs={12}
                  md={6}
                >
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    {video.title}
                  </Typography>

                  <Stack
                    direction="row"
                    spacing={1}
                    flexWrap="wrap"
                    sx={{ mt: 1 }}
                  >
                    <Chip
                      size="small"
                      label={
                        video.category ||
                        "fight"
                      }
                    />

                    {video.event_name && (
                      <Chip
                        size="small"
                        variant="outlined"
                        label={
                          video.event_name
                        }
                      />
                    )}
                  </Stack>

                  {video.fighter_names && (
                    <Typography
                      sx={{ mt: 1 }}
                    >
                      {video.fighter_names}
                    </Typography>
                  )}

                  <Button
                    size="small"
                    href={video.youtube_url}
                    target="_blank"
                    rel="noreferrer"
                    sx={{ mt: 1 }}
                  >
                    Open on YouTube
                  </Button>
                </Grid>

                <Grid
                  item
                  xs={12}
                  md={3}
                >
                  <Stack
                    spacing={1}
                    alignItems={{
                      xs: "flex-start",
                      md: "flex-end",
                    }}
                  >
                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="center"
                    >
                      <Switch
                        checked={Boolean(
                          video.approved
                        )}
                        onChange={(e) =>
                          updateVideo(
                            video,
                            {
                              approved:
                                e.target
                                  .checked,
                            }
                          )
                        }
                      />

                      <Typography
                        fontWeight={800}
                      >
                        {video.approved
                          ? "Visible to Fighters"
                          : "Hidden"}
                      </Typography>
                    </Stack>

                    <Button
                      color="error"
                      size="small"
                      onClick={() =>
                        deleteVideo(video)
                      }
                    >
                      Remove
                    </Button>
                  </Stack>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        ))}

        {!videos.length && (
          <Card>
            <CardContent>
              <Typography
                color="text.secondary"
              >
                No videos have been added yet.
              </Typography>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
