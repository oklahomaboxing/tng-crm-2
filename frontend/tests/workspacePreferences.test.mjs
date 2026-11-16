import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizePreferences,readWorkspacePreferences,saveWorkspacePreferences,visitWorkspace,togglePinnedWorkspace} from '../src/services/workspacePreferences.js';
import {ROLE_MENUS,readWorkspace,workspaceHash} from '../src/navigation/workspaces.js';
import {workspaceWorkflow} from '../src/navigation/workflows.js';
function memory(value){let saved=value;return {getItem:()=>saved,setItem:(_,v)=>{saved=v;}};}
test('corrupt or blocked browser storage never breaks a workspace',()=>{
 assert.deepEqual(readWorkspacePreferences('staff',memory('bad json')),normalizePreferences('staff'));
 const blocked={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};
 assert.equal(saveWorkspacePreferences('admin',{density:'compact'},blocked).density,'compact');
 assert.deepEqual(readWorkspacePreferences('unknown',blocked).pinned,[]);
 assert.deepEqual(normalizePreferences('__proto__',{pinned:['Members']}).pinned,[]);
});
test('favorites and recent modules cannot cross role access boundaries',()=>{
 const prefs={pinned:['Security Center','Members','Members',42],recent:['Members','User Management'],density:'not-valid'};
 assert.deepEqual(normalizePreferences('staff',prefs),{density:'comfortable',focus:false,pinned:['Members'],recent:['Members']});
 assert.deepEqual(togglePinnedWorkspace('staff',prefs,'Security Center').pinned,['Members']);
 assert.deepEqual(visitWorkspace('staff',prefs,'Security Center').recent,['Members']);
});
test('visits reorder without duplication, pins toggle, lists stay bounded',()=>{
 let p=normalizePreferences('admin');for(const page of ROLE_MENUS.admin){p=visitWorkspace('admin',p,page);p=togglePinnedWorkspace('admin',p,page);}
 assert.equal(p.pinned.length,8);assert.equal(p.recent.length,6);
 const page=p.pinned[0];assert.ok(!togglePinnedWorkspace('admin',p,page).pinned.includes(page));
 assert.equal(visitWorkspace('admin',p,p.recent[3]).recent[0],p.recent[3]);
});
test('layout preferences persist separately for each role without any tokens',()=>{
 const storage=memory('{}');saveWorkspacePreferences('admin',{density:'compact',pinned:['Reports'],token:'do-not-store'},storage);saveWorkspacePreferences('staff',{focus:true,pinned:['Members']},storage);
 assert.deepEqual(readWorkspacePreferences('admin',storage).pinned,['Reports']);assert.equal(readWorkspacePreferences('staff',storage).focus,true);
 assert.ok(!storage.getItem().includes('do-not-store'));
});
test('all staff modules have connected workflows respecting the current role',()=>{
 for(const [role,pages] of Object.entries(ROLE_MENUS))for(const page of pages){const flow=workspaceWorkflow(role,page);assert.ok(flow?.description,page);for(const next of flow.next)assert.ok(pages.includes(next));}
 assert.equal(workspaceWorkflow('rep','Members'),null);
});
test('event section links round trip and financial recap remains staff restricted',()=>{
 const hash=workspaceHash('TNG BOXING EVENTS',{eventId:2,eventSection:'recap'});
 assert.deepEqual(readWorkspace(hash,'admin').target,{eventId:2,eventSection:'recap'});
 assert.deepEqual(readWorkspace(hash,'matchmaker').target,{eventId:2});
 assert.deepEqual(readWorkspace('#/tng-boxing-events?section=invalid','staff').target,{});
 assert.deepEqual(readWorkspace('#/members?section=contracts','admin').target,{});
 assert.deepEqual(readWorkspace('#/tng-boxing-events?section=tickets','staff').target,{eventSection:'tickets'});
});
