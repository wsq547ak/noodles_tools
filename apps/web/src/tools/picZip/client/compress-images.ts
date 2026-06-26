import { CompressionResult } from "@/tools/picZip/lib/types";

type ServiceCompressionResponse = {
  width: number;
  height: number;
  originalSize: number;
  compressedSize: number;
  bytesSaved: number;
  compressionRatio: number;
  base64Data: string;
};

const DEFAULT_PROFILE = "aggressive";
const DEFAULT_PNG_MODE = "strict";

export async function compressImages(files: File[]): Promise<CompressionResult[]> {
  const results: CompressionResult[] = [];

  for (const file of files) {
    const response = await fetch("/tools/api/pic_compress", {
      method: "POST",
      headers: {
        "content-type": file.type,
        "x-compression-profile": DEFAULT_PROFILE,
        "x-png-compression-mode": DEFAULT_PNG_MODE,
      },
      body: file,
    });

    if (!response.ok) {
      const data = (await response.json().catch(() => null)) as
        | { error?: string }
        | null;
      throw new Error(data?.error ?? "压缩失败。");
    }

    const payload = (await response.json()) as ServiceCompressionResponse;

    results.push({
      id: crypto.randomUUID(),
      originalName: file.name,
      mimeType: file.type,
      width: payload.width,
      height: payload.height,
      originalSize: payload.originalSize,
      compressedSize: payload.compressedSize,
      bytesSaved: payload.bytesSaved,
      compressionRatio: payload.compressionRatio,
      dataUrl: `data:${file.type};base64,${payload.base64Data}`,
    });
  }

  return results;
}
