import { randomUUID } from "node:crypto";
import { CompressionResult } from "@/tools/picZip/lib/types";

const SERVICE_URL =
  process.env.COMPRESSION_SERVICE_URL ?? "http://127.0.0.1:8000";
const DEFAULT_PROFILE = process.env.COMPRESSION_PROFILE ?? "aggressive";
const DEFAULT_PNG_MODE = process.env.PNG_COMPRESSION_MODE ?? "strict";

type ServiceCompressionResponse = {
  width: number;
  height: number;
  originalSize: number;
  compressedSize: number;
  bytesSaved: number;
  compressionRatio: number;
  base64Data: string;
};

export class CompressionApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function compressSingleFile(file: File): Promise<CompressionResult> {
  const arrayBuffer = await file.arrayBuffer();
  const response = await fetch(`${SERVICE_URL}/tools/compress`, {
    method: "POST",
    headers: {
      "content-type": file.type,
      "x-file-name": encodeURIComponent(file.name),
      "x-compression-profile": DEFAULT_PROFILE,
      "x-png-compression-mode": DEFAULT_PNG_MODE,
    },
    body: arrayBuffer,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: string }
      | null;
    throw new CompressionApiError(
      response.status,
      payload?.error ?? `${file.name} 压缩失败。`,
    );
  }

  const payload = (await response.json()) as ServiceCompressionResponse;

  return {
    id: randomUUID(),
    originalName: file.name,
    mimeType: file.type,
    width: payload.width,
    height: payload.height,
    originalSize: payload.originalSize,
    compressedSize: payload.compressedSize,
    bytesSaved: payload.bytesSaved,
    compressionRatio: payload.compressionRatio,
    dataUrl: `data:${file.type};base64,${payload.base64Data}`,
  };
}

export async function compressFilesWithService(files: File[]) {
  return Promise.all(files.map((file) => compressSingleFile(file)));
}
