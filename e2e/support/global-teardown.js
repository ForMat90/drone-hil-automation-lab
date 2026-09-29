// After the whole suite: release the command and park the drone at the center.
const http = require("http");
const { getControlUrl } = require("./control-url");

function post(pathname) {
  const target = new URL(pathname, `${getControlUrl()}/`);
  const payload = Buffer.from("{}");
  return new Promise((resolve) => {
    const req = http.request(
      target,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": payload.length,
        },
      },
      (res) => {
        res.resume();
        resolve();
      }
    );
    req.on("error", () => resolve());
    req.setTimeout(2000, () => {
      req.destroy();
      resolve();
    });
    req.end(payload);
  });
}

module.exports = async function globalTeardown() {
  await post("/api/release");
  await post("/api/reset");
};
