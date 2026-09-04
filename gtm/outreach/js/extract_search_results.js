// Search-results page -> up to 10 candidate cards. Each card = the smallest
// ancestor of a profile link that contains exactly one distinct /in/ URL, so
// the card's text lines belong to that one person and not a neighbour.
(() => {
  const uniq = el => new Set([...el.querySelectorAll('a[href*="/in/"]')].map(a=>a.href.split('?')[0])).size;
  const anchors = [...document.querySelectorAll('a[href*="/in/"]')].filter(a=>a.innerText.trim().length>2);
  const seen = new Set(); const out = [];
  for (const a of anchors) {
    const url = a.href.split('?')[0];
    if (seen.has(url)) continue; seen.add(url);
    let c = a;
    while (c.parentElement && uniq(c.parentElement) === 1) c = c.parentElement;
    const txt = c.innerText.split('\n').map(s=>s.trim()).filter(Boolean);
    out.push({url, lines: txt.slice(0,5)});
  }
  return JSON.stringify(out.slice(0,10));
})()
