const fs=require('fs');
const {egScan}=require('./egjs.js');
for(const f of process.argv.slice(2)){
  const src=fs.readFileSync(f,'utf8');
  const r=egScan(src,{});
  console.log('--- '+f.split('/').pop());
  r.findings.forEach(x=>{console.log('  ['+x.sev.toUpperCase()+'] '+x.id+' '+x.title);
    x.hits.slice(0,4).forEach(h=>console.log('      L'+h.line+': '+h.code.slice(0,72)));});
  console.log('  => '+r.counts.blocker+' blocker / '+r.counts.warn+' warn / '+r.counts.info+' info');
}
