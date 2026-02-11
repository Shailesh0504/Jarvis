# analyze_commands.py - Analyze Command Logs for Self-Improvement
# Run this script to see what commands are failing and need retraining

"""
Usage:
    python analyze_commands.py          # Print analysis report
    python analyze_commands.py --export # Export data for retraining
    python analyze_commands.py --json   # Print stats as JSON
"""

import sys
import json
from core.command_logger import (
    get_intent_stats,
    get_training_suggestions,
    print_analysis_report,
    export_for_retraining,
    get_failure_logs,
    get_fallback_logs
)


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--export":
            output_file = export_for_retraining()
            print(f"✅ Retraining data exported to: {output_file}")
            return
        
        if arg == "--json":
            stats = get_intent_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
            return
        
        if arg == "--failures":
            failures = get_failure_logs()
            print(f"\n📋 Total Failures: {len(failures)}\n")
            for f in failures[-20:]:  # Last 20 failures
                print(f"  • \"{f.get('text')}\" → {f.get('intent')} → {f.get('result')}")
            return
        
        if arg == "--fallbacks":
            fallbacks = get_fallback_logs()
            print(f"\n📋 Total Fallbacks (No Intent Detected): {len(fallbacks)}\n")
            for f in fallbacks[-20:]:  # Last 20 fallbacks
                print(f"  • \"{f.get('text')}\"")
            return
        
        if arg == "--suggestions":
            suggestions = get_training_suggestions()
            print(f"\n💡 Training Suggestions (Top {len(suggestions)}):\n")
            for i, s in enumerate(suggestions, 1):
                print(f"  {i}. \"{s['text']}\"")
                print(f"     Count: {s['count']}x | Detected: {s['detected_intent']}")
                print(f"     → {s['suggestion']}\n")
            return
        
        if arg == "--help":
            print(__doc__)
            return
    
    # Default: print full report
    print_analysis_report()


if __name__ == "__main__":
    main()
