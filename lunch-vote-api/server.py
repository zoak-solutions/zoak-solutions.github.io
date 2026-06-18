#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sqlite3
import struct
import zlib
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse


MAX_BODY_BYTES = 16 * 1024
MAX_NAME_LENGTH = 80
MAX_NOTE_LENGTH = 500
MAX_TOKEN_LENGTH = 128
DEFAULT_DB_PATH = "/data/lunch-votes.sqlite"
TOKEN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
DEFAULT_POLL_SLUG = "lunch-vote"
DEFAULT_POLL_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "polls"))
RESULTS_CARD_WIDTH = 700
RESULTS_CARD_HEIGHT = 360
FONT_5X7 = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    ".": ["000", "000", "000", "000", "000", "110", "110"],
    "%": ["10001", "00010", "00100", "01000", "10001", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ":": ["000", "110", "110", "000", "110", "110", "000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


DB_PATH = os.environ.get("VOTE_DB_PATH", DEFAULT_DB_PATH)
IP_HASH_SALT = os.environ.get("VOTE_IP_HASH_SALT", "")
TOKEN_HASH_SALT = os.environ.get("VOTE_TOKEN_HASH_SALT", IP_HASH_SALT)
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
POLL_CONFIG_DIR = os.environ.get("POLL_CONFIG_DIR", DEFAULT_POLL_CONFIG_DIR)
POLL_CONFIGS = {}


def utc_now():
    return datetime.now(timezone.utc)


def isoformat_utc(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_yaml_scalar(value):
    value = value.strip()
    if not value:
        return ""
    if value in ("null", "Null", "NULL", "~"):
        return None
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def strip_yaml_comment(line):
    quote_char = ""
    for index, character in enumerate(line):
        if character in ("'", '"'):
            quote_char = "" if quote_char == character else character
        if character == "#" and not quote_char:
            return line[:index]
    return line


def parse_poll_yaml(path):
    data = {}
    candidates = None
    current_candidate = None
    current_tags = None
    current_tag = None

    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = strip_yaml_comment(raw_line.rstrip("\n"))
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            text = line.strip()

            if indent == 0:
                key, _, value = text.partition(":")
                key = key.strip()
                if key == "candidates":
                    candidates = []
                    data["candidates"] = candidates
                else:
                    data[key] = parse_yaml_scalar(value)
                current_candidate = None
                current_tags = None
                current_tag = None
                continue

            if candidates is not None and indent == 2 and text.startswith("- "):
                current_candidate = {}
                candidates.append(current_candidate)
                current_tags = None
                current_tag = None
                remainder = text[2:].strip()
                if remainder:
                    key, _, value = remainder.partition(":")
                    current_candidate[key.strip()] = parse_yaml_scalar(value)
                continue

            if current_candidate is not None and indent == 4:
                key, _, value = text.partition(":")
                key = key.strip()
                if key == "tags":
                    current_tags = []
                    current_candidate["tags"] = current_tags
                else:
                    current_candidate[key] = parse_yaml_scalar(value)
                current_tag = None
                continue

            if current_tags is not None and indent == 6 and text.startswith("- "):
                current_tag = {}
                current_tags.append(current_tag)
                remainder = text[2:].strip()
                if remainder:
                    key, _, value = remainder.partition(":")
                    current_tag[key.strip()] = parse_yaml_scalar(value)
                continue

            if current_tag is not None and indent == 8:
                key, _, value = text.partition(":")
                current_tag[key.strip()] = parse_yaml_scalar(value)
                continue

            raise ValueError(f"Unsupported YAML shape in {path}: {raw_line.rstrip()}")

    return data


def parse_close_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid closeTime {value!r}; use an ISO-8601 timestamp.") from error


def normalize_candidate(candidate):
    required = ("name", "details", "slug", "img")
    missing = [key for key in required if not candidate.get(key)]
    if missing:
        raise ValueError(f"Poll candidate missing required field(s): {', '.join(missing)}")
    tags = []
    for tag in candidate.get("tags") or []:
        key = str(tag.get("key", "")).strip()
        value = str(tag.get("val", "")).strip()
        if key or value:
            tags.append({"key": key, "val": value})
    return {
        "name": str(candidate["name"]).strip(),
        "details": str(candidate["details"]).strip(),
        "slug": str(candidate["slug"]).strip(),
        "img": str(candidate["img"]).strip(),
        "tags": tags,
        "informationUrl": str(candidate.get("informationUrl") or candidate.get("informaionUrl") or "").strip(),
    }


def normalize_poll_config(raw_config, path):
    title = raw_config.get("PollTitle")
    description = raw_config.get("PollDescription")
    slug = raw_config.get("PollSlug") or raw_config.get("PullSlug")
    if not title or not description or not slug:
        raise ValueError(f"{path} must define PollTitle, PollDescription, and PollSlug.")
    candidates = [normalize_candidate(candidate) for candidate in raw_config.get("candidates") or []]
    if not candidates:
        raise ValueError(f"{path} must define at least one candidate.")
    slugs = [candidate["slug"] for candidate in candidates]
    if len(slugs) != len(set(slugs)):
        raise ValueError(f"{path} contains duplicate candidate slugs.")

    close_time = parse_close_time(raw_config.get("closeTime"))
    return {
        "PollTitle": str(title).strip(),
        "PollDescription": str(description).strip(),
        "PollSlug": str(slug).strip(),
        "closeTime": isoformat_utc(close_time) if close_time else None,
        "closeTimeValue": close_time,
        "candidates": candidates,
    }


def load_poll_configs():
    configs = {}
    if not os.path.isdir(POLL_CONFIG_DIR):
        raise RuntimeError(f"Poll config directory does not exist: {POLL_CONFIG_DIR}")
    for filename in sorted(os.listdir(POLL_CONFIG_DIR)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(POLL_CONFIG_DIR, filename)
        config = normalize_poll_config(parse_poll_yaml(path), path)
        configs[config["PollSlug"]] = config
    if not configs:
        raise RuntimeError(f"No poll configs found in {POLL_CONFIG_DIR}")
    return configs


def poll_config(poll_slug):
    config = POLL_CONFIGS.get(poll_slug)
    if not config:
        raise KeyError(poll_slug)
    return config


def poll_is_closed(config):
    close_time = config.get("closeTimeValue")
    if not close_time:
        return False
    now = utc_now()
    if close_time.tzinfo is None:
        now = now.replace(tzinfo=None)
    return now >= close_time


def public_poll_config(config):
    return {
        "PollTitle": config["PollTitle"],
        "PollDescription": config["PollDescription"],
        "PollSlug": config["PollSlug"],
        "closeTime": config["closeTime"],
        "isClosed": poll_is_closed(config),
        "candidates": config["candidates"],
    }


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              poll_slug TEXT,
              candidate_slug TEXT,
              venue TEXT NOT NULL,
              voter_name TEXT,
              dietary_note TEXT,
              comment TEXT,
              vote_token_hash TEXT,
              vote_key_hash TEXT,
              ip_hash TEXT,
              user_agent TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(votes)").fetchall()}
        if "poll_slug" not in columns:
            conn.execute("ALTER TABLE votes ADD COLUMN poll_slug TEXT")
        if "candidate_slug" not in columns:
            conn.execute("ALTER TABLE votes ADD COLUMN candidate_slug TEXT")
        if "vote_token_hash" not in columns:
            conn.execute("ALTER TABLE votes ADD COLUMN vote_token_hash TEXT")
        if "vote_key_hash" not in columns:
            conn.execute("ALTER TABLE votes ADD COLUMN vote_key_hash TEXT")
        if "updated_at" not in columns:
            conn.execute("ALTER TABLE votes ADD COLUMN updated_at TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vote_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              poll_slug TEXT,
              token_hash TEXT NOT NULL UNIQUE,
              recipient_label TEXT,
              recipient_email_hash TEXT,
              created_at TEXT NOT NULL,
              used_at TEXT,
              updated_at TEXT,
              used_vote_id INTEGER,
              FOREIGN KEY (used_vote_id) REFERENCES votes(id)
            )
            """
        )
        token_columns = {row[1] for row in conn.execute("PRAGMA table_info(vote_tokens)").fetchall()}
        if "poll_slug" not in token_columns:
            conn.execute("ALTER TABLE vote_tokens ADD COLUMN poll_slug TEXT")
        if "updated_at" not in token_columns:
            conn.execute("ALTER TABLE vote_tokens ADD COLUMN updated_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_created_at ON votes(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll_slug ON votes(poll_slug)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_candidate_slug ON votes(candidate_slug)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_venue ON votes(venue)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_vote_token_hash ON votes(vote_token_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_vote_key_hash ON votes(vote_key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_ip_hash ON votes(ip_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_tokens_poll_slug ON vote_tokens(poll_slug)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vote_tokens_used_at ON vote_tokens(used_at)")


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


def hash_vote_token(token):
    if not token:
        return ""
    digest = hashlib.sha256()
    digest.update(TOKEN_HASH_SALT.encode("utf-8"))
    digest.update(b":vote-token:")
    digest.update(token.encode("utf-8"))
    return digest.hexdigest()


def hash_recipient_email(email):
    value = (email or "").strip().lower()
    if not value:
        return ""
    digest = hashlib.sha256()
    digest.update(TOKEN_HASH_SALT.encode("utf-8"))
    digest.update(b":recipient-email:")
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def is_valid_vote_token(value):
    return 24 <= len(value) <= MAX_TOKEN_LENGTH and all(character in TOKEN_CHARS for character in value)


def vote_results(config):
    with connect_db() as conn:
        rows = conn.execute(
            """
            SELECT candidate_slug, COUNT(*) AS votes
            FROM votes
            WHERE poll_slug = ?
            GROUP BY candidate_slug
            """,
            (config["PollSlug"],),
        ).fetchall()

    counts = {candidate["slug"]: 0 for candidate in config["candidates"]}
    for row in rows:
        if row["candidate_slug"] in counts:
            counts[row["candidate_slug"]] = int(row["votes"])

    total = sum(counts.values())
    options = []
    for candidate in config["candidates"]:
        votes = counts[candidate["slug"]]
        percentage = round((votes / total) * 100, 1) if total else 0
        options.append({
            "name": candidate["name"],
            "slug": candidate["slug"],
            "venue": candidate["name"],
            "votes": votes,
            "percentage": percentage,
        })
    return {
        "poll": public_poll_config(config),
        "total": total,
        "options": options,
    }


def rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


class PngCanvas:
    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = [[background for _ in range(width)] for _ in range(height)]

    def rect(self, x, y, width, height, color):
        left = max(0, int(x))
        top = max(0, int(y))
        right = min(self.width, int(x + width))
        bottom = min(self.height, int(y + height))
        for row in range(top, bottom):
            self.pixels[row][left:right] = [color] * max(0, right - left)

    def text_width(self, text, scale):
        width = 0
        for character in text.upper():
            pattern = FONT_5X7.get(character, FONT_5X7[" "])
            width += (len(pattern[0]) + 1) * scale
        return max(0, width - scale)

    def text(self, x, y, text, color, scale=2):
        cursor = int(x)
        for character in text.upper():
            pattern = FONT_5X7.get(character, FONT_5X7[" "])
            for row_index, row in enumerate(pattern):
                for col_index, value in enumerate(row):
                    if value == "1":
                        self.rect(cursor + col_index * scale, y + row_index * scale, scale, scale, color)
            cursor += (len(pattern[0]) + 1) * scale

    def png_bytes(self):
        raw_rows = []
        for row in self.pixels:
            raw_rows.append(b"\x00" + b"".join(bytes(pixel) for pixel in row))
        raw = b"".join(raw_rows)
        return (
            b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack("!IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(raw, 9))
            + png_chunk(b"IEND", b"")
        )


def png_chunk(kind, data):
    return (
        struct.pack("!I", len(data))
        + kind
        + data
        + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def render_results_card(results):
    colors = {
        "background": rgb("#F7F3EA"),
        "ink": rgb("#111111"),
        "muted": rgb("#5A5A5A"),
        "line": rgb("#D8D1C3"),
        "track": rgb("#E7DFD1"),
        "gold": rgb("#F1B51C"),
        "amber": rgb("#D98918"),
        "green": rgb("#1D8F5C"),
    }
    canvas = PngCanvas(RESULTS_CARD_WIDTH, RESULTS_CARD_HEIGHT, colors["background"])
    canvas.rect(0, 0, RESULTS_CARD_WIDTH, 8, colors["gold"])
    title = results.get("poll", {}).get("PollTitle", "Poll Vote")[:22]
    canvas.text(36, 34, title, colors["ink"], 3)
    canvas.text(36, 74, f"LIVE RESULTS - {results['total']} TOTAL VOTES", colors["muted"], 2)
    canvas.rect(36, 102, 628, 2, colors["line"])

    top = 124
    bar_x = 290
    bar_width = 260
    row_height = 40
    max_votes = max([option["votes"] for option in results["options"]] + [1])
    for index, option in enumerate(results["options"]):
        y = top + index * row_height
        votes = int(option["votes"])
        percentage = float(option["percentage"])
        filled = int(round((votes / max_votes) * bar_width)) if max_votes else 0
        label = option["name"][:22]
        count = f"{votes} VOTE{'S' if votes != 1 else ''} - {percentage:.1f}%"
        fill_color = colors["green"] if votes else colors["line"]

        canvas.text(36, y, label, colors["ink"], 2)
        canvas.rect(bar_x, y + 2, bar_width, 14, colors["track"])
        canvas.rect(bar_x, y + 2, max(2 if votes else 0, filled), 14, fill_color)
        canvas.text(568, y, count, colors["muted"], 1)

    canvas.rect(36, 326, 628, 1, colors["line"])
    canvas.text(36, 338, "OPEN THE POLL PAGE FOR FULL DETAILS", colors["muted"], 1)
    return canvas.png_bytes()


def public_base_url(handler):
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    proto = handler.headers.get("X-Forwarded-Proto", "http").split(",", 1)[0].strip() or "http"
    host = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host") or "localhost"
    return f"{proto}://{host}".rstrip("/")


def results_embed_html(handler, config):
    base_url = public_base_url(handler)
    poll_slug = config["PollSlug"]
    image_url = f"{base_url}/api/poll-vote/{poll_slug}/results-card.png"
    live_url = f"{base_url}/lunch-vote/"
    if poll_slug != DEFAULT_POLL_SLUG:
        live_url = f"{live_url}?poll={quote(poll_slug, safe='')}"
    escaped_image = quote(image_url, safe=":/?&=%.-_")
    escaped_live = quote(live_url, safe=":/?&=%.-_")
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;max-width:700px;font-family:Arial,sans-serif;">
  <tr>
    <td style="padding:0;">
      <a href="{escaped_live}" style="text-decoration:none;">
        <img src="{escaped_image}" width="700" height="360" alt="Live ZOAK poll results" style="display:block;width:100%;max-width:700px;height:auto;border:0;outline:none;text-decoration:none;" />
      </a>
    </td>
  </tr>
  <tr>
    <td style="padding:10px 0 0 0;font-size:13px;line-height:18px;color:#555555;">
      If the live results image does not load, open <a href="{escaped_live}" style="color:#8a5a00;">the poll page</a>.
    </td>
  </tr>
</table>"""


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


def candidate_by_slug(config, candidate_slug):
    for candidate in config["candidates"]:
        if candidate["slug"] == candidate_slug:
            return candidate
    return None


def candidate_by_name(config, name):
    for candidate in config["candidates"]:
        if candidate["name"] == name:
            return candidate
    return None


def resolve_poll_route(path):
    if path == "/lunch-vote":
        return DEFAULT_POLL_SLUG, ""
    if path.startswith("/lunch-vote/"):
        return DEFAULT_POLL_SLUG, path[len("/lunch-vote") :]
    prefix = "/poll-vote/"
    if path.startswith(prefix):
        rest = path[len(prefix) :]
        poll_slug, separator, suffix = rest.partition("/")
        return poll_slug, f"/{suffix}" if separator else ""
    return None, None


class LunchVoteHandler(BaseHTTPRequestHandler):
    server_version = "PollVoteAPI/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({"ok": True})
            return
        poll_slug, action = resolve_poll_route(path)
        if poll_slug is not None:
            self.handle_poll_get(poll_slug, action)
            return
        self.send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        poll_slug, action = resolve_poll_route(path)
        if poll_slug is not None and action == "":
            self.handle_vote(poll_slug)
            return
        self.send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

    def handle_poll_get(self, poll_slug, action):
        try:
            config = poll_config(poll_slug)
        except KeyError:
            self.send_json({"ok": False, "error": "Poll not found."}, HTTPStatus.NOT_FOUND)
            return

        if action in ("", "/config"):
            self.send_json(public_poll_config(config))
            return
        if action == "/results":
            self.handle_results(config)
            return
        if action == "/results-card.png":
            self.handle_results_card(config)
            return
        if action == "/results-embed.html":
            self.handle_results_embed(config)
            return
        if action == "/token":
            self.handle_token_status(config)
            return
        self.send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

    def handle_vote(self, poll_slug):
        try:
            config = poll_config(poll_slug)
        except KeyError:
            self.send_json({"ok": False, "error": "Poll not found."}, HTTPStatus.NOT_FOUND)
            return

        if poll_is_closed(config):
            self.send_json({"ok": False, "error": "This poll is closed."}, HTTPStatus.FORBIDDEN)
            return

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
            candidate_slug = clean_text(payload, "candidateSlug", 120)
            venue = clean_text(payload, "venue", 120)
            name = clean_text(payload, "name", MAX_NAME_LENGTH)
            token = clean_text(payload, "token", MAX_TOKEN_LENGTH)
            dietary = clean_text(payload, "dietary", MAX_NOTE_LENGTH)
            comment = clean_text(payload, "comment", MAX_NOTE_LENGTH)
            website = clean_text(payload, "website", MAX_NOTE_LENGTH)
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
            return

        if website:
            self.send_json({"ok": False, "error": "Invalid submission."}, HTTPStatus.BAD_REQUEST)
            return
        candidate = candidate_by_slug(config, candidate_slug) if candidate_slug else candidate_by_name(config, venue)
        if not candidate:
            self.send_json({"ok": False, "error": "Invalid candidate."}, HTTPStatus.BAD_REQUEST)
            return
        candidate_slug = candidate["slug"]
        venue = candidate["name"]
        if not is_valid_vote_token(token):
            self.send_json(
                {"ok": False, "error": "Use your unique voting link from the email invitation."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        user_agent = self.headers.get("User-Agent", "")[:500]
        client_ip = client_ip_from_headers(self)
        ip_hash = hash_ip(client_ip)
        vote_token_hash = hash_vote_token(token)
        now = isoformat_utc(utc_now())

        with connect_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            token_row = conn.execute(
                "SELECT id, used_at, used_vote_id FROM vote_tokens WHERE token_hash = ? AND poll_slug = ?",
                (vote_token_hash, config["PollSlug"]),
            ).fetchone()
            if not token_row:
                conn.rollback()
                self.send_json(
                    {"ok": False, "error": "This voting link is invalid."},
                    HTTPStatus.FORBIDDEN,
                )
                return

            existing_vote = None
            if token_row["used_vote_id"]:
                existing_vote = conn.execute(
                    "SELECT id FROM votes WHERE id = ? AND vote_token_hash = ? AND poll_slug = ?",
                    (token_row["used_vote_id"], vote_token_hash, config["PollSlug"]),
                ).fetchone()
            if not existing_vote:
                existing_vote = conn.execute(
                    """
                    SELECT id
                    FROM votes
                    WHERE vote_token_hash = ?
                      AND poll_slug = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """,
                    (vote_token_hash, config["PollSlug"]),
                ).fetchone()

            if existing_vote:
                vote_id = existing_vote["id"]
                conn.execute(
                    """
                    UPDATE votes
                    SET poll_slug = ?,
                        candidate_slug = ?,
                        venue = ?,
                        voter_name = ?,
                        dietary_note = ?,
                        comment = ?,
                        ip_hash = ?,
                        user_agent = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (config["PollSlug"], candidate_slug, venue, name, dietary, comment, ip_hash, user_agent, now, vote_id),
                )
                message = "Vote updated."
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO votes (poll_slug, candidate_slug, venue, voter_name, dietary_note, comment, vote_token_hash, ip_hash, user_agent, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (config["PollSlug"], candidate_slug, venue, name, dietary, comment, vote_token_hash, ip_hash, user_agent, now, now),
                )
                vote_id = cursor.lastrowid
                message = "Vote recorded."

            conn.execute(
                """
                UPDATE vote_tokens
                SET used_at = COALESCE(used_at, ?),
                    updated_at = ?,
                    used_vote_id = ?
                WHERE id = ?
                """,
                (now, now, vote_id, token_row["id"]),
            )

        self.send_json({
            "ok": True,
            "message": message,
            "voted": True,
            "candidateSlug": candidate_slug,
            "candidateName": venue,
            "venue": venue,
        })

    def handle_token_status(self, config):
        query = parse_qs(urlparse(self.path).query)
        token = (query.get("token") or [""])[0].strip()
        if not is_valid_vote_token(token):
            self.send_json(
                {"ok": False, "usable": False, "error": "This voting link is invalid."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        with connect_db() as conn:
            token_row = conn.execute(
                """
                SELECT t.used_at, t.used_vote_id, v.venue
                FROM vote_tokens t
                LEFT JOIN votes v ON v.id = t.used_vote_id
                WHERE t.token_hash = ?
                  AND t.poll_slug = ?
                """,
                (hash_vote_token(token), config["PollSlug"]),
            ).fetchone()

        if not token_row:
            self.send_json(
                {"ok": False, "usable": False, "error": "This voting link is invalid."},
                HTTPStatus.NOT_FOUND,
            )
            return
        voted_venue = token_row["venue"] or ""
        candidate = candidate_by_name(config, voted_venue)
        self.send_json({
            "ok": True,
            "usable": True,
            "pollClosed": poll_is_closed(config),
            "voted": bool(voted_venue),
            "candidateSlug": candidate["slug"] if candidate else "",
            "candidateName": voted_venue,
            "venue": voted_venue,
        })

    def handle_results(self, config):
        self.send_json(vote_results(config))

    def handle_results_card(self, config):
        body = render_results_card(vote_results(config))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def handle_results_embed(self, config):
        body = results_embed_html(self, config).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        message = re.sub(r"([?&]token=)[^&\s\"]+", r"\1[REDACTED]", format % args)
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), message))


def main():
    global POLL_CONFIGS
    POLL_CONFIGS = load_poll_configs()
    init_db()
    host = os.environ.get("VOTE_API_HOST", "0.0.0.0")
    port = env_int("PORT", 8080)
    httpd = ThreadingHTTPServer((host, port), LunchVoteHandler)
    print(f"Listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
