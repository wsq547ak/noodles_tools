# Image Compressor Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable image-compression module with a Next.js frontend and a standalone Python HTTP compression service that reduces PNG/JPEG file size without changing pixel dimensions.

**Architecture:** The Next.js app owns UX, upload orchestration, and result rendering. A standalone Python service owns compression decisions and binary transforms. The interface between them is a small HTTP contract so the UI module can be migrated into another Next.js app with minimal changes.

**Tech Stack:** Next.js App Router, TypeScript, React, Python 3, FastAPI, Pillow, pytest

---

## File Structure

- `apps/web/`
  - Next.js application shell and reusable compressor module
- `apps/web/src/tools/picZip/`
  - Upload UI, API client, result types
- `apps/web/src/app/api/picZip/compress/route.ts`
  - Server-side proxy from Next.js to the Python service
- `services/picZip/`
  - Standalone Python HTTP service and compression core
- `services/picZip/tests/`
  - PNG/JPEG regression tests proving dimensions remain unchanged

## Execution Notes

- Start with tests around the Python compression core because compression correctness is the primary requirement.
- Keep “same dimensions in, same dimensions out” as a hard invariant for every format.
- Prefer format-preserving output in v1: PNG input returns PNG, JPEG input returns JPEG.
- Build the Next.js side as a feature folder that can later be copied into another App Router project.
