import { test, expect } from "@playwright/test";
test("mission map, controls, selection, layers and audit export", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8000/api/control/reset");
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("Live link", { exact: true })).toBeVisible();
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  await expect(page.getByTestId('mission-map')).toHaveAttribute('data-map-ready', 'true');
  await expect(page.locator('.map-error')).toHaveCount(0);
  await expect(page.locator(".uav-marker")).toHaveCount(3);
  await expect(page.locator(".task-marker")).toHaveCount(5);
  await expect(page.locator(".sector-label")).toHaveCount(6);
  await expect(page.getByText("⊘ NO-FLY ZONE", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Select TASK-01", exact: true })
    .click();
  await expect(page.locator(".entity-detail")).toContainText("Search A1");
  await page.getByLabel("hazards", { exact: true }).uncheck();
  await expect(page.getByText("⊘ NO-FLY ZONE", { exact: true })).toBeHidden();
  await page.getByLabel("hazards", { exact: true }).check();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByTestId("sim-clock")).not.toContainText("00:00");
  await page
    .getByRole("button", { name: "Pause mission", exact: true })
    .click();
  const time = await page.getByTestId("sim-clock").textContent();
  await page.waitForTimeout(600);
  expect(await page.getByTestId("sim-clock").textContent()).toBe(time);
  await expect(page.locator(".uav-card").first()).toContainText("TASK-01");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export audit JSON" }).click();
  expect((await download).suggestedFilename()).toBe("edgesar-audit.json");
  await page.getByRole("button", { name: "Reset mission" }).click();
  await expect(page.getByTestId("sim-clock")).toContainText("00:00");
  await expect(page.locator(".state-value")).toContainText("READY");
  await page.screenshot({
    path: "../../docs/mission-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', {name:'Fit area'}).click();
  await page.waitForTimeout(600);
  await expect(
    page.getByRole("button", { name: "Run", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../docs/mission-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
