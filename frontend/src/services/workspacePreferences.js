import { ROLE_MENUS } from '../navigation/workspaces.js';
export const WORKSPACE_PREFERENCES_KEY='tng_workspace_preferences_v1';
export function normalizePreferences(role,value={}) {
  const allowed=Array.isArray(ROLE_MENUS[role])?ROLE_MENUS[role]:[];
  const list=(items,max)=>Array.isArray(items)?[...new Set(items.filter(p=>typeof p==='string'&&allowed.includes(p)))].slice(0,max):[];
  return {density:value?.density==='compact'?'compact':'comfortable',layout_version:2,focus:value?.layout_version===2?value?.focus!==false:true,pinned:list(value?.pinned,8),recent:list(value?.recent,6)};
}
export function readWorkspacePreferences(role,storage) {
  try{return normalizePreferences(role,JSON.parse((storage||window.localStorage).getItem(WORKSPACE_PREFERENCES_KEY)||'{}')?.[role]);}catch{return normalizePreferences(role);}
}
export function saveWorkspacePreferences(role,value,storage) {
  const next=normalizePreferences(role,value);
  try{const target=storage||window.localStorage;let saved;try{saved=JSON.parse(target.getItem(WORKSPACE_PREFERENCES_KEY)||'{}');}catch{}if(!saved||typeof saved!=='object'||Array.isArray(saved))saved={};if(Object.prototype.hasOwnProperty.call(ROLE_MENUS,role))target.setItem(WORKSPACE_PREFERENCES_KEY,JSON.stringify({...saved,[role]:next}));}catch{}
  return next;
}
export function visitWorkspace(role,value,page){const current=normalizePreferences(role,value);return normalizePreferences(role,{...current,recent:[page,...current.recent]});}
export function togglePinnedWorkspace(role,value,page){const current=normalizePreferences(role,value);if(!Array.isArray(ROLE_MENUS[role])||!ROLE_MENUS[role].includes(page))return current;return normalizePreferences(role,{...current,pinned:current.pinned.includes(page)?current.pinned.filter(p=>p!==page):[page,...current.pinned]});}
