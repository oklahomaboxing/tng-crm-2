import React,{useEffect,useState} from 'react';
import PublicTicketCheckout from './PublicTicketCheckout.jsx';
const API=(import.meta.env.VITE_API_URL||'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/,'');
export default function PublicSellerTickets({sellerCode,phoneEventId}){
 const[data,setData]=useState(null),[error,setError]=useState('');
 useEffect(()=>{let alive=true;setData(null);setError('');fetch(phoneEventId?`${API}/api/ticketing/public/events/${encodeURIComponent(phoneEventId)}/phone-portal`:`${API}/api/ticketing/public/sellers/${encodeURIComponent(sellerCode)}/portal`,{cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok)throw Error('This ticket link could not be found. Ask the fighter for their current ticket-sales link.');if(!alive)return;const u=new URL(d.seller_code?`/tickets/${encodeURIComponent(d.seller_code)}`:`/events/${d.event_id}/tickets`,window.location.origin);u.search=window.location.search;['seller','seller_code','fighter','join'].forEach(k=>u.searchParams.delete(k));window.history.replaceState({},'',u.pathname+u.search+window.location.hash);setData(d)}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[sellerCode,phoneEventId]);
 if(data)return <PublicTicketCheckout key={`${data.event_id}-${data.seller_code}`} eventId={data.event_id} sellerCode={data.seller_code}/>;
 return <main style={{minHeight:'100vh',background:'#09090b',color:'#fff',padding:32,fontFamily:'Arial,sans-serif'}}><section style={{maxWidth:640,margin:'50px auto'}}><h1>Ticket Sales Portal</h1>{error?<><p role="alert">{error}</p><a style={{color:'#ff9bad'}} href="mailto:marketing@tngboxinggym.com">Contact TNG for help</a></>:<p role="status">Opening your ticket sales page…</p>}</section></main>;
}
