export const ACCEPTED_TYPES = ["image/png", "image/jpeg"];

export function isSupportedImage(file: File) {
  return ACCEPTED_TYPES.includes(file.type);
}
