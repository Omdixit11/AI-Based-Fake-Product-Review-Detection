import { test, expect } from "@playwright/test";

test.describe("TruthLens E2E Suite", () => {
  test("1. Single review analysis - verdicts, gauge, and forensics", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /Analyze a review/i })).toBeVisible();

    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    // Test a promotional spammy review (expected: Fake)
    await textarea.fill(
      `OMG this is the BEST product I have EVER bought ${Date.now()}!!! Absolutely AMAZING quality, my life is CHANGED forever!!! Buy it NOW, you will NOT regret it!!! Five stars!!!!`
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });
    await analyzeBtn.click();

    // Verify verdict card and confidence gauge
    const fakeVerdict = page.getByRole("heading", { name: /Likely Fake/i });
    await expect(fakeVerdict).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("img", { name: /Fake probability/i })).toBeVisible();
    await expect(page.getByText(/Evidence highlights/i)).toBeVisible();
    await expect(page.getByText(/Top contributing tokens/i)).toBeVisible();
    await expect(page.getByText(/Red flags/i)).toBeVisible();

    // Test a balanced genuine review (expected: Genuine)
    await textarea.fill(
      `We stayed 3 nights in room 214 (${Date.now()}). The location was fine but the bathroom was dirty, the wifi failed twice, and the manager refused to refund the last night. Breakfast ended at 10 although we were told 11.`
    );
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });
    await analyzeBtn.click();

    const genuineVerdict = page.getByRole("heading", { name: /Likely Genuine/i });
    await expect(genuineVerdict).toBeVisible({ timeout: 15_000 });
  });

  test("2. Model selection - Best, Naive Bayes, and SVM", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    // Test Naive Bayes with unique text to avoid duplicate flood rule
    const textNB = `Solid performance and dependable build quality after several weeks ${Date.now()}-nb.`;
    await textarea.fill(textNB);
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });

    // Select Naive Bayes
    await page.getByRole("radio", { name: /Naive Bayes/i }).click();
    await analyzeBtn.click();
    await expect(page.getByText(/scored by NB/i)).toBeVisible({ timeout: 15_000 });
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });

    // Select SVM with unique text
    const textSVM = `Solid performance and dependable build quality after several weeks ${Date.now()}-svm.`;
    await textarea.fill(textSVM);
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });

    await page.getByRole("radio", { name: /^SVM$/i }).click();
    await analyzeBtn.click();
    await expect(page.getByText(/scored by SVM/i)).toBeVisible({ timeout: 15_000 });
  });

  test("3. Batch CSV upload and table filtering", async ({ page }) => {
    await page.goto("/batch");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /Batch analysis/i })).toBeVisible();

    const validCsv = [
      "review,rating",
      `"OMG this is the BEST purchase I have EVER made ${Date.now()}, buy it NOW, absolutely incredible quality!!!",5`,
      `"The unit arrived with broken parts and failed to operate. Support refused assistance ${Date.now()}.",1`,
      `"Average product that performs standard functions adequately without issues ${Date.now()}.",3`,
    ].join("\n");

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "reviews_sample.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(validCsv, "utf-8"),
    });

    // Verify summary stats and results table
    await expect(page.getByText(/Results/i)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/3 of 3 rows/i)).toBeVisible();

    // Verify table filters
    await page.getByRole("button", { name: /Fake only/i }).click();
    await page.getByRole("button", { name: /Genuine only/i }).click();
    await page.getByRole("button", { name: /^All$/i }).click();

    // Verify export button
    await expect(page.getByRole("button", { name: /Export CSV/i })).toBeVisible();
  });

  test("4. Invalid CSV missing review column", async ({ page }) => {
    await page.goto("/batch");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });

    const invalidCsv = ["product_id,stars,feedback", '101,5,"Nice phone"'].join("\n");

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "invalid_schema.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(invalidCsv, "utf-8"),
    });

    await expect(page.getByText(/Batch failed/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/The CSV must have a 'review' column/i).first()).toBeVisible();
  });

  test("5. History display, search, and filtering", async ({ page }) => {
    const marker = `AuditMarker${Date.now()}`;

    // Perform a scan on /analyze with this unique marker to ensure history is populated
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    await textarea.fill(`Special customer feedback containing unique tag ${marker} for validation.`);
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });
    await analyzeBtn.click();
    await expect(page.getByRole("heading", { name: /Likely/i })).toBeVisible({ timeout: 15_000 });

    // Navigate to /history
    await page.goto("/history");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /^History$/i })).toBeVisible();
    await expect(page.getByText(marker).first()).toBeVisible({ timeout: 15_000 });

    // Search filter
    const searchInput = page.getByRole("searchbox", { name: /Search history/i });
    await searchInput.fill(marker);
    await expect(page.getByText(marker).first()).toBeVisible();

    // Searching for non-existent keyword yields 0 entries
    await searchInput.fill("nonexistent_keyword_xyz_999");
    await expect(page.getByText(/0 entries matching/i)).toBeVisible();
    await searchInput.clear();

    // Verdict filters
    await page.getByRole("button", { name: /^Fake$/i }).click();
    await page.getByRole("button", { name: /^Genuine$/i }).click();
    await page.getByRole("button", { name: /^All$/i }).click();
  });

  test("6. Phase 3.5 Tier-1 rules and sarcasm UI handling", async ({ page }) => {
    await page.goto("/analyze");
    await expect(page.getByText("API online").first()).toBeVisible({ timeout: 15_000 });
    const textarea = page.getByRole("textbox", { name: /Product review text/i });
    const analyzeBtn = page.getByRole("button", { name: /Analyze review/i });

    // 6a. Sarcasm contrast heuristic
    await textarea.fill(`Wow, best phone ever, total garbage, the screen broke in a day ${Date.now()}`);
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });
    await analyzeBtn.click();
    await expect(page.getByText(/Possible sarcasm — needs human review/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });

    // 6b. Tier-1 hard rule (VELOCITY_EXCEEDED via reviews_last_minute > 5)
    await textarea.fill(`Clean and quiet stay with fast check-in ${Date.now()}.`);
    const advancedBtn = page.getByRole("button", { name: /Advanced — reviewer context/i });
    await advancedBtn.click();

    const velocityInput = page.getByRole("spinbutton", { name: /Reviews in the last minute/i });
    await velocityInput.fill("9");

    await expect(analyzeBtn).toBeEnabled({ timeout: 5_000 });
    await analyzeBtn.click();

    // Verify Tier-1 banner and short-circuit verdict
    await expect(page.getByText(/Flagged by rules — the model was skipped/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("region", { name: /Flagged by Tier-1 rules/i }).getByText(/VELOCITY_EXCEEDED/i)
    ).toBeVisible();
    await expect(page.getByText(/Auto-flagged by rules at 100%/i)).toBeVisible();
  });
});
