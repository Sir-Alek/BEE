import { testLicensed as test, expect } from "../fixtures/elia-fixture";

test.describe("Configuración", () => {
  test("abre modal, muestra Acerca de con versión", async ({ home, settings }) => {
    await home.gotoHome();
    await home.openSettings();
    await settings.expectAboutVersion();
    await settings.close();
    await expect(settings.dialog).toBeHidden();
  });

  test("cambia tema claro/oscuro", async ({ home, settings }) => {
    await home.gotoHome();
    await home.openSettings();
    await settings.openTab("general");
    const label = settings.page.locator("label[for='elia-theme-toggle'] span").first();
    const before = await label.textContent();
    await settings.toggleTheme();
    await expect(label).not.toHaveText(before ?? "");
    await settings.close();
  });
});
