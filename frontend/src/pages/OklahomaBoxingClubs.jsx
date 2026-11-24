import React,{useState} from 'react';
import {Stack,Tab,Tabs,Typography} from '@mui/material';
import AmateurDirectory from './AmateurDirectory';
import ClubWorkMessages from './ClubWorkMessages';
import TextInbox from './TextInbox';
export default function OklahomaBoxingClubs(){
 const[working,setWorking]=useState(false),[tab,setTab]=useState('contacts'),[contactId,setContactId]=useState(null);
 return <Stack spacing={2}><Typography variant="overline" color="primary">TNG BOXING / CLUB CONTACTS</Typography><Tabs value={tab} onChange={(_,v)=>{if(!working)setTab(v);}} variant="scrollable" allowScrollButtonsMobile><Tab disabled={working} value="contacts" label="Club contacts"/><Tab disabled={working} value="messages" label="Message clubs"/><Tab disabled={working} value="inbox" label="Club inbox"/></Tabs>{tab==='contacts'?<AmateurDirectory kind="club" stateFilter="OK" onMessage={c=>{setContactId(c.id);setTab('messages');}}/>:tab==='messages'?<ClubWorkMessages onBusyChange={setWorking} initialContactId={contactId} onViewInbox={()=>setTab('inbox')}/>:<TextInbox initialScope="clubs" fixedScope onBusyChange={setWorking}/>}</Stack>;
}
