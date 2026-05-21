import { expect, type Page } from "@playwright/test";

/** Page Object para la pestaña de trabajo (?job_id=…). */
export class JobWorkspacePage {
  constructor(private readonly page: Page) {}

  get promptPanel() {
    return this.page.getByTestId("elia-job-prompt");
  }

  get donePanel() {
    return this.page.getByTestId("elia-job-done");
  }

  async gotoJob(jobId: string, mode = "demo"): Promise<void> {
    await this.page.goto(`/?job_id=${encodeURIComponent(jobId)}&mode=${encodeURIComponent(mode)}`);
  }

  async waitForPrompt(title?: string | RegExp): Promise<void> {
    await this.promptPanel.waitFor({ state: "visible", timeout: 20_000 });
    if (title) {
      await expect(this.page.getByRole("heading", { name: title })).toBeVisible();
    }
  }

  async pickProject(name: string): Promise<void> {
    await this.waitForPrompt(/Seleccionar Proyecto|Proyecto/i);
    await this.page.getByRole("button", { name, exact: true }).click();
  }

  async waitForDone(timeout = 30_000): Promise<void> {
    await this.donePanel.waitFor({ state: "visible", timeout });
    await expect(this.donePanel).toContainText("Conversión finalizada");
  }
}
