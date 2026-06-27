export type RegexSeedExample = {
  sample: string;
  result: string;
};

export type RegexSeedInferRequest = {
  examples: RegexSeedExample[];
};

export type RegexSeedInference = {
  explanation: string;
  flags: string;
  pattern: string;
};

export type RegexSeedInferenceResponse = {
  inference: RegexSeedInference;
};

export type RegexSeedAiInferRequest = RegexSeedInferRequest & {
  model?: string;
};

export type RegexSeedAiInferenceResponse = {
  inference: RegexSeedInference;
  meta: {
    model: string;
    provider: "deepseek";
  };
};
