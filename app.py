import os
import pymysql
import pymysql.cursors
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__, static_folder="static")


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


# ── Static pages ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/vendor")
def vendor():
    return send_from_directory("static", "vendor.html")


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
                    s.name AS storeName,
                    s.location,
                    s.category,
                    s.rating
                FROM Blind_Box b
                JOIN Store s ON b.store_ID = s.store_ID
                WHERE b.stockQuantity > 0
                ORDER BY b.box_ID
            """)
            rows = cur.fetchall()
        for row in rows:
            if "pickUpDeadline" in row and row["pickUpDeadline"] is not None:
                row["pickUpDeadline"] = str(row["pickUpDeadline"])
        return jsonify(rows)
    finally:
        conn.close()


# ── POST /api/order ──────────────────────────────────────────────────────────

@app.route("/api/order", methods=["POST"])
def place_order():
    data = request.get_json(force=True)
    sid = data.get("SID")
    box_id = data.get("box_ID")

    if not sid or not box_id:
        return jsonify({"error": "SID and box_ID are required."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Fetch the flash price so we can deduct it from acc_balance
            cur.execute(
                "SELECT flashPrice FROM Blind_Box WHERE box_ID = %s", (box_id,)
            )
            box = cur.fetchone()
            if not box:
                return jsonify({"error": "Blind box not found."}), 404

            flash_price = box["flashPrice"]

            # Deduct balance (CHECK constraint / trigger will guard against negatives)
            cur.execute(
                "UPDATE Student SET acc_balance = acc_balance - %s WHERE SID = %s",
                (flash_price, sid),
            )

            # Place order via stored procedure
            cur.execute(
                "CALL sp_place_order(%s, %s, @order_id, @pick_code)",
                (sid, box_id),
            )
            cur.execute("SELECT @order_id AS order_id, @pick_code AS pick_code")
            result = cur.fetchone()

        conn.commit()
        return jsonify({
            "order_id": result["order_id"],
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
        # Surface MySQL SIGNAL messages (triggers, procedure errors)
        msg = e.args[1] if len(e.args) > 1 else str(e)
        return jsonify({"error": msg}), 409
    finally:
        conn.close()


# ── POST /api/claim ──────────────────────────────────────────────────────────

@app.route("/api/claim", methods=["POST"])
def claim_order():
    data = request.get_json(force=True)
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
