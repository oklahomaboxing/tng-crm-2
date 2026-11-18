import test from 'node:test';
import assert from 'node:assert/strict';
import { ROLE_MENUS, WORKSPACE_GROUPS, readWorkspace, workspaceHash, searchWorkspaces, dailyWorkspaces } from '../src/navigation/workspaces.js';
test('all workspaces belong to a navigation group', () => {
  const grouped = WORKSPACE_GROUPS.flatMap(x => x.pages);
  for (const pages of Object.values(ROLE_MENUS)) for (const page of pages) assert.ok(grouped.includes(page), page);
});
test('role navigation cannot open admin workspaces', () => {
  for (const role of ['staff', 'rep', 'member', 'fighter', 'matchmaker', 'manager', 'unknown']) {
    assert.equal(readWorkspace('#/system-overview', role), null);
    assert.equal(readWorkspace('#/security-center', role), null);
  }
  assert.equal(readWorkspace('#/system-overview', 'admin').page, 'System Overview');
});
test('event and member targets survive URL round trips', () => {
  assert.deepEqual(readWorkspace(workspaceHash('Members', { memberId: 12 }), 'admin'), { page: 'Members', target: { memberId: 12 } });
  assert.deepEqual(readWorkspace(workspaceHash('TNG BOXING EVENTS', { eventId: 7 }), 'staff'), { page: 'TNG BOXING EVENTS', target: { eventId: 7 } });
});
test('untrusted or mismatched targets are rejected', () => {
  for (const value of ['<script>', '-1', '0', 'Infinity', '9007199254740992']) assert.deepEqual(readWorkspace(`#/members?member=${value}`, 'admin').target, {});
  assert.deepEqual(readWorkspace('#/members?event=2', 'admin').target, {});
  assert.equal(readWorkspace('#/not-a-workspace', 'admin'), null);
  assert.equal(readWorkspace('#/members', 'rep'), null);
});

test('assistant is removed from navigation and old links cannot open it',()=>{assert.ok(!ROLE_MENUS.admin.includes('TNG Assistant'));assert.equal(readWorkspace('#/tng-assistant','admin'),null);});

test('each workspace has exactly one organizational home',()=>{
 const pages=WORKSPACE_GROUPS.flatMap(g=>g.pages);assert.equal(pages.length,new Set(pages).size);
 for(const allowed of Object.values(ROLE_MENUS))for(const page of allowed)assert.equal(pages.filter(p=>p===page).length,1);
});
test('task search finds apparel, contracts and renewal tools',()=>{
 assert.ok(searchWorkspaces('admin','shirts').includes('TNG Apparel'));
 assert.ok(searchWorkspaces('admin','text members').includes('Marketing Center'));
 assert.ok(searchWorkspaces('admin','sponsors').includes('TNG BOXING EVENTS'));
 assert.ok(searchWorkspaces('admin','signed contracts').includes('Promoter'));
 assert.ok(searchWorkspaces('admin','sms expired').includes('Renewal Reminders'));
 assert.ok(searchWorkspaces('staff','front desk').includes('Member Check-In'));
});
test('search and daily tools never expand role access',()=>{
 for(const role of [...Object.keys(ROLE_MENUS),'member','fighter','unknown']){
  const allowed=ROLE_MENUS[role]||[];
  for(const page of [...searchWorkspaces(role,''),...dailyWorkspaces(role)])assert.ok(allowed.includes(page));
 }
 assert.deepEqual(searchWorkspaces('staff','security'),[]);assert.deepEqual(searchWorkspaces('rep','shirts'),[]);
});

test('event offer desk supports direct links for authorized event staff',()=>{
 const hash=workspaceHash('TNG BOXING EVENTS',{eventId:3,eventSection:'offers'});
 for(const role of ['admin','staff','matchmaker'])assert.deepEqual(readWorkspace(hash,role),{page:'TNG BOXING EVENTS',target:{eventId:3,eventSection:'offers'}});
 assert.equal(readWorkspace(hash,'member'),null);
});

test('investor and sponsor logins have isolated portal navigation',()=>{
 for(const [role,page] of [['investor','Investor Portal'],['sponsor','Sponsor Portal'],['concessions','Chef & Concessions']]){
  assert.deepEqual(ROLE_MENUS[role],[page]);assert.equal(readWorkspace(workspaceHash(page),role).page,page);
  for(const forbidden of ['Dashboard','Members','Reports','Promoter','TNG BOXING EVENTS','User Management'])assert.equal(readWorkspace(workspaceHash(forbidden),role),null);
 }
 assert.equal(readWorkspace('#/investor-portal','sponsor'),null);assert.equal(readWorkspace('#/sponsor-portal','investor'),null);
});

test('chef workspace is available to admin and chef; event finance and matchmaker restrictions remain',()=>{
 for(const role of ['admin','concessions'])assert.equal(readWorkspace('#/chef-concessions',role).page,'Chef & Concessions');
 assert.equal(readWorkspace('#/concessions-portal','concessions').page,'Chef & Concessions');
 for(const role of ['investor','sponsor','member','fighter','rep','matchmaker'])assert.equal(readWorkspace('#/chef-concessions',role),null);
 assert.deepEqual(readWorkspace('#/tng-boxing-events?event=3&section=concessions','matchmaker').target,{eventId:3});
 assert.equal(readWorkspace('#/tng-boxing-events?event=3&section=concessions','admin').target.eventSection,'concessions');
});

test('event coordinator shares booking workspace with admin and has no other modules',()=>{
 assert.deepEqual(ROLE_MENUS.event_coordinator,['Venue & Event Bookings']);
 const route=workspaceHash('Venue & Event Bookings');
 assert.equal(readWorkspace(route,'admin').page,'Venue & Event Bookings');
 assert.equal(readWorkspace(route,'event_coordinator').page,'Venue & Event Bookings');
 for(const page of ['Dashboard','Members','Reports','User Management','TNG BOXING EVENTS'])assert.equal(readWorkspace(workspaceHash(page),'event_coordinator'),null);
});

test('amateur matchmaking is available only to event staff and matchmakers',()=>{
 for(const role of ['admin','staff','matchmaker'])assert.equal(readWorkspace('#/amateur-matchmaker',role).page,'Amateur Matchmaker');
 for(const role of ['manager','member','fighter','rep','investor','sponsor','concessions','event_coordinator'])assert.equal(readWorkspace('#/amateur-matchmaker',role),null);
});
