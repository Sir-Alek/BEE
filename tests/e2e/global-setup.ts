import fs from "fs";
import path from "path";

/** Limpia datos E2E antes de la suite (tests/e2e/.runtime). */
export default async function globalSetup(): Promise<void> {
  const runtime = path.join(process.cwd(), ".runtime");
  if (fs.existsSync(runtime)) {
    fs.rmSync(runtime, { recursive: true, force: true });
  }
}
