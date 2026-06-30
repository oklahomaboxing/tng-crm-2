import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';

const API='http://127.0.0.1:8000';
function App(){
 const [email,setEmail]=useState('admin@tngboxinggym.com');
 const [password,setPassword]=useState('admin123');
 const [token,setToken]=useState(localStorage.getItem('token')||'');
 const [dash,setDash]=useState(null); const [reps,setReps]=useState([]); const [leader,setLeader]=useState([]); const [msg,setMsg]=useState('');
 async function login(){const r=await fetch(API+'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})}); const j=await r.json(); if(j.token){localStorage.setItem('token',j.token);setToken(j.token);setMsg('Logged in')}else setMsg(j.detail||'Login failed')}
 async function load(){let h={Authorization:'Bearer '+token}; setDash(await (await fetch(API+'/api/dashboard',{headers:h})).json()); setReps(await (await fetch(API+'/api/reps',{headers:h})).json().catch(()=>[])); setLeader(await (await fetch(API+'/api/leaderboard',{headers:h})).json().catch(()=>[]));}
 async function addRep(){let name=prompt('Rep name?'); let repEmail=prompt('Rep email?'); let slug=prompt('Referral slug (example mike)?'); let clover=prompt('Clover link?'); if(!name||!repEmail||!slug)return; let r=await fetch(API+'/api/reps',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({name,email:repEmail,referral_slug:slug,clover_link:clover||'',password:'TNG12345'})}); setMsg(JSON.stringify(await r.json())); load();}
 if(!token)return <main style={{fontFamily:'Arial',maxWidth:420,margin:'60px auto'}}><h1>TNG CRM 2.0</h1><input value={email} onChange={e=>setEmail(e.target.value)} style={{width:'100%',padding:12,margin:6}}/><input type="password" value={password} onChange={e=>setPassword(e.target.value)} style={{width:'100%',padding:12,margin:6}}/><button onClick={login} style={{padding:12,width:'100%'}}>Login</button><p>{msg}</p></main>;
 return <main style={{fontFamily:'Arial',maxWidth:1000,margin:'30px auto'}}><h1>TNG CRM 2.0</h1><button onClick={load}>Load Dashboard</button> <button onClick={addRep}>Add Rep</button> <button onClick={()=>{localStorage.clear();setToken('')}}>Logout</button><p>{msg}</p>{dash&&<section><h2>Dashboard</h2><div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:10}}>{Object.entries(dash).map(([k,v])=><div style={{border:'1px solid #ddd',padding:16,borderRadius:8}}><b>{k}</b><br/>{typeof v==='number'?v.toFixed?.(2)||v:v}</div>)}</div></section>}<section><h2>Sales Reps</h2>{Array.isArray(reps)&&reps.map(r=><div style={{borderBottom:'1px solid #ddd',padding:8}}>{r.name} — /join/{r.slug}<br/><small>{r.email}</small></div>)}</section><section><h2>Leaderboard</h2>{Array.isArray(leader)&&leader.map(r=><div style={{borderBottom:'1px solid #ddd',padding:8}}>{r.name}: {r.sales} sales — ${(r.revenue||0).toFixed(2)} — {(r.rate*100).toFixed(0)}%</div>)}</section></main>
}
createRoot(document.getElementById('root')).render(<App/>);
