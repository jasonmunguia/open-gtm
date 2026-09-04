// The invite dialog lives in a SHADOW ROOT, not the main DOM —
// document.body.innerText never contains "Add a note". Buttons are returned
// as centre coordinates because they must be clicked with synthetic mouse
// events; .click() on shadow-root elements does not open the note field.
(() => {
  const host = [...document.querySelectorAll('*')].find(e=>e.shadowRoot && e.shadowRoot.textContent.includes('Add a note'));
  if (!host) return JSON.stringify({open:false});
  const sr = host.shadowRoot;
  const find = t => { const e=[...sr.querySelectorAll('*')].find(x=>x.children.length===0 && (x.textContent||'').trim()===t);
    if(!e) return null; const r=e.getBoundingClientRect(); return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)}; };
  return JSON.stringify({open:true, add:find('Add a note'), send:find('Send'), counter: sr.textContent.match(/\d+\/300/)?.[0]||null});
})()
