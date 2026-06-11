import { NextRequest, NextResponse } from "next/server";
import {
  CompressionApiError,
  compressFilesWithService,
} from "@/tools/picZip/server/compression-service-client";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const files = formData
    .getAll("files")
    .filter((value): value is File => value instanceof File);

  if (files.length === 0) {
    return NextResponse.json(
      { error: "请至少上传一张 PNG 或 JPEG 图片。" },
      { status: 400 },
    );
  }

  try {
    const results = await compressFilesWithService(files);
    return NextResponse.json({ results });
  } catch (error) {
    if (error instanceof CompressionApiError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }

    return NextResponse.json(
      { error: "压缩服务暂时不可用。" },
      { status: 502 },
    );
  }
}
