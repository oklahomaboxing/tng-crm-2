import React, {useState} from 'react';
import {Alert,Button,Checkbox,FormControlLabel,Dialog,DialogActions,DialogContent,DialogTitle,Stack,TextField,Typography} from '@mui/material';
import {API,authHeaders} from '../../services/api';
const empty={first_name:'',last_name:'',email:'',phone:'',address:'',city:'',state:'',zip_code:'',notes:'',activate_membership:true,membership_name:'Monthly Membership',membership_rate:150,membership_months:1};
export default function AddMemberDialog({open,onClose,onCreated}){
 const [sendSetup,setSendSetup]=useState(false);
 const [form,setForm]=useState(empty),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function save(event){event.preventDefault();if(busy)return;setBusy(true);setError('');try{
  const response=await fetch(`${API}/api/members`,{method:'POST',headers:{...authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({...form,membership_rate:Number(form.membership_rate),membership_months:Number(form.membership_months)})});
  const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not create member.');
  let setupMessage='';
  if(sendSetup){try{const sent=await fetch(`${API}/api/member/admin/invite`,{method:'POST',headers:{...authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({member_id:data.id})});const result=await sent.json();setupMessage=sent.ok?' Password setup email is sent or already available.':' Member saved; review password setup in the profile.';}catch{setupMessage=' Member saved; review password setup in the profile.';}}
  setForm(empty);setSendSetup(false);onCreated(data,`Active membership created at $${Number(form.membership_rate).toFixed(2)} for ${form.membership_months} month(s). ${data.account_access?.created || data.account_access?.already_active ? 'Portal account active; the member sets their password securely.' : 'Account access needs contact ownership review in the profile.'} No payment was recorded by this action.${setupMessage}`);
 }catch(err){setError(err.message);}finally{setBusy(false);}}
 return <Dialog open={open} onClose={busy?undefined:onClose} fullWidth maxWidth="sm"><form onSubmit={save}><DialogTitle>Add Active Member</DialogTitle><DialogContent><Stack spacing={2} sx={{pt:1}}>
 <Typography>Create the member, account access and active membership in one step. Set their agreed rate below.</Typography>{error&&<Alert severity="error">{error}</Alert>}
 {[['first_name','First name'],['last_name','Last name'],['email','Email'],['phone','Phone with area code']].map(([key,label])=><TextField key={key} label={label} type={key==='email'?'email':key==='phone'?'tel':'text'} value={form[key]} required disabled={busy} onChange={e=>setForm({...form,[key]:e.target.value})}/>)}
 <TextField label="Membership plan" value={form.membership_name} required onChange={e=>setForm({...form,membership_name:e.target.value})}/>
 <Stack direction="row" spacing={2}><TextField fullWidth label="Agreed rate ($ per term)" type="number" slotProps={{htmlInput:{min:0,max:100000,step:"0.01"}}} value={form.membership_rate} required onChange={e=>setForm({...form,membership_rate:e.target.value})}/><TextField fullWidth label="Term (months)" type="number" slotProps={{htmlInput:{min:1,max:120,step:1}}} value={form.membership_months} required onChange={e=>setForm({...form,membership_months:e.target.value})}/></Stack>
 <FormControlLabel label="Send password setup email" control={<Checkbox checked={sendSetup} onChange={e=>setSendSetup(e.target.checked)}/>}/>
 <Alert severity="info">This activates the membership. Record any money received in Sales; this form does not charge Clover or create a payment.</Alert>
 <TextField label="Notes" multiline value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/>
 </Stack></DialogContent><DialogActions><Button disabled={busy} onClick={onClose}>Cancel</Button><Button type="submit" variant="contained" disabled={busy}>{busy?'Creating…':'Create Active Member'}</Button></DialogActions></form></Dialog>;
}
