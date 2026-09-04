// Find and click THIS person's Connect button. Two rules, both scars:
// 1. Scope to the profile's own top card (the section holding the H1/H2
//    name). A profile page carries ~10 sidebar "Invite <stranger> to connect"
//    buttons; a document-wide query once clicked one and pitched a stranger.
// 2. FULL-name match on the aria-label — every token, no first-name fallback.
//    A first-name match is how "Steve" once matched a sidebar "…Stevens".
(() => {
  const toks = __TOKENS__.map(t=>t.toLowerCase());
  const aria = e => (e.getAttribute('aria-label')||'').toLowerCase();
  const head = document.querySelector('main section h1, main section h2');
  if (!head) return JSON.stringify({state:'not_rendered'});
  const headname = (head.innerText||'').trim().toLowerCase();
  if (!toks.every(t => headname.includes(t)))
    return JSON.stringify({state:'wrong_profile', h1:(head.innerText||'').trim()});
  const card = head.closest('section') || document.querySelector('main section');
  if (!card) return JSON.stringify({state:'not_rendered'});
  const vis = [...card.querySelectorAll('[aria-label]')].filter(e=>e.offsetParent!==null);
  if (vis.some(e => /pending|withdraw/.test(aria(e)))) return JSON.stringify({state:'pending'});
  const isInv = e => aria(e).startsWith('invite') && aria(e).includes('to connect');
  const b = vis.find(e => isInv(e) && toks.every(t=>aria(e).includes(t)));
  if (b) { b.click(); return JSON.stringify({state:'clicked_direct', aria:b.getAttribute('aria-label')}); }
  const more = [...card.querySelectorAll('button')].find(x => (x.innerText||'').trim()==='More' || /^more( actions)?$/i.test(x.getAttribute('aria-label')||''));
  if (!more) return JSON.stringify({state:'no_connect_no_more'});
  more.click();
  return JSON.stringify({state:'opened_more'});
})()
