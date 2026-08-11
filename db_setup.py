"""Set up the NGODatabase so the donateNgo site runs out of the box.

Safe to run any number of times:
  * creates the database and tables only if they are missing
  * seeds the NGO catalog only when it is EMPTY, so your users, donations
    and reviews are NEVER wiped (this replaces the old drop-everything
    behaviour that made accounts disappear after a restart)

To fully wipe and rebuild everything (fresh reset), load ngo_database.sql
manually instead.
"""
import re

import pymysql
from pymysql.constants import CLIENT

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "deens",
    "charset": "utf8mb4",
    "client_flag": CLIENT.MULTI_STATEMENTS,
}

SQL_FILE = "ngo_database.sql"


def ensure_setup(verbose=True):
    """Create DB + tables if missing and seed the NGO catalog if it is empty.

    Returns True if seeding happened, False if the catalog already existed.
    """
    with open(SQL_FILE, encoding="utf-8") as f:
        script = f.read()

    # Split the file into schema + seed so they can be run independently.
    marker = "-- SEED DATA"
    schema_sql, seed_sql = script.split(marker, 1)
    seed_sql = marker + seed_sql

    # Make the schema idempotent: no DROP statements, CREATE IF NOT EXISTS.
    schema_sql = re.sub(
        r"^DROP TABLE.*$", "", schema_sql, flags=re.IGNORECASE | re.MULTILINE
    )
    schema_sql = schema_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            while cur.nextset():
                pass
            cur.execute("SELECT COUNT(*) FROM ngos")
            seeded = cur.fetchone()[0] == 0
            if seeded:
                cur.execute(seed_sql)
                while cur.nextset():
                    pass
            if verbose:
                if seeded:
                    print(
                        "OK: NGO catalog seeded (users/donations/reviews "
                        "were not touched)."
                    )
                else:
                    print(
                        "OK: NGO catalog already present - nothing reseeded, "
                        "users/donations preserved."
                    )
        conn.commit()
    finally:
        conn.close()
    return seeded


def main():
    ensure_setup()


if __name__ == "__main__":
    main()
