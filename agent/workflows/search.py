"""
Web Search Workflows
LLM-driven adaptive search using Serper API with webpage content extraction
"""

import re
from typing import Dict, Any, Optional
from agent.workflows.registry import register_workflow, WorkflowContext, ParameterSpec, WorkflowValidationError


@register_workflow(
    namespace="search",
    name="web",
    summary="Search the web for information (answers questions, finds data, gets current information)",
    description="Intelligent web search for any query - automatically finds relevant information from the internet. Use this for: current events, statistics, facts, 'what is' questions, research, etc.",
    parameters=[
        ParameterSpec(name="query", type=str, required=True, description="What to search for"),
        ParameterSpec(name="num_results", type=int, required=False, default=10, description="Number of results"),
    ],
    metadata={
        "category": "SEARCH COMMANDS",
        "usage": "search:web query:\"SEARCH_QUERY\" [num_results:N]",
        "examples": [
            "search:web query:\"Ayodhya temple footfall 2025\"",
            "search:web query:\"current weather Paris\"",
            "search:web query:\"latest tech news\" num_results:5"
        ]
    }
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


@register_workflow(
    namespace="search",
    name="deep",
    summary="Deep web search with content extraction",
    description="Search the web and extract actual content from top results for comprehensive answers",
    parameters=[
        ParameterSpec(name="query", type=str, required=True, description="Search query"),
        ParameterSpec(name="num_results", type=int, default=3, description="Number of pages to scrape"),
        ParameterSpec(name="max_words", type=int, default=500, description="Max words to extract per page"),
    ],
    metadata={
        "category": "SEARCH COMMANDS",
        "usage": "search:deep query:\"QUERY\" [num_results:N] [max_words:N]",
        "examples": [
            "search:deep query:\"Ayodhya temple footfall 2025\"",
            "search:deep query:\"latest AI developments\" num_results:5"
        ]
    }
)
def search_deep_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """
    Deep search - searches web and extracts content from top pages.
    
    This workflow:
    1. Performs web search to find relevant pages
    2. Fetches and extracts text content from top results
    3. Uses LLM to summarize findings and answer the query
    
    Args:
        ctx: Workflow context
        params: Dictionary with query, num_results, max_words
    
    Returns:
        Comprehensive answer based on extracted web content
    """
    import requests
    from bs4 import BeautifulSoup
    from agent.tools.web_search import WebSearchTool
    from agent.tools.ollama_client import run_ollama
    from agent.config.runtime import LOCAL_PLANNER
    
    query = params.get("query")
    num_results = params.get("num_results", 3)
    max_words = params.get("max_words", 500)
    
    if not query:
        raise WorkflowValidationError("'query' parameter is required")
    
    output_lines = []
    output_lines.append(f"🔍 Deep Search: \"{query}\"\n")
    output_lines.append("=" * 60)
    
    try:
        # Step 1: Search for pages
        tool = WebSearchTool()
        search_result = tool.search_adaptive(
            query=query,
            num_results=num_results,
            auto_mode=True,
            auto_fields=True
        )
        
        if not search_result.get("success"):
            return f"❌ Search failed: {search_result.get('error', 'Unknown error')}"
        
        results = search_result.get("results", [])
        if not results:
            return "❌ No search results found"
        
        output_lines.append(f"\n📊 Found {len(results)} relevant pages. Extracting content...\n")
        
        # Step 2: Extract content from each result
        extracted_content = []
        
        for i, result in enumerate(results[:num_results], 1):
            link = result.get("link")
            title = result.get("title", "Untitled")
            
            if not link:
                continue
            
            output_lines.append(f"\n{i}. {title}")
            output_lines.append(f"   URL: {link}")
            
            try:
                # Fetch webpage
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(link, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Limit words
                words = text.split()[:max_words]
                content = ' '.join(words)
                
                if content:
                    extracted_content.append({
                        "title": title,
                        "url": link,
                        "content": content
                    })
                    output_lines.append(f"   ✓ Extracted {len(words)} words")
                else:
                    output_lines.append(f"   ⚠️  No content extracted")
                
            except requests.Timeout:
                output_lines.append(f"   ⏱️  Timeout - skipped")
            except Exception as e:
                output_lines.append(f"   ❌ Error: {str(e)[:50]}")
        
        if not extracted_content:
            return "\n".join(output_lines) + "\n\n❌ Could not extract content from any pages"
        
        # Step 3: Use LLM to synthesize answer
        output_lines.append(f"\n\n🤖 Analyzing {len(extracted_content)} pages...\n")
        
        # Build context for LLM
        context_parts = []
        for item in extracted_content:
            context_parts.append(f"Source: {item['title']}")
            context_parts.append(f"URL: {item['url']}")
            context_parts.append(f"Content: {item['content'][:800]}...")  # Limit per source
            context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        # Ask LLM to synthesize answer
        synthesis_prompt = f"""Based on the following web pages, answer this question: "{query}"

Web Page Content:
{context_text}

Instructions:
1. Provide a comprehensive answer based ONLY on the information from these pages
2. Cite sources when mentioning specific facts
3. If the pages don't contain the answer, say so clearly
4. Keep answer under 300 words
5. Be factual and accurate

Answer:"""
        
        answer = run_ollama(
            synthesis_prompt,
            profile=LOCAL_PLANNER,
            model="qwen3:4b-instruct",
            timeout=30
        )
        
        if not answer:
            return "\n".join(output_lines) + "\n\n❌ Failed to generate answer"
        
        output_lines.append("📝 Answer:\n")
        output_lines.append(answer.strip())
        output_lines.append("\n" + "=" * 60)
        output_lines.append(f"\n💡 Sources: {len(extracted_content)} web pages analyzed")
        
        return "\n".join(output_lines)
        
    except ValueError as e:
        return f"❌ Configuration error: {str(e)}\n\nSetup: python -m agent.tools.serper_credentials setup <api_key>"
    except Exception as e:
        return f"❌ Error during deep search: {str(e)}"
