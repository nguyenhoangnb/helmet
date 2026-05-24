import hashlib
import sqlite3
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "violations.db"


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def resolve_image_path(image_path):
    path = Path(image_path)
    candidates = [
        path,
        APP_DIR / path,
        APP_DIR.parent / path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def ensure_columns(cursor):
    existing_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(violations)").fetchall()
    }
    for column_name, column_type in {
        "image_hash": "TEXT",
        "blockchain_tx": "TEXT",
        "ipfs_uri": "TEXT",
    }.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE violations ADD COLUMN {column_name} {column_type}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_columns(cursor)

    rows = cursor.execute(
        """
        SELECT id, image_path
        FROM violations
        WHERE image_path IS NOT NULL
          AND image_path != ''
          AND (image_hash IS NULL OR image_hash = '')
        """
    ).fetchall()

    updated = 0
    missing = 0

    for violation_id, image_path in rows:
        resolved_path = resolve_image_path(image_path)
        if resolved_path is None:
            print(f"Missing image for row {violation_id}: {image_path}")
            missing += 1
            continue

        image_hash = calculate_sha256(resolved_path)
        cursor.execute(
            """
            UPDATE violations
            SET image_hash = ?,
                blockchain_tx = ?,
                ipfs_uri = ?
            WHERE id = ?
            """,
            (
                image_hash,
                f"local-chain:{image_hash[:16]}",
                f"ipfs://pending/{image_hash[:16]}",
                violation_id,
            ),
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"Updated rows: {updated}")
    print(f"Missing images: {missing}")


if __name__ == "__main__":
    main()
