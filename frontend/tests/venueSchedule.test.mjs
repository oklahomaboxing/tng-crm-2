import test from'node:test';import assert from'node:assert/strict';import{addDays,addYears,scheduleRange,mergeCalendars,scheduleRows}from'../src/venue/schedule.mjs';
const now=new Date('2026-11-27T18:00:00Z'),options={year:2026,now};
const event=(id,date,status='planning',extra={})=>({id,date,status,name:'Event '+id,...extra});
test('declined events and declined linked bookings disappear in every view without changing source data',()=>{
 const d={events:[event(1,'2026-12-01','declined'),event(2,'2026-12-02','cancelled',{booking_id:3}),event(4,'2026-12-03')],bookings:[{id:3,status:'declined',promotion_event_id:2,starts_at:'2026-12-02T15:00:00Z',ends_at:'2026-12-02T18:00:00Z'}]};
 for(const period of['year','current','past','next2']){const ids=scheduleRows(d,{...options,period}).map(e=>e.id);assert.ok(!ids.includes(1)&&!ids.includes(2)&&!ids.includes(3));}assert.equal(d.events.length,3);
});
test('current and past views distinguish completed events, today, ongoing and ended bookings',()=>{
 const d={events:[event(1,'2026-11-26'),event(2,'2026-11-27'),event(3,'2026-12-01','completed'),event(4,'2026-12-02','cancelled')],bookings:[{id:5,title:'Ended',status:'confirmed',starts_at:'2026-11-27T15:00:00Z',ends_at:'2026-11-27T16:00:00Z'},{id:6,title:'Ongoing',status:'on_hold',starts_at:'2026-11-27T17:00:00Z',ends_at:'2026-11-27T19:00:00Z'}]};
 assert.deepEqual(scheduleRows(d,{...options,period:'current'}).map(e=>e.id).sort(),[2,6]);assert.deepEqual(scheduleRows(d,{...options,period:'past'}).map(e=>e.id).sort(),[1,3,5]);
});
test('next two years spans calendar years, includes the end day, and merges boundary duplicates',()=>{
 const r=scheduleRange(2026,'next2',now);assert.equal(r.start,'2026-11-27');assert.equal(r.through,'2028-11-27');assert.equal(r.end,'2028-11-28');for(const c of r.chunks)assert.ok((Date.parse(c.end)-Date.parse(c.start))/86400000<=366);
 const e=event(1,'2027-05-01'),merged=mergeCalendars([{events:[e],bookings:[]},{events:[e,event(2,'2028-11-27'),event(3,'2028-11-28')],bookings:[]}]);assert.equal(merged.events.length,3);assert.deepEqual(scheduleRows(merged,{...options,period:'next2'}).map(e=>e.id),[1,2]);assert.deepEqual(scheduleRows(merged,{...options,period:'next2'}).map(e=>e.group),['2027-05','2028-11']);
});
test('leap-day ranges clamp correctly and dates use Oklahoma City rather than UTC day',()=>{assert.equal(addYears('2028-02-29',2),'2030-02-28');assert.equal(addDays('2028-02-29',1),'2028-03-01');assert.equal(scheduleRange(2026,'next2',new Date('2026-11-28T02:00:00Z')).start,'2026-11-27');});
