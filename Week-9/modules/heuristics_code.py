# modules/heuristics_code.py
"""
Code-level heuristics for query processing, tool selection, and result validation.
All heuristics run in Python, not in prompts.
"""

import re
import ast
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

# === HEURISTIC 1: Query Length Guard ===
def apply_query_length_guard(query: str, max_length: int = 1500) -> str:
    """Truncate or summarize queries exceeding max_length."""
    if len(query) <= max_length:
        return query
    
    # Simple truncation with ellipsis
    truncated = query[:max_length - 50] + "...[truncated for length]"
    return truncated


# === HEURISTIC 2: Tool Confidence Scoring ===
def score_tool_confidence(
    tool_name: str,
    query: str,
    tool_description: str,
    recent_successes: List[str],
    threshold: float = 0.3
) -> float:
    """
    Score tool by similarity to query + recent success rate.
    Returns score between 0.0 and 1.0.
    """
    # Similarity score (0.0 to 1.0)
    similarity = SequenceMatcher(None, query.lower(), tool_description.lower()).ratio()
    
    # Recent success bonus (0.0 to 0.3)
    success_bonus = 0.3 if tool_name in recent_successes else 0.0
    
    # Combined score
    score = (similarity * 0.7) + success_bonus
    
    return score


def filter_tools_by_confidence(
    tools: List[Dict[str, Any]],
    query: str,
    recent_successes: List[str],
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """Filter tools below confidence threshold."""
    filtered = []
    for tool in tools:
        tool_name = tool.get("name", "")
        tool_desc = tool.get("description", "")
        
        score = score_tool_confidence(tool_name, query, tool_desc, recent_successes, threshold)
        
        if score >= threshold:
            filtered.append(tool)
    
    return filtered if filtered else tools  # Fallback to all if none pass


# === HEURISTIC 3: Unsafe Argument Filter ===
UNSAFE_PATTERNS = [
    r'\.\./+',  # Path traversal
    r'<script',  # XSS
    r'</script',
    r'delete\s+from',  # SQL injection
    r'drop\s+table',
    r'rm\s+-rf',  # Dangerous shell
    r'eval\(',
    r'exec\(',
    r'__import__',
    r'system\(',
    r'popen\(',
]

def contains_unsafe_arguments(code: str) -> bool:
    """Check if code contains unsafe patterns."""
    code_lower = code.lower()
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, code_lower, re.IGNORECASE):
            return True
    return False


# === HEURISTIC 4: Sandbox Execution Timeout ===
# (Implemented in action.py using asyncio.wait_for)
SANDBOX_TIMEOUT_SECONDS = 30


# === HEURISTIC 5: Tool Diversity Limit ===
def count_distinct_tools(code: str) -> int:
    """Count distinct tool calls in code."""
    pattern = r'mcp\.call_tool\([\'"](\w+)[\'"]'
    matches = re.findall(pattern, code)
    return len(set(matches))


def exceeds_tool_diversity_limit(code: str, max_tools: int = 3) -> bool:
    """Check if code uses too many distinct tools."""
    return count_distinct_tools(code) > max_tools


# === HEURISTIC 6: Output Structure Enforcement ===
def clean_output_structure(result: str) -> str:
    """Remove markdown, imports, extra defs from final output."""
    # Remove markdown code fences
    result = re.sub(r'```[\w]*\n?', '', result)
    result = re.sub(r'```', '', result)
    
    # Remove import statements
    result = re.sub(r'^import\s+.*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^from\s+.*import.*$', '', result, flags=re.MULTILINE)
    
    # Remove function definitions (except solve)
    lines = result.split('\n')
    cleaned_lines = []
    skip_def = False
    
    for line in lines:
        if re.match(r'^\s*def\s+(?!solve)', line):
            skip_def = True
        elif skip_def and not line.startswith(' ') and not line.startswith('\t'):
            skip_def = False
        
        if not skip_def:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


# === HEURISTIC 7: Repeat Tool-Call Guard ===
def count_tool_calls(code: str, tool_name: str) -> int:
    """Count how many times a specific tool is called."""
    pattern = rf'mcp\.call_tool\([\'"]({re.escape(tool_name)})[\'"]'
    matches = re.findall(pattern, code)
    return len(matches)


def has_excessive_repeats(code: str, max_repeats: int = 2) -> bool:
    """Check if any tool is called more than max_repeats times."""
    pattern = r'mcp\.call_tool\([\'"](\w+)[\'"]'
    matches = re.findall(pattern, code)
    
    from collections import Counter
    counts = Counter(matches)
    
    return any(count > max_repeats for count in counts.values())


# === HEURISTIC 8: Memory Pollution Guard ===
def should_store_in_memory(
    tool_result: Any,
    success: bool,
    existing_results: List[str]
) -> bool:
    """Determine if result should be stored in memory."""
    # Don't store failures
    if not success:
        return False
    
    # Don't store empty results
    result_str = str(tool_result).strip()
    if not result_str or result_str == "None" or result_str == "":
        return False
    
    # Don't store duplicates
    if result_str in existing_results:
        return False
    
    # Don't store error messages
    if "error" in result_str.lower() or "failed" in result_str.lower():
        return False
    
    return True


# === HEURISTIC 9: Server Availability Check ===
def filter_available_servers(
    selected_servers: List[str],
    available_servers: List[str]
) -> List[str]:
    """Remove unavailable servers; fallback to all if none available."""
    filtered = [s for s in selected_servers if s in available_servers]
    return filtered if filtered else available_servers


# === HEURISTIC 10: AST-Based solve() Linter ===
class SolveFunctionLinter(ast.NodeVisitor):
    """AST visitor to validate solve() function safety."""
    
    def __init__(self):
        self.errors = []
        self.in_solve = False
    
    def visit_FunctionDef(self, node):
        if node.name == "solve":
            self.in_solve = True
            self.generic_visit(node)
            self.in_solve = False
        else:
            if self.in_solve:
                self.errors.append(f"Nested function definition not allowed: {node.name}")
    
    def visit_Import(self, node):
        if self.in_solve:
            self.errors.append("Import statements not allowed in solve()")
    
    def visit_ImportFrom(self, node):
        if self.in_solve:
            self.errors.append("Import statements not allowed in solve()")
    
    def visit_ClassDef(self, node):
        if self.in_solve:
            self.errors.append(f"Class definitions not allowed: {node.name}")
    
    def visit_Call(self, node):
        if self.in_solve:
            # Check for dangerous calls
            if isinstance(node.func, ast.Name):
                dangerous = ['eval', 'exec', 'compile', '__import__', 'open', 'system']
                if node.func.id in dangerous:
                    self.errors.append(f"Dangerous function call not allowed: {node.func.id}")
        self.generic_visit(node)
    
    def visit_While(self, node):
        if self.in_solve:
            # Check for potential infinite loops (basic heuristic)
            # Allow while with break statements
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self.errors.append("While loop without break statement (potential infinite loop)")
        self.generic_visit(node)


def lint_solve_function(code: str) -> tuple[bool, List[str]]:
    """
    Use AST to validate solve() function.
    Returns (is_valid, error_list).
    """
    try:
        tree = ast.parse(code)
        linter = SolveFunctionLinter()
        linter.visit(tree)
        
        if linter.errors:
            return False, linter.errors
        
        return True, []
    
    except SyntaxError as e:
        return False, [f"Syntax error: {str(e)}"]
    except Exception as e:
        return False, [f"AST parsing error: {str(e)}"]


# === Utility: Apply All Heuristics to Code ===
def validate_solve_code(code: str, query: str = "") -> tuple[bool, List[str]]:
    """
    Apply all relevant heuristics to validate solve() code.
    Returns (is_valid, error_messages).
    """
    errors = []
    
    # H3: Unsafe arguments
    if contains_unsafe_arguments(code):
        errors.append("Code contains unsafe patterns")
    
    # H5: Tool diversity
    if exceeds_tool_diversity_limit(code):
        errors.append(f"Code uses more than 3 distinct tools")
    
    # H7: Repeat tool calls
    if has_excessive_repeats(code):
        errors.append("Code calls the same tool more than 2 times")
    
    # H10: AST linting
    is_valid, ast_errors = lint_solve_function(code)
    if not is_valid:
        errors.extend(ast_errors)
    
    return len(errors) == 0, errors
