// Online-only check-in: never cache credentials, member details, API requests or attendance.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate' && new URL(event.request.url).pathname.startsWith('/kiosk/')) {
    event.respondWith(fetch(event.request).catch(() => new Response('<!doctype html><html><meta name="viewport" content="width=device-width"><title>TNG Check-In Offline</title><body style="background:#08090b;color:white;text-align:center;font:24px Arial;padding:50px"><h1>TNG BOXING</h1><p>Check-in is offline. Please visit the front desk.</p><button style="padding:24px;font-size:24px" onclick="location.reload()">Reconnect</button><script>setTimeout(()=>location.reload(),15000)</script></body></html>',{headers:{'Content-Type':'text/html','Cache-Control':'no-store'}})));
  }
});
