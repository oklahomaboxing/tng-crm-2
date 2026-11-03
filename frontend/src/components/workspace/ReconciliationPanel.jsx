import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Typography } from '@mui/material';
import FactCheckRoundedIcon from '@mui/icons-material/FactCheckRounded';
import { API, authHeaders } from '../../services/api';
export default function ReconciliationPanel({
  onNavigate
}) {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [version, setVersion] = useState(0),
    [loading, setLoading] = useState(true),
    [filter, setFilter] = useState('all');
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError('');
    fetch(`${API}/api/operations/reconciliation`, {
      headers: authHeaders(),
      cache: 'no-store',
      signal: abort.signal
    }).then(async r => {
      const d = await r.json();
      if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Reconciliation review is unavailable.');
      if (!abort.signal.aborted) setData(d);
    }).catch(e => {
      if (!abort.signal.aborted) setError(e.message);
    }).finally(() => {
      if (!abort.signal.aborted) setLoading(false);
    });
    return () => abort.abort();
  }, [version]);
  const rows = data?.issues?.filter(i => filter === 'all' || (filter === 'tickets' ? i.kind.startsWith('ticket') : !i.kind.startsWith('ticket'))) || [];
  return <Card><CardContent><Stack direction={{
        xs: 'column',
        sm: 'row'
      }} sx={{
        justifyContent: "space-between",
        gap: 2
      }}><Box><Stack direction="row" sx={{
            alignItems: "center",
            gap: 1
          }}><FactCheckRoundedIcon color="secondary" /><Typography variant="h6">Payment & access review</Typography></Stack><Typography variant="body2" color="text.secondary" sx={{
            mt: .5
          }}>Trace paid orders to tickets, gym membership terms and portal access.</Typography></Box><Button variant="outlined" disabled={loading} onClick={() => setVersion(v => v + 1)}>{loading ? 'Checking records…' : 'Refresh review'}</Button></Stack>
 {error && <Alert severity="error" sx={{
        mt: 2
      }}>{error}</Alert>}
 {loading && !data ? <Skeleton height={150} /> : data && <><Box sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3,minmax(0,1fr))',
          gap: 1,
          mt: 2,
          mb: 2
        }}>{[['Review items', data.summary.review_items], ['Issuance priorities', data.summary.urgent_items], ['Unfinished checkouts', data.summary.pending_checkouts]].map(([label, value]) => <Box key={label} sx={{
            p: 2,
            bgcolor: '#f3f6fa',
            borderRadius: 3
          }}><Typography variant="h4">{value}</Typography><Typography variant="caption" color="text.secondary">{label}</Typography></Box>)}</Box>
 <Alert severity="info" sx={{
          mb: 2
        }}>Unfinished checkouts are not paid sales. This review reads saved records; it does not charge cards, issue tickets, send messages or activate memberships.</Alert>
 <Stack direction="row" sx={{
          gap: 1,
          mb: 2
        }}>{[['all', 'All'], ['tickets', 'Tickets'], ['members', 'Memberships']].map(([key, label]) => <Button key={key} size="small" variant={filter === key ? 'contained' : 'outlined'} onClick={() => setFilter(key)}>{label}</Button>)}</Stack>
 <Stack spacing={1}>{rows.map(row => <Box key={row.key} sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 3,
            p: 2
          }}><Stack direction={{
              xs: 'column',
              sm: 'row'
            }} sx={{
              gap: 2,
              alignItems: {
                sm: 'center'
              }
            }}><Chip size="small" label={row.severity === 'error' ? 'Priority' : 'Review'} color={row.severity === 'error' ? 'error' : row.severity === 'warning' ? 'warning' : 'default'} /><Box sx={{
                flex: 1
              }}><Typography sx={{
                  fontWeight: 800
                }}>{row.title}</Typography><Typography variant="caption" color="text.secondary">{row.reference}</Typography><Typography variant="body2" color="text.secondary">{row.detail}</Typography></Box><Button variant="outlined" onClick={() => onNavigate(row.page, row.target)}>Open record</Button></Stack></Box>)}</Stack>
 {!rows.length && <Typography color="text.secondary">No review items in the displayed results for this category. External provider balances and backup restoration are not verified by this check.</Typography>}
 {data.total_issues > data.limit && <Typography variant="caption">Showing the first {data.limit} of {data.total_issues} review items.</Typography>}
 <Typography variant="caption" color="text.secondary" sx={{
          display: "block",
          mt: 2
        }}>Saved-record review · {new Date(data.generated_at).toLocaleString('en-US', {
            timeZone: 'America/Chicago'
          })} CT</Typography>
 </>}
 </CardContent></Card>;
}
