#!/usr/bin/env python3
import argparse
import csv
import os
import re
import secrets
import sqlite3
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from server import connect_db, hash_recipient_email, hash_vote_token, init_db, isoformat_utc, utc_now


DEFAULT_BASE_URL = "https://zoak.solutions/lunch-vote/"
DEFAULT_EMAIL_FROM = "ZOAK Lunch Vote <no-reply@zoak.solutions>"
DEFAULT_EMAIL_SUBJECT = "Your ZOAK lunch vote link"


def header_value(value):
    return " ".join(str(value or "").splitlines()).strip()


def safe_filename(value, fallback):
    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip().lower()).strip(".-_")
    return filename or fallback


def unique_filename(base, used):
    candidate = base
    index = 2
    while candidate in used:
        stem, ext = os.path.splitext(base)
        candidate = f"{stem}-{index}{ext}"
        index += 1
    used.add(candidate)
    return candidate


def build_vote_link(base_url, token):
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["token"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def read_voters(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit("Voter CSV must include a header row.")
        for row in reader:
            if any((value or "").strip() for value in row.values()):
                yield row


def insert_token(conn, recipient_label="", recipient_email=""):
    created_at = isoformat_utc(utc_now())
    for _ in range(5):
        token = secrets.token_urlsafe(32)
        try:
            conn.execute(
                """
                INSERT INTO vote_tokens (token_hash, recipient_label, recipient_email_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    hash_vote_token(token),
                    recipient_label.strip(),
                    hash_recipient_email(recipient_email),
                    created_at,
                ),
            )
            return token
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("Could not generate a unique token after 5 attempts.")


def build_mock_email(row, args):
    email = header_value(row.get(args.email_column, ""))
    name = header_value(row.get(args.name_column, ""))
    recipient = name or email or "Lunch voter"
    to_header = f"{name} <{email}>" if name and email else recipient
    vote_link = row["vote_link"]

    body = f"""Hi {recipient},

Please vote for the next ZOAK lunch using your unique link:
{vote_link}

This link is unique to you. Do not forward it.

Thanks,
ZOAK Solutions
"""

    return "\n".join(
        [
            f"From: {header_value(args.email_from)}",
            f"To: {to_header}",
            f"Subject: {header_value(args.email_subject)}",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
            "X-ZOAK-Mock-Email: true",
            "",
            body,
        ]
    )


def write_mock_emails(output_rows, args):
    if not args.mock_email_dir:
        return 0

    os.makedirs(args.mock_email_dir, exist_ok=True)
    used_filenames = set()
    for index, row in enumerate(output_rows, start=1):
        email = row.get(args.email_column, "")
        name = row.get(args.name_column, "")
        base = safe_filename(email or name, f"voter-{index}")
        filename = unique_filename(f"{base}.eml", used_filenames)
        output_path = os.path.join(args.mock_email_dir, filename)
        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(build_mock_email(row, args))
    return len(output_rows)


def generate(args):
    init_db()
    rows = list(read_voters(args.voters)) if args.voters else [{} for _ in range(args.count)]
    if not rows:
        raise SystemExit("No voters found.")

    input_fieldnames = list(rows[0].keys())
    output_fieldnames = input_fieldnames + [field for field in ("token", "vote_link") if field not in input_fieldnames]

    with connect_db() as conn:
        output_rows = []
        for row in rows:
            email = (row.get(args.email_column) or "").strip()
            name = (row.get(args.name_column) or "").strip()
            recipient_label = name or email
            token = insert_token(conn, recipient_label=recipient_label, recipient_email=email)
            output_row = dict(row)
            output_row["token"] = token
            output_row["vote_link"] = build_vote_link(args.base_url, token)
            output_rows.append(output_row)

    output = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    with output:
        writer = csv.DictWriter(output, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    drafted = write_mock_emails(output_rows, args)
    print(f"Generated {len(output_rows)} unique voter link(s).", file=sys.stderr)
    if drafted:
        print(f"Drafted {drafted} mock email(s) in {args.mock_email_dir}.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Manage unique lunch vote tokens.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate unique voter links.")
    generate_parser.add_argument("--voters", help="CSV with at least an email column and optional name column.")
    generate_parser.add_argument("--count", type=int, default=0, help="Generate anonymous links when no voters CSV is supplied.")
    generate_parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base lunch-vote URL.")
    generate_parser.add_argument("--output", help="Output CSV path. Defaults to stdout.")
    generate_parser.add_argument("--mock-email-dir", help="Directory where local .eml mockups should be written.")
    generate_parser.add_argument("--email-from", default=DEFAULT_EMAIL_FROM)
    generate_parser.add_argument("--email-subject", default=DEFAULT_EMAIL_SUBJECT)
    generate_parser.add_argument("--email-column", default="email")
    generate_parser.add_argument("--name-column", default="name")
    generate_parser.set_defaults(func=generate)

    args = parser.parse_args()
    if args.command == "generate" and not args.voters and args.count < 1:
        parser.error("generate requires --voters or --count.")
    args.func(args)


if __name__ == "__main__":
    main()
