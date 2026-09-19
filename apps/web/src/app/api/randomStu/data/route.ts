import { NextRequest } from "next/server";
import { proxyRandomStuRequest } from "@/tools/randomStu/server/backend-proxy";

export function GET(request: NextRequest) {
  return proxyRandomStuRequest(request, "/tools/randomStu/data", "GET");
}

export function PUT(request: NextRequest) {
  return proxyRandomStuRequest(request, "/tools/randomStu/data", "PUT");
}
