import argparse
import threading
from flask import Flask, jsonify, request
from controller.marionette_controller import EnhancedMarionetteController
from executor.command_executor import CommandExecutor
from tinydb import TinyDB
import time

app = Flask(__name__)
db = TinyDB('dom_context.json')
# Create a controller instance for the API.
controller = EnhancedMarionetteController(host="localhost", port=2828)


@app.route("/extract", methods=["GET"])
def extract_dom_context():
    # Optionally, you can accept a query parameter for max_elements.
    max_elements = int(request.args.get("max_elements", 200))
    try:
        dom_context = controller.get_full_dom_context()
        current_url = controller.client.get_url() if controller.client else "Unknown"
        entry = {
            "timestamp": time.time(),
            "url": current_url,
            "max_elements": max_elements,
            "dom_context": dom_context
        }
        db.insert(entry)
        return jsonify({
            "status": "success",
            "dom_context": dom_context
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def main():
    parser = argparse.ArgumentParser(description="Browser Automation with Natural Language Commands")
    parser.add_argument("--host", default="localhost", help="Marionette host")
    parser.add_argument("--port", type=int, default=2828, help="Marionette port")
    args = parser.parse_args()

    # Initialize the executor (which may create its own controller).
    executor = CommandExecutor(
        host=args.host,
        port=args.port
    )

    # Connect to the browser.
    connect_result = executor.connect()
    if connect_result["status"] != "success":
        print(f"Failed to connect: {connect_result['message']}")
        return

    print("Connected to Firefox. Enter commands or 'exit' to quit.")

    # Main command loop.
    while True:
        command = input("\nEnter command: ")
        if command.lower() == "exit":
            break

        print("Executing command...")
        result = executor.execute_command_iteratively(command)

        # Display results.
        if result["status"] == "success":
            print(f"✅ Command executed successfully ({result['steps_completed']}/{result['total_steps']} steps)")
        else:
            print(f"❌ Command execution failed")
        print("\nResults:")
        for i, step_result in enumerate(result["results"]):
            status = "✓" if step_result["status"] == "success" else "✗"
            message = step_result.get("message", "")
            print(f"  {i + 1}. [{status}] {message}")
            if "data" in step_result:
                data = step_result["data"]
                if len(data) > 100:
                    print(f"    Extracted data: {data[:100]}...")
                else:
                    print(f"    Extracted data: {data}")


if __name__ == "__main__":
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5001, threaded=True))
    flask_thread.daemon = True
    flask_thread.start()

    main()
