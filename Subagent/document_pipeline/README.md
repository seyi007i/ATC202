# Document Pipeline

A three-agent document processing pipeline built on the Anthropic Claude API.
Each agent has a single, well-defined responsibility, and the pipeline turns
any supported text document into a structured, synthesized report.

## Pipeline

```
Input Document
      |
      v
Extraction Agent   -- structure only, no analysis
      |
Structured Document (title, metadata, sections)
      |
      v
Analysis Agent      -- claims / entities / topics, no summarizing
      |
Claims + Entities + Topics (each with a confidence score)
      |
      v
Synthesis Agent      -- report only, never sees the original document
      |
      v
Final Report
```

The Synthesis Agent's function signature has no parameter for the original
document or the extraction output at all — there is no argument through
which a caller could pass it, enforcing the "never sees the source
document" rule structurally, not just by convention.

## Architecture

```
document_pipeline/
├── models.py            # dataclasses (ExtractedDocument, AnalysisResult, ...) + exceptions
├── config.py             # model name, token/timeout/retry/chunk-size constants
├── prompts.py             # the 3 verbatim system prompts
├── anthropic_client.py     # AnthropicAgentClient - wraps messages.create(), the DI seam
├── json_utils.py           # robust JSON extraction from LLM responses
├── validation.py           # validate_extraction_output / validate_analysis_output
├── chunking.py              # splits long documents into extraction-sized chunks
├── document_loader.py       # .txt/.md/.pdf/.docx text extraction
├── extraction.py            # extraction_agent() - chunks + merges long documents
├── analysis.py               # analysis_agent()
├── synthesis.py               # synthesis_agent()
├── orchestrator.py             # process_document() / process_document_text()
├── utils.py                     # shared logging setup
└── tests/                        # pytest suite, zero real network calls
```

**Design notes**

- **Models**: all data contracts are immutable `@dataclass(frozen=True)` types
  in `models.py`, alongside a structured exception hierarchy rooted at
  `DocumentPipelineError` (`InvalidDocumentPathError`,
  `UnsupportedDocumentFormatError`, `DocumentExtractionFailedError`,
  `AnthropicAPIError`, `AnthropicTimeoutError`, `MalformedAgentOutputError`,
  `ExtractionValidationError`, `AnalysisValidationError`).
- **Dependency injection**: every agent function and `AnthropicAgentClient`
  itself accept an injectable `client`, so tests substitute a fake that
  returns canned responses instead of calling the real API.
- **Robust JSON parsing**: agents are instructed to return JSON only, but
  `json_utils.extract_json_object` tolerates markdown code fences and stray
  prose before giving up with `MalformedAgentOutputError`.
- **Error handling**: every documented failure mode (invalid path,
  unsupported format, extraction failure, malformed output, validation
  failure, API error, timeout) has its own exception type; anything
  genuinely unexpected is wrapped in `RuntimeError` with the original
  exception chained.
- **Chunked extraction for long documents**: the Extraction Agent echoes
  document content back verbatim (per its "do not summarize" instruction),
  so a single non-streaming Anthropic call can only handle a bounded amount
  of input before its own output would need more tokens than a
  non-streaming call safely allows. Documents longer than
  `config.EXTRACTION_CHUNK_MAX_CHARS` are split on paragraph boundaries
  (`chunking.split_into_chunks`), extracted one chunk at a time, and merged
  back into a single `ExtractedDocument` — the first chunk's title/metadata
  win, sections are concatenated in order, and each chunk's independently
  auto-numbered `"Section N"` headings are renumbered sequentially across
  the merged result so they don't collide. See
  [Known Limitations](#known-limitations) for the practical ceiling this
  doesn't remove.

## Installation

Requires Python 3.12+.

```bash
cd Subagent/document_pipeline
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your-key-here   # macOS/Linux
$env:ANTHROPIC_API_KEY = "your-key-here" # Windows PowerShell
```

No API key is required to run the test suite — every test injects a fake
client.

## How to Run

All commands below are run from the repository root unless noted otherwise.

**1. Install dependencies**

```bash
pip install -r Subagent/document_pipeline/requirements.txt
```

```powershell
# Windows PowerShell
pip install -r Subagent\document_pipeline\requirements.txt
```

**2. Run the test suite (no API key needed)**

```bash
cd Subagent
pytest document_pipeline/tests -v
```

```powershell
# Windows PowerShell
cd Subagent
python -m pytest document_pipeline\tests -v
```

Every test injects a fake Anthropic client, so this works with no API key
and makes zero network calls.

**3. Run the pipeline on a real document (needs an API key)**

```bash
export ANTHROPIC_API_KEY=your-key-here
cd Subagent
python -m document_pipeline.orchestrator path/to/document.pdf
```

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-key-here"
cd Subagent
python -m document_pipeline.orchestrator path\to\document.pdf
```

Accepts `.txt`, `.md`, `.pdf`, or `.docx` and prints the final report as JSON
(see [Example Output](#example-output) below).

**4. Or call it from Python directly**

```python
from document_pipeline.orchestrator import process_document, process_document_text

report = process_document("path/to/document.docx")
print(report["executive_summary"])

# Or process raw text you already have in memory:
report = process_document_text("Some document text...")
```

## How to Run Tests

From the `Subagent/` directory:

```bash
pytest document_pipeline/tests -v
```

With coverage:

```bash
pytest document_pipeline/tests --cov=document_pipeline --cov-report=term-missing
```

The suite runs entirely offline (a `FakeAgentClient` stands in for the real
Anthropic client) and covers: JSON extraction edge cases, schema validation,
each supported/unsupported document format, Anthropic API errors/timeouts,
malformed and schema-invalid agent output, and full end-to-end pipeline
behavior including the unexpected-exception-to-`RuntimeError` wrapping.

## Supported Document Types

| Extension | Extraction method |
|-----------|--------------------|
| `.txt`    | Plain UTF-8 read |
| `.md`     | Plain UTF-8 read |
| `.pdf`    | `pymupdf` (`fitz`) |
| `.docx`   | `python-docx` |
| raw text  | `process_document_text()`, bypasses file I/O entirely |

## Error Handling

| Exception                        | Raised when |
|-----------------------------------|-------------|
| `InvalidDocumentPathError`         | The document path doesn't exist or isn't a file |
| `UnsupportedDocumentFormatError`    | The file extension isn't `.txt`/`.md`/`.pdf`/`.docx` |
| `DocumentExtractionFailedError`     | A supported file is corrupt, undecodable, or extracts to empty text |
| `AnthropicAPIError`                  | The Anthropic API returns an error response |
| `AnthropicTimeoutError`               | A request to the Anthropic API times out |
| `MalformedAgentOutputError`            | An agent's response can't be parsed as a JSON object |
| `ExtractionValidationError`             | The Extraction Agent's JSON fails schema validation |
| `AnalysisValidationError`                | The Analysis Agent's JSON fails schema validation (including out-of-range confidence scores) |
| `RuntimeError`                            | Any other unexpected exception, with the original chained via `__cause__` |

## Known Limitations

- **Per-chunk size, not overall document size.** Chunking (above) removes
  the *total* document length as a hard ceiling, but each individual chunk
  still must fit under `config.EXTRACTION_MAX_TOKENS` (8192) once echoed
  back as JSON. `config.EXTRACTION_CHUNK_MAX_CHARS` (20,000 characters) is
  a conservative default meant to leave headroom for JSON structure/escaping
  overhead; a single paragraph longer than this (e.g. a huge unbroken wall
  of text with no blank lines) becomes its own oversized chunk and can still
  raise `MalformedAgentOutputError` due to truncation (the error message
  names the exact cause and which constant to raise).
- **No streaming.** All three agents use plain, non-streaming
  `messages.create()` calls (matching this repo's existing
  `accp-module4-agent` pattern). The Anthropic SDK requires streaming for
  any call whose response may take longer than 10 minutes to generate,
  which effectively caps a single call's `max_tokens` well below what
  streaming would allow. Extraction accommodates this by chunking instead
  of raising the limit further.
- **Analysis and Synthesis are not chunked.** Only the Extraction Agent
  splits its input. The Analysis Agent receives the full (already merged)
  extracted document in one call, and could itself exceed
  `ANALYSIS_MAX_TOKENS` for an extremely claim/entity-dense merged document,
  surfacing as the same clearly-labeled truncation error.

## Example Output

```json
{
  "executive_summary": "The document discusses renewable energy policy, emphasizing investment incentives and infrastructure modernization.",
  "main_claims": ["Government incentives increased solar adoption."],
  "key_entities": ["Department of Energy"],
  "major_topics": ["Renewable Energy"],
  "overall_confidence": 0.96
}
```
