import { NextRequest } from "next/server";
import { proxyRandomStuRequest } from "@/tools/randomStu/server/backend-proxy";

export function POST(request: NextRequest) {
  return proxyRandomStuRequest(request, "/tools/randomStu/logout", "POST");
}
