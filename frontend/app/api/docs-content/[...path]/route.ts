import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET(
  _request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  // Validate path segments (only alphanumeric, hyphens, and .md extension)
  const segments = params.path;
  if (
    segments.length !== 2 ||
    !segments.every((s) => /^[a-z0-9-]+(\\.md)?$/.test(s))
  ) {
    return new NextResponse("Not found", { status: 404 });
  }

  const [category, file] = segments;
  const fileName = file.endsWith(".md") ? file : `${file}.md`;
  const filePath = path.join(process.cwd(), "content", "docs", category, fileName);

  // Prevent path traversal
  const resolvedPath = path.resolve(filePath);
  const contentDir = path.resolve(path.join(process.cwd(), "content", "docs"));
  if (!resolvedPath.startsWith(contentDir)) {
    return new NextResponse("Not found", { status: 404 });
  }

  try {
    const content = fs.readFileSync(resolvedPath, "utf-8");
    return new NextResponse(content, {
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Cache-Control": "public, max-age=3600, s-maxage=86400",
      },
    });
  } catch {
    return new NextResponse("Not found", { status: 404 });
  }
}
