# Tiny Toolbox

Small-tool workspace for reusable Next.js + Python utilities.

## Quick start

```bash
npm install
npm run dev          # 启动 Next.js，访问 http://localhost:4001
npm run dev:picZip   # 同时启动 Python 压缩服务（默认 127.0.0.1:5001）
```

> `next.config.ts` 在生产构建时保留了 `basePath: "/tools"`，所以部署后需通过 `/tools` 访问；本地 `npm run dev` 使用空 basePath，直接打开根路径即可。

## Production

```bash
npm run prod:web     # 先 build 再启动生产服务，监听 4001 端口
```

或分步执行：

```bash
npm run build:web    # 构建到 apps/web/.next
npm run start:web    # 生产模式启动 Next.js
```

构建后会生成 standalone 输出（`apps/web/.next/standalone/apps/web/server.js`），也可以直接用于容器化部署。

### 用 PM2 启动

确保已安装 PM2 和 Python 依赖：

```bash
npm install -g pm2
pip3 install -r services/picZip/requirements.txt
```

先构建前端：

```bash
npm run build:web
```

再用 PM2 同时启动前端和后端：

```bash
pm2 start ecosystem.config.js
```

`ecosystem.config.js` 里配置了两个进程：

- `tools`：Next.js standalone 前端，端口 `4001`
- `piczip`：Python 图片压缩服务，端口 `5001`

常用管理：

```bash
pm2 status
pm2 logs tools
pm2 logs piczip
pm2 restart ecosystem.config.js
pm2 stop ecosystem.config.js
pm2 delete ecosystem.config.js
```

> 不要直接用 `pm2 start npm -- prod:web`：pm2 会把 `prod:web` 当成 npm 子命令执行（实际不存在），而且 `prod:web` 会先 build 再退出，pm2 会误判为崩溃并反复重启。

## Structure

- `apps/web`: Next.js shell for all tools
- `apps/web/src/tools/picZip`: `picZip` frontend module
- `apps/web/src/app/api/picZip/compress/route.ts`: `picZip` API adapter
- `services/picZip`: `picZip` Python service

## Goals

- Keep each small tool isolated by folder
- Split frontend and backend modules cleanly
- Make new tools easy to add beside `picZip`
