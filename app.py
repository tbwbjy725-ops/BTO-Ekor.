#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import string, uuid, os
from bots import tiktok_bot

app = Flask(__name__)

SESSIONS = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(force=True, silent=True) or {}

    length = int(data.get("length", 4))
    mode = data.get("mode", "random")
    digits = bool(data.get("digits", False))
    base = (data.get("base") or "").strip().lower()
    tak = bool(data.get("tak", False))

    if length not in (3, 4, 5):
        return jsonify({"error": "length must be 3, 4 or 5"}), 400
    if mode not in ("random", "special", "ordered", "similar"):
        return jsonify({"error": "invalid mode"}), 400
    if mode == "similar" and (not base or len(base) > length):
        return jsonify({"error": "invalid base word"}), 400

    pool = string.ascii_lowercase + (string.digits if digits else "")

    session = tiktok_bot.ScanSession(length, mode, pool, base, tak, threads=20)

    sid = uuid.uuid4().hex
    SESSIONS[sid] = session
    session.start()

    return jsonify({"session_id": sid})

@app.route("/api/status/<sid>")
def api_status(sid):
    s = SESSIONS.get(sid)
    if not s:
        return jsonify({"error": "session not found"}), 404
    return jsonify(s.status())

@app.route("/api/stop/<sid>", methods=["POST"])
def api_stop(sid):
    s = SESSIONS.get(sid)
    if s:
        s.stop()
    return jsonify({"ok": True})

@app.route("/api/cleanup/<sid>", methods=["POST"])
def api_cleanup(sid):
    SESSIONS.pop(sid, None)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)