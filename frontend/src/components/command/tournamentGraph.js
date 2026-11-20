export function tournamentGraph(bouts=[]) {
 const available=new Set(bouts.map(b=>b.key)),divisions=[...new Set(bouts.map(b=>b.division_id))];let offset=0;const nodes=[],edges=[];
 for(const division of divisions){const rows=bouts.filter(b=>b.division_id===division);const rounds=[...new Set(rows.map(b=>b.round))].sort((a,b)=>a-b);const positions=new Map();let maxY=offset;
  for(const round of rounds){const current=rows.filter(b=>b.round===round);current.forEach((b,i)=>{const parents=[b.red_source,b.blue_source].map(k=>positions.get(k)).filter(v=>v!=null);const y=parents.length?parents.reduce((a,v)=>a+v,0)/parents.length:offset+i*170;positions.set(b.key,y);maxY=Math.max(maxY,y);nodes.push({id:b.key,position:{x:(round-1)*340,y},data:{bout:b},type:'bout',draggable:false,connectable:false});for(const [corner,source]of[['red',b.red_source],['blue',b.blue_source]])if(source&&available.has(source))edges.push({id:source+'-'+b.key+'-'+corner,source,target:b.key,targetHandle:corner,type:'smoothstep',animated:false});});}
  offset=maxY+240;
 }
 return {nodes,edges};
}
