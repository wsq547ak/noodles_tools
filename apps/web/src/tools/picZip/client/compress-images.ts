import { CompressionResult } from "@/tools/picZip/lib/types";

type CompressImagesResponse = {
  results: CompressionResult[];
  error?: string;
};

export async function compressImages(files: File[]) {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch("/tools/api/picZip/compress", {
    method: "POST",
    body: formData,
  });

  const data = (await response.json()) as CompressImagesResponse;

  if (!response.ok) {
    throw new Error(data.error ?? "压缩失败。");
  }

  return data.results;
}
