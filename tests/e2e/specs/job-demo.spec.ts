import { testLicensed as test, expect } from "../fixtures/elia-fixture";
import { answerDemoJobPrompt, startDemoJob } from "../helpers/license";

test.describe("Flujo de job demo", () => {
  test("job demo completa tras elegir proyecto", async ({ jobWorkspace, request }) => {
    const jobId = await startDemoJob(request);
    await answerDemoJobPrompt(request, jobId, "Proyecto B");

    await jobWorkspace.gotoJob(jobId, "demo");
    await jobWorkspace.waitForDone();
    await expect(jobWorkspace.donePanel).toContainText("Conversión finalizada");
  });

  test("job demo responde prompt desde la UI", async ({ jobWorkspace, request }) => {
    const jobId = await startDemoJob(request);

    await jobWorkspace.gotoJob(jobId, "demo");
    await jobWorkspace.pickProject("Proyecto A");
    await jobWorkspace.waitForDone();
  });
});
