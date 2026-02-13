"""
Error Pattern Analysis Prompt

Used by ErrorPatternAgent to analyze failures and suggest recovery strategies.
"""


def get_error_analysis_prompt(error_message: str, code_context: str, 
                             goal: str, language: str,
                             similar_patterns: list) -> str:
    """
    Generate prompt for LLM to analyze error and suggest solutions.
    
    Args:
        error_message: The error/exception message
        code_context: Code snippet that caused error
        goal: Original goal/task
        language: Programming language
        similar_patterns: Similar error patterns from database
    
    Returns:
        Structured prompt for error analysis
    """
    
    similar_context = ""
    if similar_patterns:
        similar_context = "\n## Similar Error Patterns from History\n"
        for pattern in similar_patterns[:3]:
            similar_context += f"""
- **Pattern**: {pattern.get('signature')}
  - Frequency: {pattern.get('frequency')} times
  - Success Rate: {pattern.get('success_rate', 0):.1%}
  - Best Solution: {pattern.get('best_solution', 'Unknown')}
"""
    
    prompt = f"""## Error Analysis & Recovery

### Original Task
**Goal**: {goal}
**Language**: {language}

### Error Occurred
**Error Message**:
```
{error_message}
```

### Code Context
```{language}
{code_context}
```
{similar_context}

### Your Task
Analyze this error and provide:

1. **Root Cause Analysis** (2-3 sentences)
   - What went wrong?
   - Why did it happen?
   - Is it a common issue?

2. **Error Classification**
   - Category: [syntax|type|logic|runtime|missing_dependency|etc]
   - Severity: [critical|high|medium|low]
   - Recoverable: [yes|no]

3. **Immediate Fix (Quick Recovery)**
   - Provide ONE specific code fix to resolve this error
   - Make it minimal and focused
   - Explain the fix in 1 sentence

4. **Preventive Measures (For Future)**
   - What should be checked BEFORE running code?
   - Any defensive programming patterns?
   - Testing strategy?

5. **Confidence Level**
   - How confident are you in the fix? (0-100%)
   - Any uncertainties?

### Response Format (JSON)
{{
  "root_cause": "explanation",
  "category": "error_category",
  "severity": "high",
  "recoverable": true,
  "immediate_fix": "code or explanation",
  "fix_code": "code snippet in {language}",
  "fix_explanation": "why this works",
  "preventive_measures": ["measure1", "measure2"],
  "confidence": 85,
  "uncertainties": []
}}

Focus on practical, actionable solutions."""
    
    return prompt


def get_error_pattern_summary_prompt(pattern_data: dict) -> str:
    """
    Generate prompt to summarize an error pattern for documentation.
    
    Args:
        pattern_data: Error pattern information
    
    Returns:
        Prompt for pattern summarization
    """
    
    solutions_context = ""
    if pattern_data.get("solutions"):
        solutions_context = "### Previous Solutions Tried\n"
        for sol in pattern_data["solutions"]:
            solutions_context += f"""
- {sol.get('description')}
  - Type: {sol.get('type')}
  - Success Rate: {sol.get('success_rate', 0):.1%}
  - Attempts: {sol.get('attempts', 0)}
"""
    
    prompt = f"""## Error Pattern Summary

### Pattern Information
**Signature**: {pattern_data.get('signature')}
**Error Type**: {pattern_data.get('error_type')}
**Language**: {pattern_data.get('language')}
**Occurrences**: {pattern_data.get('frequency', 0)}
**First Seen**: {pattern_data.get('first_seen')}

### Code Samples
```{pattern_data.get('language', 'python')}
{chr(10).join(s.get('code', '') for s in pattern_data.get('code_samples', [])[:2])}
```

{solutions_context}

### Task
Create a concise documentation entry for this recurring error:

1. **What is this error pattern?** (1 sentence)
2. **When does it occur?** (Common scenarios)
3. **Best known solution** (Explain the most successful fix)
4. **Quick reference** (One-liner for developers)

Format as markdown."""
    
    return prompt


def get_pattern_learning_prompt(successes: list, failures: list) -> str:
    """
    Generate prompt to extract learning from success/failure patterns.
    
    Args:
        successes: List of successful error recoveries
        failures: List of failed recovery attempts
    
    Returns:
        Prompt for pattern learning
    """
    
    prompt = """## Error Recovery Pattern Learning

### Successful Recoveries
"""
    for success in successes[:3]:
        prompt += f"""
- **Error**: {success.get('error_type')}
  - **Fix Applied**: {success.get('solution')}
  - **Result**: Success
  - **Time Taken**: {success.get('duration_seconds')}s
"""
    
    prompt += "\n### Failed Recovery Attempts\n"
    for failure in failures[:3]:
        prompt += f"""
- **Error**: {failure.get('error_type')}
  - **Fix Attempted**: {failure.get('solution')}
  - **Result**: Failed
  - **Reason**: {failure.get('failure_reason')}
"""
    
    prompt += """

### Analysis Task
Based on the patterns above, answer:

1. **What distinguishes successful from failed fixes?**
2. **Are there common characteristics in successful solutions?**
3. **What makes some fixes fail?**
4. **General principles for this error category?**
5. **Recommended strategy for future occurrences**

Provide insights as JSON for training the pattern database."""
    
    return prompt


def get_preemptive_fix_prompt(code: str, language: str, goal: str) -> str:
    """
    Generate prompt to suggest preemptive fixes before code execution.
    
    Args:
        code: Code to analyze
        language: Programming language
        goal: What the code is supposed to do
    
    Returns:
        Prompt for preemptive analysis
    """
    
    prompt = f"""## Preemptive Error Prevention

### Code Analysis
**Language**: {language}
**Goal**: {goal}

**Code**:
```{language}
{code}
```

### Potential Issues Detection
Scan this code for patterns that commonly cause errors:

1. **Missing Error Handling**
   - Are there try/except blocks where needed?
   - What could fail? (I/O, network, parsing)

2. **Type Safety Issues**
   - Type mismatches between variables/functions?
   - Unchecked conversions?
   - Missing type hints?

3. **Logic Errors**
   - Off-by-one errors?
   - Infinite loops?
   - Unreachable code?

4. **Resource Management**
   - Files left open?
   - Connections not closed?
   - Memory leaks?

5. **Data Validation**
   - Unchecked user input?
   - Missing null/empty checks?
   - Assumptions about data structure?

### Response Format
```json
{{
  "issues": [
    {{
      "type": "missing_error_handling",
      "severity": "high",
      "location": "line X",
      "description": "...",
      "suggested_fix": "..."
    }}
  ],
  "overall_risk": "medium",
  "recommendations": ["...", "..."]
}}
```

Focus on likely runtime errors."""
    
    return prompt
