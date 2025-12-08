"""Route helper utilities."""

from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


def build_url_preserving_unicode(
    base_url: str,
    params: dict[str, str] | None = None
) -> str:
    """Build URL preserving Unicode characters in query parameters.
    
    Args:
        base_url: Base URL
        params: Query parameters to add/merge
        
    Returns:
        Complete URL with parameters
    """
    if not params:
        return base_url
    
    # Parse the base URL
    parsed = urlparse(base_url)
    
    # Get existing query parameters
    existing_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Flatten existing params (parse_qs returns lists)
    flat_existing = {k: v[0] if v else '' for k, v in existing_params.items()}
    
    # Merge with new params (new params override existing)
    merged_params = {**flat_existing, **params}
    
    # Build query string (safe= preserves Unicode)
    query_string = urlencode(merged_params, safe=':/@!$&\'()*+,;=')
    
    # Reconstruct URL
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query_string,
        parsed.fragment
    ))


__all__ = ["build_url_preserving_unicode"]
