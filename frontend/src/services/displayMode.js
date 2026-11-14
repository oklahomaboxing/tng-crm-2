export const DISPLAY_MODE_KEY='tng_display_mode_v1';
export function readDisplayMode(storage){try{return (storage||window.localStorage).getItem(DISPLAY_MODE_KEY)==='command'?'command':'standard'}catch{return 'standard'}}
export function saveDisplayMode(mode,storage){const value=mode==='command'?'command':'standard';try{(storage||window.localStorage).setItem(DISPLAY_MODE_KEY,value)}catch{}return value}
