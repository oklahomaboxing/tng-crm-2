import {monitoringEnabled,safeMonitoringEvent}from'./privacy';
let reporter=null,starting=null;
export function initializeMonitoring(){
 if(starting)return starting;
 if(!monitoringEnabled(import.meta.env))return Promise.resolve(false);
 starting=import('@sentry/react').then(Sentry=>{Sentry.init({dsn:import.meta.env.VITE_SENTRY_DSN,sendDefaultPii:false,defaultIntegrations:false,autoSessionTracking:false,tracesSampleRate:0,beforeSend:safeMonitoringEvent,environment:import.meta.env.MODE});reporter=Sentry;return true;}).catch(()=>false);return starting;
}
export function reportWorkspaceError(error){if(reporter)reporter.captureException(error);}
