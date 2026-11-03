import React, { useEffect, useState } from 'react';
import { Alert, Avatar, Box, Button, Card, CardActionArea, CardContent, Chip, Skeleton, Stack, Typography } from '@mui/material';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import PeopleAltRoundedIcon from '@mui/icons-material/PeopleAltRounded';
import EventRoundedIcon from '@mui/icons-material/EventRounded';
import QrCodeScannerRoundedIcon from '@mui/icons-material/QrCodeScannerRounded';
import CampaignRoundedIcon from '@mui/icons-material/CampaignRounded';
import GraphicEqRoundedIcon from '@mui/icons-material/GraphicEqRounded';
import useOperationsOverview from '../hooks/useOperationsOverview';
import { WorkQueue, UpcomingEvents } from '../components/workspace/OperationsPanels';
import { API, authHeaders } from '../services/api';
const dollars = value => new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD'
}).format(Number(value));
export default function Dashboard({
  dash,
  leader,
  load,
  onNavigate,
  userName,
  error
}) {
  const operations = useOperationsOverview();
  const [facts, setFacts] = useState(null),
    [eventError, setEventError] = useState('');
  useEffect(() => {
    const abort = new AbortController();
    setEventError('');
    fetch(`${API}/api/assistant/snapshot`, {
      headers: authHeaders(),
      signal: abort.signal,
      cache: 'no-store'
    }).then(async r => {
      const d = await r.json();
      if (!r.ok || !d.members) throw new Error('Event briefing could not be refreshed.');
      if (!abort.signal.aborted) setFacts(d);
    }).catch(e => {
      if (!abort.signal.aborted) setEventError(e.message);
    });
    return () => abort.abort();
  }, [dash]);
  const launch = [['TNG Assistant', 'Ask TNG', 'Your voice command center', GraphicEqRoundedIcon], ['Member Check-In', 'Member check-in', 'Number keypad & signup QR', QrCodeScannerRoundedIcon], ['Members', 'Customer profiles', 'Gym members & customer history', PeopleAltRoundedIcon], ['TNG BOXING EVENTS', 'TNG Boxing Events', 'Fight cards, contracts & tickets', EventRoundedIcon], ['Event Check-In', 'Fight-night door', 'Scan tickets & manage entry', QrCodeScannerRoundedIcon], ['Marketing Center', 'Marketing & growth', 'Member communications', CampaignRoundedIcon]];
  const stats = [['Active members', 'active_members'], ['Expiring in 7 days', 'expiring_members'], ['Expired memberships', 'expired_members'], ['Today’s gym check-ins', 'today_checkins'], ['Revenue this month', 'revenue_this_month', true], ['Sales this month', 'sales_this_month']];
  return <Stack spacing={3}>
  <Box className="tng-hero" sx={{
      p: {
        xs: 3,
        md: 4
      }
    }}><Box className="tng-hero-orbit" /><Stack direction={{
        xs: 'column',
        md: 'row'
      }} sx={{
        justifyContent: "space-between",
        gap: 3,
        alignItems: {
          md: 'center'
        }
      }}><Box sx={{
          maxWidth: 680
        }}><Typography variant="overline" sx={{
            color: '#80cfdb'
          }}>TNGOS / OPERATIONS INTELLIGENCE</Typography><Typography variant="h3" sx={{
            mt: 1,
            fontSize: {
              xs: 31,
              md: 46
            },
            lineHeight: 1.13
          }}>Your operation.<br />One command center.</Typography><Typography sx={{
            color: '#a9b8cb',
            mt: 2,
            fontSize: 15
          }}>Welcome{userName ? `, ${userName.split(' ')[0]}` : ''}. Your gym, your promotion, your next move.</Typography><Stack direction="row" sx={{
            alignItems: "center",
            gap: 1,
            mt: 2
          }}><span className="tng-status-dot" /><Typography variant="caption" sx={{
              color: '#bbc9da'
            }}>EARNED NOT GIVEN</Typography><Chip label={new Date().toLocaleDateString('en-US', {
              timeZone: 'America/Chicago',
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            }) + ' · CT'} size="small" sx={{
              ml: 1,
              color: '#bdcbdc',
              bgcolor: '#ffffff09',
              border: '1px solid #ffffff14'
            }} /></Stack></Box><Stack spacing={1.5} sx={{
          alignItems: "flex-start"
        }}><Button variant="contained" startIcon={<GraphicEqRoundedIcon />} onClick={() => onNavigate('TNG Assistant')}>Talk to TNG</Button><Button onClick={() => onNavigate('System Overview')} endIcon={<ArrowForwardRoundedIcon />} sx={{
            color: '#e1e9f5'
          }}>Review your priorities</Button></Stack></Stack></Box>
  {error && <Alert severity="error">{error}</Alert>}
  <Stack direction="row" sx={{
      justifyContent: "space-between",
      alignItems: "center"
    }}><Box><Typography variant="overline" color="text.secondary">GYM PULSE</Typography><Typography variant="h6">The numbers that move your day</Typography></Box><Button size="small" onClick={() => {
        load();
        operations.refresh();
      }}>Refresh</Button></Stack>
  <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: 'repeat(2,minmax(0,1fr))',
        md: 'repeat(3,minmax(0,1fr))',
      xl: 'repeat(6,minmax(0,1fr))'
      },
      gap: 1.5
    }}>{stats.map(([label, key, currency], i) => <Card className="tng-metric" key={key}><CardContent><Stack direction="row" sx={{
            justifyContent: "space-between",
            mb: 2
          }}><Typography variant="caption" sx={{
              color: '#98a3b3',
              fontWeight: 800
            }}>0{i + 1}</Typography><Box sx={{
              width: 5,
              height: 5,
              bgcolor: i === 0 ? '#087f9b' : '#d6dce6',
              borderRadius: '50%',
              mt: .7
            }} /></Stack><Typography variant="body2" color="text.secondary" sx={{
            fontSize: 12,
            fontWeight: 650,
            minHeight: 36
          }}>{label}</Typography>{dash ? <Typography variant="h4" sx={{
            mt: 1,
            fontSize: {
              xs: 27,
              lg: 28
            },
            whiteSpace: 'nowrap'
          }}>{dash[key] === undefined || dash[key] === null ? '—' : currency ? dollars(dash[key]) : dash[key]}</Typography> : <Skeleton height={45} />}<Typography variant="caption" color="text.secondary" sx={{
            display: "block",
            mt: 1
          }}>{key === 'revenue_this_month' ? 'Paid sales less refunds' : key === 'expiring_members' ? 'Included in active members' : 'Saved gym records'}</Typography></CardContent></Card>)}</Box>
  {eventError && <Alert severity="warning">{eventError}</Alert>}
  {facts?.event && <Card><CardContent><Stack direction={{
          xs: 'column',
          md: 'row'
        }} sx={{
          justifyContent: "space-between",
          alignItems: {
            md: "center"
          },
          gap: 2
        }}><Box><Typography variant="overline" color="secondary">EVENT PULSE</Typography><Typography variant="h5">{facts.event.name}</Typography><Typography color="text.secondary" variant="body2">{facts.event.date} · {facts.event.venue || 'Venue to be set'}</Typography></Box><Button variant="outlined" endIcon={<ArrowForwardRoundedIcon />} onClick={() => onNavigate('TNG BOXING EVENTS', {
            eventId: facts.event.id
          })}>Open event command center</Button></Stack><Box sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr 1fr',
            md: 'repeat(4,1fr)'
          },
          gap: 2,
          mt: 3
        }}>{[['Paid tickets', facts.tickets ? (facts.tickets.unknown_quantity_orders ? '≥ ' : '') + facts.tickets.paid_quantity : '—', 'Fully paid recorded orders'], ['Recorded ticket payments', facts.tickets ? dollars(facts.tickets.gross_paid_cents / 100) : '—', 'Gross total including fees'], ['Released paper tickets', facts.tickets?.released_paper ?? '—', 'Separate from recorded paid sales'], ['Bouts on the card', facts.card?.bouts.length ?? '—', 'Saved non-cancelled bouts']].map(([label, value, note]) => <Box key={label} sx={{
            borderLeft: '2px solid #e7edf4',
            pl: 2
          }}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h4" sx={{
              mt: .5
            }}>{value}</Typography><Typography variant="caption" color="text.secondary">{note}</Typography></Box>)}</Box></CardContent></Card>}
  <Typography variant="overline" color="text.secondary">QUICK ACCESS / YOUR WORKSPACES</Typography>
  <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: '1fr',
        sm: 'repeat(2,1fr)',
        xl: 'repeat(3,1fr)'
      },
      gap: 1.5
    }}>{launch.map(([page, label, hint, Icon]) => <Card className="tng-shortcut" key={page}><CardActionArea onClick={() => onNavigate(page)}><CardContent><Stack direction="row" sx={{
              alignItems: "center",
              gap: 1.5
            }}><Avatar variant="rounded" sx={{
                bgcolor: '#111b2b',
                color: '#eef6ff',
                width: 46,
                height: 46
              }}><Icon /></Avatar><Box sx={{
                flex: 1
              }}><Typography sx={{
                  fontWeight: 800
                }}>{label}</Typography><Typography variant="body2" color="text.secondary" sx={{
                  fontSize: 12
                }}>{hint}</Typography></Box><ArrowForwardRoundedIcon sx={{
                fontSize: 17,
                color: '#8b99aa'
              }} /></Stack></CardContent></CardActionArea></Card>)}</Box>
  <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: '1fr',
        lg: '1.35fr 1fr'
      },
      gap: 3
    }}><WorkQueue data={operations.data} loading={operations.loading} error={operations.error} onNavigate={onNavigate} limit={4} /><UpcomingEvents data={operations.data} loading={operations.loading} onNavigate={onNavigate} /></Box>
  <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: '1fr',
        md: '1fr 1fr'
      },
      gap: 3
    }}><Card><CardContent><Stack direction="row" sx={{
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2
          }}><Typography variant="h6">Recent gym check-ins</Typography><Button onClick={() => onNavigate('Member Check-In')}>Open check-in</Button></Stack>{dash?.recent_checkins?.length ? dash.recent_checkins.slice(0, 6).map((r, i) => <Stack key={i} direction="row" sx={{
            justifyContent: "space-between",
            gap: 2,
            py: 1.3,
            borderTop: '1px solid',
            borderColor: 'divider'
          }}><Typography sx={{
              fontWeight: 700
            }}>{r.member}</Typography><Typography variant="body2" color="text.secondary">{r.time ? new Date(r.time + (/(?:Z|[+-]\d\d:\d\d)$/.test(r.time) ? '' : 'Z')).toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                timeZone: 'America/Chicago'
              }) : '—'}</Typography></Stack>) : <Typography color="text.secondary">{dash ? 'No recent check-ins.' : 'Attendance data is loading.'}</Typography>}</CardContent></Card><Card><CardContent><Typography variant="h6" sx={{
            mb: 2
          }}>Sales team</Typography>{leader?.length ? leader.slice(0, 5).map((rep, i) => <Stack key={rep.rep_id || i} direction="row" sx={{
            alignItems: "center",
            gap: 1.5,
            py: 1.3,
            borderTop: '1px solid',
            borderColor: 'divider'
          }}><Avatar sx={{
              width: 30,
              height: 30,
              bgcolor: '#edf2f8',
              color: '#334155',
              fontSize: 12
            }}>{i + 1}</Avatar><Box sx={{
              flex: 1
            }}><Typography sx={{
                fontWeight: 750
              }}>{rep.name}</Typography><Typography variant="caption" color="text.secondary">{rep.sales || 0} sales</Typography></Box><Typography sx={{
              fontWeight: 800
            }}>{dollars(rep.revenue || 0)}</Typography></Stack>) : <Typography color="text.secondary">No leaderboard data available.</Typography>}</CardContent></Card></Box>
 </Stack>;
}
