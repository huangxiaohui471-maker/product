from __future__ import annotations

REQUIRED={
 "shared_enterprise_context/v1":("context_id","company","version","people","offerings","scenes","knowledge","boundaries","sources"),
 "strategy_to_production/v1":("task_id","cycle_id","context_id","version","target_audience","customer_scene","belief_change","desired_action","single_variable","touch_destination","expression_boundaries","completion_gate","status"),
 "production_to_growth/v1":("handoff_id","task_id","cycle_id","context_id","artifact_id","version_id","content_master","channel_variants","single_variable","desired_action","source_refs"),
 "growth_learning_return/v1":("return_id","task_id","cycle_id","context_id","artifact_id","version_id","touch_facts","result_facts","measurement","next_experiment","source_refs"),
 "flywheel_task_state/v1":("project_id","cycle_id","task_id","current_ring","current_owner","status","context_id","next_action","completion_gate"),
}
def validate(data:dict)->list[str]:
 version=data.get("schema_version");errors=[]
 if version not in REQUIRED:return ["$.schema_version:unsupported"]
 for key in REQUIRED[version]:
  if key not in data:errors.append(f"$.{key}:required")
 if version=="strategy_to_production/v1":
  variable=data.get("single_variable") or {}
  if not all(variable.get(x) for x in ("name","from","to")) or variable.get("from")==variable.get("to"):errors.append("$.single_variable:no_change")
  if data.get("status")=="ready_for_production" and not data.get("expression_boundaries"):errors.append("$.expression_boundaries:ready_requires_boundaries")
 if version=="flywheel_task_state/v1" and str(data.get("status","")).startswith("waiting_") and not data.get("waiting_for"):errors.append("$.waiting_for:required")
 return sorted(set(errors))
