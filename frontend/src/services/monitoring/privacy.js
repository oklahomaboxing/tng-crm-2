// Allowlist only: event messages, URLs, query strings, breadcrumbs and customer data never leave TNGOS.
export function safeMonitoringEvent(event={}) {
 const values=(event.exception?.values||[]).slice(0,3).map(v=>{
  const frames=(v.stacktrace?.frames||[]).flatMap(f=>{try{const path=new URL(f.filename,'https://tngos.invalid').pathname;if(!/^\/(?:assets\/[A-Za-z0-9_.-]+\.js|src\/(?:pages|components|services|layout|theme|hooks|navigation|utils)\/[A-Za-z0-9_/.\-]+\.[jt]sx?)$/.test(path))return [];return [{filename:path,...(Number.isInteger(f.lineno)&&f.lineno>=0&&f.lineno<1e8?{lineno:f.lineno}:{}),...(Number.isInteger(f.colno)&&f.colno>=0&&f.colno<1e8?{colno:f.colno}:{})}]}catch{return []}}).slice(-20);
  return {type:'FrontendError',value:'TNGOS workspace could not render',...(frames.length?{stacktrace:{frames}}:{})};
 });
 return {event_id:/^[a-f0-9]{32}$/i.test(event.event_id||'')?event.event_id:undefined,timestamp:typeof event.timestamp==='number'?event.timestamp:undefined,platform:'javascript',level:'error',exception:values.length?{values}:undefined,tags:{application:'tngos',scope:'workspace-render'},breadcrumbs:[]};
}
export function monitoringEnabled(env={}) {return env.VITE_ERROR_MONITORING_ENABLED==='true'&&/^https:\/\/[^\s]+$/.test(env.VITE_SENTRY_DSN||'');}
