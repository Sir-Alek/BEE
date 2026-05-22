/**
 * Stub mínimo de web_capture_engine.js para smoke con Node (sin Puppeteer).
 * Uso: node tests/fixtures/stub_web_capture_engine.js <output.js> <url>
 */
const fs = require("fs");
const path = require("path");

const outputFile = process.argv[2] || path.join(__dirname, "stub_output.js");
const targetUrl = process.argv[3] || "https://example.com";

fs.mkdirSync(path.dirname(outputFile), { recursive: true });
fs.writeFileSync(
  outputFile,
  `// stub recording for ${targetUrl}\nmodule.exports = [];\n`,
  "utf8",
);

console.log("BROWSER_READY");
console.log('WINDOW_INFO:{"x":0,"y":0,"width":1280,"height":720}');
process.exit(0);
