const KEY='tngTicketPurchaseAttemptV1';
export function purchaseAttempt(payload, memory, storage, makeKey=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('')) {
 try{storage=storage||window.localStorage}catch{}
 const fingerprint=JSON.stringify(payload);let saved=memory;
 if(!saved){try{saved=JSON.parse(storage.getItem(KEY)||'null')}catch{}}
 // Reuse the same request after errors, reloads or repeated taps; never reuse a changed cart.
 const attempt=saved?.fingerprint===fingerprint&&/^[a-f0-9]{32}$/.test(saved.key)?saved:{fingerprint,key:makeKey()};
 try{storage.setItem(KEY,JSON.stringify(attempt))}catch{}
 return attempt;
}
export function clearPurchaseAttempt(){try{window.localStorage.removeItem(KEY)}catch{}}
