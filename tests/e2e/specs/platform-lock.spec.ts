import { testLicensed as test, expect } from "../fixtures/elia-fixture";

test.describe("Módulos bloqueados", () => {
  test("plataforma móvil sin flag M muestra modal de bloqueo", async ({ home }) => {
    await home.gotoHome();
    await home.selectPlatform("mobile");
    await expect(home.lockModal).toBeVisible();
    await expect(home.lockModal).toContainText(/Módulo no habilitado/i);
    await home.lockModal.getByRole("button", { name: "Entendido" }).click();
    await expect(home.lockModal).toBeHidden();
  });
});
