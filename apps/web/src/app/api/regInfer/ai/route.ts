import { NextRequest, NextResponse } from "next/server";
import {
  RegexSeedAiInferRequest,
  RegexSeedExample,
  RegexSeedAiInferenceResponse,
} from "@/tools/regSeed/lib/types";

type InferAiRequestBody = {
  examples?: RegexSeedExample[];
  model?: string;
};

const SERVICE_URL =
  process.env.REGINFER_SERVICE_URL ??
  process.env.COMPRESSION_SERVICE_URL ??
  "http://127.0.0.1:5001";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as InferAiRequestBody;
  const payload: RegexSeedAiInferRequest = {
    examples: Array.isArray(body.examples) ? body.examples : [],
    model: body.model,
  };

  try {
    const response = await fetch(`${SERVICE_URL}/tools/regInfer/ai`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = (await response.json().catch(() => null)) as
      | RegexSeedAiInferenceResponse
      | { error?: string }
      | null;

    if (!response.ok) {
      return NextResponse.json(
        {
          error: data && "error" in data ? data.error : "AI 正则推导失败。",
        },
        { status: response.status },
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "AI 推导服务暂时不可用。",
      },
      { status: 502 },
    );
  }
}
