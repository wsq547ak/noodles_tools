# Tiny Toolbox

Small-tool workspace for reusable Next.js + Python utilities.

## Quick start

```bash
npm install
npm run dev          # 启动 Next.js，访问 http://localhost:4001
npm run dev:picZip   # 同时启动 Python 压缩服务（默认 127.0.0.1:5001）
```

> `next.config.ts` 在生产构建时保留了 `basePath: "/tools"`，所以部署后需通过 `/tools` 访问；本地 `npm run dev` 使用空 basePath，直接打开根路径即可。

## Structure

- `apps/web`: Next.js shell for all tools
- `apps/web/src/tools/picZip`: `picZip` frontend module
- `apps/web/src/app/api/picZip/compress/route.ts`: `picZip` API adapter
- `services/picZip`: `picZip` Python service

## Goals

- Keep each small tool isolated by folder
- Split frontend and backend modules cleanly
- Make new tools easy to add beside `picZip`
