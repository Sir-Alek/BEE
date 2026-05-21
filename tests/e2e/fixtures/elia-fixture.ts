import { test as base, expect } from "@playwright/test";
import { ensureLicensed } from "../helpers/license";
import { HomePage } from "../pages/HomePage";
import { JobWorkspacePage } from "../pages/JobWorkspacePage";
import { SettingsPage } from "../pages/SettingsPage";

type EliaFixtures = {
  home: HomePage;
  settings: SettingsPage;
  jobWorkspace: JobWorkspacePage;
};

const testBase = base.extend<EliaFixtures>({
  home: async ({ page }, use) => {
    await use(new HomePage(page));
  },
  settings: async ({ page }, use) => {
    await use(new SettingsPage(page));
  },
  jobWorkspace: async ({ page }, use) => {
    await use(new JobWorkspacePage(page));
  },
});

/** Tests sin licencia preactivada (p. ej. flujo de activación). */
export const test = testBase;

/** Tests que requieren licencia vigente — activa vía API antes de cada caso. */
export const testLicensed = testBase.extend({
  _ensureLicense: [
    async ({ request }, use) => {
      await ensureLicensed(request);
      await use();
    },
    { auto: true },
  ],
});

export { expect };
