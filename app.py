import os
import pymysql
import pymysql.cursors
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__, static_folder="static")
app.secret_key = "super_secret_retro_key"


def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ecoeat_2"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def login_required(role=None):
    """Returns (user_id, err_response) — err_response is None when authenticated."""
    user_id = session.get("user_id")
    if not user_id:
        return None, (jsonify({"error": "Not logged in."}), 401)
    if role and session.get("role") != role:
        return None, (jsonify({"error": "Forbidden: wrong role."}), 403)
    return user_id, None


# ── Static pages ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/vendor")
def vendor():
    return send_from_directory("static", "vendor.html")

@app.route("/login")
def login_page():
    return send_from_directory("static", "login.html")

@app.route("/signup")
def signup_page():
    return send_from_directory("static", "signup.html")

@app.route("/student_dashboard")
def student_dashboard_page():
    return send_from_directory("static", "student_dashboard.html")


# ── POST /api/signup ─────────────────────────────────────────────────────────

@app.route("/api/signup", methods=["POST"])
def signup():
    data     = request.get_json(force=True)
    role     = data.get("role", "").lower()
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    phone    = data.get("phone", "").strip()

    if role not in ("student", "store"):
        return jsonify({"error": "role must be 'student' or 'store'."}), 400
    if not all([name, email, password, phone]):
        return jsonify({"error": "name, email, password, and phone are required."}), 400

    pw_hash = generate_password_hash(password)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if role == "student":
                student_number = data.get("student_number", "").strip()
                if not student_number:
                    return jsonify({"error": "student_number is required for students."}), 400
                cur.execute(
                    """INSERT INTO Student
                           (name, student_number, phone, email, password_hash, acc_balance, eco_points)
                       VALUES (%s, %s, %s, %s, %s, 50.00, 0)""",
                    (name, student_number, phone, email, pw_hash),
                )
                new_id = cur.lastrowid
            else:
                category = data.get("category", "").strip()
                location = data.get("location", "").strip()
                if not category:
                    return jsonify({"error": "category is required for stores."}), 400
                cur.execute(
                    """INSERT INTO Store (name, location, category, email, password_hash)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (name, location, category, email, pw_hash),
                )
                new_id = cur.lastrowid
        conn.commit()
        return jsonify({"message": "Account created.", "id": new_id}), 201

    except pymysql.err.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": "Email or student number already registered."}), 409
    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── POST /api/login ──────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    role     = data.get("role", "").lower()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    if role not in ("student", "store"):
        return jsonify({"error": "role must be 'student' or 'store'."}), 400
    if not email or not password:
        return jsonify({"error": "email and password are required."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if role == "student":
                cur.execute(
                    "SELECT SID AS id, name, email, password_hash, acc_balance, eco_points "
                    "FROM Student WHERE email = %s",
                    (email,),
                )
            else:
                cur.execute(
                    "SELECT store_ID AS id, name, email, password_hash, category, location, rating "
                    "FROM Store WHERE email = %s",
                    (email,),
                )
            user = cur.fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session["role"]    = role

    profile = {k: v for k, v in user.items() if k != "password_hash"}
    profile["role"] = role
    return jsonify({"message": "Logged in.", "user": profile})


# ── GET /api/me ──────────────────────────────────────────────────────────────

@app.route("/api/me", methods=["GET"])
def me():
    user_id, err = login_required()
    if err:
        return err

    role = session.get("role")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if role == "student":
                cur.execute(
                    "SELECT SID AS id, name, student_number, phone, email, acc_balance, eco_points "
                    "FROM Student WHERE SID = %s",
                    (user_id,),
                )
            else:
                cur.execute(
                    "SELECT store_ID AS id, name, location, category, rating, email "
                    "FROM Store WHERE store_ID = %s",
                    (user_id,),
                )
            user = cur.fetchone()
    finally:
        conn.close()

    if not user:
        session.clear()
        return jsonify({"error": "User not found."}), 404

    user["role"] = role
    return jsonify(user)


# ── POST /api/logout ─────────────────────────────────────────────────────────

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


# ── GET /api/student/orders ──────────────────────────────────────────────────

@app.route("/api/student/orders", methods=["GET"])
def student_get_orders():
    sid, err = login_required(role="student")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    o.order_ID,
                    o.pickUpCode,
                    o.status,
                    o.orderTime,
                    b.name          AS box_name,
                    b.flashPrice,
                    b.pickUpDeadline,
                    s.name          AS store_name,
                    IF(r.review_ID IS NOT NULL, 1, 0) AS has_review
                FROM `Order` o
                JOIN Blind_Box b ON o.box_ID  = b.box_ID
                JOIN Store     s ON b.store_ID = s.store_ID
                LEFT JOIN Review r ON r.order_ID = o.order_ID
                WHERE o.SID = %s
                ORDER BY o.order_ID DESC
            """, (sid,))
            rows = cur.fetchall()
        for row in rows:
            if row.get("pickUpDeadline") is not None:
                row["pickUpDeadline"] = str(row["pickUpDeadline"])
            if row.get("orderTime") is not None:
                row["orderTime"] = str(row["orderTime"])
        return jsonify(rows)
    except Exception as e:
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── POST /api/student/orders/<order_id>/cancel ────────────────────────────────

@app.route("/api/student/orders/<int:order_id>/cancel", methods=["POST"])
def student_cancel_order(order_id):
    sid, err = login_required(role="student")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Verify order belongs to this student and is still Pending
            cur.execute(
                """SELECT box_ID, totalAmount
                   FROM `Order`
                   WHERE order_ID = %s AND SID = %s AND status = 'Pending'""",
                (order_id, sid),
            )
            order = cur.fetchone()

            if not order:
                return jsonify({
                    "error": "Order not found, already processed, or does not belong to you."
                }), 400

            box_id      = order["box_ID"]
            total_amount = order["totalAmount"]

            # a) Cancel the order
            cur.execute(
                "UPDATE `Order` SET status = 'Canceled' WHERE order_ID = %s",
                (order_id,),
            )
            # b) Restock the blind box
            cur.execute(
                "UPDATE Blind_Box SET stockQuantity = stockQuantity + 1 WHERE box_ID = %s",
                (box_id,),
            )
            # c) Refund the student
            cur.execute(
                "UPDATE Student SET acc_balance = acc_balance + %s WHERE SID = %s",
                (total_amount, sid),
            )

        conn.commit()
        return jsonify({
            "message": "Order canceled and refund processed.",
            "refunded": float(total_amount),
        })

    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── POST /api/reviews ────────────────────────────────────────────────────────

@app.route("/api/reviews", methods=["POST"])
def submit_review():
    sid, err = login_required(role="student")
    if err:
        return err

    data     = request.get_json(force=True)
    order_id = data.get("order_ID")
    rating   = data.get("rating")
    comment  = data.get("comment", "").strip()

    if not order_id or rating is None:
        return jsonify({"error": "order_ID and rating are required."}), 400
    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return jsonify({"error": "rating must be an integer."}), 400
    if not 1 <= rating <= 5:
        return jsonify({"error": "Rating must be between 1 and 5."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Step 1: verify ownership and fetch current status
            cur.execute(
                "SELECT order_ID, status FROM `Order` WHERE order_ID = %s AND SID = %s",
                (order_id, sid),
            )
            order_row = cur.fetchone()
            if not order_row:
                return jsonify({"error": "Order not found or does not belong to you."}), 400

            # Step 2: explicit status gate with the required message
            if order_row["status"] != "Claimed":
                return jsonify({
                    "error": "You can only review orders that you have successfully claimed."
                }), 400

            # Step 3: fetch store_ID for the rating update
            cur.execute(
                """SELECT b.store_ID
                   FROM `Order` o
                   JOIN Blind_Box b ON o.box_ID = b.box_ID
                   WHERE o.order_ID = %s""",
                (order_id,),
            )
            store_id = cur.fetchone()["store_ID"]

            # Insert review (UNIQUE constraint on order_ID enforces 1-per-order)
            cur.execute(
                "INSERT INTO Review (order_ID, rating, comment) VALUES (%s, %s, %s)",
                (order_id, rating, comment or None),
            )

            # Recalculate and update the store's aggregate rating
            cur.execute(
                """UPDATE Store
                   SET rating = (
                       SELECT ROUND(AVG(r.rating), 2)
                       FROM Review r
                       JOIN `Order` o ON r.order_ID = o.order_ID
                       JOIN Blind_Box b ON o.box_ID = b.box_ID
                       WHERE b.store_ID = %s
                   )
                   WHERE store_ID = %s""",
                (store_id, store_id),
            )

        conn.commit()
        return jsonify({"message": "Review submitted. Thank you!"}), 201

    except pymysql.err.IntegrityError as e:
        conn.rollback()
        if e.args[0] == 1062:
            return jsonify({"error": "You have already reviewed this order."}), 400
        return jsonify({"error": str(e.args[1])}), 409
    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── GET /api/leaderboard ─────────────────────────────────────────────────────

@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, eco_points FROM Student ORDER BY eco_points DESC LIMIT 5"
            )
            rows = cur.fetchall()
        return jsonify(rows)
    except Exception as e:
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── GET /api/boxes ───────────────────────────────────────────────────────────

@app.route("/api/boxes", methods=["GET"])
def get_boxes():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    b.box_ID,
                    b.name,
                    b.originalPrice,
                    b.flashPrice,
                    b.stockQuantity,
                    b.pickUpDeadline,
                    s.name     AS storeName,
                    s.location,
                    s.category,
                    s.rating
                FROM Blind_Box b
                JOIN Store s ON b.store_ID = s.store_ID
                WHERE b.stockQuantity > 0
                  AND b.is_active = TRUE
                ORDER BY b.box_ID
            """)
            rows = cur.fetchall()
        for row in rows:
            if row.get("pickUpDeadline") is not None:
                row["pickUpDeadline"] = str(row["pickUpDeadline"])
        return jsonify(rows)
    finally:
        conn.close()


# ── GET /api/vendor/analytics ────────────────────────────────────────────────

@app.route("/api/vendor/analytics", methods=["GET"])
def vendor_analytics():
    store_id, err = login_required(role="store")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                       COUNT(o.order_ID)   AS total_rescued,
                       SUM(o.totalAmount)  AS total_revenue
                   FROM `Order` o
                   JOIN Blind_Box b ON o.box_ID = b.box_ID
                   WHERE b.store_ID = %s
                     AND o.status   = 'Claimed'""",
                (store_id,),
            )
            row = cur.fetchone()
        return jsonify({
            "total_rescued": row["total_rescued"] or 0,
            "total_revenue": float(row["total_revenue"] or 0),
        })
    except Exception as e:
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── GET /api/vendor/boxes ────────────────────────────────────────────────────

@app.route("/api/vendor/boxes", methods=["GET"])
def vendor_get_boxes():
    store_id, err = login_required(role="store")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT box_ID, name, originalPrice, flashPrice,
                          stockQuantity, pickUpDeadline, is_active
                   FROM Blind_Box
                   WHERE store_ID = %s
                   ORDER BY box_ID""",
                (store_id,),
            )
            rows = cur.fetchall()
        for row in rows:
            if row.get("pickUpDeadline") is not None:
                row["pickUpDeadline"] = str(row["pickUpDeadline"])
        return jsonify(rows)
    except Exception as e:
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── POST /api/vendor/boxes ────────────────────────────────────────────────────

@app.route("/api/vendor/boxes", methods=["POST"])
def vendor_add_box():
    store_id, err = login_required(role="store")
    if err:
        return err

    data = request.get_json(force=True)
    name            = data.get("name", "").strip()
    original_price  = data.get("originalPrice")
    flash_price     = data.get("flashPrice")
    stock_quantity  = data.get("stockQuantity", 0)
    pick_up_deadline = data.get("pickUpDeadline", "").strip()

    if not all([name, original_price, flash_price, pick_up_deadline]):
        return jsonify({"error": "name, originalPrice, flashPrice, and pickUpDeadline are required."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO Blind_Box
                       (store_ID, name, originalPrice, flashPrice, stockQuantity, pickUpDeadline)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (store_id, name, original_price, flash_price, stock_quantity, pick_up_deadline),
            )
            new_id = cur.lastrowid
        conn.commit()
        return jsonify({"message": "Blind box created.", "box_ID": new_id}), 201

    except pymysql.err.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": str(e.args[1])}), 409
    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── PUT /api/vendor/boxes/<box_id>/toggle ────────────────────────────────────

@app.route("/api/vendor/boxes/<int:box_id>/toggle", methods=["PUT"])
def vendor_toggle_box(box_id):
    store_id, err = login_required(role="store")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_active FROM Blind_Box WHERE box_ID = %s AND store_ID = %s",
                (box_id, store_id),
            )
            box = cur.fetchone()
            if not box:
                return jsonify({"error": "Box not found or does not belong to your store."}), 404

            new_status = not box["is_active"]
            cur.execute(
                "UPDATE Blind_Box SET is_active = %s WHERE box_ID = %s AND store_ID = %s",
                (new_status, box_id, store_id),
            )
        conn.commit()
        return jsonify({"box_ID": box_id, "is_active": new_status})

    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── DELETE /api/vendor/boxes/<box_id> ────────────────────────────────────────

@app.route("/api/vendor/boxes/<int:box_id>", methods=["DELETE"])
def vendor_delete_box(box_id):
    store_id, err = login_required(role="store")
    if err:
        return err

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Verify ownership before modifying
            cur.execute(
                "SELECT box_ID FROM Blind_Box WHERE box_ID = %s AND store_ID = %s",
                (box_id, store_id),
            )
            if not cur.fetchone():
                return jsonify({"error": "Box not found or does not belong to your store."}), 404

            # Soft-delete: deactivate instead of DELETE to preserve FK integrity
            cur.execute(
                "UPDATE Blind_Box SET is_active = FALSE WHERE box_ID = %s AND store_ID = %s",
                (box_id, store_id),
            )
        conn.commit()
        return jsonify({"message": f"Blind box {box_id} has been deactivated.", "is_active": False})

    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


# ── POST /api/order ──────────────────────────────────────────────────────────

@app.route("/api/order", methods=["POST"])
def place_order():
    sid, err = login_required(role="student")
    if err:
        return err

    data   = request.get_json(force=True)
    box_id = data.get("box_ID")

    if not box_id:
        return jsonify({"error": "box_ID is required."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT flashPrice FROM Blind_Box WHERE box_ID = %s", (box_id,)
            )
            box = cur.fetchone()
            if not box:
                return jsonify({"error": "Blind box not found."}), 404

            flash_price = box["flashPrice"]

            # Insufficient-funds guard — check before any mutation
            cur.execute(
                "SELECT acc_balance FROM Student WHERE SID = %s", (sid,)
            )
            student = cur.fetchone()
            if not student or student["acc_balance"] < flash_price:
                return jsonify({
                    "error": "Insufficient Funds! Please select a cheaper box."
                }), 400

            cur.execute(
                "UPDATE Student SET acc_balance = acc_balance - %s WHERE SID = %s",
                (flash_price, sid),
            )

            cur.execute(
                "CALL sp_place_order(%s, %s, @order_id, @pick_code)",
                (sid, box_id),
            )
            cur.execute("SELECT @order_id AS order_id, @pick_code AS pick_code")
            result = cur.fetchone()

        conn.commit()
        return jsonify({
            "order_id":   result["order_id"],
            "pickUpCode": result["pick_code"],
        }), 201

    except pymysql.err.OperationalError as e:
        conn.rollback()
        return jsonify({"error": str(e.args[1])}), 409
    except pymysql.err.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": str(e.args[1])}), 409
    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 409
    finally:
        conn.close()


# ── POST /api/claim ──────────────────────────────────────────────────────────

@app.route("/api/claim", methods=["POST"])
def claim_order():
    data         = request.get_json(force=True)
    pick_up_code = data.get("pickUpCode")

    if not pick_up_code:
        return jsonify({"error": "pickUpCode is required."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT order_ID, status FROM `Order` WHERE pickUpCode = %s",
                (pick_up_code,),
            )
            order = cur.fetchone()

            if not order:
                return jsonify({"error": "Invalid pick-up code."}), 404
            if order["status"] == "Claimed":
                return jsonify({"error": "Order already claimed."}), 409
            if order["status"] == "Canceled":
                return jsonify({"error": "Order has been canceled."}), 409

            cur.execute(
                "UPDATE `Order` SET status = 'Claimed' WHERE order_ID = %s",
                (order["order_ID"],),
            )
        conn.commit()
        return jsonify({"message": "Order claimed successfully.", "order_id": order["order_ID"]})

    except Exception as e:
        conn.rollback()
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
