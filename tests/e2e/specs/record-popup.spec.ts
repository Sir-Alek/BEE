import { testLicensed as test, expect } from "../fixtures/elia-fixture";
import { answerPuppeteerRecorderPrompts, startPuppeteerRecorderJob } from "../helpers/puppeteer";

test.describe("Grabar interacciones (popup)", () => {
  test("abre pestaña de trabajo al pulsar Grabar Interacciones", async ({ home, page }) => {
    await home.gotoHome();
    await home.urlInput.fill("https://example.com");

    const popupPromise = page.waitForEvent("popup", { timeout: 20_000 });
    await home.recordButton.click();
    const popup = await popupPromise;

    await popup.waitForURL(/job_id=[0-9a-f-]{36}/i, { timeout: 20_000 });
    const popupUrl = popup.url();
    expect(popupUrl).toMatch(/job_id=[0-9a-f-]{36}/i);
    expect(popupUrl).toMatch(/mode=puppeteer_recorder/);

    await expect(popup.getByTestId("elia-job-prompt")).toBeVisible({ timeout: 20_000 });
    await expect(popup.getByRole("heading", { name: /Nuevo Proyecto/i })).toBeVisible();

    await expect(home.page.getByTestId("elia-home-hint")).toBeVisible();
    await expect(home.page.getByTestId("elia-home-hint")).toContainText(/otra pestaña/i);
  });

  test("job puppeteer completa con stub de recorder", async ({ home, page, request }) => {
    await home.gotoHome();
    await home.urlInput.fill("https://example.com");

    const popupPromise = page.waitForEvent("popup", { timeout: 20_000 });
    await home.recordButton.click();
    const popup = await popupPromise;
    await popup.waitForURL(/job_id=[0-9a-f-]{36}/i, { timeout: 20_000 });

    const jobId = new URL(popup.url()).searchParams.get("job_id");
    expect(jobId).toBeTruthy();

    await answerPuppeteerRecorderPrompts(request, jobId!, {
      projectName: "E2EWeb",
      fileName: "e2e_grabacion.js",
    });

    await expect(popup.getByTestId("elia-job-done")).toBeVisible({ timeout: 60_000 });
    await expect(popup.getByTestId("elia-job-done")).toContainText("Conversión finalizada");
  });

  test("API directa: puppeteer_recorder con stub llega a done", async ({ request }) => {
    const jobId = await startPuppeteerRecorderJob(request, "https://example.com");
    await answerPuppeteerRecorderPrompts(request, jobId, {
      projectName: `E2EApi_${Date.now()}`,
      preferNewProject: true,
    });
    const res = await request.get(`/api/jobs/${jobId}`);
    const job = await res.json();
    expect(job.state).toBe("done");
  });
});
