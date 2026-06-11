export type CompressionResult = {
  id: string;
  originalName: string;
  mimeType: string;
  width: number;
  height: number;
  originalSize: number;
  compressedSize: number;
  bytesSaved: number;
  compressionRatio: number;
  dataUrl: string;
};
