// Browser-only synthetic research signals. No hardware or external network access.
export const CHANNELS=['Fp1','Fp2','F3','F4','C3','C4','O1','O2'];
export const FS=250;
export const BANDS={delta:[.5,4],theta:[4,8],alpha:[8,13],beta:[13,30],gamma:[30,45]};
const FREQUENCIES={alpha:10,beta:20,theta:6};
export function createSimulator(seed=42){
 let state=seed>>>0,offset=0;
 const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return(state+1)/4294967297;};
 return {read(mode='alpha',artifact=false){
  if(!(mode in FREQUENCIES))throw Error('Unsupported simulated oscillator');
  const samples=CHANNELS.map((_,ch)=>Array.from({length:50},(_,j)=>{
   const t=(offset+j)/FS,noise=Math.sqrt(-2*Math.log(random()))*Math.cos(2*Math.PI*random())*3;
   let v=24*Math.sin(2*Math.PI*FREQUENCIES[mode]*t+ch*.16)+5*Math.sin(2*Math.PI*3*t)+noise;
   if(artifact&&ch===0)v+=190*Math.sin(2*Math.PI*1.2*t);
   if(artifact&&ch===1)v+=75*Math.sin(2*Math.PI*50*t);
   if(artifact&&ch===2)v=0;
   return Math.round(v*1000)/1000;
  }));
  const frame={source:'TNGOS_BROWSER_SIMULATED',simulated:true,sample_rate:FS,channels:CHANNELS,time_seconds:offset/FS,mode,samples};offset+=50;return frame;
 }};
}
// In-place radix-2 FFT; Welch windows are fixed at 256 samples.
function fft(re,im){const n=re.length;for(let i=1,j=0;i<n;i++){let bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j){[re[i],re[j]]=[re[j],re[i]];}}
 for(let len=2;len<=n;len<<=1){const a=-2*Math.PI/len;for(let i=0;i<n;i+=len)for(let j=0;j<len/2;j++){const c=Math.cos(a*j),s=Math.sin(a*j),u=i+j,v=u+len/2,tr=re[v]*c-im[v]*s,ti=re[v]*s+im[v]*c;re[v]=re[u]-tr;im[v]=im[u]-ti;re[u]+=tr;im[u]+=ti;}}}
export function analyze(samples){
 if(samples.length!==8||samples.some(r=>r.length<256||r.some(v=>!Number.isFinite(v))))return null;
 const bands=Object.fromEntries(Object.keys(BANDS).map(k=>[k,0])),absolute={...bands},quality=[];
 const n=256,df=FS/n,window=Array.from({length:n},(_,i)=>.5-.5*Math.cos(2*Math.PI*i/n)),scale=FS*window.reduce((a,b)=>a+b*b,0);
 samples.forEach((raw,ch)=>{const row=raw.slice(-500),psd=Array(n/2+1).fill(0);let count=0;
  for(let start=0;start+n<=row.length;start+=128){const segment=row.slice(start,start+n),mean=segment.reduce((a,b)=>a+b,0)/n,re=segment.map((v,i)=>(v-mean)*window[i]),im=Array(n).fill(0);fft(re,im);for(let k=0;k<psd.length;k++)psd[k]+=(re[k]*re[k]+im[k]*im[k])*(k&&k<n/2?2:1)/scale;count++;}
  for(let k=0;k<psd.length;k++)psd[k]/=count;
  const powers=Object.fromEntries(Object.entries(BANDS).map(([name,[lo,hi]])=>[name,psd.reduce((a,v,k)=>a+(k*df>=lo&&k*df<hi?v*df:0),0)])),total=Math.max(1e-12,Object.values(powers).reduce((a,b)=>a+b,0));
  for(const name in powers){bands[name]+=powers[name]/total/8;absolute[name]+=powers[name]/8;}
  const mean=row.reduce((a,b)=>a+b,0)/row.length,std=Math.sqrt(row.reduce((a,b)=>a+(b-mean)**2,0)/row.length),flags=[];
  if(std<.2)flags.push('flatline');if(Math.max(...row.map(Math.abs))>120)flags.push('high amplitude');if(row.some((v,i)=>i>0&&Math.abs(v-row[i-1])>100))flags.push('abrupt step');
  const line=psd.reduce((a,v,k)=>a+(k*df>=49&&k*df<=61?v:0),0)/Math.max(1e-12,psd.reduce((a,b)=>a+b,0));if(line>.25)flags.push('line noise');
  quality.push({channel:CHANNELS[ch],score:Math.max(0,100-35*flags.length),flags});
 });
 const [dominant,confidence]=Object.entries(bands).sort((a,b)=>b[1]-a[1])[0];
 return{bands,absolute,quality,window_seconds:Math.min(500,samples[0].length)/FS,classification:quality.some(q=>q.flags.length)?{label:'abstain',confidence:0}:{label:dominant,confidence},method:'Browser Welch PSD + dominant-band baseline; not the standalone PyTorch model'};
}
export function virtualStep(position,label){const d={alpha:[-6,0],beta:[6,0],theta:[0,-6]}[label]||[0,0];return{x:Math.max(4,Math.min(96,position.x+d[0])),y:Math.max(4,Math.min(96,position.y+d[1]))};}
export function standaloneUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return null;}}
