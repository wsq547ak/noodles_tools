# Tiny Toolbox

Small-tool workspace for reusable Next.js + Python utilities.

## Quick start

```bash
npm install
npm run dev          # 启动 Next.js，访问 http://localhost:4001
npm run dev:backend  # 启动共享 Python 后端（127.0.0.1:5001）
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

### Linux + PM2 + Nginx 部署

推荐 Node.js 20+、Python 3.11+。在项目根目录安装依赖：

```bash
npm ci
npm install -g pm2
pip3 install -r services/picZip/requirements.txt
```

按 `.env.example` 创建服务配置，API Key 只能放在 `.env`，不要写入示例文件：

```bash
cp apps/web/.env.example apps/web/.env.local
cp services/picZip/.env.example services/picZip/.env
chmod 600 services/picZip/.env
```

构建并启动全部进程：

```bash
npm run build:web
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

`ecosystem.config.js` 配置了两个仅供 Nginx 内部访问的进程：

- `tools`：Next.js standalone 前端，端口 `4001`
- `tools_server`：共享 Python 后端，端口 `5001`，同时提供图片压缩、正则推导和学生名单识别

安装 Nginx 配置前，将 `deploy/nginx.conf` 中的 `server_name` 改成实际域名：

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/tiny-toolbox
sudo ln -s /etc/nginx/sites-available/tiny-toolbox /etc/nginx/sites-enabled/tiny-toolbox
sudo nginx -t
sudo systemctl reload nginx
```

上线地址为 `https://你的域名/tools/randomstu` 和 `https://你的域名/tools/piczip`。HTTPS 可使用 Certbot 配置：

```bash
sudo certbot --nginx -d 你的域名
```

常用管理：

```bash
pm2 status
pm2 logs tools
pm2 logs tools_server
pm2 restart ecosystem.config.js
pm2 stop ecosystem.config.js
pm2 delete ecosystem.config.js
```

> 不要直接用 `pm2 start npm -- prod:web`：pm2 会把 `prod:web` 当成 npm 子命令执行（实际不存在），而且 `prod:web` 会先 build 再退出，pm2 会误判为崩溃并反复重启。

## Structure

- `apps/web`: Next.js shell for all tools
- `apps/web/src/tools/picZip`: `picZip` frontend module
- `apps/web/src/app/api/picZip/compress/route.ts`: `picZip` API adapter
- `services/picZip/server.py`: shared Python HTTP server on port `5001`
- `apps/web/src/tools/randomStu`: `randomStu` frontend module
- `services/randomStu`: isolated `randomStu` recognition module

## Goals

- Keep each small tool isolated by folder
- Split frontend and backend modules cleanly
- Make new tools easy to add beside `picZip`
