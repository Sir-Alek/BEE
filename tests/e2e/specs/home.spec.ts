import { test, expect } from "../fixtures/elia-fixture";

test.describe("Pantalla principal", () => {
  test("carga ELIA Web UI", async ({ home }) => {
    await home.gotoHome();
    await home.expectHomeVisible();
  });

  test("alterna pestañas Automatización UI / Inteligencia de Requerimientos", async ({ home }) => {
    await home.gotoHome();
    await home.selectReqTab();
    await expect(home.page.getByText("Inteligencia de Requerimientos").first()).toBeVisible();
    await home.selectUiTab();
    await expect(home.page.getByTestId("elia-platform-web")).toBeVisible();
  });
});
