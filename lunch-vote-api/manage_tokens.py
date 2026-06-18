#!/usr/bin/env python3
import argparse
import csv
import secrets
import sqlite3
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from server import connect_db, hash_recipient_email, hash_vote_token, init_db, isoformat_utc, utc_now


DEFAULT_BASE_URL = "https://zoak.solutions/lunch-vote/"


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

    print(f"Generated {len(output_rows)} unique voter link(s).", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Manage unique lunch vote tokens.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate unique voter links.")
    generate_parser.add_argument("--voters", help="CSV with at least an email column and optional name column.")
    generate_parser.add_argument("--count", type=int, default=0, help="Generate anonymous links when no voters CSV is supplied.")
    generate_parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base lunch-vote URL.")
    generate_parser.add_argument("--output", help="Output CSV path. Defaults to stdout.")
    generate_parser.add_argument("--email-column", default="email")
    generate_parser.add_argument("--name-column", default="name")
    generate_parser.set_defaults(func=generate)

    args = parser.parse_args()
    if args.command == "generate" and not args.voters and args.count < 1:
        parser.error("generate requires --voters or --count.")
    args.func(args)


if __name__ == "__main__":
    main()
