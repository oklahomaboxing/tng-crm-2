const generatedCode=/^[A-Za-z]\d+-[A-Fa-f0-9]{8}$/;
export function ticketSellerFromLocation(location){
 const path=location.pathname||'/';const match=path.match(/^\/tickets\/([^/]+)\/?$/);
 if(match){try{return decodeURIComponent(match[1])}catch{return match[1]}}
 if(path!=='/')return null;
 const params=new URLSearchParams(location.search||'');
 for(const key of ['seller','seller_code'])if(params.get(key))return params.get(key);
 // Ordinary gym membership referrals must keep their existing registration route.
 for(const key of ['fighter','join'])if(generatedCode.test(params.get(key)||''))return params.get(key);
 return null;
}
export function publicTicketUrl(eventId,sellerCode,origin='https://tngos.tngboxinggym.com'){
 return origin.replace(/\/$/,'')+(sellerCode?`/tickets/${encodeURIComponent(sellerCode)}`:`/events/${encodeURIComponent(eventId)}/tickets`);
}

export function legacyPhoneTicketEvent(location){
 const match=(location.pathname||'').match(/^\/events\/(\d+)\/tickets\/?$/);const params=new URLSearchParams(location.search||'');
 return match&&params.get('source')==='phone'&&!params.get('seller')&&!params.get('ticket_payment')?match[1]:null;
}
