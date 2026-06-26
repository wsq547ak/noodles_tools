export type RegexSeedExample = {
  sample: string;
  result: string;
};

export type RegexSeedInference = {
  explanation: string;
  flags: string;
  pattern: string;
};

export type RegexSeedInferenceResponse = {
  inference: RegexSeedInference;
};
