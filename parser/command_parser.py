import re
from openai import OpenAI


class CommandParser:
    """Parse natural language commands for browser automation using only LLM (DeepSeek/OpenAI API)."""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def get_next_step(self, goal: str, dom_context=None, previous_steps=None):
        """
        Generate the next action to achieve the goal based on current context.
        The prompt instructs the LLM to only return action F ("complete") if the page's state (e.g. URL)
        indicates that the desired final state is achieved.
        """
        # Build a formatted summary string from the DOM context.
        dom_lines = []
        if isinstance(dom_context, list) and dom_context:
            for element in dom_context:
                tag = element.get("tag", "")
                text = element.get("text", "").strip()
                attrs = element.get("attributes", {})
                attr_list = []
                for key in ['id', 'name', 'class', 'placeholder', 'aria-label', 'title', 'href']:
                    if attrs.get(key):
                        attr_list.append(f"{key}='{attrs[key]}'")
                line = f"{tag}: '{text}'"
                if attr_list:
                    line += " (" + ", ".join(attr_list) + ")"
                dom_lines.append(line)
        else:
            dom_lines.append("No interactive elements found.")
        dom_context_str = "\n".join(dom_lines)

        # Get current URL and last action from previous steps (if available)
        current_url = "Unknown"
        last_action = "None"
        if previous_steps and len(previous_steps) > 0:
            last_step = previous_steps[-1]
            if "Navigated to" in last_step.get("message", ""):
                current_url = last_step.get("message", "").replace("Navigated to ", "")
            last_action = last_step.get("message", "")

        # Build the prompt with explicit instructions about final state.
        prompt = f"""GOAL: {goal}

CURRENT URL: {current_url}
LAST ACTION: {last_action}

Below is a summary of key interactive elements on the page:
{dom_context_str}

IMPORTANT: The task is only considered complete when the page's final state confirms redirection or the desired change. 
For example, if the goal is to click a button on the Google homepage ("https://www.google.com") that redirects you to another URL, 
then the final state is achieved only if the current URL is different from "https://www.google.com".

Based solely on the above context, decide the next single action needed to achieve the goal.
Choose exactly one action from:
A) navigate - Navigate to a URL.
B) search - Enter a search query.
C) click - Click on a specific element.
D) input - Type text into a field.
E) wait - Wait for a specified duration.
F) complete - No further action is needed; the desired final state is achieved (i.e. the current URL or state confirms redirection).

For your chosen action, please provide:
- The necessary parameter(s) (e.g., URL for navigate, query for search, text for input).
- The exact CSS selector (DOM element) from the above summary on which to perform the action, or "N/A" if not applicable.
- If the final state is confirmed (e.g., the current URL is different from the original), return action F ("complete") with an appropriate message including the new URL.

Format your response exactly as follows:
ACTION: [Letter]
PARAM: [Parameter(s)]
DOM: [Exact CSS selector or "N/A"]

Example if final state is reached:
ACTION: F
PARAM: Task completed – redirection confirmed (current URL: https://example.com/newpage)
DOM: N/A
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for browser automation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.1,
                top_p=0.95,
                stream=False,
                stop=["Input:", "##"]
            )
            response_text = response.choices[0].message.content.strip()
            print("\nLLM decision:")
            print("----------------------------------------")
            print(response_text)
            print("----------------------------------------")

            # Extract fields from the LLM response.
            action_match = re.search(r'ACTION:\s*([A-F])', response_text)
            param_match = re.search(r'PARAM:\s*(.*?)(?:\n|$)', response_text)
            dom_match = re.search(r'DOM:\s*(.*?)(?:\n|$)', response_text)

            if action_match and param_match:
                action_letter = action_match.group(1)
                param_value = param_match.group(1).strip()
                # Remove trailing commentary from the DOM field, if any.
                if dom_match:
                    dom_value = re.sub(r'\s*\(.*\)$', '', dom_match.group(1).strip())
                else:
                    dom_value = "N/A"

                action_map = {
                    'A': 'navigate',
                    'B': 'search',
                    'C': 'click',
                    'D': 'input',
                    'E': 'wait',
                    'F': 'complete'
                }
                action = action_map.get(action_letter)
                if not action:
                    print(f"Invalid action letter: {action_letter}")
                    return None

                params_dict = {}
                if action == 'navigate':
                    if param_value and not param_value.startswith(('http://', 'https://')):
                        param_value = 'https://' + param_value
                    params_dict['url'] = param_value
                elif action == 'search':
                    params_dict['query'] = param_value
                elif action == 'click':
                    # For clicks, we expect a descriptive target text.
                    params_dict['selector'] = param_value
                elif action == 'input':
                    parts = param_value.split(',', 1)
                    if len(parts) >= 2:
                        params_dict['selector'] = parts[0].strip()
                        params_dict['text'] = parts[1].strip()
                    else:
                        params_dict['selector'] = "input field"
                        params_dict['text'] = param_value
                elif action == 'wait':
                    try:
                        params_dict['seconds'] = int(re.search(r'\d+', param_value).group(0))
                    except:
                        params_dict['seconds'] = 3

                return {"action": action, "params": params_dict, "dom": dom_value}
            else:
                print("Failed to extract fields from LLM response.")
                return None
        except Exception as e:
            print(f"Error in get_next_step: {e}")
            return None
