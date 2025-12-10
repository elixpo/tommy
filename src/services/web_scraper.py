"""Web scraping service using Crawl4AI - async, LLM-ready markdown output."""

import asyncio
import logging
import hashlib
import time
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Simple in-memory cache with TTL
_scrape_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cache_key(url: str, extract_instruction: Optional[str] = None) -> str:
    """Generate cache key from URL and extraction instruction."""
    key_str = url + (extract_instruction or "")
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cached(key: str) -> Optional[dict]:
    """Get cached result if not expired."""
    if key in _scrape_cache:
        timestamp, result = _scrape_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return result
        del _scrape_cache[key]
    return None


def _set_cache(key: str, result: dict):
    """Cache a result."""
    _scrape_cache[key] = (time.time(), result)


async def scrape_url(
    url: str,
    extract_instruction: Optional[str] = None,
    include_links: bool = False,
    include_images: bool = False,
    timeout: int = 30,
    use_cache: bool = True
) -> dict:
    """
    Scrape a single URL and return clean markdown content.

    Args:
        url: The URL to scrape
        extract_instruction: Optional LLM instruction for smart extraction
                           (e.g., "Extract product prices and names")
        include_links: Include extracted links in response
        include_images: Include image URLs in response
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results

    Returns:
        Dict with:
        - success: bool
        - url: original URL
        - title: page title
        - markdown: clean markdown content (truncated if huge)
        - links: list of links (if include_links)
        - images: list of image URLs (if include_images)
        - extracted: LLM-extracted content (if extract_instruction provided)
        - error: error message (if failed)
    """
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"success": False, "url": url, "error": "Invalid URL - must include http:// or https://"}
    except Exception:
        return {"success": False, "url": url, "error": "Invalid URL format"}

    # Check cache
    cache_key = _get_cache_key(url, extract_instruction)
    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for {url}")
            cached["cached"] = True
            return cached

    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        # Configure browser - headless, fast
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )

        # Configure crawl
        crawl_config = CrawlerRunConfig(
            word_count_threshold=10,  # Skip tiny content blocks
            excluded_tags=["nav", "footer", "aside", "script", "style", "noscript"],
            remove_overlay_elements=True,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=crawl_config),
                timeout=timeout
            )

            if not result.success:
                return {
                    "success": False,
                    "url": url,
                    "error": f"Failed to fetch page: {result.error_message or 'Unknown error'}"
                }

            # Build response
            response = {
                "success": True,
                "url": url,
                "title": result.metadata.get("title", "") if result.metadata else "",
                "markdown": _truncate_content(result.markdown or "", max_chars=15000),
            }

            # Include links if requested
            if include_links and result.links:
                # Get internal and external links
                internal = result.links.get("internal", [])
                external = result.links.get("external", [])
                response["links"] = {
                    "internal": [l.get("href") for l in internal[:20] if l.get("href")],
                    "external": [l.get("href") for l in external[:20] if l.get("href")]
                }

            # Include images if requested
            if include_images and result.media:
                images = result.media.get("images", [])
                response["images"] = [img.get("src") for img in images[:10] if img.get("src")]

            # LLM extraction if instruction provided
            if extract_instruction and result.markdown:
                extracted = await _llm_extract(result.markdown, extract_instruction)
                if extracted:
                    response["extracted"] = extracted

            # Cache successful result
            if use_cache:
                _set_cache(cache_key, response)

            return response

    except asyncio.TimeoutError:
        return {"success": False, "url": url, "error": f"Timeout after {timeout}s - page took too long to load"}
    except ImportError:
        return {"success": False, "url": url, "error": "crawl4ai not installed - run: pip install crawl4ai"}
    except Exception as e:
        logger.error(f"Scrape error for {url}: {e}")
        return {"success": False, "url": url, "error": str(e)}


async def scrape_multiple(
    urls: list[str],
    extract_instruction: Optional[str] = None,
    max_concurrent: int = 5,
    timeout: int = 30
) -> dict:
    """
    Scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape
        extract_instruction: Optional LLM instruction for extraction
        max_concurrent: Max concurrent requests
        timeout: Per-URL timeout

    Returns:
        Dict with:
        - success: bool (true if at least one succeeded)
        - results: list of individual scrape results
        - succeeded: count of successful scrapes
        - failed: count of failed scrapes
    """
    if not urls:
        return {"success": False, "error": "No URLs provided", "results": []}

    # Limit URLs
    urls = urls[:10]  # Max 10 URLs per call

    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def scrape_with_limit(url: str) -> dict:
        async with semaphore:
            return await scrape_url(
                url=url,
                extract_instruction=extract_instruction,
                timeout=timeout
            )

    # Run all scrapes concurrently
    tasks = [scrape_with_limit(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    processed_results = []
    succeeded = 0
    failed = 0

    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "url": url,
                "error": str(result)
            })
            failed += 1
        elif result.get("success"):
            processed_results.append(result)
            succeeded += 1
        else:
            processed_results.append(result)
            failed += 1

    return {
        "success": succeeded > 0,
        "results": processed_results,
        "succeeded": succeeded,
        "failed": failed,
        "total": len(urls)
    }


async def _llm_extract(content: str, instruction: str) -> Optional[str]:
    """
    Use Pollinations AI to extract specific information from content.

    This is the "smart" part - using LLM to understand and extract
    based on natural language instructions.
    """
    try:
        from .pollinations import pollinations_client

        # Truncate content for LLM
        content_truncated = content[:10000]

        result = await pollinations_client.generate_text(
            system_prompt=(
                "You are a precise data extraction assistant. "
                "Extract ONLY the requested information from the content. "
                "Be concise and structured. Use bullet points or JSON if appropriate. "
                "If the requested information is not found, say 'Not found'."
            ),
            user_prompt=f"Content:\n{content_truncated}\n\n---\nExtract: {instruction}",
            temperature=0.3,
            max_tokens=1000
        )

        return result

    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return None


def _truncate_content(content: str, max_chars: int = 15000) -> str:
    """Truncate content intelligently at paragraph boundaries."""
    if len(content) <= max_chars:
        return content

    # Try to truncate at a paragraph break
    truncated = content[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:  # If we find a break in last 30%
        truncated = truncated[:last_para]

    return truncated + "\n\n...[content truncated]"


# =============================================================================
# TOOL HANDLER - Called by the AI
# =============================================================================

async def web_scrape_handler(
    action: str = "scrape",
    url: Optional[str] = None,
    urls: Optional[list[str]] = None,
    extract: Optional[str] = None,
    include_links: bool = False,
    include_images: bool = False,
    **kwargs
) -> dict:
    """
    Handle web_scrape tool calls.

    Actions:
    - scrape: Scrape a single URL, get clean markdown
    - multi: Scrape multiple URLs concurrently
    - extract: Scrape + LLM extraction with instruction

    Args:
        action: "scrape", "multi", or "extract"
        url: Single URL (for scrape/extract)
        urls: List of URLs (for multi)
        extract: LLM extraction instruction (e.g., "Extract all product prices")
        include_links: Include page links in result
        include_images: Include image URLs in result

    Returns:
        Scraped content as markdown, ready for AI consumption
    """
    if action == "scrape":
        if not url:
            return {"error": "url parameter required for scrape action"}
        return await scrape_url(
            url=url,
            include_links=include_links,
            include_images=include_images
        )

    elif action == "extract":
        if not url:
            return {"error": "url parameter required for extract action"}
        if not extract:
            return {"error": "extract parameter required - describe what to extract"}
        return await scrape_url(
            url=url,
            extract_instruction=extract,
            include_links=include_links,
            include_images=include_images
        )

    elif action == "multi":
        if not urls:
            return {"error": "urls parameter required for multi action (list of URLs)"}
        return await scrape_multiple(
            urls=urls,
            extract_instruction=extract
        )

    else:
        return {"error": f"Unknown action: {action}. Use: scrape, extract, or multi"}
