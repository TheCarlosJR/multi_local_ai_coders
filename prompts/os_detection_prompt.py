from textwrap import dedent

OS_CONTEXT_PROMPT = dedent("""
The current operating system is: {os}

When generating terminal commands:
- Use appropriate shell syntax.
- Avoid destructive system-level operations.
- Stay inside project directory.
""")
