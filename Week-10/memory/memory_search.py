import os
import json
from pathlib import Path
from typing import List, Dict
from rapidfuzz import fuzz


class MemorySearch:
    def __init__(self, logs_path: str = "memory/session_logs"):
        self.logs_path = Path(logs_path)

    def search_memory(self, user_query: str, top_k: int = 3) -> List[Dict]:
        memory_entries = self._load_queries()
        scored_results = []

        for entry in memory_entries:
            query_score = fuzz.partial_ratio(user_query.lower(), entry["query"].lower())
            summary_score = fuzz.partial_ratio(user_query.lower(), entry["solution_summary"].lower())
            length_penalty = len(entry["solution_summary"]) / 100
            score = 0.5 * query_score + 0.4 * summary_score - 0.05 * length_penalty
            scored_results.append((score, entry))

        top_matches = sorted(scored_results, key=lambda x: x[0], reverse=True)[:top_k]
        return [match[1] for match in top_matches]

    def _load_queries(self) -> List[Dict]:
        memory_entries = []
        all_json_files = list(self.logs_path.rglob("*.json"))
        print(f"🔍 Found {len(all_json_files)} JSON file(s) in '{self.logs_path}'")

        for file in all_json_files:
            count_before = len(memory_entries)
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                if isinstance(content, list):  # FORMAT 1
                    for session in content:
                        self._extract_entry(session, file.name, memory_entries)
                elif isinstance(content, dict) and "session_id" in content:  # FORMAT 2
                    self._extract_entry(content, file.name, memory_entries)
                elif isinstance(content, dict) and "turns" in content:  # FORMAT 3
                    for turn in content["turns"]:
                        self._extract_entry(turn, file.name, memory_entries)

            except Exception as e:
                print(f"⚠️ Skipping '{file}': {e}")
                continue

            count_after = len(memory_entries)
            if count_after > count_before:
                print(f"✅ {file.name}: {count_after - count_before} matching entries")

        print(f"📦 Total usable memory entries collected: {len(memory_entries)}\n")
        return memory_entries

    def _extract_entry(self, obj: dict, file_name: str, memory_entries: List[Dict]):
        original_obj = obj  # keep top-level reference

        def recursive_find(obj: dict) -> dict | None:
            if isinstance(obj, dict):
                if obj.get("original_goal_achieved") is True:
                    query = extract_query(original_obj)  # 💡 pull from full session object
                    return {
                        "query": query,
                        "summary": obj.get("solution_summary", ""),
                        "requirement": obj.get("result_requirement", "")
                    }
                for v in obj.values():
                    result = recursive_find(v)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = recursive_find(item)
                    if result:
                        return result
            return None


        def extract_query(obj: dict) -> str:
            if isinstance(obj, dict):
                if "query" in obj and isinstance(obj["query"], str):
                    return obj["query"]
                for v in obj.values():
                    q = extract_query(v)
                    if q:
                        return q
            elif isinstance(obj, list):
                for item in obj:
                    q = extract_query(item)
                    if q:
                        return q
            return ""

        try:
            match = recursive_find(obj)
            if match and match["query"]:
                print(f"✅ Extracted: {match['query'][:40]} → {match['summary'][:40]}")
                memory_entries.append({
                    "file": file_name,
                    "query": match["query"],
                    "result_requirement": match["requirement"],
                    "solution_summary": match["summary"]
                })
        except Exception as e:
            print(f"❌ Error parsing {file_name}: {e}")


if __name__ == "__main__":
    searcher = MemorySearch()
    query = input("Enter your query: ").strip()
    results = searcher.search_memory(query)

    if not results:
        print("❌ No matching memory entries found.")
    else:
        print("\n🎯 Top Matches:\n")
        for i, res in enumerate(results, 1):
            print(f"[{i}] File: {res['file']}\nQuery: {res['query']}\nResult Requirement: {res['result_requirement']}\nSummary: {res['solution_summary']}\n")
