import argparse
import hashlib
import sqlite3
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = APP_DIR / "violations.db"


def connect(db_path):
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def print_rows(rows):
    rows = list(rows)
    if not rows:
        print("No rows found.")
        return

    columns = rows[0].keys()
    widths = {
        column: max(len(column), *(len(format_value(row[column])) for row in rows))
        for column in columns
    }

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    print(header)
    print(divider)

    for row in rows:
        print(" | ".join(format_value(row[column]).ljust(widths[column]) for column in columns))


def format_value(value):
    if value is None:
        return ""
    return str(value)


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def latest(conn, limit):
    rows = conn.execute(
        """
        SELECT id, timestamp, image_hash, blockchain_tx, image_path
        FROM violations
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    print_rows(rows)


def missing_hash(conn):
    rows = conn.execute(
        """
        SELECT id, timestamp, image_path
        FROM violations
        WHERE image_hash IS NULL OR image_hash = ''
        ORDER BY id DESC
        """
    ).fetchall()
    print_rows(rows)


def stats(conn):
    rows = conn.execute(
        """
        SELECT
            COUNT(*) AS total_violations,
            SUM(CASE WHEN image_hash IS NOT NULL AND image_hash != '' THEN 1 ELSE 0 END) AS hashed_violations,
            SUM(CASE WHEN image_hash IS NULL OR image_hash = '' THEN 1 ELSE 0 END) AS missing_hash,
            SUM(CASE WHEN blockchain_tx LIKE 'local-chain:%' THEN 1 ELSE 0 END) AS local_chain_rows,
            SUM(CASE WHEN blockchain_tx LIKE '0x%' THEN 1 ELSE 0 END) AS real_blockchain_rows
        FROM violations
        """
    ).fetchall()
    print_rows(rows)


def by_date(conn):
    rows = conn.execute(
        """
        SELECT DATE(timestamp) AS violation_date, COUNT(*) AS total
        FROM violations
        GROUP BY DATE(timestamp)
        ORDER BY violation_date DESC
        """
    ).fetchall()
    print_rows(rows)


def detail(conn, violation_id):
    rows = conn.execute(
        """
        SELECT id, timestamp, camera, violation_type, image_path, confidence,
               image_hash, blockchain_tx, ipfs_uri
        FROM violations
        WHERE id = ?
        """,
        (violation_id,),
    ).fetchall()
    print_rows(rows)


def search_hash(conn, hash_text):
    rows = conn.execute(
        """
        SELECT id, timestamp, image_hash, blockchain_tx, image_path
        FROM violations
        WHERE image_hash LIKE ?
           OR blockchain_tx LIKE ?
        ORDER BY id DESC
        """,
        (f"%{hash_text}%", f"%{hash_text}%"),
    ).fetchall()
    print_rows(rows)


def verify_image_by_hash(conn, hash_text):
    rows = conn.execute(
        """
        SELECT id, timestamp, image_hash, blockchain_tx, image_path
        FROM violations
        WHERE image_hash LIKE ?
           OR blockchain_tx LIKE ?
        ORDER BY id DESC
        """,
        (f"%{hash_text}%", f"%{hash_text}%"),
    ).fetchall()

    verified_rows = []
    for row in rows:
        image_path = Path(format_value(row["image_path"]))
        stored_hash = format_value(row["image_hash"])
        current_hash = ""

        if not image_path.exists():
            status = "MISSING_FILE"
        elif not stored_hash:
            status = "NO_STORED_HASH"
            current_hash = calculate_sha256(image_path)
        else:
            current_hash = calculate_sha256(image_path)
            status = "MATCH" if current_hash == stored_hash else "MISMATCH"

        verified_rows.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "status": status,
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "image_path": row["image_path"],
        })

    print_rows(verified_rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query helmet violation records from SQLite."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path to violations.db. Default: app/violations.db",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    latest_parser = subparsers.add_parser("latest", help="Show latest violations.")
    latest_parser.add_argument("--limit", type=int, default=10)

    subparsers.add_parser("missing-hash", help="Show rows without image_hash.")
    subparsers.add_parser("stats", help="Show aggregate counts.")
    subparsers.add_parser("by-date", help="Count violations by date.")

    detail_parser = subparsers.add_parser("detail", help="Show one violation by id.")
    detail_parser.add_argument("id", type=int)

    search_parser = subparsers.add_parser("search-hash", help="Search by hash/tx text.")
    search_parser.add_argument("text")

    verify_parser = subparsers.add_parser(
        "verify-image",
        help="Find image by hash/tx text and compare file SHA-256.",
    )
    verify_parser.add_argument("text")

    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db)

    with connect(db_path) as conn:
        if args.command == "latest":
            latest(conn, args.limit)
        elif args.command == "missing-hash":
            missing_hash(conn)
        elif args.command == "stats":
            stats(conn)
        elif args.command == "by-date":
            by_date(conn)
        elif args.command == "detail":
            detail(conn, args.id)
        elif args.command == "search-hash":
            search_hash(conn, args.text)
        elif args.command == "verify-image":
            verify_image_by_hash(conn, args.text)


if __name__ == "__main__":
    main()
