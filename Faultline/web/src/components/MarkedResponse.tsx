type Props = {
  text: string;
  spanStart: number | null;
  spanEnd: number | null;
};

/**
 * Renders the target's reply with the offending span marked.
 *
 * The judge returns character offsets into this exact string, so the mark is
 * placed by slicing rather than by matching text - no diffing, and no chance of
 * highlighting a coincidental second occurrence.
 */
export function MarkedResponse({ text, spanStart, spanEnd }: Props) {
  const hasSpan =
    spanStart !== null &&
    spanEnd !== null &&
    spanStart >= 0 &&
    spanEnd <= text.length &&
    spanStart < spanEnd;

  if (!hasSpan) {
    return <p className="transcript">{text}</p>;
  }

  return (
    <p className="transcript">
      {text.slice(0, spanStart)}
      <mark className="leak">{text.slice(spanStart, spanEnd)}</mark>
      {text.slice(spanEnd)}
    </p>
  );
}
