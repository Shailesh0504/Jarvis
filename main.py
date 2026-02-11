# main.py - Jarvis Voice Assistant
# Default: python main.py              (tray + Type-to-Jarvis GUI + voice)
#           python main.py --voice-only (voice-only, no GUI)
#           python main.py --enhanced   (professional audio - use with tray or --voice-only)

import sys
import time

# Colorful terminal (colorama) - init early so all prints can use it
try:
    from core.terminal_colors import init as init_terminal_colors, you, jarvis, tag, shutdown
    init_terminal_colors()
except Exception:
    def you(t): return f"You: {t}"
    def jarvis(t): return f"Jarvis: {t}"
    def tag(l, t, c=None): return f"[{l}] {t}"
    def shutdown(t): return t
from core.ai_fallback import ai_reply
from skills.web_search import open_google_search
from core.async_listener import AsyncListener
from core import command_router  # module ref for hot-reload
from core.context_manager import ContextManager
from core import intent_detector  # module ref for hot-reload
from core import reasoning_engine  # module ref for hot-reload
from core.speaker_async import speak_async
from core.learning_manager import learn as learn_correction, DANGEROUS_INTENTS, record_pattern_use
from core.translator import detect_language, to_english
from core.app_indexer import build_index
from skills.battery_monitor import start_battery_monitor, stop_battery_monitor
from skills.outlook_listener import start_outlook_listener
from core.service_manager import ServiceManager
from skills.todo import get_pending_todos_summary
from core.nlp import initialize as initialize_nlp
from core.command_logger import get_logger  # Self-improvement logging
from core.auto_trainer import auto_train_on_startup  # Automatic self-learning
from scripts.train_intent_model import smart_train_on_startup  # ML model training

# Enhanced listener for professional audio (optional)
ENHANCED_AUDIO_AVAILABLE = False
try:
    from core.enhanced_listener import EnhancedListener, create_enhanced_listener
    ENHANCED_AUDIO_AVAILABLE = True
except ImportError:
    pass


def create_listener(enhanced: bool = False, debug: bool = False):
    """
    Create the appropriate listener based on mode.
    
    Args:
        enhanced: If True, use professional audio processing (far-field, noise suppression)
        debug: Enable debug output
        
    Returns:
        Listener instance (AsyncListener or EnhancedListener)
    """
    if enhanced and ENHANCED_AUDIO_AVAILABLE:
        print(tag("Jarvis", "🎤 Professional audio mode enabled (far-field, noise suppression)"))
        return create_enhanced_listener(
            far_field=True,
            language="hi-IN",
            debug=debug
        )
    else:
        if enhanced and not ENHANCED_AUDIO_AVAILABLE:
            print(tag("Jarvis", "⚠️ Enhanced audio not available, install scipy and webrtcvad"))
        return AsyncListener(debug=debug)

def drain_with_continuation(listener, continuation_sec: float = 1.0) -> str | None:
    """
    Non-blocking: get one recognized phrase, optionally merging continuations
    (e.g. "open" then "Chrome") into a single command. Returns None if no input.
    """
    raw_text = listener.get_text()
    if not raw_text or not (text := raw_text.strip()):
        return None
    parts = [text]
    start = time.time()
    while time.time() - start < continuation_sec:
        more = listener.get_text()
        if more and (more := more.strip()):
            parts.append(more)
            start = time.time()
        time.sleep(0.06)
    return " ".join(parts)


def process_command(text: str, context: ContextManager, quiet: bool = False) -> tuple[list[str], str, list[dict] | None, str]:
    """
    Processes the command text and returns:
    - list of responses
    - language
    - list of intent objects
    - result status: "success" | "fallback" | "not_found" | "failure"

    Pipeline (smart rule-based): intent samajhna → context se refine → flexible rules + friendly templates se react (natural, dost-jaisi). Speech → Translate + Normalize → [intent pipeline] → route or AI fallback.
    quiet: if True, do not print "You: ..." (for testing.py).
    """
    if not quiet:
        print(you(text))
    context.set("original_utterance", text)
    
    try:
        context.update_active_window(force=True)
    except Exception:
        pass

    # --- Translate + Normalize (once): lang detect + to_english; normalize is inside detect_intent (preprocess)
    lang = detect_language(text)
    text_en = text
    if lang != "en":
        text_en = to_english(text, lang)
        if text_en == text:
            response = "I'm having a bit of trouble with translation right now. Could you please try that in English?"
            return [response], lang, None, "failure"

    # --- Emotion (lightweight signal: tone + verbosity, does not replace intent)
    from core.emotion_detector import detect_emotion
    context.set("user_emotion", detect_emotion(text_en))

    # --- Conversation state first: when in human-like flow (flirt/casual), handle turn — no Google, no commands
    conv_state = context.get("conversation_state")
    if conv_state in ("QUESTION", "FOLLOW_UP", "DEPTH"):
        try:
            from core.conversation_flow import handle_conversation_flow
            resp, handled = handle_conversation_flow(text_en, context)
            if handled and resp:
                return [resp], lang, None, "success"
        except Exception:
            pass

    # --- IQ Quiz: if user is in the middle of the quiz, treat input as answer
    try:
        from skills.iq_quiz import is_iq_quiz_active, handle_iq_answer
        if is_iq_quiz_active(context):
            iq_resp = handle_iq_answer(text_en, context)
            if iq_resp:
                return [iq_resp], lang, None, "success"
    except Exception:
        pass

    intent_objs = intent_detector.detect_intent(text_en, context)
    # Reasoning: disambiguate intents using context (e.g. "open serverv list" → server list, not todo)
    # Also: short "wahi"/"dubara" → repeat last action when applicable (natural conversation)
    intent_objs = reasoning_engine.refine_intents(intent_objs, text_en, context)

    # Self-correction: user was asked "kya karna chahiye tha?" and now replied with an intent
    if context.has("waiting_for_correction") and intent_objs:
        data = context.get("waiting_for_correction") or {}
        last_user_text = data.get("user_text") or ""
        wrong_intent = data.get("wrong_intent")
        correct_intent = intent_objs[0].get("intent")
        if last_user_text and correct_intent:
            if correct_intent in DANGEROUS_INTENTS:
                context.set("waiting_for_correction", None)
                return (
                    ["Ye action main learn nahi karti — safety ke liye. Koi aur bataiye?"],
                    lang,
                    intent_objs,
                    "success",
                )
            learn_correction(last_user_text, correct_intent, wrong_intent)
        context.set("waiting_for_correction", None)
        return (
            ["Noted. Agli baar main wohi samajh kar sahi karungi."],
            lang,
            intent_objs,
            "success",
        )

    responses = []
    result_status = "success"

    if intent_objs:
        # Sophisticated decision: low confidence + ambiguous → ask one natural clarification
        if len(intent_objs) == 1 and reasoning_engine.should_clarify_before_acting(intent_objs, text_en, context):
            responses.append("Isi ki baat kar rahe ho? Thoda aur bata do, sahi se kar doongi.")
            result_status = "clarify"
            return responses, lang, intent_objs, result_status
        # Pipeline: intent found → route
        for intent_obj in intent_objs:
            response = command_router.route_command(intent_obj, text_en, context)
            if response:
                responses.append(response)
            # Reason explanation mode: append why we chose this intent (if enabled)
            try:
                from config.settings import SETTINGS
                if SETTINGS.get("reason_explanation_mode"):
                    intent_name = intent_obj.get("intent")
                    explanation = reasoning_engine.explain_choice(intent_name, text_en, context)
                    if explanation:
                        responses.append(explanation)
            except Exception:
                pass
                # Check if response indicates failure/not_found
                if isinstance(response, str):
                    response_lower = response.lower()
                    if any(kw in response_lower for kw in ["nahi mila", "not found", "couldn't find", "samajh nahi", "didn't understand"]):
                        result_status = "not_found"
        # LEVEL 2: Record pattern use for frequency learning (same text + intent seen N times)
        if responses and result_status == "success":
            try:
                record_pattern_use(text_en, intent_objs[0].get("intent", ""))
            except Exception:
                pass
    else:
        # No intent matched — sophisticated decision: short vague input → natural prompt, not search
        query = (text_en or "").strip()
        word_count = len(query.split())
        last_action = getattr(context, "get_last_action", lambda: None)()
        if word_count <= 3 and query and last_action:
            # Short vague reply after doing something: offer to repeat or ask for more
            responses.append(
                "Samajh nahi aaya. Kuch aur bolo, ya wahi kaam dobara karoon?"
                if last_action in ("open_app", "play_youtube", "open_website") else
                "Thoda detail mein bolo, ya main search karke bata doon?"
            )
            result_status = "fallback"
        elif len(query) >= 2 and word_count > 3:
            response = open_google_search(query)
            responses.append(response)
            result_status = "fallback"
        else:
            response = ai_reply(text_en, context)
            if response:
                responses.append(response)
            result_status = "fallback"
    
    return responses, lang, intent_objs, result_status


def main(enhanced_audio: bool = False, debug: bool = False):
    """
    Main function to run Jarvis.
    
    Args:
        enhanced_audio: Enable professional audio mode (far-field, noise suppression)
        debug: Enable debug output
    """
    # Initialize services and models
    initialize_nlp()
    build_index(force=False, max_age_hours=24)
    
    # 🤖 ML MODEL: Retrain if intents.json changed (skips if up-to-date)
    smart_train_on_startup(verbose=debug)
    
    # 🧠 AUTO-LEARNING: Learn from previous sessions (skips if no new data)
    auto_train_on_startup(force=False, verbose=debug)
    
    # ⏰ CHECK MISSED REMINDERS: Show any reminders missed in the last hour
    from skills.reminder import check_missed_reminders_on_startup
    check_missed_reminders_on_startup()

    context = ContextManager()
    listener = create_listener(enhanced=enhanced_audio, debug=debug)
    logger = get_logger()  # Command logger for self-improvement
    
    service_manager = ServiceManager()
    service_manager.register("listener", listener.start, listener.stop)
    service_manager.register("battery_monitor", start_battery_monitor, stop_battery_monitor)
    service_manager.register("outlook_listener", start_outlook_listener)
    
    service_manager.start_all()

    # Startup: battery % in soft Hinglish
    from skills.battery_info import get_battery_startup_message_hinglish
    startup_msg = get_battery_startup_message_hinglish()
    print(jarvis(startup_msg))
    speak_async(startup_msg, lang="hi")

    # Speak = dedicated thread (speaker_async). Listen = dedicated threads (AsyncListener capture + STT).
    # Main loop only polls get_text() and calls speak_async(); neither blocks the other.
    try:
        while True:
            text = drain_with_continuation(listener)
            if not text:
                time.sleep(0.05)
                continue

            responses, lang, intent_objs, result_status = process_command(text, context)
            
            # Get English text for logging
            text_en = context.get("original_utterance", text)
            if lang != "en":
                text_en = to_english(text, lang) or text

            if responses:
                full_response = ". ".join(str(r) if not isinstance(r, dict) else r.get("speak", str(r)) for r in responses)
                # Never echo user input as response (dangerous / confusing)
                norm_user = (text or "").strip().lower()
                norm_resp = full_response.strip().lower()
                if norm_user and (
                    norm_resp == norm_user
                    or (norm_user in norm_resp and len(norm_resp) < len(norm_user) + 100)
                ):
                    full_response = "Theek hai 😊 main abhi kuch shant sa chala rahi hoon."
                print(jarvis(full_response))
                
                # Tone: story TTS (sentence pauses) overrides; else emotion, then intent-based
                tts_story = any(isinstance(r, dict) and r.get("tts_mode") == "story" for r in responses)
                last_intent = intent_objs[-1] if intent_objs else None
                if tts_story:
                    tone = "story"
                    lang = "hi"
                else:
                    emotion = context.get("user_emotion") or "neutral"
                    if emotion == "angry":
                        tone = "calm"
                    elif emotion == "frustrated":
                        tone = "supportive"
                    elif emotion == "sleepy":
                        tone = "soft"
                    else:
                        tone = "default"
                        if last_intent:
                            intent_str = last_intent.get("intent", "")
                            if any(k in intent_str for k in ["time", "date", "greet", "joke", "reminder", "email"]):
                                tone = "success"
                            elif any(k in intent_str for k in ["exit", "shutdown", "restart", "lock"]):
                                tone = "notify"

                speak_async(full_response, lang, tone=tone)
                intent_name = last_intent.get("intent") if last_intent else None
                entities = last_intent.get("entities", {}) if last_intent else {}
                context.remember_turn(intent=intent_name, user_text=text, response=full_response, entities=entities)
                
                # ✅ LOG COMMAND FOR SELF-IMPROVEMENT
                logger.log_command(
                    text=text,
                    text_en=text_en if text_en != text else None,
                    intent_obj=last_intent,
                    result=result_status,
                    response=full_response
                )

            if intent_objs and any(i.get("intent") == "exit" for i in intent_objs):
                from core.speaker_async import wait_until_done
                wait_until_done(timeout=15.0)  # let full goodbye message finish before exit
                raise SystemExit("Exiting on user command.")

    except (KeyboardInterrupt, SystemExit):
        print(shutdown("Shutting down..."))
    finally:
        service_manager.stop_all()


def run_with_tray():
    """Run Jarvis with system tray icon and GUI."""
    import threading

    # Initialize core services first
    debug = "--debug" in sys.argv or "-d" in sys.argv
    if debug:
        print(tag("Jarvis", "Initializing..."))
    initialize_nlp()
    build_index(force=False, max_age_hours=24)

    # 🤖 ML MODEL: Retrain if intents.json changed
    smart_train_on_startup(verbose=debug)

    # 🧠 AUTO-LEARNING: Learn from previous sessions
    auto_train_on_startup(force=False, verbose=debug)

    # ⏰ CHECK MISSED REMINDERS: Show any reminders missed in the last hour
    from skills.reminder import check_missed_reminders_on_startup
    check_missed_reminders_on_startup()

    # Now import and run tray
    from desktop_overlay.tray import run_tray, service_manager, _init_app

    # Initialize the GUI app and show Type-to-Jarvis window by default
    app = _init_app()
    app.root.after(100, app.show)

    # Register services
    service_manager.register("battery_monitor", start_battery_monitor, stop_battery_monitor)
    service_manager.start_all()

    # Start Outlook listener
    start_outlook_listener()

    # Run tray in background thread
    threading.Thread(target=run_tray, daemon=True).start()

    # Startup greeting: battery % in soft Hinglish (after a short delay so tray is ready)
    from skills.battery_info import get_battery_startup_message_hinglish
    def _speak_startup():
        msg = get_battery_startup_message_hinglish()
        speak_async(msg, lang="hi")
    app.root.after(1200, _speak_startup)

    # Run tkinter mainloop (must be in main thread)
    if debug:
        print(tag("Jarvis", "System tray is running. Right-click the tray icon for options."))
    app.root.mainloop()


JARVIS_BANNER = r"""
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║         ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗          ║
   ║         ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝          ║
   ║         ██║███████║██████╔╝██║   ██║██║███████╗          ║
   ║    ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║          ║
   ║    ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║          ║
   ║     ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝          ║
   ║                                                          ║
   ║          Just A Rather Very Intelligent System           ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(JARVIS_BANNER)
    # Check command line arguments
    if "--voice-only" in sys.argv or "-v" in sys.argv:
        # Voice-only mode (no tray, no Type-to-Jarvis GUI)
        enhanced = "--enhanced" in sys.argv or "--pro" in sys.argv
        debug = "--debug" in sys.argv or "-d" in sys.argv
        main(enhanced_audio=enhanced, debug=debug)
    elif "--help" in sys.argv or "-h" in sys.argv:
        print("""
Jarvis Voice Assistant - Like Iron Man's JARVIS for your PC

Usage:
    python main.py               Run with tray + Type-to-Jarvis GUI + voice (default)
    python main.py --voice-only  Run voice-only mode (no GUI)
    python main.py -v            Same as --voice-only
    python main.py --enhanced    Professional audio (use with default or --voice-only)
    python main.py --pro         Same as --enhanced
    python main.py --debug       Enable debug output
    python main.py --help        Show this help message

Default mode starts: system tray icon + Type-to-Jarvis window + voice.

Audio Modes:
    Standard:  Basic microphone capture with Google STT
    Enhanced:  Professional-grade audio (pip install scipy webrtcvad)

Examples:
    python main.py                     Tray + GUI (default)
    python main.py --voice-only        Voice only, no GUI
    python main.py --enhanced --debug  Far-field with debug
        """)
    else:
        # Default: run with tray + Type-to-Jarvis GUI
        run_with_tray()
