import React,{useState} from 'react';
import {Alert,Stack,Tab,Tabs,Typography} from '@mui/material';
import AmateurDirectory from './AmateurDirectory';
import ClubWorkMessages from './ClubWorkMessages';
import TextInbox from './TextInbox';
export default function OklahomaBoxingClubs(){
 const[working,setWorking]=useState(false),[tab,setTab]=useState('contacts'),[contactId,setContactId]=useState(null),[inboxView,setInboxView]=useState('clubs');
 const messageClub=c=>{setContactId(c.id);setTab('messages');};
 return <Stack spacing={2}><Typography variant="overline" color="primary">TNG BOXING / CLUB CONTACTS</Typography><Tabs value={tab} onChange={(_,v)=>{if(!working)setTab(v);}} variant="scrollable" allowScrollButtonsMobile><Tab disabled={working} value="contacts" label="Club contacts"/><Tab disabled={working} value="messages" label="Message clubs"/><Tab disabled={working} value="inbox" label="Club inbox"/></Tabs>{tab==='contacts'?<AmateurDirectory kind="club" stateFilter="OK" onMessage={messageClub}/>:tab==='messages'?<ClubWorkMessages onBusyChange={setWorking} initialContactId={contactId} onViewInbox={()=>{setInboxView('conversations');setTab('inbox');}}/>:<Stack spacing={2}><Tabs value={inboxView} onChange={(_,v)=>{if(!working)setInboxView(v);}}><Tab disabled={working} value="clubs" label="Find a club / new message"/><Tab disabled={working} value="conversations" label="Existing conversations"/></Tabs>{inboxView==='clubs'?<><Alert severity="info">All saved Oklahoma clubs appear here, including clubs with no messages yet. Choose Message club to compose a work text. Saved conversations and replies are in Existing conversations.</Alert><AmateurDirectory kind="club" stateFilter="OK" onMessage={messageClub}/></>:<TextInbox initialScope="clubs" fixedScope onBusyChange={setWorking}/>}</Stack>}</Stack>;
}
