# `broken_link_checker.py` cheat sheet

| Component | Purpose |
| --- | --- |
| `normalize` | Validates HTTP/HTTPS URL, IDNA hostname, port, credentials and whitespace; removes fragments and default ports. |
| `origin` | Defines exact website scope as scheme and authority. |
| `Links` | Extracts anchor/area hrefs and the first HTML base href. |
| `NoRedirects` | Disables automatic redirects so every hop can be checked. |
| `Client.open_once` | Paces requests per origin and returns HTTP errors as responses. |
| `Client.policy` | Caches robots policy and supported pacing directives per origin. |
| `Client.fetch` | Checks robots/scope on each redirect hop, classifies status, reads bounded internal HTML. |
| `scan` | Breadth-first traversal, unique-target scheduling, all source-page references, JSON/CSV output. |
| `main` | Interactive or CLI input, limits, output folder, external switch, exit codes. |

## Data flow

1. Normalize starting URL and initialize queue/source map.
2. Fetch target once per scheduled normalized URL; redirects can still revisit destinations.
3. Parse successful internal HTML and queue new hyperlinks within limits.
4. Record each discovered target's referring page, including references found after the target was checked.
5. Write JSON summary and CSV rows for each source-target pair.

Status failures such as 404 are broken; 401/403/429 and transport/robots failures are unchecked. External targets are skipped unless enabled; external HTML never expands the crawl. The page cap counts internal URL checks, not just successfully parsed pages. Resource requests from images/scripts/CSS are not discovered. An oversized HTML response has a crawl note and is not parsed.
