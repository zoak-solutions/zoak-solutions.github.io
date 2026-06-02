#!/usr/bin/env python3
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


ALLOWED_VENUES = {
    "Hazel",
    "Il Solito Posto",
    "Supernormal",
    "Tazio",
    "Rare Steakhouse",
}
VENUE_ORDER = [
    "Hazel",
    "Il Solito Posto",
    "Supernormal",
    "Tazio",
    "Rare Steakhouse",
]
MAX_BODY_BYTES = 16 * 1024
MAX_NAME_LENGTH = 80
MAX_NOTE_LENGTH = 500
DEFAULT_DB_PATH = "/data/lunch-votes.sqlite"


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


DB_PATH = os.environ.get("VOTE_DB_PATH", DEFAULT_DB_PATH)
IP_HASH_SALT = os.environ.get("VOTE_IP_HASH_SALT", "")
DUPLICATE_WINDOW_SECONDS = env_int("VOTE_DUPLICATE_WINDOW_SECONDS", 12 * 60 * 60)


def utc_now():
    return datetime.now(timezone.utc)


def isoformat_utc(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              venue TEXT NOT NULL,
              voter_name TEXT,
              dietary_note TEXT,
              comment TEXT,
              ip_hash TEXT,
              user_agent TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_created_at ON votes(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_venue ON votes(venue)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_ip_hash ON votes(ip_hash)")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def client_ip_from_headers(handler):
    forwarded_for = handler.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return handler.client_address[0]


def hash_ip(ip_address):
    if not ip_address:
        return ""
    digest = hashlib.sha256()
    digest.update(IP_HASH_SALT.encode("utf-8"))
    digest.update(b":")
    digest.update(ip_address.encode("utf-8"))
    return digest.hexdigest()


def clean_text(payload, key, max_length):
    value = payload.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{key} is too long.")
    return value


class LunchVoteHandler(BaseHTTPRequestHandler):
    server_version = "LunchVoteAPI/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({"ok": True})
            return
        if path == "/lunch-vote/results":
            self.handle_results()
            return
        self.send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/lunch-vote":
            self.handle_vote()
            return
        self.send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

    def handle_vote(self):
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            self.send_json({"ok": False, "error": "Expected application/json."}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json({"ok": False, "error": "Invalid request length."}, HTTPStatus.BAD_REQUEST)
            return

        if content_length > MAX_BODY_BYTES:
            self.send_json({"ok": False, "error": "Request body is too large."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json({"ok": False, "error": "Invalid JSON."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(payload, dict):
            self.send_json({"ok": False, "error": "Invalid JSON payload."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            venue = clean_text(payload, "venue", 120)
            name = clean_text(payload, "name", MAX_NAME_LENGTH)
            dietary = clean_text(payload, "dietary", MAX_NOTE_LENGTH)
            comment = clean_text(payload, "comment", MAX_NOTE_LENGTH)
            website = clean_text(payload, "website", MAX_NOTE_LENGTH)
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
            return

        if website:
            self.send_json({"ok": False, "error": "Invalid submission."}, HTTPStatus.BAD_REQUEST)
            return
        if venue not in ALLOWED_VENUES:
            self.send_json({"ok": False, "error": "Invalid venue."}, HTTPStatus.BAD_REQUEST)
            return

        ip_hash = hash_ip(client_ip_from_headers(self))
        user_agent = self.headers.get("User-Agent", "")[:500]
        created_at = isoformat_utc(utc_now())

        with connect_db() as conn:
            if ip_hash and DUPLICATE_WINDOW_SECONDS > 0:
                cutoff = isoformat_utc(utc_now() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS))
                duplicate = conn.execute(
                    """
                    SELECT 1
                    FROM votes
                    WHERE ip_hash = ? AND created_at >= ?
                    LIMIT 1
                    """,
                    (ip_hash, cutoff),
                ).fetchone()
                if duplicate:
                    self.send_json(
                        {
                            "ok": False,
                            "error": "A vote has already been recorded recently from this network.",
                        },
                        HTTPStatus.TOO_MANY_REQUESTS,
                    )
                    return

            conn.execute(
                """
                INSERT INTO votes (venue, voter_name, dietary_note, comment, ip_hash, user_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (venue, name, dietary, comment, ip_hash, user_agent, created_at),
            )

        self.send_json({"ok": True, "message": "Vote recorded."})

    def handle_results(self):
        with connect_db() as conn:
            rows = conn.execute(
                """
                SELECT venue, COUNT(*) AS votes
                FROM votes
                GROUP BY venue
                """
            ).fetchall()

        counts = {venue: 0 for venue in VENUE_ORDER}
        for row in rows:
            if row["venue"] in counts:
                counts[row["venue"]] = int(row["votes"])

        total = sum(counts.values())
        options = []
        for venue in VENUE_ORDER:
            votes = counts[venue]
            percentage = round((votes / total) * 100, 1) if total else 0
            options.append({"venue": venue, "votes": votes, "percentage": percentage})

        self.send_json({"total": total, "options": options})

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))


def main():
    init_db()
    host = os.environ.get("VOTE_API_HOST", "0.0.0.0")
    port = env_int("PORT", 8080)
    httpd = ThreadingHTTPServer((host, port), LunchVoteHandler)
    print(f"Listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
