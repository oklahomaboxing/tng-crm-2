import React, { useEffect, useRef, useState } from "react";
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
  Alert,
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function DuplicateReview() {
  const [duplicates, setDuplicates] = useState([]);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState('');
  const merging=useRef(false);

  async function loadDuplicates() {
    const res = await fetch(`${API}/api/duplicates/members`, {
      headers: {
        Authorization: "Bearer " + localStorage.getItem("token"),
      },
    });

    const data = await res.json();
    if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not load matching profiles.');
    setDuplicates(Array.isArray(data) ? data : []);
  }

  async function mergeMembers(keepId, mergeId) {
    if(merging.current)return;merging.current=true;setBusy(true);setError('');setNotice('');
    try {
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
      throw new Error(data.detail || "Merge failed");
    }

    await loadDuplicates();setNotice('Profiles merged. Purchases, attendance, member numbers and login access are retained.');
    }catch(e){setError(e.message);}finally{merging.current=false;setBusy(false);}
  }

  useEffect(() => {
    loadDuplicates().catch(e=>setError(e.message));
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
      <Typography sx={{mb:2}}>Review the profiles, then press Merge once. Matching email or phone is enough; names and birthdates do not need to be corrected first. The selected profile keeps its contact details, and the latest recorded membership term is retained. Shared family contact details can also appear here.</Typography>
      {notice&&<Alert severity="success" sx={{mb:2}}>{notice}</Alert>}
      {error&&<Alert severity="error" sx={{mb:2}}>{error}</Alert>}

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
                      label={d.contact_match ? 'Matching contact details' : 'Matching name'}
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
                      disabled={busy}
                      onClick={() =>
                        mergeMembers(
                          d.recommended_keep_id,
                          d.recommended_merge_id
                        )
                      }
                    >
                      {busy?'Merging…':'Merge'}
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      disabled={busy}
                      onClick={() =>
                        mergeMembers(d.member_a.id, d.member_b.id)
                      }
                    >
                      Keep {d.member_a.name} / Merge {d.member_b.name}
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      disabled={busy}
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
