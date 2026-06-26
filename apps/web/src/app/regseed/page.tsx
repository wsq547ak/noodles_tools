import type { Metadata } from "next";
import { RegSeedPage } from "@/tools/regSeed/components/reg-seed-page";

export const metadata: Metadata = {
  title: "RegSeed | 正则推导工具",
  description: "根据样本和期望结果推导可复用的正则表达式，并实时验证提取效果。",
};

export default function RegSeedToolPage() {
  return <RegSeedPage />;
}
