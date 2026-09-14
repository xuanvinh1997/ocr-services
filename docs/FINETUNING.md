# Fine-tuning

Input JSONL records require `document_id`, `image`, `instruction`, `answer`, and
`task`. Task values are `ocr`, `table`, `formula`, or `chart`; labels must be
reviewed ground truth. Tables use OTSL and formulas use LaTeX.

`training.prepare` validates required data, verifies each referenced image, rejects
pixel-identical images crossing document groups, and splits by `document_id`. This
prevents exact duplicate leakage but does not detect near duplicates.

Training adapters must mask instruction, image, and padding tokens so loss applies
only to answer tokens. Training implementations must reject over-length examples
rather than truncating labels. Use one of the configurations under
`configs/training`, record trainable-module names and counts, evaluate held-out data,
then merge and reload the adapter into vLLM before approval.
