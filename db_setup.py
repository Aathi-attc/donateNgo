"""Set up the NGODatabase so the donateNgo site runs out of the box.

Safe to run any number of times:
  * creates the database and tables only if they are missing
  * seeds the NGO catalog only when it is EMPTY, so users, donations
    and reviews are never wiped.

To fully reset the database, load ngo_database.sql manually instead.
"""

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
    """Create the database and tables if missing, and seed the NGO list
    only when the ngos table is empty.

    Returns True if seeding happened, False if the list already existed.
    """
    with open(SQL_FILE, encoding="utf-8") as file:
        script = file.read()

    # Split the file into two parts: the schema and the seed data.
    marker = "-- SEED DATA"
    parts = script.split(marker, 1)
    schema_sql = parts[0]
    seed_sql = marker + parts[1]

    # Make the schema safe to run again: remove the DROP TABLE lines and
    # add IF NOT EXISTS to every CREATE TABLE statement.
    new_lines = []
    for line in schema_sql.split("\n"):
        if line.strip().upper().startswith("DROP TABLE"):
            continue
        new_lines.append(line)
    schema_sql = "\n".join(new_lines)
    schema_sql = schema_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()

        cur.execute(schema_sql)
        while cur.nextset():
            pass

        cur.execute("SELECT COUNT(*) FROM ngos")
        count = cur.fetchone()[0]
        seeded = count == 0
        if seeded:
            cur.execute(seed_sql)
            while cur.nextset():
                pass

        conn.commit()
        cur.close()
    finally:
        conn.close()

    if verbose:
        if seeded:
            print(
                "OK: NGO catalog seeded (users/donations/reviews were not touched)."
            )
        else:
            print("OK: NGO catalog already present - nothing reseeded.")

    return seeded


def main():
    ensure_setup()


if __name__ == "__main__":
    main()
