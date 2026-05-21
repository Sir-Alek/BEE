import type { Page } from "@playwright/test";

/** Base Page Object: navegación común y esperas dinámicas. */
export class BasePage {
  constructor(public readonly page: Page) {}

  async gotoHome(): Promise<void> {
    await this.page.goto("/");
    await this.page.getByTestId("elia-home").waitFor({ state: "visible", timeout: 15_000 });
  }

  async openSettings(): Promise<void> {
    await this.page.getByTestId("elia-settings-open").click();
    await this.page.getByTestId("elia-settings-dialog").waitFor({ state: "visible" });
  }
}
