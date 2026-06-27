import {
  RegexSeedExample,
  RegexSeedInferenceResponse,
} from "@/tools/regSeed/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export async function inferRegex(examples: RegexSeedExample[]) {
  const response = await fetch(`${API_BASE}/api/regInfer`, {
    body: JSON.stringify({ examples }),
    headers: {
      "content-type": "application/json",
    },
    method: "POST",
  });

  const data = (await response.json()) as
    | RegexSeedInferenceResponse
    | { error?: string };

  if (!response.ok || !("inference" in data)) {
    const message = "error" in data ? data.error : undefined;
    throw new Error(message ?? "正则推导失败。");
  }

  return data.inference;
}
