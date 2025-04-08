import base64
import time

import cv2
import numpy as np
from marionette_driver.marionette import Marionette
from marionette_driver.by import By
from marionette_driver.errors import NoSuchElementException, TimeoutException
from marionette_driver.wait import Wait
from marionette_driver.keys import Keys
from pytesseract import pytesseract


class EnhancedMarionetteController:
    def __init__(self, host='localhost', port=2828):
        self.host = host
        self.port = port
        self.client = None
        self.timeout = 10

    def connect(self, timeout=30):
        """Connect to Firefox Marionette."""
        try:
            print(f"Connecting to Marionette at {self.host}:{self.port}...")
            self.client = Marionette(host=self.host, port=self.port)
            self.client.start_session(timeout=timeout)
            print("Marionette session started successfully.")
            return {"status": "success", "message": "Connected to Firefox"}
        except ConnectionRefusedError:
            error_msg = "Connection refused. Make sure Firefox is running with Marionette enabled."
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error connecting to Firefox Marionette: {e}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}

    def navigate(self, url):
        """Navigate to a URL using Marionette native command."""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            self.client.navigate(url)
            # Wait for page load to complete
            Wait(self.client).until(lambda _: self.client.execute_script('return document.readyState') == 'complete')
            return {"status": "success", "message": f"Navigated to {url}"}
        except TimeoutException:
            return {"status": "error", "message": f"Timeout while navigating to {url}"}
        except Exception as e:
            return {"status": "error", "message": f"Navigation failed: {str(e)}"}

    def find_element(self, selector, by=By.CSS_SELECTOR):
        """Find an element using Marionette native command."""
        try:
            element = self.client.find_element(by, selector)
            return element
        except NoSuchElementException:
            return None
        except Exception as e:
            print(f"Error finding element {selector}: {e}")
            return None

    def click(self, selector, by=By.CSS_SELECTOR):
        """Click an element using Marionette native command."""
        try:
            element = self.find_element(selector, by)
            if not element:
                return {"status": "error", "message": f"Element not found: {selector}"}

            # Scroll the element into view, centering it
            self.client.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'});",
                [element]
            )
            time.sleep(1)

            element.click()
            return {"status": "success", "message": f"Clicked element: {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Click failed: {str(e)}"}

    def input_text(self, selector, text, by=By.CSS_SELECTOR):
        """Type text into an element using Marionette native commands."""
        try:
            element = self.find_element(selector, by)
            if not element:
                return {"status": "error", "message": f"Element not found: {selector}"}

            # Native Marionette clear command
            element.clear()

            # Native Marionette send_keys command
            element.send_keys(text)
            return {"status": "success", "message": f"Entered text in element: {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Text input failed: {str(e)}"}

    def extract(self, selector, by=By.CSS_SELECTOR):
        """Extract text content from an element using Marionette native property."""
        try:
            element = self.find_element(selector, by)
            if not element:
                return {"status": "error", "message": f"Element not found: {selector}"}

            # Native Marionette text property
            text = element.text
            return {"status": "success", "message": f"Extracted content", "data": text}
        except Exception as e:
            return {"status": "error", "message": f"Extraction failed: {str(e)}"}

    def search(self, query):
        """Generic search method that works on any site with a search box."""
        try:
            # Get current URL to determine what site we're on
            current_url = self.client.get_url()
            print(f"Current URL: {current_url}")

            # Try multiple common search input selectors
            search_selectors = [
                "input[name='q']",  # Common for many sites
                "input[type='search']",  # HTML5 search type
                "input[placeholder*='search' i]",  # Placeholder containing "search"
                "input[aria-label*='search' i]",  # Aria label containing "search"
                ".search-input",  # Common class
                "textarea[name='q']",  # Some sites use textarea
                "#search",  # Common ID
                "[name='s']",  # WordPress and others
                "[name='search']",  # Another common name
                "input[name='query']",  # Another common name
                "[role='search'] input[type='text']",  # Role with text input
                "[role='search'] input:not([type='submit'])",  # Role with non-submit input
                "form input[type='text']"  # Generic form input
            ]

            # Try to find a search input
            search_input = None
            used_selector = None

            for selector in search_selectors:
                try:
                    print(f"Trying selector: {selector}")
                    elements = self.client.find_elements("css selector", selector)
                    if elements and len(elements) > 0:
                        # Make sure we're not selecting a button or submit input
                        for element in elements:
                            element_type = element.get_attribute("type")
                            if element_type != "submit" and element_type != "button":
                                search_input = element
                                used_selector = selector
                                print(f"Found search input with selector: {selector}")
                                break

                        if search_input:
                            break
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue

            if not search_input:
                return {"status": "error", "message": f"Could not find search box on {current_url}"}

            # Try to scroll to the element in a way that works with fixed elements
            try:
                # Try using JavaScript to focus the element directly without scrolling
                self.client.execute_script("arguments[0].focus();", [search_input])
            except Exception as e:
                print(f"Focus attempt failed: {e}")
                try:
                    # Alternative approach - scroll with offset
                    self.client.execute_script("""
                        window.scrollTo(0, 0); 
                        arguments[0].scrollIntoView(false);
                    """, [search_input])
                except Exception as e2:
                    print(f"Scroll attempt failed: {e2}")

            # Clear the input
            try:
                search_input.clear()
            except Exception as clear_error:
                print(f"Clear failed: {clear_error}")
                # Try setting value to empty string with JavaScript
                try:
                    self.client.execute_script("arguments[0].value = '';", [search_input])
                except Exception as js_error:
                    print(f"JavaScript clear failed: {js_error}")

            # Enter text
            try:
                search_input.send_keys(query)
                print(f"Entered search query: {query}")
            except Exception as input_error:
                print(f"Input failed: {input_error}")
                # Try setting value with JavaScript
                try:
                    self.client.execute_script("arguments[0].value = arguments[1];", [search_input, query])
                    print(f"Entered search query with JavaScript: {query}")
                except Exception as js_input_error:
                    print(f"JavaScript input failed: {js_input_error}")
                    return {"status": "error", "message": f"Could not enter search query: {str(js_input_error)}"}

            # Submit the search
            try:
                search_input.send_keys(Keys.RETURN)
                print("Pressed Enter to submit search")
            except Exception as submit_error:
                print(f"Enter key failed: {submit_error}")
                # Try to find and click a search button
                try:
                    # Try common search button selectors
                    button_selectors = [
                        "button[type='submit']",
                        "input[type='submit']",
                        ".search-button",
                        "[aria-label*='search' i]",
                        "button[name='btnK']",  # Google specific
                        "#search-button",
                        "form button",
                        "button:contains('Search')"
                    ]

                    for button_selector in button_selectors:
                        try:
                            buttons = self.client.find_elements("css selector", button_selector)
                            if buttons and len(buttons) > 0:
                                print(f"Found search button with selector: {button_selector}")
                                buttons[0].click()
                                print("Clicked search button")
                                break
                        except Exception as button_error:
                            print(f"Button selector {button_selector} failed: {button_error}")
                except Exception as find_button_error:
                    print(f"Finding button failed: {find_button_error}")
                    # Try submitting the form with JavaScript
                    try:
                        self.client.execute_script("arguments[0].form.submit();", [search_input])
                        print("Submitted form with JavaScript")
                    except Exception as js_submit_error:
                        print(f"JavaScript form submit failed: {js_submit_error}")
                        return {"status": "error", "message": f"Could not submit search: {str(js_submit_error)}"}

            # Wait for results
            time.sleep(3)

            return {
                "status": "success",
                "message": f"Performed search for: {query}",
                "details": f"Used selector: {used_selector}"
            }
        except Exception as e:
            print(f"Search failed with error: {str(e)}")
            return {"status": "error", "message": f"Search failed: {str(e)}"}

    def select_search_result(self, index=0):
        """Click on a search result using generic patterns."""
        # Generic selectors that should work on any site
        selectors = [
            "a[href]:not([href^='#'])",  # Any meaningful link
            "h2 a",  # Heading links (common for results)
            "h3 a",  # Smaller heading links
            "[role='link']",  # ARIA role for links
            "article a",  # Links within articles
            "li a",  # Links in list items
            ".result a",  # Common result class
            "main a",  # Links in main content
            "[role='main'] a"  # Links in main content (ARIA)
        ]

        try:
            # Wait for results to load
            time.sleep(3)

            # Get current URL for logging
            current_url = self.client.get_url()
            print(f"Looking for result #{index + 1} on {current_url}")

            for selector in selectors:
                try:
                    print(f"Trying selector: {selector}")
                    elements = self.client.find_elements(By.CSS_SELECTOR, selector)
                    print(f"Found {len(elements)} elements with selector: {selector}")

                    # Skip if not enough results
                    if not elements or len(elements) <= index:
                        print(f"Not enough results with {selector}, needed at least {index + 1}")
                        continue

                    # Get target element
                    target_element = elements[index]

                    # Get element text for reporting
                    try:
                        element_text = target_element.text
                        if not element_text:
                            element_text = target_element.get_attribute("textContent")
                        element_text = element_text.strip() if element_text else "Unknown"
                        if len(element_text) > 50:
                            element_text = element_text[:50] + "..."
                    except:
                        element_text = "Unknown"

                    print(f"Found result #{index + 1}: {element_text}")

                    # Simple scroll
                    self.client.execute_script("window.scrollBy(0, window.innerHeight/2);")
                    time.sleep(1)

                    # Try clicking directly
                    try:
                        target_element.click()
                        print(f"Clicked on result #{index + 1}")
                        time.sleep(3)  # Wait for page load
                        return {"status": "success", "message": f"Clicked result #{index + 1}: {element_text}"}
                    except Exception as e:
                        print(f"Direct click failed: {e}")
                        # Continue to next element or selector
                except Exception as selector_error:
                    print(f"Error with selector {selector}: {selector_error}")
                    continue

            return {"status": "error", "message": f"Could not find result at index {index}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to click search result: {str(e)}"}

    def get_full_dom_context(self):

        script = """
        function extractAllElements() {
            const elements = Array.from(document.querySelectorAll("*"));
            return elements.map(el => {
                const rect = el.getBoundingClientRect();
                let attrs = {};
                for (let attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return {
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent.trim(),
                    attributes: attrs,
                    position: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    }
                };
            });
        }
        return extractAllElements();
        """
        try:
            return self.client.execute_script(script)
        except Exception as e:
            print("Error extracting full DOM context:", e)
            return []

    def get_dom_context(self, max_elements=200):
        """
        Extract a curated list of key interactive elements from the page.
        This version relaxes filtering so that elements with minimal text but
        with meaningful attributes (like href, placeholder, or aria-label) are included.
        The maximum number of elements returned is increased (default=200).
        """
        script = """
        function getInteractiveElements(maxElements) {
            // Define a selector that covers most interactive elements.
            const selectors = 'a, button, input, textarea, select, [role="button"], [role="link"], [role="search"], [role="textbox"], form';
            const allElements = Array.from(document.querySelectorAll(selectors));

            // Filter for elements that are visible and either have non-empty text
            // OR have at least one meaningful attribute (placeholder, aria-label, id, or href).
            const visibleElements = allElements.filter(el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                  style.visibility !== 'hidden' &&
                                  style.display !== 'none';
                const textPresent = el.textContent && el.textContent.trim().length > 0;
                const hasAttributes = el.getAttribute('placeholder') || el.getAttribute('aria-label') || el.id || el.href;
                return isVisible && (textPresent || hasAttributes);
            });

            // Sort elements by priority:
            // Inputs and buttons first, then anchor tags, then others.
            visibleElements.sort((a, b) => {
                function priority(el) {
                    const tag = el.tagName.toLowerCase();
                    if (tag === 'input' || tag === 'button') return 1;
                    if (tag === 'a') return 2;
                    return 3;
                }
                return priority(a) - priority(b);
            });

            // Limit to maxElements and map to a simplified structure.
            return visibleElements.slice(0, maxElements).map(el => {
                let textContent = el.textContent ? el.textContent.trim() : "";
                if (textContent.length > 100) textContent = textContent.substring(0, 100) + '...';
                return {
                    tag: el.tagName.toLowerCase(),
                    text: textContent,
                    attributes: {
                        id: el.id || null,
                        name: el.name || null,
                        class: el.className || null,
                        placeholder: el.getAttribute('placeholder') || null,
                        'aria-label': el.getAttribute('aria-label') || null,
                        href: el.href || null,
                        title: el.getAttribute('title') || null
                    },
                    position: {
                        top: Math.round(el.getBoundingClientRect().top),
                        left: Math.round(el.getBoundingClientRect().left)
                    }
                };
            });
        }
        return getInteractiveElements(arguments[0] || 200);
        """
        try:
            return self.client.execute_script(script, [max_elements])
        except Exception as e:
            print(f"Error getting DOM context: {e}")
            return []

    def submit_search(self, selector):
        """
        Submit the search by sending the Enter key to the search input.
        This fallback is used when clicking the search button fails.
        """
        try:
            element = self.find_element(selector, by=By.CSS_SELECTOR)
            if element:
                from marionette_driver.keys import Keys
                # Ensure the element is focused before sending the key events
                self.client.execute_script("arguments[0].focus();", [element])
                time.sleep(0.5)
                # Simulate a keydown, keypress, and keyup sequence for the Enter key
                element.send_keys(Keys.RETURN)
                time.sleep(3)
                return {"status": "success", "message": f"Submitted search via Enter on {selector}"}
            else:
                return {"status": "error", "message": f"Search input not found: {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Error submitting search: {str(e)}"}

    def click_by_coordinates(self, x: int, y: int) -> dict:
        """
        Click an element at the given viewport coordinates (x, y).
        Uses document.elementFromPoint to find the element and triggers its click event.
        """
        try:
            script = """
                var elem = document.elementFromPoint(arguments[0], arguments[1]);
                if (elem) {
                    elem.click();
                    return true;
                } else {
                    return false;
                }
            """
            result = self.client.execute_script(script, [x, y])
            if result:
                return {"status": "success", "message": f"Clicked at coordinates ({x}, {y})"}
            else:
                return {"status": "error", "message": f"No element found at coordinates ({x}, {y})"}
        except Exception as e:
            return {"status": "error", "message": f"Click by coordinates failed: {str(e)}"}

    def get_target_coordinates_ocr(self, target_text: str, confidence_threshold: int = 60) -> dict:
        """
        Capture the current screenshot, use pytesseract OCR to detect text, and return the center
        coordinates of the first bounding box that contains the target text.

        Args:
          target_text (str): The text you are looking for (e.g., "Add to cart", "Search").
          confidence_threshold (int): Minimum OCR confidence (0-100) to consider the detection valid.

        Returns:
          A dictionary with {"x": int, "y": int} if found, or an empty dict if not.
        """
        try:
            # Capture screenshot as a base64-encoded string
            screenshot_b64 = self.client.screenshot(format='base64')
            # Decode the base64 string
            screenshot_bytes = base64.b64decode(screenshot_b64)
            # Convert to numpy array and decode image with OpenCV
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Convert image to grayscale for better OCR performance
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Run OCR with pytesseract to get detailed data
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

            num_boxes = len(data['text'])
            for i in range(num_boxes):
                text = data['text'][i].strip()
                try:
                    conf = int(data['conf'][i])
                except:
                    conf = 0
                # Check if OCR confidence is above threshold and target_text appears in the detected text
                if conf > confidence_threshold and target_text.lower() in text.lower():
                    left = data['left'][i]
                    top = data['top'][i]
                    width = data['width'][i]
                    height = data['height'][i]
                    # Calculate the center coordinates
                    x_center = left + width // 2
                    y_center = top + height // 2
                    print(f"OCR detected '{text}' at ({x_center}, {y_center}) with confidence {conf}")
                    return {"x": x_center, "y": y_center}
            print(f"OCR did not find any text matching '{target_text}' with confidence above {confidence_threshold}")
            return {}
        except Exception as e:
            print("Error in get_target_coordinates_ocr:", e)
            return {}


