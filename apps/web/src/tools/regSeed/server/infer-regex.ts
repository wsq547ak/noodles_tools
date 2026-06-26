import { RegexSeedExample, RegexSeedInference } from "../lib/types";
import { extractWithPattern } from "../lib/regex";

type LocatedExample = {
  positions: number[];
  result: string;
  sample: string;
};

type ChosenContext = {
  post: string;
  pre: string;
};

type Candidate = {
  explanation: string;
  pattern: string;
};

export function inferRegexFromExamples(
  examples: RegexSeedExample[],
): RegexSeedInference {
  const normalized = examples
    .map((example) => ({
      result: example.result.trim(),
      sample: example.sample.trim(),
    }))
    .filter((example) => example.sample.length > 0);

  if (normalized.length < 2) {
    throw new Error("请至少填写 2 条样本。");
  }

  const positives = normalized.filter((example) => example.result.length > 0);
  if (positives.length === 0) {
    throw new Error("至少需要 1 条非空结果样本用于推导正则。");
  }

  const located = positives.map(locateExample);
  const bestContexts = chooseBestContexts(located);
  const left = longestCommonSuffix(bestContexts.map((context) => context.pre));
  const right = longestCommonPrefix(bestContexts.map((context) => context.post));

  const candidates = buildCandidates(left, right, positives);
  const winner = candidates.find((candidate) =>
    normalized.every(
      (example) => extractWithPattern(candidate.pattern, "", example.sample) === example.result,
    ),
  );

  if (!winner) {
    throw new Error("暂时没法稳定反推出正则，请补充更明确的样本和目标结果。");
  }

  return {
    explanation: winner.explanation,
    flags: "",
    pattern: winner.pattern,
  };
}

function locateExample(example: RegexSeedExample): LocatedExample {
  const positions = collectPositions(example.sample, example.result).slice(0, 6);

  if (positions.length === 0) {
    throw new Error(`样本「${example.sample}」里找不到目标结果「${example.result}」。`);
  }

  return {
    positions,
    result: example.result,
    sample: example.sample,
  };
}

function chooseBestContexts(located: LocatedExample[]): ChosenContext[] {
  let bestScore = Number.NEGATIVE_INFINITY;
  let best: ChosenContext[] = [];

  walkChoices(
    located,
    0,
    [],
    (chosen) => {
      const score = scoreContexts(chosen);
      if (score > bestScore) {
        bestScore = score;
        best = chosen;
      }
    },
  );

  return best;
}

function walkChoices(
  located: LocatedExample[],
  index: number,
  chosen: ChosenContext[],
  commit: (chosen: ChosenContext[]) => void,
) {
  if (index >= located.length) {
    commit(chosen);
    return;
  }

  const current = located[index];
  for (const position of current.positions) {
    const nextChosen = [
      ...chosen,
      {
        pre: current.sample.slice(0, position),
        post: current.sample.slice(position + current.result.length),
      },
    ];
    walkChoices(located, index + 1, nextChosen, commit);
  }
}

function scoreContexts(contexts: ChosenContext[]) {
  const left = longestCommonSuffix(contexts.map((context) => context.pre));
  const right = longestCommonPrefix(contexts.map((context) => context.post));
  return left.length * 4 + right.length * 4 + Math.min(contexts.length, 5);
}

function buildCandidates(
  left: string,
  right: string,
  positives: RegexSeedExample[],
): Candidate[] {
  const candidates: Candidate[] = [];
  const escapedLeft = escapeRegex(left);
  const escapedRight = escapeRegex(right);

  if (left.length > 0 && right.length > 0) {
    candidates.push({
      explanation: `根据样本里结果两侧共同出现的边界「${left}」和「${right}」来截取目标内容。`,
      pattern: `${escapedLeft}(?<capture>.*?)${escapedRight}`,
    });
  }

  if (left.length > 0) {
    candidates.push({
      explanation: `根据样本里结果左侧共同出现的边界「${left}」，向右提取到字符串结束。`,
      pattern: `${escapedLeft}(?<capture>.*)$`,
    });
  }

  if (right.length > 0) {
    candidates.push({
      explanation: `根据样本里结果右侧共同出现的边界「${right}」，从字符串开头提取到边界前。`,
      pattern: `^(?<capture>.*?)${escapedRight}`,
    });
  }

  const identicalResult = uniqueValue(positives.map((example) => example.result));
  if (identicalResult) {
    candidates.push({
      explanation: "当前非空结果样本完全一致，所以先按固定文本匹配处理。",
      pattern: `(?<capture>${escapeRegex(identicalResult)})`,
    });
  }

  candidates.push({
    explanation: "没有更稳定的边界时，退回到整行提取。",
    pattern: `^(?<capture>.*)$`,
  });

  return dedupeCandidates(candidates);
}

function collectPositions(sample: string, result: string) {
  const positions: number[] = [];
  let cursor = 0;

  while (cursor <= sample.length) {
    const next = sample.indexOf(result, cursor);
    if (next === -1) {
      break;
    }

    positions.push(next);
    cursor = next + Math.max(result.length, 1);
  }

  return positions;
}

function longestCommonPrefix(values: string[]) {
  if (values.length === 0) {
    return "";
  }

  let prefix = values[0];
  for (let index = 1; index < values.length; index += 1) {
    while (!values[index].startsWith(prefix) && prefix.length > 0) {
      prefix = prefix.slice(0, -1);
    }
  }

  return prefix;
}

function longestCommonSuffix(values: string[]) {
  if (values.length === 0) {
    return "";
  }

  let suffix = values[0];
  for (let index = 1; index < values.length; index += 1) {
    while (!values[index].endsWith(suffix) && suffix.length > 0) {
      suffix = suffix.slice(1);
    }
  }

  return suffix;
}

function uniqueValue(values: string[]) {
  const unique = [...new Set(values)];
  return unique.length === 1 ? unique[0] : null;
}

function dedupeCandidates(candidates: Candidate[]) {
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    if (seen.has(candidate.pattern)) {
      return false;
    }

    seen.add(candidate.pattern);
    return true;
  });
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
