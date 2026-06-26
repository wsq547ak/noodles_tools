"use client";

import { useMemo, useState, useTransition } from "react";
import { inferRegex } from "@/tools/regSeed/client/infer-regex";
import {
  extractWithPattern,
  parseRegexLiteral,
  toRegexLiteral,
} from "@/tools/regSeed/lib/regex";
import { RegexSeedExample } from "@/tools/regSeed/lib/types";
import styles from "./reg-seed-page.module.css";

const DEFAULT_ROWS: RegexSeedExample[] = [
  {
    sample: "www.188.com/fff/123.html?a=1&c=t",
    result: "a=1&c=t",
  },
  {
    sample: "https://188.com/fff/123",
    result: "",
  },
];

const MAX_EXAMPLES = 10;

export function RegSeedPage() {
  const [examples, setExamples] = useState(DEFAULT_ROWS);
  const [regexLiteral, setRegexLiteral] = useState("");
  const [inferredRegexLiteral, setInferredRegexLiteral] = useState("");
  const [explanation, setExplanation] = useState("");
  const [testInput, setTestInput] = useState(
    "www.188.com/fff/123.html?a=1&c=t\nhttps://188.com/fff/123\nhttp://188.com/ddd?trust=true",
  );
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isPending, startTransition] = useTransition();

  const activeRegexLiteral = regexLiteral.trim() || inferredRegexLiteral.trim();
  const filledExamples = examples.filter(
    (example) => example.sample.trim().length > 0,
  ).length;
  const canInfer = examples.some((example) => example.sample.trim().length > 0);

  const testLines = useMemo(
    () =>
      testInput
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0),
    [testInput],
  );

  const testResults = useMemo(() => {
    if (testLines.length === 0) {
      return [];
    }

    if (activeRegexLiteral.length === 0) {
      return testLines.map((line) => ({
        matched: false,
        output: "",
        sample: line,
      }));
    }

    try {
      const { flags, pattern } = parseRegexLiteral(activeRegexLiteral);
      return testLines.map((line) => {
        const output = extractWithPattern(pattern, flags, line);
        return {
          matched: output.length > 0,
          output,
          sample: line,
        };
      });
    } catch {
      return testLines.map((line) => ({
        matched: false,
        output: "正则格式无效",
        sample: line,
      }));
    }
  }, [activeRegexLiteral, testLines]);

  function updateExample(
    index: number,
    key: keyof RegexSeedExample,
    value: string,
  ) {
    setExamples((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item,
      ),
    );
  }

  function removeExample(index: number) {
    setExamples((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  function resetExamples() {
    setExamples(DEFAULT_ROWS);
    setRegexLiteral("");
    setInferredRegexLiteral("");
    setExplanation("");
    setError(null);
    setSuccess(null);
  }

  function addExample() {
    setExamples((current) =>
      current.length < MAX_EXAMPLES
        ? [...current, { sample: "", result: "" }]
        : current,
    );
  }

  function handleInfer() {
    setError(null);
    setSuccess(null);

    startTransition(() => {
      void inferRegex(examples)
        .then((inference) => {
          const nextRegexLiteral = toRegexLiteral(
            inference.pattern,
            inference.flags,
          );
          setInferredRegexLiteral(nextRegexLiteral);
          setRegexLiteral(nextRegexLiteral);
          setExplanation(inference.explanation);
          setSuccess("正则推导完成，可在右侧继续测试或手动微调。");
        })
        .catch((nextError: unknown) => {
          setError(
            nextError instanceof Error ? nextError.message : "正则推导失败。",
          );
        });
    });
  }

  function copyRegex() {
    if (!activeRegexLiteral) return;

    void navigator.clipboard.writeText(activeRegexLiteral).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>RegSeed</p>
        <h1 className={styles.title}>正则模糊推导</h1>
        <p className={styles.subtitle}>
          输入样本与期望提取结果，自动反推正则表达式，并实时验证提取效果。
        </p>
      </header>

      <section className={styles.layout}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>样本输入</h2>
            <span className={styles.badge}>{filledExamples} / {MAX_EXAMPLES}</span>
          </div>
          <p className={styles.panelHint}>
            左侧填写原始文本，右侧填写期望提取结果。结果留空表示该样本不应命中。
          </p>

          <div className={styles.examples}>
            <div className={styles.exampleHeader}>
              <span>原始样本</span>
              <span>期望结果</span>
              <span aria-hidden="true" className={styles.exampleActionCell} />
            </div>
            {examples.map((example, index) => (
              <div className={styles.exampleRow} key={index}>
                <label className={styles.field}>
                  <span className={styles.visuallyHidden}>原始样本 {index + 1}</span>
                  <input
                    className={styles.input}
                    onChange={(event) =>
                      updateExample(index, "sample", event.target.value)
                    }
                    placeholder="输入原始样本"
                    value={example.sample}
                  />
                </label>
                <label className={styles.field}>
                  <span className={styles.visuallyHidden}>期望结果 {index + 1}</span>
                  <input
                    className={styles.input}
                    onChange={(event) =>
                      updateExample(index, "result", event.target.value)
                    }
                    placeholder="留空表示不提取"
                    value={example.result}
                  />
                </label>
                <button
                  aria-label={`删除样本 ${index + 1}`}
                  className={styles.iconButton}
                  disabled={examples.length <= 1}
                  onClick={() => removeExample(index)}
                  type="button"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className={styles.actions}>
            <button
              className={styles.primaryButton}
              disabled={isPending || !canInfer}
              onClick={handleInfer}
              type="button"
            >
              {isPending ? "推导中…" : "推导正则"}
            </button>
            <button
              className={styles.secondaryButton}
              disabled={examples.length >= MAX_EXAMPLES}
              onClick={addExample}
              type="button"
            >
              添加样本
            </button>
            <button
              className={styles.tertiaryButton}
              onClick={resetExamples}
              type="button"
            >
              重置
            </button>
          </div>

          {error ? <p className={styles.error}>{error}</p> : null}
          {success ? <p className={styles.success}>{success}</p> : null}
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>推导结果</h2>
            <span
              className={
                activeRegexLiteral ? styles.statusPillActive : styles.statusPill
              }
            >
              {activeRegexLiteral ? "可测试" : "待推导"}
            </span>
          </div>

          <div className={styles.regexBox}>
            <label className={styles.field}>
              <span className={styles.label}>正则表达式</span>
              <div className={styles.regexInputWrap}>
                <input
                  className={styles.regexInput}
                  onChange={(event) => setRegexLiteral(event.target.value)}
                  placeholder="推导完成后显示正则，也可直接编辑"
                  value={regexLiteral || inferredRegexLiteral}
                />
                <button
                  className={styles.copyButton}
                  disabled={!activeRegexLiteral}
                  onClick={copyRegex}
                  type="button"
                >
                  {copied ? "已复制" : "复制"}
                </button>
              </div>
            </label>
            <p className={styles.explanation}>
              {explanation || "推导完成后，这里会说明正则的截取逻辑。"}
            </p>
          </div>

          <div className={styles.divider} />

          <label className={styles.field}>
            <span className={styles.label}>测试文本</span>
            <textarea
              className={styles.textarea}
              onChange={(event) => setTestInput(event.target.value)}
              placeholder="每行输入一个需要测试的文本"
              rows={5}
              value={testInput}
            />
          </label>

          <div className={styles.testResults}>
            <h3 className={styles.resultsTitle}>验证结果</h3>
            {testResults.length === 0 ? (
              <div className={styles.emptyState}>
                <p className={styles.emptyTitle}>等待测试文本</p>
                <p className={styles.empty}>
                  在上方输入测试文本，或生成正则后查看逐条提取结果。
                </p>
              </div>
            ) : (
              testResults.map((result, index) => (
                <article className={styles.testItem} key={`${result.sample}-${index}`}>
                  <div className={styles.testItemHeader}>
                    <span className={styles.testIndex}>#{index + 1}</span>
                    <span
                      className={
                        result.matched ? styles.testHit : styles.testMiss
                      }
                    >
                      {result.matched ? "命中" : "未命中"}
                    </span>
                  </div>
                  <p className={styles.testSample}>{result.sample}</p>
                  <div className={styles.testOutputWrap}>
                    <span className={styles.testOutputLabel}>提取结果</span>
                    <span className={styles.testOutput}>
                      {result.output || "(空字符串)"}
                    </span>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
