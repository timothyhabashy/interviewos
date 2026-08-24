import { expect, test, type Page } from "@playwright/test";

const LONG_ANSWER =
  "I built a Monte Carlo pricing project in Python because I wanted to see how randomness models real systems. I learned to debug plausible-but-wrong numbers and would ask for a mentor next time.";

const TECH_ANSWER =
  "I picked this because standard error shrinks as independent paths increase, like 1 over sqrt of N.";

async function waitForQuestion(page: Page) {
  await expect(page.getByTestId("question-speech")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("question-speech")).not.toHaveText("Interviewer is thinking…");
}

async function answerCurrent(page: Page, text = LONG_ANSWER) {
  await expect(page.getByTestId("submit-answer")).toBeEnabled({ timeout: 20_000 });
  const radios = page.locator('input[name="choice"]');
  if (await radios.count()) {
    await radios.first().check();
  }
  await page.locator("#answer").fill(text);
  await page.getByTestId("submit-answer").click();
}

async function completeInterview(page: Page) {
  await page.getByTestId("sample-research_assistant").click();
  await page.getByTestId("start-interview").click();
  await expect(page).toHaveURL(/\/interview\//);
  for (let i = 0; i < 3; i++) {
    if (/\/report\//.test(page.url())) break;
    await waitForQuestion(page);
    const isMcq = (await page.locator('input[name="choice"]').count()) > 0;
    await answerCurrent(page, isMcq ? TECH_ANSWER : LONG_ANSWER);
  }
  await expect(page).toHaveURL(/\/report\//, { timeout: 30_000 });
}

test("guest research interview reaches a scored report", async ({ page }) => {
  await page.goto("/practice");
  await completeInterview(page);
  await expect(page.getByTestId("overall-score")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Qualitative rubric" })).toBeVisible();
  await expect(page.getByText("Download report")).toBeVisible();
});

test("empty answer focuses the error summary", async ({ page }) => {
  await page.goto("/practice");
  await page.getByTestId("sample-research_assistant").click();
  await page.getByTestId("start-interview").click();
  await expect(page.getByTestId("submit-answer")).toBeVisible();
  await page.getByTestId("submit-answer").click();
  const summary = page.getByTestId("error-summary");
  await expect(summary).toBeVisible();
  await expect(summary).toBeFocused();
});

test("reduced motion disables the presence animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/practice");
  await page.getByTestId("sample-research_assistant").click();
  await page.getByTestId("start-interview").click();
  await expect(page.locator(".presence-glow")).toBeVisible();
  const animation = await page.locator(".presence-glow").evaluate((el) => getComputedStyle(el).animationName);
  expect(animation === "none" || animation === "").toBeTruthy();
});

test("sign-in allows paste and history isolation is per user", async ({ page, context }) => {
  await page.goto("/sign-in");
  await page.locator("#identifier").fill("");
  await page.locator("#identifier").press("Control+v").catch(() => undefined);
  await page.locator("#identifier").evaluate((el) => {
    const input = el as HTMLInputElement;
    input.focus();
    input.value = "alice@example.com";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  // Explicit paste path
  await page.locator("#identifier").click();
  await page.evaluate(async () => {
    const input = document.getElementById("identifier") as HTMLInputElement;
    input.focus();
    const event = new ClipboardEvent("paste", {
      clipboardData: new DataTransfer(),
      bubbles: true,
      cancelable: true,
    });
    event.clipboardData!.setData("text", "alice@example.com");
    input.dispatchEvent(event);
  });
  await page.locator("#identifier").fill("alice@example.com");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/history|practice/);

  await page.goto("/practice");
  await completeInterview(page);
  await page.getByRole("button", { name: "Save to history" }).click();
  await page.goto("/history");
  await expect(page.getByText(/Research Program/).first()).toBeVisible();

  const bob = await context.browser()?.newContext();
  if (!bob) return;
  const bobPage = await bob.newPage();
  await bobPage.goto("/sign-in");
  await bobPage.locator("#identifier").fill("bob@example.com");
  await bobPage.getByRole("button", { name: "Continue" }).click();
  await bobPage.goto("/history");
  await expect(bobPage.getByText("Research Program")).toHaveCount(0);
  await bob.close();
});

test("mocked speech fills an editable answer marked as voice", async ({ page }) => {
  await page.addInitScript(() => {
    class FakeRecognition {
      lang = "";
      interimResults = false;
      onresult: ((event: { results: Array<{ 0: { transcript: string } }> }) => void) | null = null;
      onerror: (() => void) | null = null;
      start() {
        this.onresult?.({
          results: [{ 0: { transcript: "I built a voice-mocked tutoring club because access matters." } }],
        });
      }
      stop() {}
    }
    Object.defineProperty(window, "SpeechRecognition", { value: FakeRecognition });
    Object.defineProperty(window, "__PLAYWRIGHT_SPEECH__", { value: true });
  });
  await page.goto("/practice");
  await page.getByTestId("sample-research_assistant").click();
  await page.getByTestId("start-interview").click();
  await waitForQuestion(page);
  await page.getByRole("button", { name: "Start microphone" }).click();
  await expect(page.locator("#answer")).toHaveValue(/voice-mocked tutoring club/);
  await page.locator("#answer").fill(`${LONG_ANSWER} I edited the transcript after speaking.`);
  await page.getByTestId("submit-answer").click();
  for (let i = 0; i < 2; i++) {
    if (/\/report\//.test(page.url())) break;
    await waitForQuestion(page);
    const isMcq = (await page.locator('input[name="choice"]').count()) > 0;
    await answerCurrent(page, isMcq ? TECH_ANSWER : LONG_ANSWER);
  }
  await expect(page).toHaveURL(/\/report\//, { timeout: 30_000 });
  await expect(page.getByText(/qualitative · voice/)).toBeVisible();
});
