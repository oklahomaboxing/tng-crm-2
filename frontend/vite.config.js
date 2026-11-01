import { defineConfig } from 'vite';
// Android 11 shipped with Chromium/WebView 83; keep kiosk entry syntax compatible.
// Browser/WebView security updates are still recommended on the physical device.
export default defineConfig({ build: { target: 'chrome83' } });
