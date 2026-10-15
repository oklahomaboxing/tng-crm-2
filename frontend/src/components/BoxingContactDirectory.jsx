import React, { useState } from 'react';
import { Alert, Box, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material';
import contacts from '../data/boxingContacts.json';

const group = row => row.category === 'Boxer' ? 'Boxers' : row.category === 'Management' ? 'Managers' : row.category.includes('matchmaking') || row.category === 'Matchmaking' ? 'Matchmakers' : 'Promoters';
const external = (label, href) => <Button key={label + href} component="a" href={href} target="_blank" rel="noopener noreferrer" size="small" variant="outlined">{label}</Button>;
export default function BoxingContactDirectory() {
  const [open, setOpen] = useState(false), [query, setQuery] = useState(''), [category, setCategory] = useState('All');
  const filtered = contacts.filter(row => (category === 'All' || group(row) === category) && Object.values(row).join(' ').toLowerCase().includes(query.trim().toLowerCase()));
  return <>
    <Button variant="outlined" onClick={() => setOpen(true)}>Boxing contacts · {contacts.length} public routes</Button>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="lg">
      <DialogTitle>Boxing contact directory</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography color="text.secondary">Find boxer social profiles, management agencies, matchmakers and promoter offices. Sources checked October 15, 2026.</Typography>
          <Alert severity="info">Athlete social links come from official promoter profiles. Office contacts and company accounts are labeled separately. Confirm current representation and availability before making an offer.</Alert>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField fullWidth label="Search name, location or organization" value={query} onChange={e => setQuery(e.target.value)} />
            <TextField select label="Contact type" value={category} onChange={e => setCategory(e.target.value)} sx={{ minWidth: 190 }}>{['All', 'Boxers', 'Managers', 'Matchmakers', 'Promoters'].map(x => <MenuItem key={x} value={x}>{x}</MenuItem>)}</TextField>
          </Stack>
          <Typography variant="body2">{filtered.length} matching contacts</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            {filtered.map(row => <Card key={row.name} variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={1.5}>
                <Box><Chip size="small" label={row.category} /><Typography variant="h6" sx={{ mt: 1 }}>{row.name}</Typography><Typography color="text.secondary">{row.region}</Typography></Box>
                <Typography variant="body2">{row.contact_route}</Typography>
                <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}>
                  {row.instagram && external('Instagram', row.instagram)}{row.facebook && external('Facebook', row.facebook)}
                  {row.email && <Button component="a" href={`mailto:${row.email}`} size="small">{row.email}</Button>}
                  {row.phone && <Button component="a" href={`tel:${row.phone.replace(/[^+\d]/g, '')}`} size="small">{row.phone}</Button>}
                  {row.other_platforms && row.other_platforms.split(' ; ').map(url => external(url.includes('tiktok.com') ? 'TikTok' : url.includes('youtube.com') ? 'YouTube' : 'X', url))}
                  {external('Official source / contact page', row.source_url)}
                </Stack>
              </Stack>
            </Card>)}
          </Box>
          {!filtered.length && <Typography>No contacts match. Try a different name, city or contact type.</Typography>}
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)}>Close</Button></DialogActions>
    </Dialog>
  </>;
}
