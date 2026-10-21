"""Crawl a website and report broken HTTP/HTTPS hyperlinks and their source pages."""

import argparse
import csv
import json
import time
from collections import deque
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

AGENT = "Broken-Link-Checker/1.0"
MAX_BYTES = 5 * 1024 * 1024


def normalize(value):
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("URL contains whitespace or control characters.")
    p = urlsplit(value)
    if p.scheme.lower() not in ("http", "https") or not p.hostname:
        raise ValueError("Use an HTTP/HTTPS URL or hostname.")
    if p.username is not None or p.password is not None:
        raise ValueError("Embedded credentials are not supported.")
    port = p.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid port.")
    host = p.hostname.encode("idna").decode("ascii")
    host = f"[{host}]" if ":" in host else host
    scheme = p.scheme.lower()
    if port is not None and port != (443 if scheme == "https" else 80):
        host += f":{port}"
    return urlunsplit((scheme, host, p.path or "/", p.query, ""))


def origin(url):
    p = urlsplit(url)
    return p.scheme, p.netloc


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "base" and self.base is None:
            self.base = attrs.get("href")
        if tag in ("a", "area") and attrs.get("href"):
            self.hrefs.append(attrs["href"])


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    """Manual redirects allow scope, robots, and pacing checks on every hop."""
    def __init__(self, delay):
        self.delay = delay
        self.opener = build_opener(NoRedirects())
        self.policies = {}
        self.last = {}

    def open_once(self, url, interval):
        site = origin(url)
        time.sleep(max(0, interval - (time.monotonic() - self.last.get(site, 0))))
        self.last[site] = time.monotonic()
        try:
            return self.opener.open(Request(url, headers={"User-Agent": AGENT}), timeout=15)
        except HTTPError as error:
            return error

    def policy(self, url):
        site = origin(url)
        if site not in self.policies:
            robots = RobotFileParser()
            policy_url = urlunsplit((*site, "/robots.txt", "", ""))
            try:
                with self.open_once(policy_url, self.delay) as response:
                    if response.code in (404, 410):
                        robots.parse([])
                    elif response.code == 200:
                        data = response.read(MAX_BYTES + 1)
                        if len(data) > MAX_BYTES:
                            raise ValueError("robots.txt too large")
                        robots.parse(data.decode("utf-8", errors="replace").splitlines())
                    else:
                        raise ValueError(f"robots.txt HTTP {response.code} (redirects not followed)")
                interval = max(self.delay, robots.crawl_delay(AGENT) or 0)
                rate = robots.request_rate(AGENT)
                if rate and rate.requests > 0:
                    interval = max(interval, rate.seconds / rate.requests)
                self.policies[site] = (robots, interval, None)
            except (OSError, ValueError, HTTPException) as error:
                self.policies[site] = (None, self.delay, str(error))
        return self.policies[site]

    def fetch(self, url, site, external):
        current = url
        for hop in range(11):
            if origin(current) != site and not external:
                return {"result": "skipped", "detail": "external URL or redirect", "final_url": current}, None
            robots, interval, error = self.policy(current)
            if error or not robots.can_fetch(AGENT, current):
                return {"result": "unchecked", "detail": error or "robots-disallowed", "final_url": current}, None
            with self.open_once(current, interval) as response:
                status = response.code
                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        return {"result": "broken", "status": status, "detail": "redirect missing Location"}, None
                    current = normalize(urljoin(current, location))
                    continue
                result = {"status": status, "final_url": current,
                          "result": "ok" if 200 <= status < 300 else
                                    "unchecked" if status in (401, 403, 429) else "broken"}
                if result["result"] != "ok":
                    result["detail"] = str(response.reason)
                    return result, None
                # External links are checked but never parsed or crawled.
                if origin(current) != site or response.headers.get_content_type() not in ("text/html", "application/xhtml+xml"):
                    return result, None
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    result["crawl_note"] = "HTML exceeds 5 MiB; links not parsed"
                    return result, None
                encoding = response.headers.get_content_charset() or "utf-8"
                try:
                    text = data.decode(encoding, errors="replace")
                except LookupError:
                    text = data.decode("utf-8", errors="replace")
                return result, text
        return {"result": "broken", "detail": "redirect limit exceeded", "final_url": current}, None


def scan(start, output="reports", max_pages=100, max_links=2000, delay=1, external=False):
    start = normalize(start)
    site = origin(start)
    client = Client(delay)
    queue = deque([start])
    sources = {start: set()}
    results = {}
    pages = 0
    truncated = False
    while queue:
        url = queue.popleft()
        internal = origin(url) == site
        if internal and pages >= max_pages:
            results[url] = {"result": "unchecked", "detail": "page/URL request limit"}
            continue
        if internal:
            pages += 1
        print(f"Checking: {url}")
        try:
            result, text = client.fetch(url, site, external)
        except (OSError, ValueError, HTTPException) as error:
            result, text = {"result": "unchecked", "detail": str(error)}, None
        results[url] = result
        if text is None:
            continue
        parser = Links()
        parser.feed(text)
        final = result.get("final_url", url)
        base = urljoin(final, parser.base) if parser.base else final
        for href in parser.hrefs:
            try:
                target = urljoin(base, href)
                if urlsplit(target).scheme.lower() not in ("http", "https"):
                    continue
                target = normalize(target)
            except ValueError:
                continue
            if target not in sources:
                if len(sources) >= max_links:
                    truncated = True
                    continue
                sources[target] = set()
                queue.append(target)
            sources[target].add(final)
    records = [{"url": url, **result, "source_pages": sorted(sources[url])}
               for url, result in results.items()]
    report = {"start_url": start, "internal_attempts": pages,
              "link_limit_reached": truncated, "records": records}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (output / "links.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_page", "url", "result", "status", "final_url", "detail"])
        for row in records:
            for source in row["source_pages"] or [""]:
                writer.writerow([source, row["url"], row["result"], row.get("status", ""),
                                 row.get("final_url", ""), row.get("detail", "")])
    for category in ("ok", "broken", "unchecked", "skipped"):
        print(f"{category.title()}: {sum(r['result'] == category for r in records)}")
    print(f"Reports: {output.resolve()}")
    if truncated:
        print("Link discovery limit reached; increase --max-links for more coverage.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("website", nargs="?")
    parser.add_argument("--output", default="reports")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-links", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=1)
    parser.add_argument("--external", action="store_true", help="Also check external targets without crawling them")
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_links < 1 or not 0 <= args.delay < float("inf"):
        parser.error("Limits must be positive; delay must be finite and non-negative.")
    try:
        start = args.website if args.website is not None else input("Website: ")
        report = scan(start, args.output, args.max_pages, args.max_links, args.delay, args.external)
        incomplete = report["link_limit_reached"] or any(
            r["result"] in ("broken", "unchecked") or r.get("crawl_note") for r in report["records"])
        return 1 if incomplete else 0
    except (OSError, ValueError, HTTPException) as error:
        print(f"Scan failed: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled; final reports were not written.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
