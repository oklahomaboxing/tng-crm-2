export const okcDay=now=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
export function addDays(day,count){const d=new Date(day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+count);return d.toISOString().slice(0,10);}
export function addYears(day,count){const[y,m,d]=day.split('-').map(Number),year=y+count,last=new Date(Date.UTC(year,m,0)).getUTCDate();return `${year}-${String(m).padStart(2,'0')}-${String(Math.min(d,last)).padStart(2,'0')}`;}
export function scheduleRange(year,period,now=new Date()){
 const start=period==='next2'?okcDay(now):`${year}-01-01`,through=period==='next2'?addYears(start,2):`${year}-12-31`,end=addDays(through,1),chunks=[];
 for(let cursor=start;cursor<end;){const next=addDays(cursor,366)<end?addDays(cursor,366):end;chunks.push({start:cursor,end:next});cursor=next;}
 return {start,end,through,chunks};
}
export function mergeCalendars(parts){return {events:[...new Map(parts.flatMap(p=>p.events||[]).map(e=>[e.id,e])).values()],bookings:[...new Map(parts.flatMap(p=>p.bookings||[]).map(e=>[e.id,e])).values()]};}
const status=x=>String(x||'').trim().toLowerCase();
export function scheduleRows(data,{year,period='year',type='all',month='all',search='',now=new Date()}){
 const range=scheduleRange(year,period,now),today=okcDay(now),events=data?.events||[],bookings=data?.bookings||[],bookingById=new Map(bookings.map(b=>[b.id,b])),eventIds=new Set(events.map(e=>e.id));
 const rows=[...events.map(e=>({...e,booking:bookingById.get(e.booking_id),key:'event-'+e.id,kind:'tng',title:e.name,start:String(e.date||'').slice(0,10)})),...bookings.filter(b=>!b.promotion_event_id||!eventIds.has(b.promotion_event_id)).map(b=>({...b,key:'booking-'+b.id,kind:'booking',start:okcDay(new Date(b.starts_at))}))];
 return rows.filter(e=>{
  if(status(e.status)==='declined'||status(e.booking?.status)==='declined')return false;
  const past=['completed','complete','finished'].includes(status(e.status))||(e.kind==='booking'?new Date(e.ends_at).getTime()<=now.getTime():e.start<today);
  const inactive=['cancelled','canceled','archived'].includes(status(e.status));
  if((period==='current'||period==='next2')&&(past||inactive))return false;
  if(period==='past'&&!past)return false;
  if(period==='next2'&&!(e.kind==='booking'?e.start<=range.through&&okcDay(new Date(new Date(e.ends_at).getTime()-1))>=range.start:e.start>=range.start&&e.start<=range.through))return false;
  return (type==='all'||e.kind===type||(type==='booking'&&e.booking))&&(month==='all'||Number((e.start<range.start?range.start:e.start).slice(5,7))-1===Number(month))&&`${e.title} ${e.venue||''} ${e.contact_name||e.booking?.contact_name||''} ${e.status}`.toLowerCase().includes(search.toLowerCase().trim());
 }).map(e=>({...e,group:(e.start<range.start?range.start:e.start).slice(0,7)})).sort((a,b)=>a.start.localeCompare(b.start)||a.title.localeCompare(b.title));
}
