"""
Web Search Tool using Serper API
LLM-driven adaptive search with dynamic mode and field selection
"""

import json
from typing import Dict, List, Optional, Any

import requests

from agent.config.runtime import LOCAL_PLANNER
from agent.tools.ollama_client import run_ollama
from agent.tools.serper_credentials import get_serper_api_key


# Available Serper API modes
SERPER_MODES = [
    "search",      # General web search
    "images",      # Image search
    "videos",      # Video search
    "places",      # Local places
    "maps",        # Map results
    "news",        # News articles
    "shopping",    # Shopping results
    "scholar",     # Academic papers
    "patents",     # Patent search
    "autocomplete" # Search suggestions
]


def llm_choose_mode(query: str, timeout: int = 10) -> str:
    """
    Ask local LLM to choose the best Serper mode for the query.
    
    Args:
        query: User's search query
        timeout: Timeout in seconds
    
    Returns:
        Chosen mode (e.g., "search", "images", "videos")
    """
    prompt = f"""Choose the BEST search mode for this query.

Query: "{query}"

Modes: search, images, videos, places, maps, news, shopping, scholar, patents, autocomplete

Rules:
- search: general web pages (default)
- images: pictures/photos
- videos: video content
- places: locations/businesses
- news: current events
- shopping: products

Return ONLY the mode name:"""

    response = run_ollama(
        prompt,
        profile=LOCAL_PLANNER,
        model="qwen3:4b-instruct",
        timeout=timeout,
    )

    if response:
        mode = response.strip().lower()
        if mode in SERPER_MODES:
            return mode
        for valid_mode in SERPER_MODES:
            if valid_mode in mode:
                return valid_mode

    print("⚠️  LLM mode selection failed, defaulting to 'search'")
    return "search"


def llm_choose_fields(query: str, sample_result: Dict[str, Any], mode: str, timeout: int = 10) -> List[str]:
    """
    Ask local LLM to choose which fields to extract from the result.
    
    Args:
        query: User's search query
        sample_result: Sample result item from Serper API
        mode: The Serper mode used
        timeout: Timeout in seconds
    
    Returns:
        List of field names to extract
    """
    # Get available fields
    available_fields = list(sample_result.keys())
    
    # Format sample (truncate long values)
    sample_formatted = {}
    for key, value in sample_result.items():
        if isinstance(value, str) and len(value) > 100:
            sample_formatted[key] = value[:100] + "..."
        else:
            sample_formatted[key] = value
    
    sample_json = json.dumps(sample_formatted, indent=2)
    
    prompt = f"""Choose the MOST RELEVANT fields to show.

Query: "{query}"
Mode: {mode}

Sample result:
{sample_json}

Available fields: {", ".join(available_fields)}

Instructions:
- Choose 3-5 most relevant fields
- Always include "title" and "link" if available
- Return comma-separated field names only

Fields:"""

    response = run_ollama(
        prompt,
        profile=LOCAL_PLANNER,
        model="qwen3:4b-instruct",
        timeout=timeout,
    )

    if response:
        fields_response = response.strip()
        fields = [f.strip() for f in fields_response.split(",")]
        valid_fields = [f for f in fields if f in available_fields]
        if valid_fields:
            return valid_fields

    if mode == "images":
        defaults = ["title", "imageUrl", "link"]
    elif mode == "videos":
        defaults = ["title", "link", "duration"]
    elif mode == "news":
        defaults = ["title", "link", "date"]
    elif mode == "places":
        defaults = ["title", "address", "rating"]
    else:
        defaults = ["title", "link", "snippet"]

    print("⚠️  LLM field selection failed, using fallback fields")
    return [f for f in defaults if f in available_fields]


class WebSearchTool:
    """
    Adaptive web search using Serper API.
    LLM chooses the best mode and fields dynamically.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize WebSearchTool.
        
        Args:
            api_key: Serper API key (loads from pickle if not provided)
        """
        self.api_key = api_key or get_serper_api_key()
        if not self.api_key:
            raise ValueError(
                "Serper API key not found. Run:\n"
                "  python -m agent.tools.serper_credentials setup <your_api_key>\n\n"
                "Get your key at https://serper.dev"
            )
        
        self.base_url = "https://google.serper.dev"
    
    def search_adaptive(
        self,
        query: str,
        num_results: int = 10,
        auto_mode: bool = True,
        auto_fields: bool = True,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adaptive search with LLM-driven mode and field selection.
        
        Args:
            query: Search query
            num_results: Number of results (1-100)
            auto_mode: Let LLM choose the mode
            auto_fields: Let LLM choose which fields to extract
            mode: Manual mode override (if auto_mode=False)
        
        Returns:
            Dictionary with search results and metadata
        """
        if not query or not query.strip():
            return {"error": "Query cannot be empty", "success": False}
        
        # Step 1: Choose mode (LLM or manual)
        if auto_mode:
            chosen_mode = llm_choose_mode(query)
        else:
            chosen_mode = mode or "search"
        
        if chosen_mode not in SERPER_MODES:
            return {
                "error": f"Invalid mode: {chosen_mode}",
                "success": False,
                "available_modes": SERPER_MODES
            }
        
        # Step 2: Call Serper API
        endpoint = f"{self.base_url}/{chosen_mode}"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query.strip(),
            "num": num_results
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            
            # Step 3: Determine the results key
            # Different modes return results in different keys
            results_key = None
            for key in ["organic", "images", "videos", "news", "places", "shopping", "results"]:
                if key in results and results[key]:
                    results_key = key
                    break
            
            if not results_key:
                return {
                    "success": False,
                    "error": "No results found",
                    "mode": chosen_mode,
                    "raw_response": results
                }
            
            result_items = results[results_key]
            
            # Limit results to requested number
            result_items = result_items[:num_results]
            
            # Step 4: Choose fields (LLM or defaults)
            if auto_fields and result_items:
                chosen_fields = llm_choose_fields(query, result_items[0], chosen_mode)
            else:
                # Default fields
                chosen_fields = ["title", "link", "snippet"]
            
            return {
                "success": True,
                "query": query,
                "mode": chosen_mode,
                "fields": chosen_fields,
                "results": result_items,
                "results_key": results_key,
                "count": len(result_items),
                "raw_response": results
            }
            
        except requests.exceptions.Timeout:
            return {
                "error": "Request timed out",
                "success": False,
                "mode": chosen_mode
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "success": False,
                "mode": chosen_mode
            }
        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}",
                "success": False,
                "mode": chosen_mode
            }
    
    def format_results(self, search_result: Dict[str, Any]) -> str:
        """
        Format search results using LLM-chosen fields.
        
        Args:
            search_result: Result from search_adaptive()
        
        Returns:
            Formatted string
        """
        if not search_result.get("success"):
            return f"❌ Search failed: {search_result.get('error', 'Unknown error')}"
        
        query = search_result.get("query", "")
        mode = search_result.get("mode", "search")
        fields = search_result.get("fields", ["title", "link"])
        results = search_result.get("results", [])
        
        output = []
        output.append(f"🔍 Search results for: \"{query}\"")
        output.append(f"📊 Mode: {mode}")
        output.append(f"📋 Fields: {', '.join(fields)}")
        output.append("")
        
        if not results:
            output.append("No results found.")
            return "\n".join(output)
        
        output.append(f"Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            output.append(f"{i}. Result:")
            for field in fields:
                if field in result:
                    value = result[field]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 200:
                        value = value[:200] + "..."
                    output.append(f"   {field}: {value}")
            output.append("")
        
        return "\n".join(output)


# Convenience function
def search_web(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Quick adaptive web search.
    
    Args:
        query: Search query
        num_results: Number of results
    
    Returns:
        Search results dictionary
    """
    try:
        tool = WebSearchTool()
        return tool.search_adaptive(query, num_results)
    except ValueError as e:
        return {"error": str(e), "success": False}


def search_web_formatted(query: str, num_results: int = 10) -> str:
    """
    Quick adaptive web search with formatted output.
    
    Args:
        query: Search query
        num_results: Number of results
    
    Returns:
        Formatted string
    """
    try:
        tool = WebSearchTool()
        result = tool.search_adaptive(query, num_results)
        return tool.format_results(result)
    except ValueError as e:
        return f"❌ Error: {e}"
