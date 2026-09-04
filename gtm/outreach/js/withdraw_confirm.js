(()=>{const b=[...document.querySelectorAll('button')]
  .find(x=>x.offsetParent!==null && /^withdraw$/i.test((x.innerText||'').trim()));
  if(b){b.click();return JSON.stringify({w:1})} return JSON.stringify({w:0})})()
