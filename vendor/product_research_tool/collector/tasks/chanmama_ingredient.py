# -*- coding: utf-8 -*-
"""蝉妈妈·成分增长榜采集任务（每 7 天）。
蝉妈妈请求体加密，不从接口读，从美妆属性分析页的 DOM 读渲染结果。"""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webbridge import Bridge
import config

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data")

# 从美妆属性分析页 DOM 抽成分榜（排名/名称/关联商品数/销量/销售额/环比）
_EXTRACT_JS = """
(()=>{
  const rows=[...document.querySelectorAll('tr')].map(r=>{
    const c=[...r.querySelectorAll('td,th')].map(x=>(x.innerText||'').replace(/\\s+/g,' ').trim());
    return c;
  }).filter(r=>r.length>=5 && /^\\d|持平|^\\d+\\s*\\d*$/.test(r[0]||''));
  return rows.slice(0,40).map(c=>({
    rank: c[0], name: c[1], product_cnt: c[2], volume: c[3], amount: c[4], mom: c[5]||''
  }));
})()
"""


def run(tab="成分", session="chanmama-collect"):
    """主入口：打开美妆属性分析页，切到「成分」Tab，抽榜。"""
    if tab not in ("成分", "功效"):
        return {"ok": False, "error": "只支持成分或功效 Tab"}
    br = Bridge(session)
    st = br.status()
    if not st.get("extension_connected"):
        return {"ok": False, "error": "Kimi 扩展未连接，请打开装了扩展的 Chrome 后重试"}

    br.navigate(config.CHANMAMA["base"] + config.CHANMAMA["ingredient_page"],
                new_tab=False, group_title="蝉妈妈·成分榜采集")
    br.wait(9)
    current_url = br.evaluate("location.href").get("data", {}).get("value", "") or ""
    if "/login" in current_url:
        return {"ok": False, "error": "蝉妈妈后台未登录；请在浏览器中手动登录后重试", "url": current_url}

    # 切到指定 Tab（成分/功效）
    br.evaluate(
        "(()=>{const els=[...document.querySelectorAll('*')];"
        "const el=els.find(e=>(e.innerText||'').trim()==='%s'&&e.children.length===0);"
        "if(el){el.click();return true}return false})()" % tab
    )
    br.wait(3)

    rows = br.evaluate(_EXTRACT_JS).get("data", {}).get("value", []) or []
    if not rows:
        return {"ok": False, "error": "页面没有可识别的成分/功效表格；检查登录态和当前筛选"}
    result = {"tab": tab, "source": "蝉妈妈·美妆属性分析",
              "captured_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "period": "页面当前筛选（采集器未设置/核实）", "count": len(rows), "rows": rows}

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "ingredient_%s.json" % tab)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return {"ok": True, "file": path, "count": len(rows)}


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "成分"
    result = run(t)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        sys.exit(1)
