import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

PERFORMANCE_LOG_PATH = Path("tool_performance_log.jsonl")

class ToolPerformanceTracker:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or PERFORMANCE_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def log_tool_call(self, tool: str, success: bool, latency_ms: float, retries: int = 0):
        """Log a single tool call performance metric"""
        entry = {
            "tool": tool,
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "retries": retries,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_tool_stats(self, tool: str, recent_n: int = 50) -> Dict:
        """Get performance statistics for a specific tool"""
        if not self.log_path.exists():
            return {
                "success_rate": 1.0,
                "avg_latency_ms": 0,
                "recent_failures": 0,
                "total_calls": 0
            }
        
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry["tool"] == tool:
                        entries.append(entry)
                except:
                    continue
        
        # Get recent entries
        recent = entries[-recent_n:] if len(entries) > recent_n else entries
        
        if not recent:
            return {
                "success_rate": 1.0,
                "avg_latency_ms": 0,
                "recent_failures": 0,
                "total_calls": 0
            }
        
        successes = sum(1 for e in recent if e["success"])
        failures = len(recent) - successes
        avg_latency = sum(e["latency_ms"] for e in recent) / len(recent)
        
        # Count consecutive recent failures
        recent_failures = 0
        for entry in reversed(recent[-10:]):  # Check last 10
            if not entry["success"]:
                recent_failures += 1
            else:
                break
        
        return {
            "success_rate": successes / len(recent),
            "avg_latency_ms": round(avg_latency, 2),
            "recent_failures": recent_failures,
            "total_calls": len(recent)
        }
    
    def get_all_tool_stats(self, recent_n: int = 50) -> Dict[str, Dict]:
        """Get performance statistics for all tools"""
        if not self.log_path.exists():
            return {}
        
        tool_entries = defaultdict(list)
        
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    tool_entries[entry["tool"]].append(entry)
                except:
                    continue
        
        stats = {}
        for tool, entries in tool_entries.items():
            recent = entries[-recent_n:] if len(entries) > recent_n else entries
            
            if not recent:
                continue
            
            successes = sum(1 for e in recent if e["success"])
            failures = len(recent) - successes
            avg_latency = sum(e["latency_ms"] for e in recent) / len(recent)
            
            # Count consecutive recent failures
            recent_failures = 0
            for entry in reversed(recent[-10:]):
                if not entry["success"]:
                    recent_failures += 1
                else:
                    break
            
            stats[tool] = {
                "success_rate": successes / len(recent),
                "avg_latency_ms": round(avg_latency, 2),
                "recent_failures": recent_failures,
                "total_calls": len(recent)
            }
        
        return stats

# Global tracker instance
_tracker = ToolPerformanceTracker()

def log_tool_call(tool: str, success: bool, latency_ms: float, retries: int = 0):
    """Convenience function to log tool calls"""
    _tracker.log_tool_call(tool, success, latency_ms, retries)

def get_tool_stats(tool: str, recent_n: int = 50) -> Dict:
    """Convenience function to get tool stats"""
    return _tracker.get_tool_stats(tool, recent_n)

def get_all_tool_stats(recent_n: int = 50) -> Dict[str, Dict]:
    """Convenience function to get all tool stats"""
    return _tracker.get_all_tool_stats(recent_n)
