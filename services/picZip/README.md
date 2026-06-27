# Python Compression Service

This service accepts raw PNG or JPEG bytes over HTTP and returns compressed bytes
as base64 while preserving the original image dimensions.

Profiles:

- `balanced`: safer quality floor, lighter palette reduction
- `aggressive`: lower JPEG quality floor and deeper PNG palette search
- `strict` PNG mode: lossless PNG re-encode, preserves image content
- `visual` PNG mode: TinyPNG-like palette reduction for smaller files with slight visual drift

## Endpoints

- `GET /tools/health`
- `POST /tools/pic_compress`
  - Headers:
    - `content-type: image/png` or `image/jpeg`
    - `x-compression-profile: balanced` or `aggressive`
    - `x-png-compression-mode: strict` or `visual`
  - Body:
    - Raw image bytes
- `POST /tools/regInfer/ai`
  - Body:

```json
{
  "examples": [
    { "sample": "www.188.com/fff/123.html?a=1&c=t", "result": "a=1&c=t" },
    { "sample": "https://188.com/fff/123", "result": "" }
  ],
  "model": "deepseek-v4-flash"
}
```

当前接口已预留，等待接入模型实现。

## Run

```bash
PICZIP_PORT=5001 python3 -m services.picZip.server
```

Default host/port:

```bash
python3 -m services.picZip.server
```

服务启动时会自动读取同目录下的 `.env`：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
PICZIP_HOST=127.0.0.1
PICZIP_PORT=5001
```
