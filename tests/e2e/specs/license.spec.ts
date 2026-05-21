import { test, expect } from "../fixtures/elia-fixture";
import {
  fetchLicenseStatus,
  generateActivationKey,
} from "../helpers/license";

test.describe("Licencia", () => {
  test.describe.configure({ mode: "serial" });

  test("muestra banner si no hay licencia activa", async ({ home, request }) => {
    const st = await fetchLicenseStatus(request);
    expect(st.can_run_jobs).toBe(false);

    await home.gotoHome();
    await home.expectLicenseBannerVisible();
  });

  test("activa licencia válida desde Configuración", async ({ home, settings, request }) => {
    await home.gotoHome();
    const st = await fetchLicenseStatus(request);
    const key = generateActivationKey(st.machine_fingerprint);

    await home.openSettings();
    await settings.activateLicense(key);
    await settings.expectLicenseMessage(/activada correctamente/i);

    await settings.close();
    await expect(home.licenseBanner).toBeHidden();

    const after = await fetchLicenseStatus(request);
    expect(after.can_run_jobs).toBe(true);
  });
});
