"""donateNgo — Flask app backed by the local MySQL NGODatabase.

The single-page front-end (templates/donateNgo.html) reads and writes
everything through these API endpoints, so the MySQL database on this
machine is the real source of truth. To let other computers on the
local network use the same database, run Flask on 0.0.0.0 (default
below) and point those machines at this computer's LAN IP.
"""
import json
from datetime import datetime

import pymysql
from flask import Flask, g, jsonify, render_template, request

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "deens",
    "database": "NGODatabase",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    g.pop("db", None)


def query(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def execute(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return cur.lastrowid


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else None


def row_user(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "location": row["location"],
        "causes": json_loads(row["causes"]),
        "avatarColor": row["avatar_color"],
        "avatarImage": row["avatar_image"],
        "since": row["since"],
    }


def json_loads(value):
    try:
        return json.loads(value or "[]")
    except (ValueError, TypeError):
        return []


def donation_series(rows):
    """Aggregate live donations into a day/month/year series so the donation
    report timeline adapts to how recent the giving is:
      donations within ~2 months  -> by day
      donations within ~2 years   -> by month
      donations older / spread out -> by year
    """
    if not rows:
        return {"granularity": "year", "labels": [], "values": [], "live": True}
    rows = sorted(rows, key=lambda x: x[0])
    span_days = (rows[-1][0] - rows[0][0]).days
    if span_days <= 60:
        granularity, keyfmt, labelfmt = "day", "%Y-%m-%d", "%d %b"
    elif span_days <= 730:
        granularity, keyfmt, labelfmt = "month", "%Y-%m", "%b '%y"
    else:
        granularity, keyfmt, labelfmt = "year", "%Y", "%Y"
    buckets = {}
    for dt, amt in rows:
        key = dt.strftime(keyfmt)
        b = buckets.setdefault(key, {"label": dt.strftime(labelfmt), "total": 0.0})
        b["total"] += amt
    order = sorted(buckets)
    return {
        "granularity": granularity,
        "labels": [buckets[k]["label"] for k in order],
        "values": [round(buckets[k]["total"]) for k in order],
        "live": True,
    }


USER_FIELDS = "id,name,email,location,causes,avatar_color,avatar_image,since"


@app.route("/")
def index():
    return render_template("donateNgo.html")


@app.route("/api/ngos")
def api_ngos():
    ngos = query(
        "SELECT id,name,tagline,category,location,founded,verified,impact,"
        "description,email,phone,website FROM ngos ORDER BY id"
    )

    # Real donations made through the app (live data).
    don_rows = query(
        "SELECT ngo_id, created_at, amount FROM donations ORDER BY created_at"
    )
    real_by = {}
    for r in don_rows:
        real_by.setdefault(r["ngo_id"], []).append((r["created_at"], float(r["amount"])))

    revs = query(
        "SELECT id, ngo_id, user_id, COALESCE(NULLIF(user_name,''),'Anonymous') "
        "AS user_name, rating, text, created_at FROM reviews "
        "ORDER BY created_at DESC, id DESC"
    )
    rev_by = {}
    for r in revs:
        rev_by.setdefault(r["ngo_id"], []).append(r)

    # Individual donations (live data) so the report can say who gave how much.
    don_list = query(
        "SELECT d.ngo_id, d.amount, d.created_at, "
        "COALESCE(NULLIF(u.name,''),'Anonymous') AS donor "
        "FROM donations d LEFT JOIN users u ON u.id=d.user_id "
        "ORDER BY d.created_at DESC, d.id DESC"
    )
    don_by = {}
    for r in don_list:
        don_by.setdefault(r["ngo_id"], []).append(
            {
                "user": r["donor"],
                "amount": float(r["amount"]),
                "createdAt": iso(r["created_at"]),
            }
        )

    out = []
    for n in ngos:
        nid = n["id"]
        rl = rev_by.get(nid, [])
        rating = round(sum(x["rating"] for x in rl) / len(rl), 1) if rl else None
        # Only real in-app donations appear on the chart; no seed fallback.
        donations = (
            donation_series(real_by[nid]) if nid in real_by
            else {"granularity": "year", "labels": [], "values": [], "live": True}
        )
        out.append(
            {
                "id": nid,
                "name": n["name"],
                "tagline": n["tagline"],
                "category": n["category"],
                "location": n["location"],
                "founded": n["founded"],
                "verified": bool(n["verified"]),
                "impact": n["impact"],
                "desc": n["description"],
                "email": n["email"],
                "phone": n["phone"],
                "website": n["website"],
                "rating": rating,
                "reviews": len(rl),
                "donations": donations,
                "donationsList": don_by.get(nid, []),
                "reviewsList": [
                    {
                        "id": r["id"],
                        "userId": r["user_id"],
                        "user": r["user_name"],
                        "rating": r["rating"],
                        "text": r["text"],
                        "createdAt": iso(r["created_at"]),
                    }
                    for r in rl
                ],
            }
        )

    # Content version: changes whenever an NGO is added/removed, a review is
    # written, or a donation lands, so clients can refresh without reloading.
    rev_max = max((r["id"] for r in revs), default=0)
    don_max = query("SELECT COALESCE(MAX(id),0) AS m FROM donations")[0]["m"]
    version = "{}-{}-{}".format(len(ngos), rev_max, don_max)
    return jsonify({"version": version, "ngos": out})


@app.route("/api/me")
def api_me():
    uid = request.args.get("id")
    rows = query(f"SELECT {USER_FIELDS} FROM users WHERE id=%s", (uid,))
    if not rows:
        return jsonify({"error": "User not found"}), 404
    return jsonify(row_user(rows[0]))


@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(force=True)
    email = (d.get("email") or "").strip().lower()
    rows = query(
        f"SELECT {USER_FIELDS} FROM users WHERE email=%s AND password_hash=%s",
        (email, d.get("password_hash", "")),
    )
    if not rows:
        return jsonify({"error": "Incorrect email or password."}), 401
    return jsonify(row_user(rows[0]))


@app.route("/api/register", methods=["POST"])
def api_register():
    d = request.get_json(force=True)
    email = (d.get("email") or "").strip().lower()
    if query("SELECT id FROM users WHERE email=%s", (email,)):
        return (
            jsonify(
                {"error": "An account with this email already exists — try signing in."}
            ),
            409,
        )
    uid = execute(
        "INSERT INTO users (name,email,password_hash,location,causes,"
        "avatar_color,avatar_image,since,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            (d.get("name") or "").strip(),
            email,
            d.get("password_hash", ""),
            d.get("location") or "Bengaluru, Karnataka",
            json.dumps(d.get("causes") or []),
            d.get("avatar_color", 0),
            None,
            d.get("since") or datetime.now().year,
            datetime.now(),
        ),
    )
    rows = query(f"SELECT {USER_FIELDS} FROM users WHERE id=%s", (uid,))
    return jsonify(row_user(rows[0])), 201


@app.route("/api/me", methods=["PUT"])
def api_me_update():
    d = request.get_json(force=True)
    uid = d.get("id")
    email = (d.get("email") or "").strip().lower()
    if query("SELECT id FROM users WHERE email=%s AND id<>%s", (email, uid)):
        return jsonify({"error": "That email is already used by another account."}), 409
    execute(
        "UPDATE users SET name=%s,email=%s,location=%s,causes=%s,avatar_color=%s,"
        "avatar_image=%s WHERE id=%s",
        (
            (d.get("name") or "").strip(),
            email,
            d.get("location") or "",
            json.dumps(d.get("causes") or []),
            d.get("avatar_color", 0),
            d.get("avatar_image"),
            uid,
        ),
    )
    rows = query(f"SELECT {USER_FIELDS} FROM users WHERE id=%s", (uid,))
    if not rows:
        return jsonify({"error": "User not found"}), 404
    return jsonify(row_user(rows[0]))


@app.route("/api/me/profile")
def api_me_profile():
    uid = request.args.get("id")
    rows = query(f"SELECT {USER_FIELDS} FROM users WHERE id=%s", (uid,))
    if not rows:
        return jsonify({"error": "User not found"}), 404

    stats = query(
        "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt "
        "FROM donations WHERE user_id=%s",
        (uid,),
    )
    rev_cnt = query("SELECT COUNT(*) AS cnt FROM reviews WHERE user_id=%s", (uid,))
    by_year = query(
        "SELECT YEAR(created_at) AS yr, SUM(amount) AS total "
        "FROM donations WHERE user_id=%s GROUP BY YEAR(created_at) ORDER BY yr",
        (uid,),
    )
    # Adaptive day/month/year giving-history series, same logic as the NGO
    # donation report so the profile chart matches its granularity.
    giving_rows = query(
        "SELECT created_at, amount FROM donations WHERE user_id=%s ORDER BY created_at",
        (uid,),
    )
    giving_chart = donation_series(
        [(r["created_at"], float(r["amount"])) for r in giving_rows]
    )
    my_reviews = query(
        "SELECT r.rating, r.text, r.created_at, n.name AS ngo_name, n.id AS ngo_id "
        "FROM reviews r JOIN ngos n ON n.id=r.ngo_id "
        "WHERE r.user_id=%s ORDER BY r.created_at DESC, r.id DESC",
        (uid,),
    )
    my_dons = query(
        "SELECT d.amount, d.created_at, n.name AS ngo_name, n.id AS ngo_id, d.status "
        "FROM donations d JOIN ngos n ON n.id=d.ngo_id "
        "WHERE d.user_id=%s ORDER BY d.created_at DESC, d.id DESC",
        (uid,),
    )

    return jsonify(
        {
            "user": row_user(rows[0]),
            "total": float(stats[0]["total"]),
            "count": int(stats[0]["cnt"]),
            "reviewCount": int(rev_cnt[0]["cnt"]),
            "byYear": [
                {"yr": r["yr"], "total": float(r["total"])} for r in by_year
            ],
            "chart": giving_chart,
            "reviews": [
                {
                    "rating": r["rating"],
                    "text": r["text"],
                    "createdAt": iso(r["created_at"]),
                    "ngoName": r["ngo_name"],
                    "ngoId": r["ngo_id"],
                }
                for r in my_reviews
            ],
            "donations": [
                {
                    "amount": float(r["amount"]),
                    "createdAt": iso(r["created_at"]),
                    "ngoName": r["ngo_name"],
                    "ngoId": r["ngo_id"],
                    "status": r["status"],
                }
                for r in my_dons
            ],
        }
    )


@app.route("/api/stats")
def api_stats():
    verified = query("SELECT COUNT(*) AS c FROM ngos WHERE verified=1")[0]["c"]
    total_ngos = query("SELECT COUNT(*) AS c FROM ngos")[0]["c"]
    reviews = query("SELECT COUNT(*) AS c FROM reviews")[0]["c"]
    don_row = query(
        "SELECT COALESCE(SUM(amount),0) AS s, COUNT(*) AS c FROM donations"
    )[0]
    cats = query("SELECT COUNT(DISTINCT category) AS c FROM ngos")[0]["c"]
    users = query("SELECT COUNT(*) AS c FROM users")[0]["c"]
    return jsonify(
        {
            "verifiedNgos": int(verified),
            "totalNgos": int(total_ngos),
            "donorReviews": int(reviews),
            "totalDonations": int(don_row["c"]),
            "trackedRupees": float(don_row["s"]),
            "categories": int(cats),
            "activeUsers": int(users),
        }
    )


@app.route("/api/me/password", methods=["POST"])
def api_me_password():
    d = request.get_json(force=True)
    uid = d.get("id")
    rows = query("SELECT password_hash FROM users WHERE id=%s", (uid,))
    if not rows:
        return jsonify({"error": "User not found"}), 404
    if rows[0]["password_hash"] != d.get("current_hash", ""):
        return jsonify({"error": "Current password is incorrect."}), 400
    new_hash = (d.get("new_hash") or "").strip()
    if not new_hash:
        return jsonify({"error": "New password is missing."}), 400
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, uid))
    return jsonify({"ok": True})


@app.route("/api/reviews", methods=["POST", "DELETE"])
def api_review():
    d = request.get_json(force=True)
    if request.method == "DELETE":
        cur = get_db().cursor()
        cur.execute(
            "DELETE FROM reviews WHERE id=%s AND user_id=%s",
            (d.get("id"), d.get("user_id")),
        )
        deleted = cur.rowcount
        cur.close()
        if not deleted:
            return (
                jsonify(
                    {"error": "Review not found, or you can only delete your own reviews."}
                ),
                404,
            )
        return jsonify({"ok": True})
    execute(
        "INSERT INTO reviews (ngo_id,user_id,user_name,rating,text,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (
            d.get("ngo_id"),
            d.get("user_id"),
            (d.get("user_name") or "Anonymous"),
            int(d.get("rating", 5)),
            d.get("text", ""),
            datetime.now(),
        ),
    )
    return jsonify({"ok": True})


@app.route("/api/donations", methods=["POST"])
def api_donation():
    d = request.get_json(force=True)
    execute(
        "INSERT INTO donations (user_id,ngo_id,amount,card_last4,status,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (
            d.get("user_id"),
            d.get("ngo_id"),
            float(d.get("amount", 0)),
            d.get("card_last4"),
            d.get("status") or "completed (simulated)",
            datetime.now(),
        ),
    )
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Make sure the database exists (creates tables + seeds the NGO catalog
    # only if empty). This never deletes users or donations, so accounts
    # survive server restarts.
    try:
        from db_setup import ensure_setup

        ensure_setup()
    except Exception as exc:  # pragma: no cover - server should still try to start
        print("WARNING: could not auto-setup the database:", exc)

    # 0.0.0.0 = reachable from other computers on the local network.
    app.run(host="0.0.0.0", port=5000, debug=True)
