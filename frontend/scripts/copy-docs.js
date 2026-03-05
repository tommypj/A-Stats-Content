/**
 * Copies content/docs/ markdown files into public/docs-content/
 * so they can be fetched as static assets by the in-app help center.
 * Runs automatically via the "prebuild" npm script.
 */
const fs = require("fs");
const path = require("path");

const src = path.join(__dirname, "..", "content", "docs");
const dest = path.join(__dirname, "..", "public", "docs-content");

function copyDir(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return;
  fs.mkdirSync(destDir, { recursive: true });

  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name);
    const destPath = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else if (entry.name.endsWith(".md")) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// Clean destination first
if (fs.existsSync(dest)) {
  fs.rmSync(dest, { recursive: true });
}

copyDir(src, dest);

const count = fs
  .readdirSync(dest, { recursive: true })
  .filter((f) => f.toString().endsWith(".md")).length;
console.log(`Copied ${count} docs files to public/docs-content/`);
