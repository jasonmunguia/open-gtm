// The employment gate reads the profile's ACTUAL positions from the same
// internal API the page itself uses, never the headline. Headlines are
// self-written and go stale: they keep naming a job someone already left, and
// stay put while they job-hunt. In the original runs two headlines that read
// as clean fits belonged to a job seeker and to an employee of an excluded
// mega-corp — caught only after the invites had gone out.
// Returns [{co, t, end: 'current'|'ended'}] for the newest positions.
(() => {
  const slug = location.pathname.split('/in/')[1].replace(/\/$/,'');
  return fetch('/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity=' + slug +
    '&decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-79',
    {headers:{'csrf-token':(document.cookie.match(/JSESSIONID="?([^";]+)/)||[])[1],
              'accept':'application/vnd.linkedin.normalized+json+2.1'}})
    .then(r=>r.json())
    .then(j=>{
      const inc = j.included||[];
      const pos = inc.filter(x=>x.companyName || (x.$type||'').includes('Position'));
      return JSON.stringify(pos.slice(0,6).map(p=>({co:p.companyName, t:p.title,
        end: p.dateRange && p.dateRange.end ? 'ended' : 'current'})));
    })
    .catch(e=>JSON.stringify({err:String(e).slice(0,80)}));
})()
