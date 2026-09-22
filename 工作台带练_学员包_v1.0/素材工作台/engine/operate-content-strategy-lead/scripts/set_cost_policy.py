#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json,read_json
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--preset",choices=["observe","operate","research"],required=True);a=p.parse_args()
    presets=read_json(ROOT/"assets/cost_policy_presets.json",{})["presets"];policy={"schema_version":"cost_policy/v1","mode":a.preset,**presets[a.preset],"alert_at_ratio":.8,"principle":"value_first_with_runaway_guard"};out=Path(a.workspace)/"config/cost_policy.json";atomic_write_json(out,policy);print(out)
