import { NextRequest, NextResponse } from "next/server";

const SERVICE_URL =
  process.env.RANDOMSTU_SERVICE_URL ??
  process.env.COMPRESSION_SERVICE_URL ??
  "http://127.0.0.1:5001";
const MAX_IMAGE_SIZE = 12 * 1024 * 1024;
const SUPPORTED_TYPES = new Set([
  "image/gif",
  "image/jpeg",
  "image/png",
  "image/webp",
]);

export async function POST(request: NextRequest) {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0] ?? "";
  const contentLength = Number(request.headers.get("content-length") ?? 0);

  if (!SUPPORTED_TYPES.has(contentType)) {
    return NextResponse.json(
      { error: "仅支持 PNG、JPEG、WebP 和 GIF 图片。" },
      { status: 400 },
    );
  }
  if (contentLength > MAX_IMAGE_SIZE) {
    return NextResponse.json({ error: "图片不能超过 12 MB。" }, { status: 413 });
  }

  const image = await request.arrayBuffer();
  if (image.byteLength === 0 || image.byteLength > MAX_IMAGE_SIZE) {
    return NextResponse.json(
      { error: image.byteLength === 0 ? "上传的图片为空。" : "图片不能超过 12 MB。" },
      { status: image.byteLength === 0 ? 400 : 413 },
    );
  }

  try {
    const cookie = request.headers.get("cookie");
    const forwardedFor = request.headers.get("x-forwarded-for");
    const response = await fetch(`${SERVICE_URL}/tools/randomStu/recognize`, {
      method: "POST",
      headers: {
        "content-type": contentType,
        ...(cookie ? { cookie } : {}),
        ...(forwardedFor ? { "x-forwarded-for": forwardedFor } : {}),
      },
      body: image,
      signal: AbortSignal.timeout(130_000),
    });
    const data = (await response.json().catch(() => null)) as
      | { error?: string; students?: unknown[] }
      | null;

    if (!response.ok) {
      return NextResponse.json(
        { error: data?.error ?? "图片识别失败，请稍后重试。" },
        { status: response.status },
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `图片识别服务不可用：${error.message}`
            : "图片识别服务不可用。",
      },
      { status: 502 },
    );
  }
}
