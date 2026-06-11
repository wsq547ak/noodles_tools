# Tiny Toolbox

Small-tool workspace for reusable Next.js + Python utilities.

## Structure

- `apps/web`: Next.js shell for all tools
- `apps/web/src/tools/picZip`: `picZip` frontend module
- `apps/web/src/app/api/picZip/compress/route.ts`: `picZip` API adapter
- `services/picZip`: `picZip` Python service

## Goals

- Keep each small tool isolated by folder
- Split frontend and backend modules cleanly
- Make new tools easy to add beside `picZip`
