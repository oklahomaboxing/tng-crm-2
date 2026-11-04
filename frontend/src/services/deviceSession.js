// Version the explicit choice so older cached opt-outs do not silently select timed login.
export function staySignedIn(storage = localStorage) {
  return storage.getItem('tng_session_preference_version') !== '2' || storage.getItem('tng_remember_device') !== 'false';
}
export function saveStaySignedIn(enabled, storage = localStorage) {
  storage.setItem('tng_remember_device', String(enabled));
  storage.setItem('tng_session_preference_version', '2');
}
const upgrading = new Map();
export function rememberValidSession(token, {api, storage = localStorage, fetcher = fetch, notify = () => window.dispatchEvent(new Event('tng-token-updated'))}) {
  if (upgrading.has(token)) return upgrading.get(token);
  const task = (async () => {
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    try {
      const response = await fetcher(`${api}/api/auth/remember-device`, {method:'POST',headers:{Authorization:`Bearer ${token}`},signal:controller.signal});
      if (!response.ok) return false;
      const data = await response.json();
      if (typeof data.token !== 'string' || !data.persistent) return false;
      if (storage.getItem('token') === token && staySignedIn(storage)) {
        storage.setItem('token',data.token);saveStaySignedIn(true,storage);notify();return true;
      }
      // A logout, account switch or opt-out won the race. Never restore that login.
      if (storage.getItem('token') !== data.token) await fetcher(`${api}/api/auth/logout`,{method:'POST',headers:{Authorization:`Bearer ${data.token}`},keepalive:true}).catch(()=>{});
      return false;
    } catch { return false; }
    finally { clearTimeout(timeout);upgrading.delete(token); }
  })();
  upgrading.set(token,task);
  return task;
}
