// Fill the note textarea with the NATIVE value setter, then dispatch `input`.
// React ignores a plain `.value =` assignment: the counter stays at 0/300 and
// Send stays disabled. Returns both lengths so the caller can prove the text
// landed intact before clicking Send.
(() => {
  const NOTE = __NOTE__;
  const host = [...document.querySelectorAll('*')].find(e=>e.shadowRoot && e.shadowRoot.querySelector('textarea'));
  if (!host) return JSON.stringify({len: NOTE.length, taLen: -1});
  const ta = host.shadowRoot.querySelector('textarea');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  setter.call(ta, NOTE);
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  return JSON.stringify({len: NOTE.length, taLen: ta.value.length});
})()
