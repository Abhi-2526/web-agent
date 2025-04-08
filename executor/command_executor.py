import re
import time
from typing import Dict, Any, List
from controller.marionette_controller import EnhancedMarionetteController
from parser.command_parser import CommandParser


class CommandExecutor:
    """Execute browser automation commands."""

    def __init__(self, host='localhost', port=2828):
        self.controller = EnhancedMarionetteController(host=host, port=port)
        self.parser = CommandParser(api_key="sk-57d5003fdb004b66be37aabcd0e346ec")
        self.connected = False

    def connect(self):
        """Ensure connection to the browser."""
        if not self.connected:
            result = self.controller.connect()
            self.connected = (result["status"] == "success")
            return result
        return {"status": "success", "message": "Already connected"}

    def _execute_step(self, step: dict) -> dict:
        """
        Execute a single automation step.
        For click actions:
          - First, try clicking using the provided DOM selector.
          - If that fails and vision-based coordinates (coords) are provided, use them.
          - Otherwise, trigger the OCR fallback using the descriptive target text.
        """
        action = step.get("action")
        params = step.get("params", {})
        # Cleaned DOM selector from get_next_step
        dom_selector = step.get("dom", "").strip()
        # Optional: vision-based coordinates (e.g., {"x": 100, "y": 200})
        coords = step.get("coords")

        try:
            if action == "navigate":
                return self.controller.navigate(params["url"])

            elif action == "click":
                # 1. Try using the DOM-based selector.
                if dom_selector and dom_selector.upper() != "N/A":
                    try:
                        result = self.controller.click(dom_selector)
                        if result["status"] == "success":
                            return result
                        else:
                            print(f"Click using DOM selector '{dom_selector}' failed: {result.get('message')}")
                    except Exception as click_exception:
                        print(f"Click using DOM selector '{dom_selector}' failed: {click_exception}")

                # 2. If vision-based coordinates are provided, try them.
                if coords and "x" in coords and "y" in coords:
                    print(f"Using vision-based coordinates fallback: {coords}")
                    return self.controller.click_by_coordinates(coords["x"], coords["y"])

                # 3. Fallback to OCR: use the descriptive parameter text to attempt to locate the target via OCR.
                target_text = params.get("selector", "").strip()
                if target_text:
                    print(f"Using OCR fallback to find text: '{target_text}'")
                    ocr_coords = self.controller.get_target_coordinates_ocr(target_text)
                    if ocr_coords:
                        print(f"OCR provided coordinates: {ocr_coords}")
                        return self.controller.click_by_coordinates(ocr_coords["x"], ocr_coords["y"])
                    else:
                        print("OCR fallback did not find the target element.")

                # 4. Last resort: try using the descriptive parameter as a selector.
                fallback_selector = params.get("selector", "").strip()
                if fallback_selector:
                    return self.controller.click(fallback_selector)
                else:
                    return {"status": "error", "message": "No valid selector provided for click action."}

            elif action == "search":
                return self.controller.search(params["query"])

            elif action == "input":
                selector = dom_selector if dom_selector and dom_selector.upper() != "N/A" else params.get("selector",
                                                                                                          "").strip()
                return self.controller.input_text(selector, params["text"])

            elif action == "extract":
                selector = dom_selector if dom_selector and dom_selector.upper() != "N/A" else params.get("selector",
                                                                                                          "").strip()
                return self.controller.extract(selector)

            elif action == "wait":
                seconds = int(params.get("seconds", 2))
                time.sleep(seconds)
                return {"status": "success", "message": f"Waited {seconds} seconds"}

            elif action == "complete":
                return {"status": "success", "message": "Task completed successfully"}

            else:
                return {"status": "error", "message": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "message": f"Error executing {action}: {str(e)}"}

    def _attempt_recovery(self, failed_step, error_result, step_index, all_steps):
        """Try to recover from common errors."""
        action = failed_step["action"]
        params = failed_step.get("params", {})
        error_msg = error_result.get("message", "")

        # Case 1: Element not found - try waiting and retrying
        if "not found" in error_msg and action in ["click", "input", "extract"]:
            print(f"Recovery attempt: Waiting for element to appear...")
            time.sleep(3)
            retry_result = self._execute_step(failed_step)
            if retry_result["status"] == "success":
                return retry_result

        # Case 2: Search box not found - try navigating to search engine first
        if action == "search" and "search box" in error_msg and step_index == 0:
            print("Recovery attempt: Navigating to Google first...")
            nav_step = {"action": "navigate", "params": {"url": "https://www.google.com"}}
            nav_result = self._execute_step(nav_step)
            if nav_result["status"] == "success":
                return self._execute_step(failed_step)

        # No recovery possible
        return None

    def execute_command_iteratively(self, command_text: str) -> Dict[str, Any]:
        """Execute a natural language command iteratively based on DOM context."""
        try:
            # Ensure connection
            if not self.connected:
                connect_result = self.connect()
                if connect_result["status"] != "success":
                    return connect_result

            # Execute steps iteratively
            results = []
            max_steps = 15
            consecutive_failures = 0
            max_failures = 3  # Max number of consecutive failures before giving up

            for i in range(max_steps):
                # Get current DOM state
                dom_context = self.controller.get_dom_context()

                # Log current page state
                print(f"\n--- Step {i + 1}: Analyzing current page ---")
                current_url = self.controller.client.get_url() if self.controller.client else "Not connected"
                print(f"Current URL: {current_url}")
                print(f"Found {len(dom_context)} interactive elements")

                # Get next step from LLM
                next_step = self.parser.get_next_step(command_text, dom_context, results)
                print(next_step)

                if not next_step:
                    print("Failed to determine next step")
                    break

                if next_step.get("action") == "complete":
                    print("Task completed successfully")
                    message = next_step.get("params", {}).get("message", "Task completed")
                    results.append({"status": "success", "message": message})
                    break

                # Execute the step
                print(f"Executing: {next_step['action']} {next_step.get('params', {})}")
                result = self._execute_step(next_step)
                results.append(result)

                # Handle success/failure
                if result["status"] == "success":
                    consecutive_failures = 0
                    print(f"Success: {result['message']}")
                    # Allow page to load
                    time.sleep(1.5)
                else:
                    consecutive_failures += 1
                    print(f"Failed: {result['message']}")

                    # Try recovery
                    if consecutive_failures < max_failures:
                        print("Attempting recovery...")
                        recovered = self._attempt_recovery(next_step, result, i, [])
                        if recovered:
                            results[-1] = recovered
                            consecutive_failures = 0
                            print(f"Recovery succeeded: {recovered['message']}")
                            time.sleep(1.5)
                        else:
                            print("Recovery failed")
                    else:
                        print(f"Exceeded maximum consecutive failures ({max_failures}), stopping execution")
                        break

            return {
                "status": "success" if any(r.get("action") == "complete" for r in results) or all(
                    r["status"] == "success" for r in results) else "error",
                "steps_completed": len(results),
                "total_steps": len(results),
                "results": results
            }
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {"status": "error", "message": f"Command execution failed: {str(e)}", "results": []}