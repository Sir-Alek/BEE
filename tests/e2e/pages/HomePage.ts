import { expect, type Page } from "@playwright/test";
import { BasePage } from "./BasePage";

export class HomePage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  get homeSurface() {
    return this.page.getByTestId("elia-home");
  }

  get licenseBanner() {
    return this.page.getByTestId("elia-license-banner");
  }

  get errorAlert() {
    return this.page.getByTestId("elia-error-alert");
  }

  get urlInput() {
    return this.page.getByTestId("elia-web-url");
  }

  get recordButton() {
    return this.page.getByTestId("elia-btn-record");
  }

  get lockModal() {
    return this.page.getByTestId("elia-lock-modal");
  }

  async selectUiTab(): Promise<void> {
    await this.page.getByTestId("elia-home-tab-ui").click();
  }

  async selectReqTab(): Promise<void> {
    await this.page.getByTestId("elia-home-tab-req").click();
  }

  async selectPlatform(platform: "web" | "mobile" | "legacy"): Promise<void> {
    await this.page.getByTestId(`elia-platform-${platform}`).click();
  }

  async clickRecordExpectingPopup(): Promise<import("@playwright/test").Page> {
    const popupPromise = this.page.waitForEvent("popup", { timeout: 15_000 });
    await this.recordButton.click();
    return popupPromise;
  }

  async clickRecordWithoutUrl(): Promise<void> {
    await this.recordButton.click();
  }

  async clickDocToBdd(): Promise<void> {
    await this.page.getByTestId("elia-btn-doc-bdd").click();
  }

  async expectHomeVisible(): Promise<void> {
    await expect(this.homeSurface).toBeVisible();
    await expect(this.page.getByRole("heading", { name: "ELIA Web UI" })).toBeVisible();
  }

  async expectLicenseBannerVisible(): Promise<void> {
    await expect(this.licenseBanner).toBeVisible();
  }
}
