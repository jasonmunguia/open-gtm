// A profile page is "ready" when <main> exists AND an action button has
// rendered. Background windows paint slowly; a missing <main> means
// not-rendered-yet, never "no Connect button".
JSON.stringify({main:!!document.querySelector('main'),
  acts:[...document.querySelectorAll('[aria-label]')].some(e=>/to connect|pending|withdraw/i.test(e.getAttribute('aria-label')||''))})
