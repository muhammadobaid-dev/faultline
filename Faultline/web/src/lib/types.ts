export type Turn = {
  user: string;
  assistant: string;
};

export type Failure = {
  id: string;
  ruleId: string;
  ruleTitle: string;
  packName: string;
  packVersion: number;
  technique: string;
  turns: Turn[];
  /** Character offsets into the final assistant message. Null when the judge
   *  returned a span that is not verbatim, in which case nothing is marked. */
  spanStart: number | null;
  spanEnd: number | null;
  spanIsVerbatim: boolean;
  rationale: string;
  saferResponse: string;
  confidence: "high" | "medium" | "low";
  judgedBy: string;
  escalated: boolean;
};

export type ReplayData = {
  pack: { id: string; name: string; version: number };
  target: { id: string; name: string };
  judge: string;
  failures: Failure[];
};
