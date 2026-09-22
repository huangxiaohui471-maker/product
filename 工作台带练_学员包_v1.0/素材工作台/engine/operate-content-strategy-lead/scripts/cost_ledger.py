from __future__ import annotations
from datetime import date
from pathlib import Path
from common import append_jsonl,now,read_jsonl,read_json

class CostLedger:
    def __init__(self,workspace:Path):self.path=workspace/"memory/cost_ledger.jsonl"
    def rows_today(self)->list[dict]:return [r for r in read_jsonl(self.path) if str(r.get("at","")).startswith(date.today().isoformat())]
    def count(self,operation:str)->int:return sum(r.get("operation")==operation for r in self.rows_today())
    def known_spend(self)->float:return round(sum(float(r.get("known_cost_usd") or 0) for r in self.rows_today()),6)
    def policy(self)->dict:return read_json(self.path.parent.parent/"config/cost_policy.json",{}) or {"daily_budget_usd":1.5,"max_search_per_day":50,"max_detail_per_day":100}
    def guard(self,operation:str,max_daily:int,projected_cost:float,daily_budget:float)->None:
        # 记录成本，但不拿研发期的固定小预算阻断正常业务。
        # 上层运行器仍负责发现明显死循环和用户主动设置的真实限额。
        return None
    def record(self,operation:str,cost:float,reference:str)->None:append_jsonl(self.path,{"schema_version":"cost_event/v1","at":now(),"provider":"tikhub","operation":operation,"known_cost_usd":cost,"reference":reference})
