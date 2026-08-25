# Project Agent Instructions

These instructions apply to every coding-agent session working in this repository.

## Keep Search and Command Output Bounded

Prevent oversized tool responses that can exhaust the conversation context or halt the agent thread.

- Never run an unbounded repository-wide content search or print an entire large file.
- Scope searches as narrowly as possible by directory, file glob, language, and specific symbol or phrase.
- Use a two-stage search when the result size is uncertain:
  1. Return matching file paths only.
  2. Inspect a small number of relevant matches or targeted line ranges.
- Request only one small page of search results at a time. Use pagination/offsets and stop as soon as enough context has been found.
- Limit terminal output with the tool's output caps (for example, `head_lines` and `tail_lines`) rather than allowing unrestricted output.
- Exclude generated, cached, vendored, minified, binary, build-output, and dependency directories unless they are explicitly relevant. This includes locations such as `.git`, `__pycache__`, build/dist directories, virtual environments, coverage output, and dependency caches.
- Avoid broad expressions such as `.*` across the whole repository. Split broad investigations into several focused searches.
- For large or single-line files, search for filenames or matching paths first, then read only a bounded excerpt around the relevant location.
- If output size is uncertain, choose the more conservative search and refine incrementally.
- Do not repeat or quote large tool outputs in chat; summarize only the relevant findings.
