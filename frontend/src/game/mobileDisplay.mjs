// Optional browser features must never prevent a round from starting.
export async function requestScreenAwake(wakeLock){try{return wakeLock?.request?await wakeLock.request('screen'):null;}catch{return null;}}
export function isPhonePlay(touch,width){return !!touch&&Number.isFinite(width)&&width<1100;}
