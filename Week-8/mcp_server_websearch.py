from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import urllib.parse
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import time
import re


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str
    position: int


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)


class DuckDuckGoSearcher:
    BASE_URL = "https://html.duckduckgo.com/html"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.rate_limiter = RateLimiter()

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query. This could be due to DuckDuckGo's bot detection or the query returned no matches. Please try rephrasing your search or try again in a few minutes."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.position}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)

    async def search(
        self, query: str, ctx: Context, max_results: int = 10
    ) -> List[SearchResult]:
        try:
            # Apply rate limiting
            await self.rate_limiter.acquire()

            # Create form data for POST request
            data = {
                "q": query,
                "b": "",
                "kl": "",
            }

            await ctx.info(f"Searching DuckDuckGo for: {query}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL, data=data, headers=self.HEADERS, timeout=30.0
                )
                response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, "html.parser")
            if not soup:
                await ctx.error("Failed to parse HTML response")
                return []

            results = []
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                if not title_elem:
                    continue

                link_elem = title_elem.find("a")
                if not link_elem:
                    continue

                title = link_elem.get_text(strip=True)
                link = link_elem.get("href", "")

                # Skip ad results
                if "y.js" in link:
                    continue

                # Clean up DuckDuckGo redirect URLs
                if link.startswith("//duckduckgo.com/l/?uddg="):
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])

                snippet_elem = result.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(
                    SearchResult(
                        title=title,
                        link=link,
                        snippet=snippet,
                        position=len(results) + 1,
                    )
                )

                if len(results) >= max_results:
                    break

            await ctx.info(f"Successfully found {len(results)} results")
            return results

        except httpx.TimeoutException:
            await ctx.error("Search request timed out")
            return []
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred: {str(e)}")
            return []
        except Exception as e:
            await ctx.error(f"Unexpected error during search: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        """Fetch and parse content from a webpage"""
        try:
            await self.rate_limiter.acquire()

            await ctx.info(f"Fetching content from: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            # Get the text content
            text = soup.get_text()

            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text).strip()

            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "... [content truncated]"

            await ctx.info(
                f"Successfully fetched and parsed content ({len(text)} characters)"
            )
            return text

        except httpx.TimeoutException:
            await ctx.error(f"Request timed out for URL: {url}")
            return "Error: The request timed out while trying to fetch the webpage."
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"


# Initialize FastMCP server
mcp = FastMCP("WebSearch")
searcher = DuckDuckGoSearcher()
fetcher = WebContentFetcher()


@mcp.tool()
async def search(query: str, ctx: Context, max_results: int = 10) -> str:
    """
    Search DuckDuckGo and return formatted results.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        ctx: MCP context for logging
    """
    try:
        results = await searcher.search(query, ctx, max_results)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@mcp.tool()
async def fetch_content(url: str, ctx: Context) -> str:
    """
    Fetch and parse content from a webpage URL.

    Args:
        url: The webpage URL to fetch content from
        ctx: MCP context for logging
    """
    return await fetcher.fetch_and_parse(url, ctx)


@mcp.tool()
async def extract_table(content: str, ctx: Context) -> str:
    """
    Extract structured table data from HTML content or plain text.
    Parses tables and returns them in a clean, structured format suitable for spreadsheets.

    Args:
        content: HTML content or plain text containing table data
        ctx: MCP context for logging

    Returns:
        JSON string with extracted table data in format:
        {
            "headers": ["Column1", "Column2", ...],
            "rows": [["value1", "value2", ...], ...]
        }
    """
    import json
    
    try:
        await ctx.info("Extracting table data from content")
        
        # Try to parse as HTML first
        soup = BeautifulSoup(content, "html.parser")
        tables = soup.find_all("table")
        
        if tables:
            # Extract the first table found
            table = tables[0]
            headers = []
            rows = []
            
            # Extract headers
            header_row = table.find("thead")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            else:
                # Try to get headers from first row
                first_row = table.find("tr")
                if first_row:
                    headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]
            
            # Extract data rows
            tbody = table.find("tbody") or table
            for row in tbody.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if cells and cells != headers:  # Skip header row if it appears in tbody
                    rows.append(cells)
            
            result = {
                "headers": headers,
                "rows": rows[:50],  # Limit to first 50 rows
                "total_rows": len(rows)
            }
            
            await ctx.info(f"Extracted table with {len(headers)} columns and {len(rows)} rows")
            return json.dumps(result, indent=2)
        
        # If no HTML table found, try to parse structured text
        # Look for patterns like "Pos. Driver Nationality Team Pts."
        lines = content.split("\n")
        
        # Try to find F1-style standings pattern
        # Pattern: Position Driver Team Points
        standings_pattern = re.compile(r'^(\d+)\s+(.+?)\s+([A-Z]{3})\s+([A-Z]{3})\s+(.+?)\s+(\d+)$')
        
        extracted_rows = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try F1 standings pattern
            match = standings_pattern.match(line)
            if match:
                pos, driver, code1, code2, team, points = match.groups()
                extracted_rows.append([pos, driver.strip(), team.strip(), points])
        
        if extracted_rows:
            result = {
                "headers": ["Position", "Driver", "Team", "Points"],
                "rows": extracted_rows[:50],
                "total_rows": len(extracted_rows)
            }
            await ctx.info(f"Extracted F1 standings with {len(extracted_rows)} drivers")
            return json.dumps(result, indent=2)
        
        # Fallback: simple whitespace splitting
        potential_rows = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains multiple words/numbers separated by spaces
            parts = line.split()
            if len(parts) >= 3:  # At least 3 columns
                potential_rows.append(parts)
        
        if potential_rows and len(potential_rows) > 1:
            # First row might be headers
            headers = potential_rows[0]
            rows = potential_rows[1:51]  # Limit to 50 rows
            
            result = {
                "headers": headers,
                "rows": rows,
                "total_rows": len(potential_rows) - 1
            }
            
            await ctx.info(f"Extracted text table with {len(headers)} columns and {len(rows)} rows")
            return json.dumps(result, indent=2)
        
        await ctx.warning("No table structure found in content")
        return json.dumps({
            "error": "No table structure found in the provided content",
            "headers": [],
            "rows": []
        })
        
    except Exception as e:
        await ctx.error(f"Error extracting table: {str(e)}")
        return json.dumps({
            "error": f"Failed to extract table: {str(e)}",
            "headers": [],
            "rows": []
        })


if __name__ == "__main__":
    print("mcp_server_3.py starting")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
            mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
        print("\nShutting down...")