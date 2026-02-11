import os
import sys

# Add project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, PROJECT_ROOT)

from core.context_manager import ContextManager
from main import process_command

def test_intent(text):
    """
    Tests the intent detection for a given text.
    """
    context = ContextManager()
    response, lang, intent = process_command(text, context)
    print(f"Text: '{text}'")
    print(f"Intent: {intent}")
    print(f"Response: {response}")
    print("-" * 20)

if __name__ == "__main__":
    test_intent("which day it is")
    test_intent("what time is it")
    test_intent("what's the weather like in London")
    test_intent("what's the weather like")
    test_intent("open chrome")
    test_intent("hello there")
    test_intent("goodbye")
