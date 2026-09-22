(() => {
  const t = (document.body ? document.body.innerText : '') || '';
  const head = t.replace(/\s+/g, ' ').slice(0, 220);
  return JSON.stringify({
    url: location.href,
    title: document.title,
    len: t.length,
    hasLoginWord: t.indexOf('注册/登录') >= 0 || t.indexOf('登录') >= 0,
    hasUserMenu: !!document.querySelector('[class*=avatar],[class*=Avatar],[class*=user-info],[class*=userInfo]'),
    head: head
  });
})()
