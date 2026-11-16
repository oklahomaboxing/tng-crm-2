const OFF_CARD=new Set(['cancelled','canceled','void','withdrawn','declined','rejected','removed','deleted']);
export function isCurrentBout(bout){return !OFF_CARD.has(String(bout?.status||'').trim().toLowerCase());}
