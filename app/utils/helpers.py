"""Helper utility functions"""
from typing import Any, Dict


def format_error_message(error: Exception) -> Dict[str, Any]:
    """Format error message with type and status code"""
    error_message = str(error)
    status_code = 500
    error_type = "unknown"
    
    if "401" in error_message or "Unauthorized" in error_message:
        error_message = "Reddit API authentication failed. Please check your API credentials."
        status_code = 401
        error_type = "api_error"
    elif "403" in error_message or "Forbidden" in error_message:
        error_message = "Access forbidden. The subreddit may be private or banned."
        status_code = 403
        error_type = "api_error"
    elif "404" in error_message or "not found" in error_message.lower():
        error_message = "Subreddit or user not found."
        status_code = 404
        error_type = "validation_error"
    elif "429" in error_message or "rate limit" in error_message.lower():
        error_message = "Rate limit exceeded. Please wait a moment and try again."
        status_code = 429
        error_type = "rate_limit_error"
    elif "timeout" in error_message.lower():
        error_message = "Request timed out. Please try again."
        status_code = 504
        error_type = "timeout_error"
    else:
        error_type = "api_error"
    
    return {
        "error": error_message,
        "error_type": error_type,
        "status_code": status_code
    }

