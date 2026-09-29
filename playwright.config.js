const { defineConfig } = require("@playwright/test");

// Playwright is used here purely as an API test runner: no browser is launched,
// the tests call the HTTP bridge and the result is visible in Gazebo.
module.exports = defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.js",
  globalSetup: require.resolve("./e2e/support/global-setup.js"),
  globalTeardown: require.resolve("./e2e/support/global-teardown.js"),
  // One shared Gazebo world means one test at a time.
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  reporter: [["list"]],
});
