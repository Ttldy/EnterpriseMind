import { expect, test } from "@playwright/test";

test("admin can login and open knowledge admin", async ({
  page,
}) => {
  await page.goto("/login");
  await page
    .getByTestId("username")
    .locator("input")
    .fill("admin");
  await page
    .getByTestId("password")
    .locator("input")
    .fill("AdminPassw0rd!");
  await page.getByTestId("submit").click();

  await expect(page).toHaveURL(/\/chat$/);
  await page.goto("/admin/knowledge");
  await expect(
    page.getByText("知识库与文档", {
      exact: true,
    }),
  ).toBeVisible();
});

test("it employee receives a cited answer", async ({
  page,
}) => {
  await page.goto("/login");
  await page
    .getByTestId("username")
    .locator("input")
    .fill("it01");
  await page
    .getByTestId("password")
    .locator("input")
    .fill("ItPassw0rd!");
  await page.getByTestId("submit").click();

  await page
    .getByTestId("chat-input")
    .locator("textarea")
    .fill("VPN 无法连接时怎么办？");
  await page.getByTestId("chat-send").click();

  await expect(
    page.getByText("internal-vpn-guide.md"),
  ).toBeVisible({
    timeout: 180_000,
  });
  await expect(
    page.getByText("ollama", { exact: true }),
  ).toBeVisible();
});