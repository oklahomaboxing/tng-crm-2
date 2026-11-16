import { ROLE_MENUS, WORKSPACE_HINTS, workspaceGroup } from './workspaces.js';
const related={
 Dashboard:['System Overview','Members','TNG BOXING EVENTS','Reports'],
 'System Overview':['Clover','Duplicate Review','Security Center','Reports'],
 Members:['Member Check-In','Renewal Reminders','Duplicate Review','Products'],
 'Member Check-In':['Members','Check-In Kiosk','Renewal Reminders'],
 'Check-In Kiosk':['Member Check-In','Members','System Overview'],
 'Renewal Reminders':['Members','Text Inbox','Marketing Center'],
 TNGTrainer:['Members','Member Check-In','Products'],
 Promoter:['TNG BOXING EVENTS','Fight Calendar','Fighter Portal Videos'],
 'TNG BOXING EVENTS':['Promoter','Event Check-In','Fight Calendar','Reports'],
 'Event Check-In':['TNG BOXING EVENTS','Promoter'],
 'Fight Calendar':['TNG BOXING EVENTS','Promoter'],
 'Fighter Portal Videos':['Promoter','TNG BOXING EVENTS'],
 'Manager Portal':[],
 'TNG Apparel':['Products','Sales','Clover','Marketing Center'],
 Sales:['Members','Products','Reports','Clover'],
 Products:['Sales','TNG Apparel','Clover'],
 Reports:['TNG BOXING EVENTS','Sales','System Overview'],
 'My Sales':[],
 'Text Inbox':['Members','Call Center','Marketing Center'],
 'Call Center':['Text Inbox','Leads','Members','TNG BOXING EVENTS'],
 'Marketing Center':['Members','Text Inbox','Leads','QR Referrals'],
 Leads:['Marketing Center','Call Center','QR Referrals'],
 'QR Referrals':['Leads','Marketing Center','Members'],
 Clover:['System Overview','Sales','Products','Duplicate Review'],
 'Duplicate Review':['Members','Clover','System Overview'],
 'User Management':['Security Center','System Overview'],
 'Security Center':['User Management','System Overview'],
};
export function workspaceWorkflow(role,page){
 const allowed=ROLE_MENUS[role]||[];
 if(!allowed.includes(page))return null;
 return {description:WORKSPACE_HINTS[page]||'',group:workspaceGroup(page),next:(related[page]||[]).filter(p=>allowed.includes(p))};
}
