from textwrap import dedent

ERROR_RECOVERY_PROMPT = dedent("""
The previous execution failed.

Error log:
{error_log}

Analyze root cause and propose a fix.

Return ONLY valid JSON:

{{
  "root_cause": "What went wrong",
  "fix_strategy": "How to fix it",
  "next_step": "What to try next"
}}

Be precise.
Do not repeat the same mistake.
""")
