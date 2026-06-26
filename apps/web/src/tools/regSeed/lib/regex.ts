export function toRegexLiteral(pattern: string, flags: string) {
  return `/${pattern}/${flags}`;
}

export function parseRegexLiteral(input: string) {
  const trimmed = input.trim();
  const literalMatch = trimmed.match(/^\/(.+)\/([a-z]*)$/i);

  if (literalMatch) {
    return {
      flags: literalMatch[2] ?? "",
      pattern: literalMatch[1] ?? "",
    };
  }

  return {
    flags: "",
    pattern: trimmed,
  };
}

export function extractWithPattern(
  pattern: string,
  flags: string,
  value: string,
): string {
  const regex = new RegExp(pattern, flags);
  const matched = regex.exec(value);

  if (!matched) {
    return "";
  }

  if (matched.groups?.capture !== undefined) {
    return matched.groups.capture;
  }

  if (matched[1] !== undefined) {
    return matched[1];
  }

  return matched[0] ?? "";
}
