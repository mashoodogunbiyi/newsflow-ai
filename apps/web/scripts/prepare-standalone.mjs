import { cpSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const projectRoot = process.cwd();
const standaloneRoot = resolve(projectRoot, ".next", "standalone");

if (!existsSync(resolve(standaloneRoot, "server.js"))) {
  throw new Error("Standalone output is missing. Run npm run build before npm run start.");
}

function copyDirectory(source, destination) {
  if (!existsSync(source)) {
    throw new Error(`Required standalone asset directory is missing: ${source}`);
  }

  mkdirSync(destination, { recursive: true });
  cpSync(source, destination, { force: true, recursive: true });
}

copyDirectory(resolve(projectRoot, "public"), resolve(standaloneRoot, "public"));
copyDirectory(resolve(projectRoot, ".next", "static"), resolve(standaloneRoot, ".next", "static"));
