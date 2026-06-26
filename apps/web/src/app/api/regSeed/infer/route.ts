import { NextRequest, NextResponse } from "next/server";
import { RegexSeedExample } from "@/tools/regSeed/lib/types";
import { inferRegexFromExamples } from "@/tools/regSeed/server/infer-regex";

type InferRequestBody = {
  examples?: RegexSeedExample[];
};

export async function POST(request: NextRequest) {
  const body = (await request.json()) as InferRequestBody;
  const examples = Array.isArray(body.examples) ? body.examples : [];

  try {
    const inference = inferRegexFromExamples(examples);
    return NextResponse.json({ inference });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "正则推导失败。",
      },
      { status: 400 },
    );
  }
}
