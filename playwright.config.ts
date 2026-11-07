import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// Its own servers, database and stub model, so the tests never touch the
// dev database or call a real model.
const backend = "http://127.0.0.1:8001";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5174" },
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8001",
      url: `${backend}/api/health`,
      reuseExistingServer: false,
      env: {
        UNDERCOVER_DB: join(tmpdir(), "undercover-e2e.db"),
        MODEL_NAME: "stub",
        BACKEND_URL: backend,
      },
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: "http://localhost:5174",
      reuseExistingServer: false,
      env: { BACKEND_URL: backend },
    },
  ],
});
