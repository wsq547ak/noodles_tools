import { NextRequest, NextResponse } from "next/server";

const SERVICE_URL =
  process.env.RANDOMSTU_SERVICE_URL ??
  process.env.COMPRESSION_SERVICE_URL ??
  "http://127.0.0.1:5001";

export async function proxyRandomStuRequest(
  request: NextRequest,
  backendPath: string,
  method: "GET" | "POST" | "PUT",
) {
  const headers: Record<string, string> = {};
  const contentType = request.headers.get("content-type");
  const cookie = request.headers.get("cookie");
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (contentType) headers["content-type"] = contentType;
  if (cookie) headers.cookie = cookie;
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  try {
    const response = await fetch(`${SERVICE_URL}${backendPath}`, {
      method,
      headers,
      body: method === "GET" ? undefined : await request.arrayBuffer(),
      signal: AbortSignal.timeout(30_000),
      cache: "no-store",
    });
    const result = new NextResponse(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
    const setCookie = response.headers.get("set-cookie");
    if (setCookie) result.headers.set("set-cookie", setCookie);
    return result;
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `后台数据服务不可用：${error.message}`
            : "后台数据服务不可用。",
      },
      { status: 502 },
    );
  }
}
