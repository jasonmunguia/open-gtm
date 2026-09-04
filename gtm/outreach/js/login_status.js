// 200 only with a live session; anything else means log in.
fetch('/voyager/api/me',{headers:{'csrf-token':(document.cookie.match(/JSESSIONID="?([^";]+)/)||[])[1]}})
  .then(r=>r.status).catch(()=>0)
