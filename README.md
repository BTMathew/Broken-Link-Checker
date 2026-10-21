# Broken Link Checker

`broken_link_checker.py` crawls a website's HTML pages and checks HTTP/HTTPS hyperlinks. It reports each link's result and every discovered source page containing it. Python 3.9+ is required; no extra packages or browser installation are needed.

## Run

From this project folder:

```powershell
python broken_link_checker.py
python broken_link_checker.py https://example.com
python broken_link_checker.py https://example.com --external --max-pages 500
python broken_link_checker.py --help
```

The first command prompts for a website. Bare hostnames default to HTTPS. Use the site's final URL, including its exact scheme and www hostname. The default scan covers the exact starting origin (scheme, hostname, port). With `--external`, external links and cross-origin redirects are also checked, but their pages are never crawled for more links.

## What it checks

The crawler follows anchor and image-map hyperlinks from successful HTML/XHTML responses. Relative links and HTML base URLs are resolved, fragments are removed, and each normalized target is scheduled once. Reports retain all discovered source-page references to each target. GET is used rather than HEAD so servers that handle HEAD differently do not produce misleading results.

| Result | Meaning |
| --- | --- |
| `ok` | Final response is HTTP 200-299 |
| `broken` | HTTP failure such as 404/410/500, malformed redirect, or excessive redirects |
| `unchecked` | Network/TLS failure, robots restriction/policy failure, 401/403/429, or page limit prevents a conclusion |
| `skipped` | External target or redirect excluded by default scope |

Network failures and access/rate limits are flagged for review instead of assumed permanently broken. An HTTP 200 error page (soft 404) cannot be detected by status alone. Redirects are followed up to 10 hops after robots/scope checks; final URLs are recorded.

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `website` | Prompt | Starting URL or hostname |
| `--output` | `reports` | Report folder relative to the terminal's current directory |
| `--max-pages` | `100` | Maximum scheduled internal URL checks, including non-HTML and failed targets |
| `--max-links` | `2000` | Maximum unique discovered URLs, including starting URL and external links |
| `--delay` | `1` | Minimum seconds between requests per origin; robots timing can increase it |
| `--external` | Off | Check external targets without crawling their content |

Query-string links are included, so calendars/search filters can generate many URLs. Limits keep those spaces bounded. Each redirect hop is paced. Socket operations use a 15-second timeout, not a whole-scan deadline. HTML parsing is capped at 5 MiB per response; larger pages retain their status result with a crawl note and are not explored.

## Robots and coverage

Each contacted origin's robots.txt is loaded and cached. Missing policy (404/410) permits checks; other failures, including redirected robots.txt, leave that origin unchecked. Supported Crawl-delay and Request-rate directives are honored. HTTPS verification remains enabled; system proxy settings may apply.

The scan covers discoverable permitted pages within configured limits. It cannot guarantee finding every page: unlinked pages, JavaScript-generated links, logins, form submissions, and sitemap-only URLs are excluded. Images, scripts, stylesheets, mailto/tel links, and fragment-anchor existence are outside this version's checks. External websites are never recursively crawled. Use `--external` if you want the report to include checked outgoing links.

## Reports

```text
reports/
|-- report.json
`-- links.csv
```

JSON includes all results, source-page lists, statuses, final URLs, crawl notes, and the link-limit flag. CSV has one row per source-page/target pair, making broken links easy to locate. The starting URL has a blank source unless another page links to it. Files are overwritten on each completed scan; use different output folders to retain runs. Cancellation does not write a final report. Output stays local and is ignored by Git.

Exit 0 means no broken/unchecked results or crawl truncation were found within the selected scope. Skipped external links do not cause failure. Exit 1 means issues, incomplete coverage, cancellation, or a handled error; CLI syntax errors use 2. Always review reports for details.

## Common issues

- **Only one page checked**: verify the final www/HTTPS hostname, robots policy, and whether links require JavaScript.
- **401, 403, or 429**: authentication, bot restrictions, or rate limits prevent a reliable conclusion. These are unchecked results.
- **Network/TLS errors**: check DNS, connectivity, the system clock, and Python's trust store.
- **Incomplete scan**: raise limits carefully and examine robots restrictions and oversized-page notes.

## Project files

```text
Broken-Link-Checker/
|-- broken_link_checker.py
|-- README.md
|-- CHEAT.md
|-- PROMPT.md
`-- .gitignore
```

[CHEAT.md](CHEAT.md) explains the implementation. [PROMPT.md](PROMPT.md) contains recreation prompts.
