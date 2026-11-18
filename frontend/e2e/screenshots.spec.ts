import { test, expect } from "@playwright/test";
import path from "path";

const SCREENSHOTS_DIR = path.resolve(__dirname, "../../docs/screenshots");

test.describe("Phase 5 Screenshot Generator", () => {
  test.beforeEach(async ({ page }) => {
    // Default desktop viewport
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("1. landing.png", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /TruthLens reads it/i })).toBeVisible();
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "landing.png"),
      fullPage: false,
    });
  });

  test("2. analyze-fake.png", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    await textarea.fill(
      "OMG this is the BEST product I have EVER bought! Absolutely AMAZING quality, my life is CHANGED forever! Buy it NOW, you will NOT regret it! Five stars!"
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5000 });
    await analyzeBtn.click();

    await expect(page.getByRole("heading", { name: /Likely Fake/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Evidence highlights/i)).toBeVisible();
    await expect(page.getByText(/Top contributing tokens/i)).toBeVisible();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "analyze-fake.png"),
      fullPage: false,
    });
  });

  test("3. analyze-genuine.png", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    await textarea.fill(
      "The location of the hotel was convenient for attending the downtown conference, but the room itself was disappointing. The carpet had several visible stains and the air conditioner made a rattling noise throughout the night. The front desk staff was polite during check-in, though breakfast service was slow and crowded."
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5000 });
    await analyzeBtn.click();

    await expect(page.getByRole("heading", { name: /Likely Genuine/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Evidence highlights/i)).toBeVisible();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "analyze-genuine.png"),
      fullPage: false,
    });
  });

  test("4. batch.png", async ({ page }) => {
    await page.goto("/batch");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    const csvContent = [
      "review,rating",
      '"OMG this is the BEST purchase I have EVER made, absolutely incredible quality!!!",5',
      '"The unit arrived with broken parts and failed to operate. Support refused assistance.",1',
      '"Average product that performs standard functions adequately without issues.",3',
    ].join("\n");

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "reviews_batch.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csvContent, "utf-8"),
    });

    await expect(page.getByText(/Results/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/3 of 3 rows/i)).toBeVisible();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "batch.png"),
      fullPage: false,
    });
  });

  test("5. model-lab.png", async ({ page }) => {
    await page.goto("/model-lab");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Deceptive Opinion Spam Corpus/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Accuracy/i).first()).toBeVisible();
    await page.waitForTimeout(1500); // Allow SVG charts to animate in

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "model-lab.png"),
      fullPage: false,
    });
  });

  test("6. history.png", async ({ page }) => {
    await page.goto("/history");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /^History$/i })).toBeVisible();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "history.png"),
      fullPage: false,
    });
  });

  test("7. how-it-works.png", async ({ page }) => {
    await page.goto("/how-it-works");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /How TruthLens works/i })).toBeVisible();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "how-it-works.png"),
      fullPage: false,
    });
  });

  test("8. analyze-light.png", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    // Set theme to light
    await page.evaluate(() => {
      window.localStorage.setItem("truthlens-theme", "light");
      document.documentElement.classList.add("light");
    });
    await page.reload();
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    await textarea.fill(
      "OMG this is the BEST product I have EVER bought! Absolutely AMAZING quality, my life is CHANGED forever! Buy it NOW, you will NOT regret it! Five stars!"
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5000 });
    await analyzeBtn.click();

    await expect(page.getByRole("heading", { name: /Likely Fake/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "analyze-light.png"),
      fullPage: false,
    });

    // Reset theme back to dark
    await page.evaluate(() => {
      window.localStorage.setItem("truthlens-theme", "dark");
      document.documentElement.classList.remove("light");
    });
  });

  test("9. analyze-mobile.png", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/analyze");
    await expect(page.getByRole("heading", { name: /Analyze a review/i })).toBeVisible({ timeout: 15_000 });

    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    await textarea.fill(
      "OMG this is the BEST product I have EVER bought! Absolutely AMAZING quality, my life is CHANGED forever!"
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5000 });
    await analyzeBtn.click();

    await expect(page.getByRole("heading", { name: /Likely Fake/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, "analyze-mobile.png"),
      fullPage: false,
    });
  });
});
