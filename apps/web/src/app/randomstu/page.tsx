import type { Metadata } from "next";
import { RandomStuPage } from "@/tools/randomStu/components/random-stu-page";

export const metadata: Metadata = {
  title: "随机点名 | RandomStu",
  description: "在浏览器本地管理班级名单并公平随机抽取学生。",
};

export default function RandomStuToolPage() {
  return <RandomStuPage />;
}
