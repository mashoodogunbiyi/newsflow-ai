import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const webDirectory = resolve(scriptDirectory, "..");
const applicationUrl = "http://127.0.0.1:3100";
const mockApiUrl = "http://127.0.0.1:4100";
const children = [];
let stopping = false;

function start(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: webDirectory,
    env: { ...process.env, ...options.env },
    stdio: "inherit",
  });
  children.push(child);
  return child;
}

async function waitFor(url, process, label) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (process.exitCode !== null) {
      throw new Error(`${label} stopped before it became available.`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The local service is still starting.
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 500));
  }
  throw new Error(`${label} did not become available in time.`);
}

async function stopChildren() {
  if (stopping) return;
  stopping = true;

  await Promise.all(
    children.map(
      (child) =>
        new Promise((resolveStop) => {
          if (child.exitCode !== null) {
            resolveStop();
            return;
          }
          child.once("exit", resolveStop);
          child.kill("SIGTERM");
          setTimeout(() => {
            if (child.exitCode === null) child.kill("SIGKILL");
          }, 5_000).unref();
        }),
    ),
  );
}

async function main() {
  const mockApi = start(process.execPath, ["e2e/support/mock-api.mjs"]);
  const frontend = start("npm", ["run", "dev"], {
    env: {
      API_INTERNAL_BASE_URL: mockApiUrl,
      HOSTNAME: "127.0.0.1",
      NEXT_PUBLIC_API_BASE_URL: mockApiUrl,
      PORT: "3100",
    },
  });

  const unexpectedExit = Promise.race(
    [mockApi, frontend].map(
      (child) =>
        new Promise((resolveExit) => {
          child.once("exit", (code, signal) => {
            if (!stopping) {
              resolveExit(
                new Error(
                  `A demonstration service stopped unexpectedly (code ${code}, signal ${signal}).`,
                ),
              );
            }
          });
        }),
    ),
  );

  await waitFor(`${mockApiUrl}/health`, mockApi, "Synthetic API");
  await waitFor(applicationUrl, frontend, "Next.js frontend");

  const resetResponse = await fetch(`${mockApiUrl}/__test/reset`, { method: "POST" });
  if (!resetResponse.ok) {
    throw new Error("The synthetic demonstration state could not be reset.");
  }

  process.stdout.write(`
NewsFlow AI demonstration is ready.

Open: ${applicationUrl}
Email: owner@example.com
Password: TestPassword123!
Synthetic article URL: https://example.invalid/newsflow/synthetic-clean-energy

This isolated mode uses synthetic data and mocked AI responses. It makes no CNN or OpenAI request.
Press Ctrl+C to stop both local demonstration services.

`);

  throw await unexpectedExit;
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, async () => {
    await stopChildren();
    process.exit(0);
  });
}

try {
  await main();
} catch (error) {
  process.stderr.write(`Demonstration startup failed: ${error.message}\n`);
  process.exitCode = 1;
} finally {
  await stopChildren();
}
