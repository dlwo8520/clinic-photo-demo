#!/usr/bin/env python3
"""Exercise a deployed fictional clinic demo over verified HTTPS, without Django.

This is an HTTP acceptance check. It does not automate a browser or iPhone Safari.
Passwords and upload-session tokens are never written to the evidence file.
"""

import argparse
import collections
import datetime as dt
import getpass
import hashlib
import html.parser
import http.cookiejar
import json
import os
from pathlib import Path
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib


class VerificationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def origin(url):
    parsed = urllib.parse.urlsplit(url)
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise VerificationError("Invalid server port.") from exc
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def validate_base_url(value, allow_local):
    parsed = urllib.parse.urlsplit(value)
    require(parsed.hostname and not parsed.username and not parsed.password,
            "Use a server URL without embedded credentials.")
    require(not parsed.query and not parsed.fragment and parsed.path in ("", "/"),
            "Use the server origin only, without a path, query, or fragment.")
    local_http = (allow_local and parsed.scheme == "http" and
                  parsed.hostname in ("127.0.0.1", "localhost", "::1"))
    require(parsed.scheme == "https" or local_http,
            "HTTPS is required. --allow-local permits HTTP loopback QA only.")
    origin(value)
    return value.rstrip("/")


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, expected_origin):
        super().__init__()
        self.expected_origin = expected_origin

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        require(origin(newurl) == self.expected_origin,
                "Refused a redirect to another origin.")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class ClinicHTML(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.csrf = None
        self.has_password = False
        self.has_demo = False
        self.rows = []
        self.compare_json = ""
        self._row = None
        self._cell = None
        self._script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and attrs.get("name") == "demo" and attrs.get("value") == "staff":
            self.has_demo = True
        if tag == "input":
            if attrs.get("name") == "csrfmiddlewaretoken":
                self.csrf = attrs.get("value")
            if attrs.get("name") == "password":
                self.has_password = True
        elif tag == "tr":
            self._row = {"cells": [], "id": None}
        elif tag == "td" and self._row is not None:
            self._cell = []
        elif tag == "a" and self._row is not None:
            match = re.fullmatch(r"/patients/(\d+)/", attrs.get("href", ""))
            if match:
                self._row["id"] = int(match.group(1))
        elif tag == "script" and attrs.get("id") == "compare-data":
            self._script = True

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        if self._script:
            self.compare_json += data

    def handle_endtag(self, tag):
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row["cells"].append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            cells = self._row["cells"]
            if self._row["id"] and len(cells) >= 4:
                self.rows.append({"id": self._row["id"], "name": cells[0],
                                  "chart_number": cells[1], "last_visit": cells[2],
                                  "visit_count": cells[3]})
            self._row = None
            self._cell = None
        elif tag == "script":
            self._script = False


def parse_html(body):
    page = ClinicHTML()
    page.feed(body.decode("utf-8"))
    return page


class Client:
    def __init__(self, base_url):
        self.base_url = base_url
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
            SameOriginRedirect(origin(base_url)),
        )

    def url(self, path):
        url = urllib.parse.urljoin(self.base_url + "/", path)
        require(origin(url) == origin(self.base_url), "Refused a request to another origin.")
        return url

    def csrf(self):
        tokens = [cookie.value for cookie in self.cookies if cookie.name == "csrftoken"]
        require(tokens, "CSRF cookie was not returned by the server.")
        return tokens[-1]

    def request(self, path, *, method="GET", body=None, content_type=None,
                anonymous=False, follow=True):
        headers = {"User-Agent": "ClinicDemoAcceptance/1.0", "Accept": "*/*"}
        if method != "GET":
            headers.update({"Referer": self.base_url + "/", "Origin": self.base_url,
                            "X-CSRFToken": self.csrf()})
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.url(path), data=body, method=method, headers=headers)
        if anonymous:
            handlers = [SameOriginRedirect(origin(self.base_url))] if follow else [NoRedirect()]
            opener = urllib.request.build_opener(*handlers)
        else:
            opener = self.opener
        try:
            with opener.open(request, timeout=60) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Do not print exception URLs: an upload URL contains a secret token.
            raise VerificationError("HTTP connection failed; check the host, TLS certificate, and network.") from exc

    def html(self, path):
        status, body, _ = self.request(path)
        require(status == 200, f"HTML request returned HTTP {status}.")
        return parse_html(body), body

    def json(self, path, *, data=None, body=None, content_type=None):
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            content_type = "application/json"
        method = "POST" if body is not None else "GET"
        status, response, _ = self.request(path, method=method, body=body, content_type=content_type)
        require(200 <= status < 300, f"API request returned HTTP {status}.")
        try:
            return json.loads(response)
        except (ValueError, UnicodeDecodeError) as exc:
            raise VerificationError("API returned invalid JSON; check authentication and server logs.") from exc

    def login(self, username, password=None):
        page, _ = self.html("/login/?next=/patients/")
        require(page.csrf, "Login form did not contain a CSRF token.")
        fields = {"csrfmiddlewaretoken": page.csrf, "next": "/patients/"}
        if page.has_demo:
            fields["demo"] = "staff"
        else:
            password = password or getpass.getpass("Demo staff password: ")
            require(password, "A password is required.")
            fields.update(username=username, password=password)
        payload = urllib.parse.urlencode(fields).encode("utf-8")
        status, body, _ = self.request("/login/", method="POST", body=payload,
                                       content_type="application/x-www-form-urlencoded")
        require(status == 200 and not parse_html(body).has_password and not parse_html(body).has_demo,
                "Staff login failed. Check the demo account and authentication mode.")


def image_bytes(index):
    """Make a labeled fictional 320x240 PNG using only the standard library."""
    width, height = 320, 240
    pixels = bytearray([235, 242, 238] * width * height)

    def rect(x, y, w, h, color):
        for yy in range(y, min(height, y + h)):
            for xx in range(x, min(width, x + w)):
                offset = (yy * width + xx) * 3
                pixels[offset:offset + 3] = bytes(color)

    rect(18, 18, 284, 204, (17, 91 + index * 5, 82))
    glyphs = {
        "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
        "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
        "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
        "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
        "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
        "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
        "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
        "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
        " ": ("00000",) * 7,
    }
    for letter_index, letter in enumerate(f"DEMO {index}"):
        for y, row in enumerate(glyphs[letter]):
            for x, pixel in enumerate(row):
                if pixel == "1":
                    rect(56 + letter_index * 36 + x * 6, 98 + y * 6, 6, 6, (255, 255, 255))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    scanlines = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))


def multipart(items):
    boundary = "ClinicAcceptance" + uuid.uuid4().hex
    parts = []
    for item in items:
        for key, value in (("client_ids", item["client_id"]), ("body_sites", "가상 검증 사진")):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode("utf-8"))
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="photos"; '
                      f'filename="fictional-check-{item["index"]}.png"\r\nContent-Type: image/png\r\n\r\n').encode("ascii"))
        parts.append(item["data"] + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def photo_list(client, visit_id):
    data = client.json(f"/api/visits/{visit_id}/photos/")
    require(int(data.get("visit_id", -1)) == int(visit_id), "Photo API returned another visit.")
    photos = data.get("photos", [])
    require(data.get("photo_count") == len(photos), "Photo count does not match the list.")
    return photos


def photo_snapshot(client, photo):
    result = {"id": photo["id"], "url": photo["url"], "thumbnail_url": photo["thumbnail_url"]}
    for field, digest_key in (("url", "sha256"), ("thumbnail_url", "thumbnail_sha256")):
        status, body, headers = client.request(photo[field])
        require(status == 200 and headers.get_content_type().startswith("image/") and body,
                "An authenticated photo or thumbnail could not be read.")
        result[digest_key] = hashlib.sha256(body).hexdigest()
    return result


def visit_snapshot(client, visit):
    photos = photo_list(client, visit["id"])
    return {"id": visit["id"], "week": visit["week"], "photo_count": len(photos),
            "photos": [photo_snapshot(client, photo) for photo in photos]}


def check_initial(client, args):
    search = "/patients/?" + urllib.parse.urlencode({"q": args.patient_chart})
    page, _ = client.html(search)
    matches = [row for row in page.rows if row["chart_number"] == args.patient_chart]
    require(len(matches) == 1, "The representative chart search did not return exactly one patient.")
    patient = matches[0]
    partial = patient["name"][:-1] or patient["name"]
    partial_page, _ = client.html("/patients/?" + urllib.parse.urlencode({"q": partial}))
    require(any(row["id"] == patient["id"] for row in partial_page.rows),
            "Partial-name search did not return the representative patient.")
    namesakes, _ = client.html("/patients/?" + urllib.parse.urlencode({"q": args.namesake_query}))
    groups = collections.defaultdict(set)
    for row in namesakes.rows:
        groups[row["name"]].add(row["chart_number"])
    require(any(len(charts) >= 2 for charts in groups.values()),
            "Namesake search did not show matching names with distinct chart numbers.")
    compare, _ = client.html(f'/patients/{patient["id"]}/')
    require(compare.compare_json, "Comparison page did not contain its visit/photo data.")
    try:
        data = json.loads(compare.compare_json)
    except ValueError as exc:
        raise VerificationError("Comparison data was not valid JSON.") from exc
    visits = data.get("visits", [])
    selected = {}
    for week, minimum in ((1, 4), (2, 5), (3, 0)):
        candidates = [visit for visit in visits if visit.get("week") == week]
        require(candidates, f"Representative week {week} is missing.")
        selected[week] = max(candidates, key=lambda visit: (visit["visited_on"], visit["id"]))
        actual = photo_list(client, selected[week]["id"])
        require(len(actual) >= minimum, f"Week {week} has fewer than {minimum} photos.")
    sample = photo_list(client, selected[1]["id"])[0]
    photo_snapshot(client, sample)
    for field in ("url", "thumbnail_url"):
        status, _, _ = client.request(sample[field], anonymous=True, follow=False)
        require(status in (301, 302, 303, 307, 308, 401, 403, 404),
                "An unauthenticated request could access a private photo or thumbnail.")
    return patient, selected


def check_upload(client, selected):
    visit = selected[3]
    before = photo_list(client, visit["id"])
    baseline_ids = {photo["id"] for photo in before}
    session = client.json(f'/api/visits/{visit["id"]}/upload-sessions/', body=b"")
    upload_url = session.get("url", "")
    require(origin(upload_url) == origin(client.base_url), "QR URL does not use the deployed server origin.")
    require(urllib.parse.urlsplit(upload_url).scheme == urllib.parse.urlsplit(client.base_url).scheme,
            "QR URL does not use the expected HTTPS scheme.")
    token_match = re.fullmatch(r"/upload/([^/]+)/", urllib.parse.urlsplit(upload_url).path)
    require(token_match, "QR URL does not match the supported upload route.")
    token = token_match.group(1)
    mobile, mobile_body = client.html(upload_url)
    require(mobile.csrf and 'id="library-input"' in mobile_body.decode("utf-8"),
            "The authenticated mobile upload form is incomplete.")
    status, qr_bytes, headers = client.request(session["qr_url"])
    require(status == 200 and headers.get_content_type() == "image/png" and qr_bytes.startswith(b"\x89PNG"),
            "QR image could not be loaded through the authenticated route.")
    items = [{"index": index, "client_id": str(uuid.uuid4()), "data": image_bytes(index)} for index in range(1, 5)]

    def send(batch):
        body, content_type = multipart(batch)
        result = client.json(f"/api/uploads/{token}/photos/", body=body, content_type=content_type)
        rows = result.get("results", [])
        require(len(rows) == len(batch), "Upload did not return one result per photo.")
        by_id = {row.get("client_id"): row for row in rows}
        require(set(by_id) == {item["client_id"] for item in batch}, "Upload result request IDs do not match.")
        return by_id

    first = send(items[:3])
    require(all(row.get("status") == "saved" for row in first.values()), "One of the three initial uploads failed.")
    after_three = photo_list(client, visit["id"])
    require(len(after_three) == len(before) + 3 and baseline_ids <= {p["id"] for p in after_three},
            "The three-photo upload did not preserve the baseline and add exactly three photos.")
    fourth = send(items[3:])
    require(fourth[items[3]["client_id"]].get("status") == "saved", "The additional photo upload failed.")
    after_four = photo_list(client, visit["id"])
    uploaded_ids = [first[item["client_id"]]["photo"]["id"] for item in items[:3]]
    uploaded_ids.append(fourth[items[3]["client_id"]]["photo"]["id"])
    require(len(after_four) == len(before) + 4 and baseline_ids <= {p["id"] for p in after_four},
            "The additional upload did not preserve existing photos and add exactly one photo.")
    require(after_four[-1]["id"] == uploaded_ids[-1], "The final photo is not last in the current visit list.")
    replay = send(items[3:])
    require(replay[items[3]["client_id"]].get("status") == "duplicate" and
            replay[items[3]["client_id"]]["photo"]["id"] == uploaded_ids[-1],
            "Replaying a stored request did not return the original photo as duplicate.")
    final = photo_list(client, visit["id"])
    require([p["id"] for p in final] == [p["id"] for p in after_four], "Replay changed the photo list.")
    return {"performed": True, "visit_id": visit["id"], "week": 3,
            "baseline_photo_ids": sorted(baseline_ids), "baseline_count": len(before),
            "after_three_count": len(after_three), "after_four_count": len(after_four),
            "uploaded_photo_ids": uploaded_ids, "request_ids": [item["client_id"] for item in items],
            "replay_duplicate": True, "qr_uses_expected_origin": True,
            "qr_image_sha256": hashlib.sha256(qr_bytes).hexdigest()}


def restart_check(client, previous):
    require(previous.get("schema_version") == 1 and previous.get("visits"), "Unsupported or empty evidence file.")
    require(origin(previous.get("base_url", "")) == origin(client.base_url),
            "Restart evidence belongs to another server origin.")
    verified = []
    for visit in previous["visits"]:
        current = {photo["id"]: photo for photo in photo_list(client, visit["id"])}
        for stored in visit["photos"]:
            require(stored["id"] in current, "A previously recorded photo is missing after restart.")
            actual = photo_snapshot(client, current[stored["id"]])
            require(actual["sha256"] == stored["sha256"] and
                    actual["thumbnail_sha256"] == stored["thumbnail_sha256"],
                    "A previously recorded image or thumbnail changed after restart.")
            verified.append(stored["id"])
    return {"verified_at": timestamp(), "photo_ids": verified,
            "photo_and_thumbnail_sha256_unchanged": True,
            "limitation": "HTTP evidence confirms persistence; the script cannot itself prove that a restart occurred."}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Deployed HTTPS origin, e.g. https://clinic-demo.onrender.com")
    parser.add_argument("--username", default="dlwo8520")
    parser.add_argument("--patient-chart", default="DEMO-1001")
    parser.add_argument("--namesake-query", default="김하")
    parser.add_argument("--upload", action="store_true", help="Explicitly add fictional photos (3 then 1) to the representative week-3 visit")
    parser.add_argument("--check-restart", type=Path, metavar="EVIDENCE_JSON", help="Verify stored IDs/hashes in the same active instance (not a Free instance restart)")
    parser.add_argument("--check-reset", action="store_true", help="After a Free instance replacement, verify week 1=4, week 2=5, week 3=0")
    parser.add_argument("--output", type=Path, default=Path("artifacts/public-verification.json"))
    parser.add_argument("--allow-local", action="store_true", help="Allow HTTP only on localhost/127.0.0.1/::1 for local QA")
    args = parser.parse_args()
    require(not (args.upload and args.check_restart), "Use --upload and --check-restart as separate runs.")
    require(not (args.check_reset and (args.upload or args.check_restart)), "Use --check-reset separately.")
    args.base_url = validate_base_url(args.base_url, args.allow_local)
    return args


def main():
    try:
        args = arguments()
        password = os.environ.get("CLINIC_DEMO_PASSWORD")
        client = Client(args.base_url)
        client.login(args.username, password)
        del password
        if args.check_restart:
            previous = json.loads(args.check_restart.read_text(encoding="utf-8"))
            evidence = dict(previous)
            evidence["restart_verification"] = restart_check(client, previous)
        else:
            patient, selected = check_initial(client, args)
            if args.check_reset:
                for week, expected in ((1, 4), (2, 5), (3, 0)):
                    require(len(photo_list(client, selected[week]["id"])) == expected,
                            f"Free demo week {week} did not reset to {expected} sample photos.")
            original_visits = [visit_snapshot(client, selected[week]) for week in (1, 2)]
            upload = check_upload(client, selected) if args.upload else {"performed": False}
            if args.upload:
                after_originals = [visit_snapshot(client, selected[week]) for week in (1, 2)]
                require(after_originals == original_visits, "Week-1 or week-2 photos changed during the week-3 upload.")
                upload["week1_and_week2_unchanged"] = True
            evidence = {"schema_version": 1, "verified_at": timestamp(), "base_url": args.base_url,
                        "transport": "HTTPS with certificate verification" if args.base_url.startswith("https:") else "HTTP loopback QA only",
                        "patient_chart": args.patient_chart, "patient_id": patient["id"],
                        "checks": {"staff_login": True, "partial_name_search": True,
                                   "chart_search": True, "namesake_chart_distinction": True,
                                   "week1_at_least_four": True, "week2_at_least_five": True,
                                   "authenticated_photo_and_thumbnail": True,
                                   "anonymous_photo_and_thumbnail_blocked": True},
                        "upload": upload,
                        "free_sample_reset_verified": args.check_reset,
                        "visits": original_visits + [visit_snapshot(client, selected[3])],
                        "manual_checks_required": [
                            "PC browser: select week 3, upload from another session, confirm thumbnails/count and last large photo update without page reload.",
                            "iPhone Safari: scan QR, log in and return to this visit, test camera and multiple library selection, preview/removal and partial retry.",
                            "Same active server: use --check-restart to re-fetch stored hashes; after Free instance replacement use --check-reset for baseline samples.",
                        ]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: HTTP acceptance evidence written to {args.output}")
        if args.check_restart:
            print("Previously recorded photo IDs and image/thumbnail SHA-256 values remain available.")
        elif args.upload:
            upload = evidence["upload"]
            print(f'Week 3: {upload["baseline_count"]} -> {upload["after_three_count"]} -> {upload["after_four_count"]} photos; request replay did not duplicate.')
        print("PC live-refresh behavior and real iPhone Safari still require manual checks.")
        return 0
    except (VerificationError, ValueError, KeyError, OSError) as exc:
        # Internal errors below contain only controlled messages, never passwords or tokens.
        if isinstance(exc, VerificationError):
            print(f"FAIL: {exc}", file=sys.stderr)
        else:
            print(f"FAIL: Cannot read/write evidence or unexpected response shape ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
