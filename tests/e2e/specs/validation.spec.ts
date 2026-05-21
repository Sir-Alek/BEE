import { testLicensed as test, expect } from "../fixtures/elia-fixture";

test.describe("Validación de formularios", () => {
  test("grabar sin URL muestra error", async ({ home }) => {
    await home.gotoHome();
    await home.urlInput.fill("");
    await home.clickRecordWithoutUrl();
    await expect(home.errorAlert).toBeVisible();
    await expect(home.errorAlert).toContainText(/URL requerida/i);
  });

  test("doc-to-bdd sin documentos muestra error", async ({ home }) => {
    await home.gotoHome();
    await home.selectReqTab();
    await home.clickDocToBdd();
    await expect(home.errorAlert).toBeVisible();
    await expect(home.errorAlert).toContainText(/documento/i);
  });
});
