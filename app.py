#donateNgo — a Flask website backed by the MySQL NGODatabase.

import json
from datetime import datetime

import pymysql
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# The columns used every time we read a user from the users table.
USER_FIELDS = "id,name,email,location,causes,avatar_color,avatar_image,since"


def connect():
    """Open a connection to the NGODatabase on this computer."""
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="deens",
        database="NGODatabase",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    return conn


def run_select(sql, values=()):
    """Run a SELECT query and return all the rows as a list of dicts."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql, values)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def run_insert(sql, values=()):
    """Run an INSERT query and return the id of the new row."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql, values)
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return new_id


def run_change(sql, values=()):
    """Run an UPDATE or DELETE query and return how many rows changed."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql, values)
    conn.commit()
    changed = cur.rowcount
    cur.close()
    conn.close()
    return changed


def to_iso(dt):
    """Turn a date-time into text like 2025-01-31T14:30:00."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def load_json(text):
    """Read the causes field (stored as JSON text) and return a list."""
    if text:
        try:
            return json.loads(text)
        except ValueError:
            return []
    return []


def user_to_dict(row):
    """Change one row of the users table into the dict the website wants."""
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "location": row["location"],
        "causes": load_json(row["causes"]),
        "avatarColor": row["avatar_color"],
        "avatarImage": row["avatar_image"],
        "since": row["since"],
    }


def make_chart(rows):
    """Make a bar chart from (date, amount) pairs.

    Recent donations (within 2 months) are grouped by day, donations
    within about 2 years by month, and everything older by year.
    """
    if len(rows) == 0:
        return {"granularity": "year", "labels": [], "values": [], "live": True}

    rows.sort()
    first_date = rows[0][0]
    last_date = rows[-1][0]
    total_days = (last_date - first_date).days

    if total_days <= 60:
        granularity = "day"
        key_format = "%Y-%m-%d"
        label_format = "%d %b"
    elif total_days <= 730:
        granularity = "month"
        key_format = "%Y-%m"
        label_format = "%b '%y"
    else:
        granularity = "year"
        key_format = "%Y"
        label_format = "%Y"

    buckets = {}
    for row in rows:
        dt = row[0]
        amount = row[1]
        key = dt.strftime(key_format)
        if key not in buckets:
            buckets[key] = {"label": dt.strftime(label_format), "total": 0.0}
        buckets[key]["total"] = buckets[key]["total"] + amount

    keys = list(buckets.keys())
    keys.sort()
    labels = []
    values = []
    for key in keys:
        labels.append(buckets[key]["label"])
        values.append(round(buckets[key]["total"]))

    return {
        "granularity": granularity,
        "labels": labels,
        "values": values,
        "live": True,
    }


@app.route("/")
def index():
    return render_template("donateNgo.html")


@app.route("/api/ngos")
def api_ngos():
    ngos = run_select(
        "SELECT id,name,tagline,category,location,founded,verified,"
        "description,email,phone,website FROM ngos ORDER BY id"
    )

    # All donations, grouped by NGO (used for the chart).
    donation_rows = run_select(
        "SELECT ngo_id, created_at, amount FROM donations ORDER BY created_at"
    )
    donations_by_ngo = {}
    for row in donation_rows:
        ngo_id = row["ngo_id"]
        if ngo_id not in donations_by_ngo:
            donations_by_ngo[ngo_id] = []
        donations_by_ngo[ngo_id].append((row["created_at"], float(row["amount"])))

    # All reviews, grouped by NGO.
    review_rows = run_select(
        "SELECT id,ngo_id,user_id,user_name,rating,text,created_at "
        "FROM reviews ORDER BY created_at DESC, id DESC"
    )
    reviews_by_ngo = {}
    for row in review_rows:
        ngo_id = row["ngo_id"]
        if ngo_id not in reviews_by_ngo:
            reviews_by_ngo[ngo_id] = []
        reviews_by_ngo[ngo_id].append(row)

    # Every donation with the donor's name, grouped by NGO.
    don_rows = run_select(
        "SELECT d.ngo_id, d.amount, d.created_at, u.name "
        "FROM donations d JOIN users u ON u.id = d.user_id "
        "ORDER BY d.created_at DESC, d.id DESC"
    )
    donlist_by_ngo = {}
    for row in don_rows:
        name = row["name"]
        if name is None or name == "":
            name = "Anonymous"
        ngo_id = row["ngo_id"]
        if ngo_id not in donlist_by_ngo:
            donlist_by_ngo[ngo_id] = []
        donlist_by_ngo[ngo_id].append(
            {
                "user": name,
                "amount": float(row["amount"]),
                "createdAt": to_iso(row["created_at"]),
            }
        )

    result = []
    for ngo in ngos:
        ngo_id = ngo["id"]
        reviews = reviews_by_ngo.get(ngo_id, [])

        if len(reviews) == 0:
            rating = None
        else:
            total = 0
            for rev in reviews:
                total = total + rev["rating"]
            rating = round(total / len(reviews), 1)

        if ngo_id in donations_by_ngo:
            donations = make_chart(donations_by_ngo[ngo_id])
        else:
            donations = {"granularity": "year", "labels": [], "values": [], "live": True}

        review_list = []
        for rev in reviews:
            name = rev["user_name"]
            if name is None or name == "":
                name = "Anonymous"
            review_list.append(
                {
                    "id": rev["id"],
                    "userId": rev["user_id"],
                    "user": name,
                    "rating": rev["rating"],
                    "text": rev["text"],
                    "createdAt": to_iso(rev["created_at"]),
                }
            )

        result.append(
            {
                "id": ngo_id,
                "name": ngo["name"],
                "tagline": ngo["tagline"],
                "category": ngo["category"],
                "location": ngo["location"],
                "founded": ngo["founded"],
                "verified": bool(ngo["verified"]),
                "desc": ngo["description"],
                "email": ngo["email"],
                "phone": ngo["phone"],
                "website": ngo["website"],
                "rating": rating,
                "reviews": len(reviews),
                "donations": donations,
                "donationsList": donlist_by_ngo.get(ngo_id, []),
                "reviewsList": review_list,
            }
        )

    # Version number: changes whenever an NGO, a review or a donation
    # changes, so the website knows to refresh itself.
    max_review_id = 0
    for rev in review_rows:
        if rev["id"] > max_review_id:
            max_review_id = rev["id"]
    max_donation = run_select("SELECT MAX(id) AS m FROM donations")[0]
    max_donation_id = max_donation["m"]
    if max_donation_id is None:
        max_donation_id = 0
    version = str(len(ngos)) + "-" + str(max_review_id) + "-" + str(max_donation_id)

    return jsonify({"version": version, "ngos": result})


@app.route("/api/me")
def api_me():
    user_id = request.args.get("id")
    rows = run_select("SELECT " + USER_FIELDS + " FROM users WHERE id=%s", (user_id,))
    if len(rows) == 0:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user_to_dict(rows[0]))


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    rows = run_select(
        "SELECT " + USER_FIELDS + " FROM users WHERE email=%s AND password_hash=%s",
        (email, data.get("password_hash", "")),
    )
    if len(rows) == 0:
        return jsonify({"error": "Incorrect email or password."}), 401
    return jsonify(user_to_dict(rows[0]))


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()

    exists = run_select("SELECT id FROM users WHERE email=%s", (email,))
    if len(exists) > 0:
        return (
            jsonify(
                {"error": "An account with this email already exists — try signing in."}
            ),
            409,
        )

    new_id = run_insert(
        "INSERT INTO users (name,email,password_hash,location,causes,"
        "avatar_color,avatar_image,since,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            (data.get("name") or "").strip(),
            email,
            data.get("password_hash", ""),
            data.get("location") or "Bengaluru, Karnataka",
            json.dumps(data.get("causes") or []),
            data.get("avatar_color", 0),
            None,
            data.get("since") or datetime.now().year,
            datetime.now(),
        ),
    )
    rows = run_select("SELECT " + USER_FIELDS + " FROM users WHERE id=%s", (new_id,))
    return jsonify(user_to_dict(rows[0])), 201


@app.route("/api/me", methods=["PUT"])
def api_me_update():
    data = request.get_json(force=True)
    user_id = data.get("id")
    email = (data.get("email") or "").strip().lower()

    conflict = run_select(
        "SELECT id FROM users WHERE email=%s AND id<>%s", (email, user_id)
    )
    if len(conflict) > 0:
        return jsonify({"error": "That email is already used by another account."}), 409

    run_change(
        "UPDATE users SET name=%s,email=%s,location=%s,causes=%s,avatar_color=%s,"
        "avatar_image=%s WHERE id=%s",
        (
            (data.get("name") or "").strip(),
            email,
            data.get("location") or "",
            json.dumps(data.get("causes") or []),
            data.get("avatar_color", 0),
            data.get("avatar_image"),
            user_id,
        ),
    )
    rows = run_select("SELECT " + USER_FIELDS + " FROM users WHERE id=%s", (user_id,))
    if len(rows) == 0:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user_to_dict(rows[0]))


@app.route("/api/me/profile")
def api_me_profile():
    user_id = request.args.get("id")
    rows = run_select("SELECT " + USER_FIELDS + " FROM users WHERE id=%s", (user_id,))
    if len(rows) == 0:
        return jsonify({"error": "User not found"}), 404

    # How much this user has donated in total.
    stat_row = run_select(
        "SELECT SUM(amount) AS total, COUNT(*) AS cnt "
        "FROM donations WHERE user_id=%s",
        (user_id,),
    )[0]
    total = stat_row["total"]
    if total is None:
        total = 0
    count = stat_row["cnt"]

    review_count = run_select(
        "SELECT COUNT(*) AS cnt FROM reviews WHERE user_id=%s", (user_id,)
    )[0]["cnt"]

    # Donation total for each year (for the profile page).
    year_rows = run_select(
        "SELECT YEAR(created_at) AS yr, SUM(amount) AS total "
        "FROM donations WHERE user_id=%s GROUP BY YEAR(created_at) ORDER BY yr",
        (user_id,),
    )
    by_year = []
    for row in year_rows:
        by_year.append({"yr": row["yr"], "total": float(row["total"])})

    # Giving-history chart, same grouping as the NGO chart.
    giving_rows = run_select(
        "SELECT created_at, amount FROM donations "
        "WHERE user_id=%s ORDER BY created_at",
        (user_id,),
    )
    giving_pairs = []
    for row in giving_rows:
        giving_pairs.append((row["created_at"], float(row["amount"])))
    giving_chart = make_chart(giving_pairs)

    # This user's reviews, with the name of each NGO they reviewed.
    review_rows = run_select(
        "SELECT r.rating, r.text, r.created_at, n.name AS ngo_name, n.id AS ngo_id "
        "FROM reviews r JOIN ngos n ON n.id = r.ngo_id "
        "WHERE r.user_id=%s ORDER BY r.created_at DESC, r.id DESC",
        (user_id,),
    )
    my_reviews = []
    for row in review_rows:
        my_reviews.append(
            {
                "rating": row["rating"],
                "text": row["text"],
                "createdAt": to_iso(row["created_at"]),
                "ngoName": row["ngo_name"],
                "ngoId": row["ngo_id"],
            }
        )

    # This user's donations, with the name of each NGO they donated to.
    donation_rows = run_select(
        "SELECT d.amount, d.created_at, n.name AS ngo_name, n.id AS ngo_id, d.status "
        "FROM donations d JOIN ngos n ON n.id = d.ngo_id "
        "WHERE d.user_id=%s ORDER BY d.created_at DESC, d.id DESC",
        (user_id,),
    )
    my_donations = []
    for row in donation_rows:
        my_donations.append(
            {
                "amount": float(row["amount"]),
                "createdAt": to_iso(row["created_at"]),
                "ngoName": row["ngo_name"],
                "ngoId": row["ngo_id"],
                "status": row["status"],
            }
        )

    return jsonify(
        {
            "user": user_to_dict(rows[0]),
            "total": float(total),
            "count": int(count),
            "reviewCount": int(review_count),
            "byYear": by_year,
            "chart": giving_chart,
            "reviews": my_reviews,
            "donations": my_donations,
        }
    )


@app.route("/api/stats")
def api_stats():
    verified = run_select("SELECT COUNT(*) AS c FROM ngos WHERE verified=1")[0]["c"]
    total_ngos = run_select("SELECT COUNT(*) AS c FROM ngos")[0]["c"]
    reviews = run_select("SELECT COUNT(*) AS c FROM reviews")[0]["c"]

    don_row = run_select("SELECT SUM(amount) AS s, COUNT(*) AS c FROM donations")[0]
    amount = don_row["s"]
    if amount is None:
        amount = 0

    cats = run_select("SELECT COUNT(DISTINCT category) AS c FROM ngos")[0]["c"]
    users = run_select("SELECT COUNT(*) AS c FROM users")[0]["c"]

    return jsonify(
        {
            "verifiedNgos": int(verified),
            "totalNgos": int(total_ngos),
            "donorReviews": int(reviews),
            "totalDonations": int(don_row["c"]),
            "trackedRupees": float(amount),
            "categories": int(cats),
            "activeUsers": int(users),
        }
    )


@app.route("/api/me/password", methods=["POST"])
def api_me_password():
    data = request.get_json(force=True)
    user_id = data.get("id")
    rows = run_select("SELECT password_hash FROM users WHERE id=%s", (user_id,))
    if len(rows) == 0:
        return jsonify({"error": "User not found"}), 404
    if rows[0]["password_hash"] != data.get("current_hash", ""):
        return jsonify({"error": "Current password is incorrect."}), 400

    new_hash = (data.get("new_hash") or "").strip()
    if new_hash == "":
        return jsonify({"error": "New password is missing."}), 400

    run_change("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
    return jsonify({"ok": True})


@app.route("/api/reviews", methods=["POST", "DELETE"])
def api_review():
    data = request.get_json(force=True)
    if request.method == "DELETE":
        deleted = run_change(
            "DELETE FROM reviews WHERE id=%s AND user_id=%s",
            (data.get("id"), data.get("user_id")),
        )
        if deleted == 0:
            return (
                jsonify(
                    {"error": "Review not found, or you can only delete your own reviews."}
                ),
                404,
            )
        return jsonify({"ok": True})

    run_insert(
        "INSERT INTO reviews (ngo_id,user_id,user_name,rating,text,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (
            data.get("ngo_id"),
            data.get("user_id"),
            data.get("user_name") or "Anonymous",
            int(data.get("rating", 5)),
            data.get("text", ""),
            datetime.now(),
        ),
    )
    return jsonify({"ok": True})


@app.route("/api/donations", methods=["POST"])
def api_donation():
    data = request.get_json(force=True)
    run_insert(
        "INSERT INTO donations (user_id,ngo_id,amount,card_last4,status,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (
            data.get("user_id"),
            data.get("ngo_id"),
            float(data.get("amount", 0)),
            data.get("card_last4"),
            data.get("status") or "completed (simulated)",
            datetime.now(),
        ),
    )
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Create the database and tables if missing (never deletes users or
    # donations, so accounts survive a server restart).
    try:
        from db_setup import ensure_setup

        ensure_setup()
    except Exception as exc:
        print("WARNING: could not auto-setup the database:", exc)

    # 0.0.0.0 = reachable from other computers on the local network.
    app.run(host="0.0.0.0", port=5000, debug=True)
