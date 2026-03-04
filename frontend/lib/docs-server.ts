import fs from "fs";
import path from "path";

// Read markdown content from disk (server-side only)
export function getDocContent(
  categorySlug: string,
  articleSlug: string
): string | null {
  const filePath = path.join(
    process.cwd(),
    "content",
    "docs",
    categorySlug,
    `${articleSlug}.md`
  );
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}
