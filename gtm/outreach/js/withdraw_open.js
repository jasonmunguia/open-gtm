// Emergency path only: click this profile's Pending button so the Withdraw
// confirmation appears. Scoped to <main> and visible elements.
(()=>{const p=[...document.querySelectorAll('main [aria-label]')]
  .filter(e=>e.offsetParent!==null)
  .find(e=>/pending/i.test(e.getAttribute('aria-label')||''));
  if(p){p.click();return JSON.stringify({c:1})} return JSON.stringify({c:0})})()
