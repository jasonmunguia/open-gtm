// Newest pending connection invitations, with recipient slug and the note
// text that was attached. This is the ONLY proof a send happened: the toast
// is not, and "a new invitation exists" is not either (see verify.py).
fetch('/voyager/api/relationships/sentInvitationViewsV2?count=__COUNT__&invitationType=CONNECTION&q=invitationType&start=0',
  {headers:{'csrf-token':(document.cookie.match(/JSESSIONID="?([^";]+)/)||[])[1],
            'accept':'application/vnd.linkedin.normalized+json+2.1'}})
.then(r=>r.json())
.then(j=>{
  const inc = j.included || [];
  const profs = {};
  inc.filter(x=>x.firstName).forEach(x=>{ profs[x.entityUrn]= {name: x.firstName+' '+x.lastName, slug: x.publicIdentifier||''}; });
  const invs = inc.filter(x=>/Invitation$/.test(x.$type||'') || x.sentTime);
  return JSON.stringify(invs.map(x=>{
    // normalized+json stores references under starred keys ('*toMember')
    const refs = [x.toMember, x['*toMember'], (x.invitee||{}).miniProfile, (x.invitee||{})['*miniProfile']];
    const p = refs.map(r=>profs[r]).find(Boolean) || {};
    return { to: p.name || x.toMemberId || '?', slug: p.slug || '',
             msg: x.message || x.customMessage || '', sent: x.sentTime || 0 };
  }));
})
