from flask import Flask, render_template, request, jsonify, redirect, url_for
import serial
import serial.tools.list_ports
import threading
import time

app = Flask(__name__)

# Protocol & Hardware Constants matching vex/virtual_controller.iqpython
BAUD_RATE = 115200
SERIAL_TIMEOUT = 1.5
VALID_COMMANDS = {"ping", "happy", "stop", "forward", "spin"}

# Thread-safe global serial state
serial_lock = threading.Lock()
vex_serial = None
active_port = None


def is_connected():
    """Check if the VEX serial connection is currently initialized and open."""
    return vex_serial is not None and vex_serial.is_open


@app.route("/")
def index():
    """Render the setup wizard by default, or redirect/render dashboard."""
    return render_template("setup.html", port=active_port, connected=is_connected())


@app.route("/setup")
def setup_page():
    """Render the Neo-Brutalist interactive setup guide."""
    return render_template("setup.html", port=active_port, connected=is_connected())


@app.route("/dashboard")
def dashboard_page():
    """Render the main robot operation dashboard."""
    return render_template("index.html", port=active_port, connected=is_connected())


@app.route("/api/ports", methods=["GET"])
def list_serial_ports():
    """Scan Windows COM ports and flag likely VEX IQ devices."""
    ports_info = []
    for p in sorted(serial.tools.list_ports.comports(), key=lambda x: x.device):
        desc_lower = (p.description or "").lower()
        hwid_lower = (p.hwid or "").lower()
        is_vex = "vex" in desc_lower or "2888" in hwid_lower
        ports_info.append({
            "device": p.device,
            "description": p.description,
            "hwid": p.hwid,
            "is_vex": is_vex
        })
    return jsonify({
        "status": "success",
        "ports": ports_info,
        "connected": is_connected(),
        "active_port": active_port if is_connected() else None
    })


@app.route("/api/connect", methods=["POST"])
def connect_robot():
    """Open the selected COM port and optionally verify connection."""
    global vex_serial, active_port
    data = request.get_json(silent=True) or {}
    port = data.get("port")

    if not port:
        return jsonify({"status": "error", "message": "No COM port specified."}), 400

    with serial_lock:
        if vex_serial and vex_serial.is_open:
            try:
                vex_serial.close()
            except Exception:
                pass
            vex_serial = None
            active_port = None

        try:
            vex_serial = serial.Serial(
                port=port,
                baudrate=BAUD_RATE,
                timeout=SERIAL_TIMEOUT,
                write_timeout=SERIAL_TIMEOUT
            )
            time.sleep(0.2)
            vex_serial.reset_input_buffer()
            vex_serial.reset_output_buffer()
            active_port = port
            print(f"[HARDWARE] Connected to VEX IQ on {active_port}")
            return jsonify({
                "status": "connected",
                "port": active_port,
                "message": f"Successfully opened {active_port}."
            })
        except Exception as e:
            vex_serial = None
            active_port = None
            print(f"[ERROR] Failed to open {port}: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/command", methods=["POST"])
def send_command():
    """Send a newline-terminated command to the VEX IQ Brain (with Simulation fallback)."""
    global vex_serial, active_port
    data = request.get_json(silent=True) or {}
    cmd = str(data.get("command", data.get("emotion", ""))).strip().lower()

    if cmd not in VALID_COMMANDS:
        return jsonify({
            "status": "error",
            "message": f"Invalid command '{cmd}'. Allowed: {sorted(VALID_COMMANDS)}"
        }), 400

    with serial_lock:
        if is_connected():
            try:
                vex_serial.reset_input_buffer()
                vex_serial.write(f"{cmd}\n".encode("utf-8"))
                vex_serial.flush()
                print(f"[HARDWARE TX] Sent '{cmd}' -> {active_port}")

                reply = None
                if cmd == "ping":
                    time.sleep(0.2)
                    reply = vex_serial.readline().decode("utf-8", errors="ignore").strip()
                    print(f"[HARDWARE RX] Received: '{reply}'")

                return jsonify({
                    "status": "success",
                    "mode": "hardware",
                    "command": cmd,
                    "port": active_port,
                    "reply": reply
                })
            except Exception as e:
                print(f"[ERROR] Serial write failed: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            # Simulation Mode fallback so frontend UI testing works even with robot unplugged
            print(f"[SIMULATION TX] Simulated '{cmd}' (No hardware connected)")
            sim_reply = "PONG_OK" if cmd == "ping" else None
            return jsonify({
                "status": "success",
                "mode": "simulation",
                "command": cmd,
                "port": None,
                "reply": sim_reply
            })


@app.route("/api/status", methods=["GET"])
def connection_status():
    """Return current serial connection health."""
    return jsonify({
        "status": "online",
        "connected": is_connected(),
        "port": active_port if is_connected() else None
    })


if __name__ == "__main__":
    print("=== VEX IQ ROBOT EMOTIONS - SERVER ONLINE ===")
    # use_reloader=False prevents duplicate processes from fighting over the Windows COM port
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)