"""
Web Search Workflows
LLM-driven adaptive search using Serper API
"""

from typing import Dict, Any, Optional
from agent.workflows.registry import register_workflow, WorkflowContext, ParameterSpec


@register_workflow(
    namespace="search",
    name="web",
    summary="Search the web adaptively (LLM chooses mode and fields)",
    description="Intelligent web search - LLM automatically selects the best search mode and result fields",
    parameters=[
        ParameterSpec(name="query", type=str, required=True),
        ParameterSpec(name="num_results", type=int, required=False, default=10),
    ]
)
def search_web_adaptive(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """
    Adaptive web search with LLM-driven mode and field selection.
    
    The LLM will:
    1. Analyze the query and choose the best Serper mode (search, images, videos, news, etc.)
    2. Examine the API response and select the most relevant fields to display
    
    Args:
        ctx: Workflow context
        params: Dictionary with 'query' (str) and optional 'num_results' (int)
    
    Returns:
        Formatted string output
    
    Examples:
        - "Python tutorials" → mode: search, fields: title, link, snippet
        - "cute puppies" → mode: images, fields: title, imageUrl, link
        - "AI news today" → mode: news, fields: title, link, date
        - "restaurants near me" → mode: places, fields: title, address, rating
    """
    from agent.tools.web_search import WebSearchTool
    
    query = params.get("query")
    num_results = params.get("num_results", 10)
    
    if not query:
        return "❌ Error: query parameter is required"
    
    try:
        tool = WebSearchTool()
        
        # LLM-driven adaptive search
        result = tool.search_adaptive(
            query=query,
            num_results=num_results,
            auto_mode=True,   # Let LLM choose mode
            auto_fields=True  # Let LLM choose fields
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Search failed"),
                "output": f"❌ Search failed: {result.get('error', 'Unknown error')}"
            }
        
        # Format results with better presentation
        formatted_output = tool.format_results(result)
        
        # NOTE: The search tool already uses LLM internally for:
        # 1. Choosing the best search mode (places, news, images, etc.)
        # 2. Selecting relevant fields to display from API response
        # This two-stage LLM process happens inside WebSearchTool.search_adaptive()
        
        return formatted_output
    
    except ValueError as e:
        error_msg = str(e)
        return {
            "success": False,
            "error": error_msg,
            "output": f"❌ Configuration error: {error_msg}\n\n" +
                     "Setup: python -m agent.tools.serper_credentials setup <api_key>\n" +
                     "Get key at: https://serper.dev"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": f"❌ Unexpected error: {str(e)}"
        }


@register_workflow(
    namespace="search",
    name="manual",
    summary="Search with manual mode selection",
    description="Web search with explicit mode selection (bypass LLM mode selection)",
    parameters=[
        ParameterSpec(name="query", type=str, required=True),
        ParameterSpec(name="mode", type=str, required=True),
        ParameterSpec(name="num_results", type=int, required=False, default=10),
    ]
)
def search_web_manual(
    ctx: WorkflowContext,
    query: str,
    mode: str,
    num_results: int = 10
) -> Dict[str, Any]:
    """
    Web search with manual mode selection.
    
    Args:
        ctx: Workflow context
        query: Search query
        mode: Serper mode (search, images, videos, news, places, maps, shopping, scholar, patents)
        num_results: Number of results (1-100, default 10)
    
    Returns:
        Dictionary with formatted search results
    """
    from agent.tools.web_search import WebSearchTool, SERPER_MODES
    
    if mode not in SERPER_MODES:
        return {
            "success": False,
            "error": f"Invalid mode: {mode}",
            "output": f"❌ Invalid mode: {mode}\n\nAvailable modes: {', '.join(SERPER_MODES)}"
        }
    
    try:
        tool = WebSearchTool()
        
        # Manual mode, but still let LLM choose fields
        result = tool.search_adaptive(
            query=query,
            num_results=num_results,
            auto_mode=False,
            auto_fields=True,
            mode=mode
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Search failed"),
                "output": f"❌ Search failed: {result.get('error', 'Unknown error')}"
            }
        
        formatted_output = tool.format_results(result)
        
        return {
            "success": True,
            "output": formatted_output,
            "mode": result.get("mode"),
            "fields": result.get("fields"),
            "count": result.get("count"),
            "raw_results": result
        }
    
    except ValueError as e:
        error_msg = str(e)
        return {
            "success": False,
            "error": error_msg,
            "output": f"❌ Configuration error: {error_msg}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": f"❌ Unexpected error: {str(e)}"
        }


@register_workflow(
    namespace="search",
    name="quick",
    summary="Quick search (first 3 results)",
    description="Fast web search returning only top 3 results",
    parameters=[
        ParameterSpec(name="query", type=str, required=True),
    ]
)
def search_quick(
    ctx: WorkflowContext,
    query: str
) -> Dict[str, Any]:
    """
    Quick search - returns top 3 results only.
    
    Args:
        ctx: Workflow context
        query: Search query
    
    Returns:
        Dictionary with formatted search results
    """
    return search_web_adaptive(ctx, query, num_results=3)
