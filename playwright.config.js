const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.js",
  globalSetup: require.resolve("./e2e/global-setup.js"),
  globalTeardown: require.resolve("./e2e/global-teardown.js"),
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  reporter: [["list"]],
  use: {
    baseURL: process.env.DRONE_CONTROL_URL || "http://127.0.0.1:8765",
  },
});
