type RecognizedStudent = {
  number: string;
  name: string;
};

type RecognitionResponse = {
  error?: string;
  students?: RecognizedStudent[];
};

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export async function recognizeRosterImage(file: File): Promise<RecognizedStudent[]> {
  const response = await fetch(`${basePath}/api/randomStu/recognize`, {
    method: "POST",
    headers: { "content-type": file.type },
    body: file,
  });
  const result = (await response.json().catch(() => null)) as RecognitionResponse | null;
  if (!response.ok) {
    throw new Error(result?.error ?? "图片识别失败，请稍后重试。");
  }
  if (!Array.isArray(result?.students)) {
    throw new Error("识别服务没有返回有效的学生名单。");
  }
  return result.students;
}
