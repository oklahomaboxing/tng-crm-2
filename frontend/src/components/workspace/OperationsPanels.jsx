import React from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Typography } from '@mui/material';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
const date = value => value ? new Date(value).toLocaleString([], { timeZone: 'America/Chicago', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'No saved sync yet';
export function WorkQueue({ data, loading, error, onNavigate, limit }) {
  return <Card sx={{ height: '100%' }}><CardContent>
    <Stack direction="row" sx={{alignItems: "center", justifyContent: "space-between", mb: 2}}><Typography variant="h6" sx={{fontWeight: 900}}>Needs attention</Typography>{data && <Chip size="small" label={`${data.work_queue.length} ${data.work_queue.length === 1 ? "area" : "areas"}`} />}</Stack>
    {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}
    {loading && !data ? <Skeleton height={160}/> : data?.work_queue?.length ? <Stack spacing={1}>{data.work_queue.slice(0, limit).map(item => <Box key={item.id} sx={{ border: '1px solid #e8e8ed', borderRadius: 2, p: 1.5 }}>
      <Stack direction="row" sx={{alignItems: "center", gap: 1.5}}><Chip label={item.count} color={item.severity === 'error' ? 'error' : item.severity === 'warning' ? 'warning' : 'default'} size="small"/><Box sx={{flex: 1}}><Typography sx={{fontWeight: 800}}>{item.title}</Typography><Typography variant="body2" color="text.secondary">{item.description}</Typography></Box><Button size="small" onClick={() => onNavigate(item.page)} aria-label={`Review ${item.title}`}>Review</Button></Stack>
    </Box>)}</Stack> : data ? <Alert severity="success">No issues in the monitored queues. Provider connections still need their own checks.</Alert> : !error && <Typography color="text.secondary">Operations data is not available yet.</Typography>}
    {limit && data?.work_queue?.length > limit && <Button sx={{ mt: 2 }} endIcon={<ArrowForwardRoundedIcon/>} onClick={() => onNavigate('System Overview')}>Open full work queue</Button>}
  </CardContent></Card>;
}
export function UpcomingEvents({ data, loading, onNavigate }) {
  return <Card sx={{ height: '100%' }}><CardContent><Stack direction="row" sx={{justifyContent: "space-between", alignItems: "center", mb: 2}}><Typography variant="h6" sx={{fontWeight: 900}}>Upcoming fight nights</Typography><Button onClick={() => onNavigate('TNG BOXING EVENTS')}>All events</Button></Stack>
    {loading && !data ? <Skeleton height={160}/> : data?.upcoming_events?.length ? <Stack spacing={1.5}>{data.upcoming_events.map(event => <Box key={event.id} sx={{ borderRadius: 2, bgcolor: '#f6f6f9', p: 2 }}><Typography variant="caption" color="error.main" sx={{fontWeight: 900}}>{new Date(event.date + 'T12:00:00').toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</Typography><Typography sx={{fontWeight: 900,  mt: .5 }}>{event.name}</Typography><Typography variant="body2" color="text.secondary">{event.venue || 'Venue to be announced'}</Typography><Button size="small" onClick={() => onNavigate('TNG BOXING EVENTS', { eventId: event.id })} sx={{ mt: 1 }} endIcon={<ArrowForwardRoundedIcon/>}>Open event</Button></Box>)}</Stack> : <Typography color="text.secondary">{data ? 'No upcoming dated events.' : 'Event overview unavailable.'}</Typography>}
  </CardContent></Card>;
}
export function IntegrationCards({ data, onNavigate }) {
  return <Card><CardContent><Typography variant="h6" sx={{fontWeight: 900}}>Connections and account security</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Configuration is shown below. A saved key does not confirm that a provider connection or campaign is approved.</Typography>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 1.5 }}>
      {(data?.integrations || []).map(item => <Box key={item.name} sx={{ border: '1px solid #e8e8ed', borderRadius: 2, p: 2 }}><Typography sx={{fontWeight: 800}}>{item.name}</Typography><Chip size="small" label={item.configured ? 'Configured · not verified' : 'Setup needed'} color={item.configured ? 'default' : 'warning'} sx={{ my: 1 }}/><Button size="small" fullWidth onClick={() => onNavigate(item.page)}>Open workspace</Button></Box>)}
      <Box sx={{ border: '1px solid #e8e8ed', borderRadius: 2, p: 2 }}><Typography sx={{fontWeight: 800}}>Your admin account</Typography><Chip size="small" label={data?.security?.mfa_enabled ? 'Authenticator enabled' : 'Authenticator not enabled'} color={data?.security?.mfa_enabled ? 'success' : 'warning'} sx={{ my: 1 }}/><Button size="small" fullWidth onClick={() => onNavigate('Security Center')}>Security Center</Button></Box>
    </Box><Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>Last customer sync: {date(data?.last_customer_sync_at)} CT · Automatic customer sync {data?.customer_sync_enabled ? 'enabled' : 'disabled'}</Typography>
  </CardContent></Card>;
}
