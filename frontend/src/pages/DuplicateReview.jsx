import React, { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Stack,
  Divider,
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function DuplicateReview() {
  const [duplicates, setDuplicates] = useState([]);

  async function loadDuplicates() {
    const res = await fetch(`${API}/api/duplicates/members`, {
      headers: {
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
    });

    const data = await res.json();
    setDuplicates(Array.isArray(data) ? data : []);
  }

  async function mergeMembers(keepId, mergeId) {
    if (!window.confirm("Merge these members? This cannot be undone.")) return;

    const res = await fetch(`${API}/api/duplicates/members/merge`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
      body: JSON.stringify({
        keep_id: keepId,
        merge_id: mergeId,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Merge failed");
      return;
    }

    alert("✅ Members merged successfully");
    loadDuplicates();
  }

  useEffect(() => {
    loadDuplicates();
  }, []);

  function MemberCard({ member, recommended }) {
    return (
      <Card
        sx={{
          borderRadius: 3,
          border: recommended ? "2px solid #2e7d32" : "1px solid #ddd",
          height: "100%",
        }}
      >
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6" fontWeight="bold">
              {member.name || "Unnamed Member"}
            </Typography>

            {recommended && (
              <Chip color="success" label="Recommended Keep" />
            )}
          </Stack>

          <Divider sx={{ my: 2 }} />

          <Typography><b>Member #:</b> {member.member_number || "-"}</Typography>
          <Typography><b>Email:</b> {member.email || "-"}</Typography>
          <Typography><b>Phone:</b> {member.phone || "-"}</Typography>
          <Typography><b>Clover ID:</b> {member.clover_customer_id || "-"}</Typography>

          <Divider sx={{ my: 2 }} />

          <Typography><b>Membership:</b> {member.membership_type || "-"}</Typography>
          <Typography><b>Status:</b> {member.membership_status || "-"}</Typography>
          <Typography><b>Payments:</b> {member.payment_count || 0}</Typography>
          <Typography>
            <b>Lifetime Value:</b> ${Number(member.lifetime_value || 0).toFixed(2)}
          </Typography>
          <Typography><b>Attendance:</b> {member.attendance_count || 0}</Typography>
          <Typography><b>Score:</b> {member.score || 0}</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
        Duplicate Review
      </Typography>

      {duplicates.length === 0 ? (
        <Card sx={{ borderRadius: 3 }}>
          <CardContent>
            <Typography>No duplicate members found.</Typography>
          </CardContent>
        </Card>
      ) : (
        <Stack spacing={3}>
          {duplicates.map((d, index) => {
            const aRecommended = d.recommended_keep_id === d.member_a.id;
            const bRecommended = d.recommended_keep_id === d.member_b.id;

            return (
              <Card key={index} sx={{ borderRadius: 3 }}>
                <CardContent>
                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Chip
                      color={d.confidence >= 100 ? "success" : "warning"}
                      label={`${d.confidence}% confidence`}
                    />
                    <Chip label={d.reasons.join(", ")} />
                  </Stack>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <MemberCard
                        member={d.member_a}
                        recommended={aRecommended}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <MemberCard
                        member={d.member_b}
                        recommended={bRecommended}
                      />
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 3 }} />

                  <Stack direction="row" spacing={2} flexWrap="wrap">
                    <Button
                      variant="contained"
                      color="success"
                      onClick={() =>
                        mergeMembers(
                          d.recommended_keep_id,
                          d.recommended_merge_id
                        )
                      }
                    >
                      ✅ Use Recommended Merge
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      onClick={() =>
                        mergeMembers(d.member_a.id, d.member_b.id)
                      }
                    >
                      Keep {d.member_a.name} / Merge {d.member_b.name}
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      onClick={() =>
                        mergeMembers(d.member_b.id, d.member_a.id)
                      }
                    >
                      Keep {d.member_b.name} / Merge {d.member_a.name}
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}