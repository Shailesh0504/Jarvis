"""
testing.py - Test all Jarvis commands and show intent + response.
Run: python testing.py
Optional: python testing.py --verbose  (show full response text)
          python testing.py --filter greet  (run only tests containing "greet")
"""
import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, PROJECT_ROOT)


def run_tests(verbose: bool = False, filter_keyword: str = None):
    try:
        from core.context_manager import ContextManager
        from core.nlp import initialize as initialize_nlp
        from main import process_command
    except Exception as e:
        print("Init failed:", e)
        import traceback
        traceback.print_exc()
        return

    # Minimal init so intent detection works (skip index/training for speed)
    initialize_nlp()
    context = ContextManager()

    # Test commands: (user input, optional expected intent for pass/fail)
    TEST_COMMANDS = [
        # Greetings & goodbye
        ("hi", "greet"),
        ("hello jarvis", "greet"),
        ("good night", "good_night"),
        ("good morning", None),
        ("bye", None),
        # Time & date
        ("time kya hua hai", "get_time"),
        ("what is the time", "get_time"),
        ("aaj ki tarikh kya hai", "get_date"),
        # Behavioural (reasoning + sleep)
        ("to main soya kyun nahi abhi tak", "reasoning_question"),
        ("mujhe nind nahi aa rahi hai", "sleep_issue"),
        # Reminder / alarm
        ("mujhe kal 5:10 am ko jaga dena", "reminder"),
        ("remind me at 9 pm", "reminder"),
        # Todo
        ("mera todo dikhao", "show_todo_list"),
        ("aaj kya pending hai", None),
        ("recycle bin clear karo", "clear_recycle_bin"),
        # System / cleanup
        ("clear recycle bin", "clear_recycle_bin"),
        ("lock system", "lock_system"),
        # Media
        ("play shape of you on youtube", "play_youtube"),
        ("play my favourite", None),
        # Info
        ("battery kitni hai", "get_battery_status"),
        ("tell me a joke", None),
        ("latest news", "get_news"),
        # Conversation end
        ("kuch nahi", "graceful_end"),
        ("thanks", "appreciation"),
    ]

    if filter_keyword:
        TEST_COMMANDS = [(c, e) for c, e in TEST_COMMANDS if filter_keyword.lower() in (c + (e or "")).lower()]

    results = []
    for cmd, expected_intent in TEST_COMMANDS:
        # Fresh context per command so greet/good_night/graceful_end aren't blocked by has_active_conversation()
        context = ContextManager()
        context.set("original_utterance", cmd)
        try:
            responses, lang, intent_objs, status = process_command(cmd, context, quiet=True)
        except Exception as e:
            results.append((cmd, None, f"[Error: {e}]", "failure", expected_intent, None))
            continue

        intent_str = ""
        if intent_objs:
            intent_str = ", ".join(obj.get("intent", "?") for obj in intent_objs)
        else:
            intent_str = "(none)"

        response_text = (responses[0] if responses else "") or ""
        if not verbose and len(response_text) > 70:
            response_text = response_text[:67] + "..."

        passed = None
        if expected_intent and intent_str:
            passed = expected_intent in intent_str
        elif expected_intent and not intent_str:
            passed = False

        results.append((cmd, intent_str, response_text, status, expected_intent, passed))

    # Print table
    col_cmd = 42
    col_intent = 28
    col_status = 10
    col_ok = 6

    def row(a, b, c, d, e=None):
        ok = ""
        if e is True:
            ok = "  OK"
        elif e is False:
            ok = " FAIL"
        return (
            (a[: col_cmd - 1] + ".." if len(a) > col_cmd else a).ljust(col_cmd)
            + (b[: col_intent - 1] + ".." if len(b) > col_intent else b).ljust(col_intent)
            + str(c).ljust(col_status)
            + ok
        )

    print()
    print("=" * (col_cmd + col_intent + col_status + col_ok + 2))
    print("  JARVIS COMMAND TEST RESULTS")
    print("=" * (col_cmd + col_intent + col_status + col_ok + 2))
    print(row("COMMAND", "INTENT", "STATUS", "OK?"))
    print("-" * (col_cmd + col_intent + col_status + col_ok + 2))

    for r in results:
        cmd = r[0]
        intent_str = r[1] or "(none)"
        status = r[3]
        expected = r[4]
        passed = r[5] if len(r) > 5 else None
        print(row(cmd, intent_str, status, passed))

    print("-" * (col_cmd + col_intent + col_status + col_ok + 2))

    if verbose:
        print("\n--- RESPONSES (full) ---")
        for r in results:
            print(f"  [{r[0]}]")
            print(f"    -> {r[2]}")
            print()

    # Summary
    with_expected = [r for r in results if r[4] is not None]
    if with_expected:
        passed_count = sum(1 for r in with_expected if r[5] is True)
        fail_count = sum(1 for r in with_expected if r[5] is False)
        print(f"Expected intent check: {passed_count} passed, {fail_count} failed (of {len(with_expected)} with expected intent)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Jarvis commands and show intent + response.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full response text")
    parser.add_argument("--filter", "-f", type=str, default=None, help="Run only tests containing this keyword (e.g. greet)")
    args = parser.parse_args()
    run_tests(verbose=args.verbose, filter_keyword=args.filter)
