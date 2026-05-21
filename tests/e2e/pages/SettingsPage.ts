import { expect, type Page } from "@playwright/test";
import { BasePage } from "./BasePage";

export class SettingsPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  get dialog() {
    return this.page.getByTestId("elia-settings-dialog");
  }

  async openTab(tab: "general" | "ai" | "license" | "connectors" | "about"): Promise<void> {
    const tabBtn = this.page.getByTestId(`elia-settings-tab-${tab}`);
    if (await tabBtn.isVisible()) {
      await tabBtn.click();
    }
  }

  async close(): Promise<void> {
    await this.dialog.getByRole("button", { name: "Cerrar" }).click();
    await this.dialog.waitFor({ state: "hidden" });
  }

  async activateLicense(key: string): Promise<void> {
    await this.openTab("license");
    await this.page.getByTestId("elia-license-key").fill(key);
    await this.page.getByTestId("elia-license-activate").click();
  }

  async expectLicenseMessage(text: string | RegExp): Promise<void> {
    await expect(this.page.getByTestId("elia-license-message")).toContainText(text);
  }

  async toggleTheme(): Promise<void> {
    await this.openTab("general");
    await this.page.locator("#elia-theme-toggle").click({ force: true });
  }

  async expectAboutVersion(): Promise<void> {
    await this.openTab("about");
    await expect(this.page.getByTestId("elia-about-panel")).toBeVisible();
    await expect(this.page.getByTestId("elia-about-panel")).toContainText("Versión:");
  }
}
