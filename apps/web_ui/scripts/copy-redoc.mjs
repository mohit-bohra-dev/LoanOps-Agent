// Vendors the Redoc standalone bundle from node_modules into public/redoc so it
// is served locally (no public CDN at runtime — honors the local-first rule).
// Runs automatically via the postinstall / predev / prebuild npm hooks.
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");

const src = resolve(root, "node_modules/redoc/bundles/redoc.standalone.js");
const destDir = resolve(root, "public/redoc");
const dest = resolve(destDir, "redoc.standalone.js");

if (!existsSync(src)) {
  console.error(
    "[copy-redoc] redoc.standalone.js not found at %s — is the 'redoc' package installed?",
    src,
  );
  process.exit(1);
}

mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log("[copy-redoc] vendored Redoc bundle -> %s", dest);
