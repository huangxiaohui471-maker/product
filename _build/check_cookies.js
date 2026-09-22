// 用 CDP 检查各评价渠道的 cookie 登录态（不打开页面，只看 cookie）
const { chromium } = require('playwright');
const PORT = process.argv[2] || '9222';
const TARGETS = [
  ['小红书', 'https://www.xiaohongshu.com'],
  ['抖音', 'https://www.douyin.com'],
  ['抖店/罗盘', 'https://compass.jinritemai.com'],
  ['淘宝', 'https://www.taobao.com'],
  ['天猫', 'https://www.tmall.com'],
  ['FastMoss', 'https://www.fastmoss.com'],
  ['蝉妈妈', 'https://www.chanmama.com'],
];
(async () => {
  let b;
  try {
    b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT, { timeout: 15000 });
  } catch (e) {
    console.log(PORT + ' 连接失败: ' + String(e).slice(0, 90));
    return;
  }
  const ctx = b.contexts()[0];
  for (const [name, url] of TARGETS) {
    try {
      const cks = await ctx.cookies(url);
      const names = cks.map((c) => c.name);
      const loginish = names.filter((n) => /^(SID|sessionid|web_session|_l_g_|cna|login|token|passport|a1|webId|ttwid|odin_tt|sid_tt|uid_tt|is_login|w_uid|cookie2|fm_token|access_token)/i.test(n));
      console.log(`${name.padEnd(12)} cookie ${String(cks.length).padStart(3)} 个 | 疑似登录态: ${loginish.slice(0, 6).join(', ') || '（无）'}`);
    } catch (e) {
      console.log(name + ' 读取失败 ' + String(e).slice(0, 60));
    }
  }
  await b.close();
})();
