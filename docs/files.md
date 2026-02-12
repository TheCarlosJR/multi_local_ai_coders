```
ROOT/
├─ agents/
│   ├─ planner.py
│   ├─ executor.py
│   ├─ reviewer.py
│   └─ memory.py
├─ core/
│   ├─ agent_runner.py
│   ├─ prompts.py
│   └─ config.py
├─ docs/
│   └─ requirements.txt
├─ prompts/
│   ├─ base_prompt.py
│   ├─ commit_message_prompt.py
│   ├─ error_recovery_prompt.py
│   ├─ executor_prompt.py
│   ├─ memory_retrieval_prompt.py
│   ├─ os_detection_prompt.py
│   ├─ planner_prompt.py
│   └─ reviewer_prompt.py
├─ tools/
│   ├─ filesystem_tool.py
│   ├─ git_tool.py
│   ├─ terminal_tool.py
│   └─ web_tool.py
├─ vector_store/
│   └─ chromadb_store.py
└─ main.py
```