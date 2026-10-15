import React, { useEffect, useRef, useState } from "react";
import { Alert, Box, Button, Card, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, MenuItem, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { BookmarkPlus, ExternalLink, Search, Users } from "lucide-react";
const API=import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
async function request(path,options={}) {
 const r=await fetch(`${API}/api/boxing/scouting${path}`,{...options,headers:{Authorization:`Bearer ${localStorage.getItem("token")}`,"Content-Type":"application/json"},signal:AbortSignal.timeout(70000)});
 const data=await r.json();if(!r.ok)throw Error(typeof data.detail==="string"?data.detail:"Could not complete the request");return data;
}
const label=x=>x.replaceAll("_"," ");
export default function BoxerDatabase() {
 const [options,setOptions]=useState({states:{},divisions:[]}),[data,setData]=useState({items:[],total:0,database_total:0,shortlisted:0});
 const [q,setQ]=useState(""),[division,setDivision]=useState(""),[state,setState]=useState(""),[status,setStatus]=useState(""),[contact,setContact]=useState(false),[page,setPage]=useState(1);
 const [loading,setLoading]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState(""),[selected,setSelected]=useState(null),[note,setNote]=useState(""),[editStatus,setEditStatus]=useState("new"),[availability,setAvailability]=useState("unknown");
 const [running,setRunning]=useState(false),[progress,setProgress]=useState(null),[discoveryClass,setDiscoveryClass]=useState(""),[searchNote,setSearchNote]=useState("");
 const stop=useRef(false),active=useRef(true),paramsRef=useRef(""),loadVersion=useRef(0);
 const params=new URLSearchParams({q,division,state,status,page:String(page),contact_only:String(contact)}).toString();
 paramsRef.current=params;
 async function load(){const version=++loadVersion.current;setLoading(true);try{const x=await request(`/prospects?${paramsRef.current}`);if(active.current&&version===loadVersion.current)setData(x);}catch(e){if(active.current)setError(e.message);}finally{if(active.current)setLoading(false);}}
 useEffect(()=>{active.current=true;request('/options').then(setOptions).catch(e=>setError(e.message));return()=>{active.current=false;stop.current=true;};},[]);
 useEffect(()=>{const id=setTimeout(load,250);return()=>clearTimeout(id);},[params]);
 function filter(setter,value){setter(value);setPage(1);}
 function open(row){setSelected(row);setNote(row.notes||"");setEditStatus(row.status);setAvailability(row.availability);}
 async function save(){try{await request(`/prospects/${selected.id}`,{method:'PATCH',body:JSON.stringify({status:editStatus,availability,notes:note})});setSelected(null);setMessage('Prospect updated. Active roster and bouts were not changed.');load();}catch(e){setError(e.message);}}
 async function shortlist(row){try{await request(`/prospects/${row.id}`,{method:'PATCH',body:JSON.stringify({status:row.status==='shortlisted'?'reviewing':'shortlisted',availability:row.availability,notes:row.notes||''})});load();}catch(e){setError(e.message);}}
 async function discover(){
  stop.current=false;setRunning(true);setError('');setMessage('');
  const classes=discoveryClass?options.divisions.filter(x=>x.key===discoveryClass):options.divisions;
  let added=0,failed=0,completed=0;
  for(const item of classes){
   if(stop.current || !active.current)break;
   setProgress({done:completed,total:classes.length,label:item.label,added,failed});
   try{const r=await request('/discover',{method:'POST',body:JSON.stringify({division:item.key,states:state?[state]:Object.keys(options.states),query:searchNote})});added+=r.inserted;}
   catch(e){failed++;if(active.current)setError(`${item.label}: ${e.message}`);}
   completed++;if(active.current){setProgress({done:completed,total:classes.length,label:item.label,added,failed});load();}
  }
  if(active.current){setMessage(`Research finished: ${added} new prospects saved; ${completed} weight groups searched; ${failed} failed requests. Empty groups remain empty. Coverage is not a complete boxer registry.`);setRunning(false);}
 }
 return <Stack spacing={2.5}>
  <Box><Typography className="promotion-eyebrow" color="text.secondary">NATIONWIDE SCOUTING / SEPARATE FROM YOUR ACTIVE ROSTER</Typography><Typography component="h1" variant="h4" sx={{mt:1}}>Your boxer scouting database.</Typography><Typography color="text.secondary" sx={{mt:1}}>Browse source-backed prospects across weight groups. Review the evidence, choose your shortlist, then confirm the details.</Typography></Box>
  <Stack direction="row" useFlexGap sx={{gap:2,flexWrap:"wrap"}}>{[[data.database_total,'Saved prospects'],[data.shortlisted,'Shortlisted'],[options.divisions.length,'Weight groups']].map(([n,l])=><Chip key={l} icon={<Users size={15}/>} label={`${n} ${l}`}/>)}</Stack>
  <Alert severity="info">Research records are not certified records or confirmed availability. Weight group is a search category; verify actual weight, current record, identity and commission eligibility before making a match. Selecting a prospect does not book or contact them.</Alert>
  {error&&<Alert severity="error" onClose={()=>setError('')}>{error}</Alert>}{message&&<Alert severity="success" onClose={()=>setMessage('')}>{message}</Alert>}
  <Card sx={{p:2.5}}>
   <Typography variant="h6">Grow the database</Typography><Typography variant="body2" color="text.secondary" sx={{mb:2}}>Search public sources and save sourced results automatically. Each group returns up to eight candidates; repeated searches skip exact-source duplicates. Nationwide is the default; the state filter below also narrows new research.</Typography>
   <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'240px minmax(0,1fr) auto'},gap:2}}>
    <TextField select label="Research weight groups" value={discoveryClass} onChange={e=>setDiscoveryClass(e.target.value)} disabled={running}><MenuItem value="">All weight groups</MenuItem>{options.divisions.map(x=><MenuItem key={x.key} value={x.key}>{x.label}{x.limit_lb?` · ${x.limit_lb} lb`:''}</MenuItem>)}</TextField>
    <TextField label="Research focus (optional)" placeholder="e.g. developing pros with public gym contacts" value={searchNote} onChange={e=>setSearchNote(e.target.value)} disabled={running} slotProps={{htmlInput:{maxLength:200}}}/>
    <Button variant="contained" startIcon={running?<CircularProgress size={16} color="inherit"/>:<Search size={17}/>} disabled={running||!options.divisions.length} onClick={discover}>{running?'Researching…':'Find & save prospects'}</Button>
   </Box>
   {running&&<Box sx={{mt:2}}><LinearProgress variant="determinate" value={progress?progress.done/progress.total*100:0}/><Typography variant="body2" sx={{mt:1}}>{progress?.label}: {progress?.done}/{progress?.total} groups completed · {progress?.added||0} new prospects</Typography><Button onClick={()=>{stop.current=true;setMessage('Stopping after the current request. Saved prospects will remain.');}}>Stop after this group</Button></Box>}
  </Card>
  <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))',lg:'2fr 1fr 1fr 1fr'},gap:1.5}}>
   <TextField label="Search name, record, city or gym" value={q} onChange={e=>filter(setQ,e.target.value)}/>
   <TextField select label="Weight group" value={division} onChange={e=>filter(setDivision,e.target.value)}><MenuItem value="">All weight groups</MenuItem>{options.divisions.map(x=><MenuItem key={x.key} value={x.key}>{x.label}</MenuItem>)}<MenuItem value="unknown">Unknown</MenuItem></TextField>
   <TextField select label="State / research area" value={state} onChange={e=>filter(setState,e.target.value)}><MenuItem value="">Nationwide</MenuItem>{Object.entries(options.states).map(([k,v])=><MenuItem key={k} value={k}>{v}</MenuItem>)}</TextField>
   <TextField select label="Status" value={status} onChange={e=>filter(setStatus,e.target.value)}><MenuItem value="">All statuses</MenuItem>{['new','reviewing','shortlisted','contacted','passed'].map(x=><MenuItem key={x} value={x}>{label(x)}</MenuItem>)}</TextField>
  </Box>
  <Stack direction="row" spacing={1} alignItems="center"><Button variant={contact?'contained':'outlined'} onClick={()=>filter(setContact,!contact)}>With published contact</Button><Typography variant="body2" color="text.secondary">{data.total} matching prospects {loading?'· Loading…':''}</Typography></Stack>
  <Card><TableContainer><Table size="small" sx={{minWidth:760}}><TableHead><TableRow>{['Boxer / source-reported record','Location','Reported weight / research group','Status','Choose'].map(x=><TableCell key={x}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{data.items.map(row=><TableRow key={row.id} hover><TableCell><Button onClick={()=>open(row)} sx={{fontWeight:800,justifyContent:'flex-start',textAlign:'left'}}>{row.name}</Button><Typography variant="body2" color="text.secondary">{row.record||'Record unknown'}</Typography></TableCell><TableCell>{[row.city,row.state].filter(Boolean).join(', ')}<Typography variant="caption" sx={{display:"block",mt:.5}}>{row.gym_or_manager||'Gym / manager unknown'}</Typography></TableCell><TableCell>{row.weight||'Weight not established'}<Typography variant="caption" sx={{display:"block",mt:.5}}>Research group: {label(row.division)}</Typography></TableCell><TableCell><Chip size="small" label={label(row.status)}/><Typography variant="caption" sx={{display:"block",mt:.5}}>Availability: {row.availability}</Typography></TableCell><TableCell><Button variant={row.status==='shortlisted'?'contained':'outlined'} startIcon={<BookmarkPlus size={14}/>} onClick={()=>shortlist(row)}>{row.status==='shortlisted'?'Selected':'Shortlist'}</Button></TableCell></TableRow>)}</TableBody></Table></TableContainer>{!data.items.length&&!loading&&<Box sx={{p:4,textAlign:'center'}}><Typography fontWeight={800}>No prospects match this view.</Typography><Typography color="text.secondary">Run a research group above or broaden your filters. Discovered prospects stay separate from the active fighter pool.</Typography></Box>}</Card>
  <Stack direction="row" sx={{alignItems:"center",justifyContent:"space-between",gap:2}}><Button disabled={page<=1||loading} onClick={()=>setPage(p=>p-1)}>Previous</Button><Typography variant="body2">Page {page} of {Math.max(1,Math.ceil(data.total/30))}</Typography><Button disabled={page*30>=data.total||loading} onClick={()=>setPage(p=>p+1)}>Next</Button></Stack>
  <Dialog open={!!selected} onClose={()=>setSelected(null)} fullWidth maxWidth="md"><DialogTitle>{selected?.name}</DialogTitle><DialogContent>{selected&&<Stack spacing={2} sx={{pt:1}}><Typography>{selected.last_activity||'Recent activity unknown.'}</Typography><Typography sx={{whiteSpace:'pre-wrap'}}>{selected.evidence}</Typography><Button component="a" href={selected.source_url} target="_blank" rel="noopener noreferrer" endIcon={<ExternalLink size={15}/>}>Open original source</Button><Typography variant="body2">Researched: {new Date(selected.researched_at+'Z').toLocaleString()}</Typography><Typography>Published contact: {selected.business_phone||selected.business_email||'Not found. Review the source or associated gym.'}</Typography><TextField select label="Prospect status" value={editStatus} onChange={e=>setEditStatus(e.target.value)}>{['new','reviewing','shortlisted','contacted','passed'].map(x=><MenuItem key={x} value={x}>{label(x)}</MenuItem>)}</TextField><TextField select label="Staff-confirmed availability" value={availability} onChange={e=>setAvailability(e.target.value)}>{['unknown','available','unavailable'].map(x=><MenuItem key={x} value={x}>{x}</MenuItem>)}</TextField><TextField multiline minRows={3} label="Notes, bout interest and follow-up" value={note} onChange={e=>setNote(e.target.value)} slotProps={{htmlInput:{maxLength:4000}}}/></Stack>}</DialogContent><DialogActions><Button onClick={()=>setSelected(null)}>Close</Button><Button variant="contained" onClick={save}>Save review</Button></DialogActions></Dialog>
 </Stack>;
}
