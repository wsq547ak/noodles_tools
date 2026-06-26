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

## Run

```bash
PICZIP_PORT=5001 python3 -m services.picZip.server
```

Default host/port:

```bash
python3 -m services.picZip.server
```
