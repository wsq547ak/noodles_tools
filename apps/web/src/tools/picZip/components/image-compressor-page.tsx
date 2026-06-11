"use client";

import { useState, useTransition } from "react";
import { compressImages } from "@/tools/picZip/client/compress-images";
import { ACCEPTED_TYPES, isSupportedImage } from "@/tools/picZip/lib/file";
import { formatBytes, formatPercent } from "@/tools/picZip/lib/format";
import { CompressionResult } from "@/tools/picZip/lib/types";
import styles from "./image-compressor-page.module.css";

type UploadState = "idle" | "uploading" | "error";

export function ImageCompressorPage() {
  const [results, setResults] = useState<CompressionResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<UploadState>("idle");
  const [isPending, startTransition] = useTransition();

  const originalSize = results.reduce((sum, item) => sum + item.originalSize, 0);
  const compressedSize = results.reduce(
    (sum, item) => sum + item.compressedSize,
    0,
  );
  const bytesSaved = originalSize - compressedSize;
  const compressionRatio =
    originalSize === 0 ? 0 : (bytesSaved / originalSize) * 100;
  const summary = {
    count: results.length,
    originalSize,
    compressedSize,
    bytesSaved,
    compressionRatio,
  };

  async function handleFiles(fileList: FileList | null) {
    if (!fileList) {
      return;
    }

    const files = Array.from(fileList);
    const unsupported = files.find((file) => !isSupportedImage(file));

    if (unsupported) {
      setError("当前版本仅支持 PNG 和 JPEG 图片。");
      setStatus("error");
      return;
    }

    setError(null);
    setStatus("uploading");

    startTransition(() => {
      void compressImages(files)
        .then((nextResults) => {
          setResults((currentResults) => [...nextResults, ...currentResults]);
          setStatus("idle");
        })
        .catch((nextError: unknown) => {
          setStatus("error");
          setError(
            nextError instanceof Error
              ? nextError.message
              : "压缩时发生了异常。",
          );
        });
    });
  }

  function downloadResult(result: CompressionResult) {
    const anchor = document.createElement("a");
    anchor.href = result.dataUrl;
    anchor.download = result.originalName;
    anchor.click();
  }

  function downloadAll() {
    results.forEach((result, index) => {
      window.setTimeout(() => downloadResult(result), index * 150);
    });
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>可复用压缩模块</p>
        <h1 className={styles.title}>无损图片压缩</h1>
        {/* <p className={styles.subtitle}>
          前端模块可迁移，Python 压缩服务可独立部署，并且每张压缩后的图片都会保持原始宽高。
        </p> */}
      </section>

      <section className={styles.panel}>
        <label className={styles.dropzone}>
          <input
            className={styles.input}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            multiple
            onChange={(event) => void handleFiles(event.target.files)}
          />
          <span className={styles.dropTitle}>将图片拖到这里，或点击选择文件</span>
          <span className={styles.dropText}>
            支持批量上传。压缩后保持原始像素尺寸不变。
          </span>
        </label>

        <div className={styles.statusRow}>
          <div>
            <strong>状态：</strong>{" "}
            {status === "uploading" || isPending ? "压缩中..." : "就绪"}
          </div>
          <div>
            <strong>支持格式：</strong> PNG、JPEG
          </div>
        </div>

        {error ? <p className={styles.error}>{error}</p> : null}
      </section>

      <section className={styles.summaryGrid}>
        <article className={styles.summaryCard}>
          <span>图片总数</span>
          <strong>{summary.count}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>原始大小</span>
          <strong>{formatBytes(summary.originalSize)}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>压缩后大小</span>
          <strong>{formatBytes(summary.compressedSize)}</strong>
        </article>
        <article className={styles.summaryCard}>
          <span>节省体积</span>
          <strong>{formatBytes(summary.bytesSaved)}</strong>
          <em>{formatPercent(summary.compressionRatio)}</em>
        </article>
      </section>

      <section className={styles.resultsPanel}>
        <div className={styles.resultsHeader}>
          <h2>压缩结果</h2>
          <button
            className={styles.secondaryButton}
            disabled={results.length === 0}
            onClick={downloadAll}
            type="button"
          >
            全部下载
          </button>
        </div>

        <div className={styles.resultsList}>
          {results.length === 0 ? (
            <p className={styles.emptyState}>
              上传图片后，这里会显示压缩结果、图片尺寸和每张图片节省的体积。
            </p>
          ) : (
            results.map((result) => (
              <article className={styles.resultCard} key={result.id}>
                <img
                  alt={result.originalName}
                  className={styles.preview}
                  height={result.height}
                  loading="lazy"
                  src={result.dataUrl}
                  width={result.width}
                />
                <div className={styles.resultMeta}>
                  <div>
                    <h3>{result.originalName}</h3>
                    <p>
                      {result.width} x {result.height} px
                    </p>
                  </div>
                  <dl className={styles.metrics}>
                    <div>
                      <dt>压缩前</dt>
                      <dd>{formatBytes(result.originalSize)}</dd>
                    </div>
                    <div>
                      <dt>压缩后</dt>
                      <dd>{formatBytes(result.compressedSize)}</dd>
                    </div>
                    <div>
                      <dt>节省</dt>
                      <dd>{formatBytes(result.bytesSaved)}</dd>
                    </div>
                    <div>
                      <dt>压缩率</dt>
                      <dd>{formatPercent(result.compressionRatio)}</dd>
                    </div>
                  </dl>
                  <button
                    className={styles.primaryButton}
                    onClick={() => downloadResult(result)}
                    type="button"
                  >
                    下载
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
