import { readdir, readFile } from "node:fs/promises";
import { join, relative } from "node:path";
import { gzipSync } from "node:zlib";

const CHUNKS_DIRECTORY = join(process.cwd(), ".next", "static", "chunks");
const BUDGETS = {
  gzipBytes: 500_000,
  largestRawChunkBytes: 350_000,
  rawBytes: 1_500_000,
};

async function javascriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nestedFiles = await Promise.all(
    entries.map(async (entry) => {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) return javascriptFiles(path);
      return entry.isFile() && entry.name.endsWith(".js") ? [path] : [];
    }),
  );
  return nestedFiles.flat();
}

let files;
try {
  files = await javascriptFiles(CHUNKS_DIRECTORY);
} catch (error) {
  const reason = error instanceof Error ? error.message : String(error);
  process.stderr.write(`No production build was found: ${reason}\nRun npm run build first.\n`);
  process.exit(1);
}

if (files.length === 0) {
  process.stderr.write("No JavaScript chunks were found in the production build.\n");
  process.exit(1);
}

const chunks = await Promise.all(
  files.map(async (path) => {
    const contents = await readFile(path);
    return {
      gzipBytes: gzipSync(contents).byteLength,
      path: relative(process.cwd(), path),
      rawBytes: contents.byteLength,
    };
  }),
);
const rawBytes = chunks.reduce((total, chunk) => total + chunk.rawBytes, 0);
const gzipBytes = chunks.reduce((total, chunk) => total + chunk.gzipBytes, 0);
const largestChunk = chunks.reduce((largest, chunk) =>
  chunk.rawBytes > largest.rawBytes ? chunk : largest,
);
const metrics = {
  budgets: BUDGETS,
  files: chunks.length,
  gzipBytes,
  largestChunk,
  rawBytes,
};

process.stdout.write(`NFA80_BUNDLE_METRIC ${JSON.stringify(metrics)}\n`);

const failures = [];
if (rawBytes > BUDGETS.rawBytes) {
  failures.push(`all raw chunks total ${rawBytes} bytes (budget ${BUDGETS.rawBytes})`);
}
if (gzipBytes > BUDGETS.gzipBytes) {
  failures.push(`all gzip chunks total ${gzipBytes} bytes (budget ${BUDGETS.gzipBytes})`);
}
if (largestChunk.rawBytes > BUDGETS.largestRawChunkBytes) {
  failures.push(
    `largest raw chunk ${largestChunk.path} is ${largestChunk.rawBytes} bytes ` +
      `(budget ${BUDGETS.largestRawChunkBytes})`,
  );
}

if (failures.length > 0) {
  process.stderr.write(`Frontend bundle budget failed:\n- ${failures.join("\n- ")}\n`);
  process.exit(1);
}

process.stdout.write("Frontend production JavaScript bundle is within the NFA-80 budgets.\n");
