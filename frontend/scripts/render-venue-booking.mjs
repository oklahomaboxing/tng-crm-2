import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
// Preserve the built application's scripts/styles while giving social crawlers
// route-specific metadata without executing React. All other routes stay generic.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dist=path.join(root,'dist');
const original=await readFile(path.join(dist,'index.html'),'utf8');
const title='TNG Boxing & Event Center | Book Our Venue';
const description='Book TNG Boxing & Event Center in Oklahoma City for your next event. Explore the venue and submit a booking inquiry.';
const canonical='https://tngos.tngboxinggym.com/venue/book';
const picture='https://tngos.tngboxinggym.com/images/tng-venue-original.jpg';
const escape=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const meta=[['name','description',description],['property','og:type','website'],['property','og:site_name','TNG Boxing & Event Center'],['property','og:title',title],['property','og:description',description],['property','og:url',canonical],['property','og:image',picture],['property','og:image:secure_url',picture],['property','og:image:type','image/jpeg'],['property','og:image:width','554'],['property','og:image:height','554'],['property','og:image:alt','TNG Boxing event space with boxing ring and event seating'],['name','twitter:card','summary_large_image'],['name','twitter:title',title],['name','twitter:description',description],['name','twitter:image',picture],['name','twitter:image:alt','TNG Boxing event space with boxing ring and event seating']].map(([attribute,key,value])=>`<meta ${attribute}="${key}" content="${escape(value)}">`).join('\n');
const head=`<title>${escape(title)}</title>\n<link rel="canonical" href="${canonical}">\n${meta}`;
const html=original.replace(/<title>[\s\S]*?<\/title>/gi,'').replace(/<meta\b(?=[^>]*\bname=["']description["'])[^>]*>/gi,'').replace('</head>',head+'\n</head>');
if(!html.includes('og:image')||!html.includes('type="module"'))throw Error('Venue preview must include metadata and the booking application');
await mkdir(path.join(dist,'venue','book'),{recursive:true});
await writeFile(path.join(dist,'venue','book','index.html'),html);
console.log('Built venue booking preview HTML; shared application entry preserved.');
