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
├── config.py             # model name, token/timeout/retry constants
├── prompts.py             # the 3 verbatim system prompts
├── anthropic_client.py     # AnthropicAgentClient - wraps messages.create(), the DI seam
├── json_utils.py           # robust JSON extraction from LLM responses
├── validation.py           # validate_extraction_output / validate_analysis_output
├── document_loader.py       # .txt/.md/.pdf/.docx text extraction
├── extraction.py            # extraction_agent()
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
