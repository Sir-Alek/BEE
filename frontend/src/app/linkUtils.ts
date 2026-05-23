import type { RecordingRef, ScenarioRef } from "../types";

/** feature_file + scenario_name para API link_scenario (mismo separador que backend). */
export function encodeScenarioLink(s: ScenarioRef): string {
  return `${s.feature_file}\x1f${s.scenario_name}`;
}

export function encodeRecordingLink(r: RecordingRef): string {
  return `${r.project}\x1e${r.file_name}`;
}
