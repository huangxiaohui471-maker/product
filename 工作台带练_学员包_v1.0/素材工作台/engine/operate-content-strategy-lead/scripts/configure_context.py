#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json, now, read_json
from context import validate_context

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--long-term-business",required=True)
    p.add_argument("--business-goal",required=True);p.add_argument("--current-priority",required=True);p.add_argument("--target-customer",required=True)
    p.add_argument("--product",action="append",required=True);p.add_argument("--claim-boundary",action="append",required=True)
    p.add_argument("--production-capability",action="append",required=True);p.add_argument("--platform",action="append",default=["manual"]);a=p.parse_args()
    path=Path(a.workspace)/"config/enterprise_context.json";c=read_json(path,{})
    c.update({"long_term_business":a.long_term_business,"business_goal":a.business_goal,"current_priority":a.current_priority,
        "target_customer":a.target_customer,"products":a.product,"claim_boundaries":a.claim_boundary,
        "production_capabilities":a.production_capability,"authorization_scope":{"platforms":a.platform,"public_sources_only":True,"max_downloads_per_run":5},"updated_at":now()})
    errors=validate_context(c)
    if errors: raise SystemExit("；".join(errors))
    atomic_write_json(path,c);print(path)
