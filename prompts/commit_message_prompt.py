from textwrap import dedent

COMMIT_PROMPT = dedent("""
Generate a professional git commit message.

Context:
- Goal: {goal}
- Changes: {changes}

Rules:
- Use conventional commits format.
- Be concise.
- Mention impacted modules.
""")
