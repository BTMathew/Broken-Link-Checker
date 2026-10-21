# AI prompt guide: building `broken_link_checker.py`

## 1. Project skeleton

```text
Create Broken-Link-Checker with broken_link_checker.py, README.md, CHEAT.md, PROMPT.md, and .gitignore. Use Python 3.9+ standard library only. Keep work local until publication is requested.
```

## 2. Input and HTTP client

```text
Normalize hostname/HTTP/HTTPS input, defaulting to HTTPS. Support IDNA, custom ports, and IPv6; reject credentials, invalid ports, and raw whitespace. Remove fragments/default ports. Build a urllib client with manual redirects so each hop is checked for exact-origin scope, robots permission, pacing, and a 10-hop limit. Cache robots per origin, permit absent 404/410 policy, and leave other policy failures unchecked. Honor Crawl-delay/Request-rate and use 15-second socket timeouts with normal TLS verification.
```

## 3. Crawl and classify

```text
Breadth-first crawl internal anchor/area hyperlinks from HTMLParser, respecting base href. Track all source pages for each unique normalized target. Default to 100 internal URL checks, 2000 unique targets, one-second per-origin delay. Include query strings. Parse successful internal HTML up to 5 MiB; report oversized crawl notes. Do not crawl external HTML; skip external targets by default and enable status checks with --external. GET requests classify 2xx as ok, 401/403/429 as unchecked, and other final HTTP failures as broken. Mark network/TLS/robots failures unchecked; malformed or excessive redirects broken.
```

## 4. CLI and output

```text
Accept optional website or prompt, --output, --max-pages, --max-links, --delay, and --external. Write report.json and links.csv with status, classification, final URL, details, and all source references. Print summary counts. Return 1 for broken/unchecked results, crawl notes or link truncation; 0 otherwise; CLI syntax errors use 2. Clearly document scope, limits, no browser/JS, no asset or fragment checks, soft-404 limitations, report overwrite behavior and cancellation behavior. No dependency installation needed.
```

## 5. Verify

```text
Use local HTTP servers to test recursive discovery, cycles, redirects, 404/500 links, 403 uncertainty, robots disallow, external scope, source attribution, query links, limits, and JSON/CSV reports. Avoid live external crawling for routine tests.
```
