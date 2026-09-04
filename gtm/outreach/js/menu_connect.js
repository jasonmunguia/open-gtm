// Connect hidden under the More/⋯ menu. The dropdown renders in a PORTAL
// outside the top card, so container scoping cannot work here. A Connect leaf
// qualifies only if (a) it lives inside a dropdown/menu container, not a
// sidebar card, and (b) its nearest aria-label ancestor reads
// "Invite <name> to connect" with EVERY candidate token present — the aria
// carries the recipient's name, so this is a per-item recipient check.
(() => {
  const toks = __TOKENS__.map(t=>t.toLowerCase());
  const aria = e => (e.getAttribute('aria-label')||'').toLowerCase();
  const leaves = [...document.querySelectorAll('*')].filter(e=>e.offsetParent!==null && e.children.length===0 && /^connect$/i.test((e.innerText||'').trim()));
  for (const l of leaves) {
    if (!l.closest('[role=menu],[role=dialog],.artdeco-dropdown__content,[class*=dropdown]')) continue;
    const holder = l.closest('[aria-label]');
    if (!holder) continue;
    const a = aria(holder);
    if (a.startsWith('invite') && a.includes('to connect') && toks.every(t=>a.includes(t))) {
      l.click(); return JSON.stringify({state:'clicked_menu', aria:holder.getAttribute('aria-label')});
    }
  }
  return JSON.stringify({state:'none'});
})()
