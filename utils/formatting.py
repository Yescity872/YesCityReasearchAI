from typing import List, Dict, Any

def format_tool_results(results: List[Dict[str, Any]]) -> str:
    """Format tool results into a readable string for the LLM."""
    if not results:
        return "No results found."
    
    formatted = []
    # Limit context size by processing max 20 results if too many
    # Sorting by relevance or quality would be ideal here if possible
    processed_results = results[:20] if len(results) > 20 else results
    
    for i, item in enumerate(processed_results, 1):
        # Extract key fields for conciseness
        _id = item.get('_id', 'N/A')
        name = item.get('shops') or item.get('foodPlace') or "Unknown Place"
        address = item.get('address', 'No address')
        desc = item.get('famousFor') or item.get('description') or "No description"
        category = item.get('category', 'General')
        
        entry = f"{i}. ID: {_id} | Name: {name} | Category: {category} | Details: {desc}"
             
        formatted.append(entry)
    
    if len(results) > 20:
        formatted.append(f"... and {len(results) - 20} more results.")
        
    return "\n".join(formatted)
