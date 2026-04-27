# tool-document-text

A registered deterministic capability of `kind: tool`.

It turns an uploaded document path into plain text. It supports UTF-8 text,
markdown, and PDFs with embedded text. Scanned image PDFs are intentionally not
handled here; that would be a separate OCR capability.

Agents call it through the registry:

```json
{
  "trace_id": "...",
  "inputs": { "path": "/data/inbox/cv.pdf" }
}
```

The response uses the standard envelope:

```json
{
  "outputs": {
    "text": "Extracted document text...",
    "media_type": "application/pdf"
  },
  "signals": {
    "path_within_root": true,
    "extracted_text_present": true
  }
}
```

This keeps `tool-filesystem` as low-level file/list access and makes document
interpretation a separate replaceable capability.
