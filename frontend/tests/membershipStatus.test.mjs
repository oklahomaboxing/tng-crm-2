import test from 'node:test';
import assert from 'node:assert/strict';
import {memberDate,membershipCategory,rosterTotals} from '../src/utils/membershipStatus.js';
test('UTC timestamps are not interpreted as local Central Time',()=>{
 assert.equal(memberDate('2026-11-01T12:00:00').toISOString(),'2026-11-01T12:00:00.000Z');
 assert.equal(memberDate('2026-11-01T07:00:00-05:00').toISOString(),'2026-11-01T12:00:00.000Z');
 assert.equal(memberDate('bad'),null);
});
test('server membership category wins over stale saved active flags',()=>{
 assert.equal(membershipCategory({membership_category:'expired',membership_status:'active'}),'expired');
 assert.equal(membershipCategory({member_type:'CUSTOMER',membership_status:'pending'}),'contact');
});
test('active includes expiring and contacts are excluded from members',()=>{
 const totals=rosterTotals(['active','expiring','expired','contact','review'].map(membership_category=>({membership_category})));
 assert.equal(totals.active,2);assert.equal(totals.expiring,1);assert.equal(totals.expired,1);assert.equal(totals.contact,1);assert.equal(totals.all,4);
});
test('end time already passed is expired even less than one day ago',()=>{
 const now=Date.parse('2026-11-01T12:00:00Z');
 const row={first_name:'Gym',email:'gym@example.com',member_type:'MEMBER',membership_status:'active',membership_start:'2026-10-01T12:00:00',membership_end:'2026-11-01T11:59:59'};
 assert.equal(membershipCategory(row,now),'expired');
});
test('missing name or email does not qualify as a member in fallback',()=>{
 for(const identity of [{first_name:'A'},{email:'a@example.com'},{first_name:'A',email:'bad'}]){
  assert.equal(membershipCategory({...identity,member_type:'MEMBER',membership_status:'active',membership_start:'2026-11-01'}),'contact');
 }
});
