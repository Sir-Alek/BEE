export type SettingsTabId = "general" | "ai" | "license" | "connectors" | "about";

export const SETTINGS_TABS: { id: SettingsTabId; label: string }[] = [
  { id: "general", label: "General" },
  { id: "ai", label: "Inteligencia" },
  { id: "connectors", label: "Conectores" },
  { id: "license", label: "Licencia" },
  { id: "about", label: "Acerca de" },
];

const SETTINGS_TABS_WITHOUT_LICENSE: SettingsTabId[] = ["general", "license", "about"];

export { SETTINGS_TABS_WITHOUT_LICENSE };

export function settingsTabsForLicense(canRunJobs: boolean) {
  if (canRunJobs) return SETTINGS_TABS;
  return SETTINGS_TABS.filter((t) => SETTINGS_TABS_WITHOUT_LICENSE.includes(t.id));
}
