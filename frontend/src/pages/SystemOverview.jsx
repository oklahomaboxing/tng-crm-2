import React from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import useOperationsOverview from '../hooks/useOperationsOverview';
import { WorkQueue, UpcomingEvents, IntegrationCards } from '../components/workspace/OperationsPanels';
export default function SystemOverview({ onNavigate }) {
  const { data, loading, error, refresh } = useOperationsOverview();
  return <Stack spacing={3}>
    <Stack direction={{ xs: 'column', sm: 'row' }} sx={{justifyContent: "space-between", gap: 2}}><Box><Typography variant="overline" color="error.main" sx={{fontWeight: 900}}>TNGOS OPERATIONS</Typography><Typography variant="h4" sx={{fontWeight: 900}}>System Overview</Typography><Typography color="text.secondary">One place to review membership, ticket fulfillment, delivery and connection readiness.</Typography></Box><Button variant="outlined" onClick={refresh} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh overview'}</Button></Stack>
    <Alert severity="info">This page only reads saved records. Reviewing it does not send messages, change payments, activate tickets or merge profiles.</Alert>
    {error && <Alert severity="error">{error}</Alert>}
    {loading && !data ? <Skeleton height={180}/> : data && <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
      {[['Member profiles', data.members.profiles], ['Paid ticket orders', data.tickets.paid_orders], ['Unfinished checkouts', data.tickets.pending_checkouts], ['Marketing drafts', data.marketing_drafts]].map(([title, value]) => <Card key={title}><CardContent><Typography variant="body2" color="text.secondary">{title}</Typography><Typography variant="h3" sx={{fontWeight: 900}}>{value}</Typography>{title === 'Unfinished checkouts' && <Typography variant="caption" color="text.secondary">Not counted as paid sales</Typography>}</CardContent></Card>)}
    </Box>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.35fr 1fr' }, gap: 3 }}><WorkQueue {...{ data, loading, error, onNavigate }}/><UpcomingEvents {...{ data, loading, onNavigate }}/></Box>
    {!!data?.paid_ticket_issues?.length && <Card><CardContent><Typography variant="h6" sx={{fontWeight: 900}}>Paid ticket fulfillment review</Typography><TableContainer><Table><TableHead><TableRow><TableCell>Receipt</TableCell><TableCell>Tickets expected</TableCell><TableCell>Issued</TableCell><TableCell>Review</TableCell></TableRow></TableHead><TableBody>{data.paid_ticket_issues.map(item => <TableRow key={item.order_id}><TableCell>{item.receipt_number || `Order ${item.order_id}`}</TableCell><TableCell>{item.expected ?? 'Order items need review'}</TableCell><TableCell>{item.issued}</TableCell><TableCell><Button onClick={() => onNavigate('TNG BOXING EVENTS', { eventId: item.event_id })}>Open event</Button></TableCell></TableRow>)}</TableBody></Table></TableContainer></CardContent></Card>}
    {data && <IntegrationCards {...{ data, onNavigate }}/>}<Typography variant="caption" color="text.secondary">{data ? `Snapshot: ${new Date(data.generated_at).toLocaleString()} · Business timezone: Central Time` : ''}</Typography>
  </Stack>;
}
