# Project Architecture

This is a FastAPI-based web application for browsing images and GIFs from Reddit subreddits.

## Project Structure

```
project_x/
├── app/
│   ├── api/          # API route handlers
│   │   └── download.py  # Download endpoint
│   ├── services/     # Business logic services
│   │   ├── reddit_service.py    # Reddit API interactions
│   │   ├── media_service.py     # Media URL processing
│   │   └── cache_service.py     # Caching layer
│   ├── models/       # Pydantic models and schemas
│   │   └── schemas.py
│   └── utils/        # Utility functions
│       ├── helpers.py    # Helper functions
│       └── logger.py     # Logging configuration
├── templates/         # HTML templates (Jinja2)
│   └── index.html
├── tests/            # Test files
│   ├── test_api.py
│   └── test_services.py
├── docs/             # Documentation
│   └── API.md
├── main.py           # FastAPI application entry point
└── requirements.txt  # Python dependencies
```

## Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **Reddit API**: PRAW (Python Reddit API Wrapper)
- **HTTP Client**: aiohttp (async HTTP requests)
- **Templating**: Jinja2
- **Caching**: In-memory caching with TTL
- **Environment**: python-dotenv for configuration

## Key Components

### Main Application (`main.py`)
- FastAPI app initialization
- Middleware configuration (GZip, security headers)
- Route registration
- Error handling

### Services Layer (`app/services/`)
- **reddit_service.py**: Reddit API client initialization and subreddit search
- **media_service.py**: Media URL detection, conversion, and Redgifs URL extraction
- **cache_service.py**: Response caching with configurable TTL

### API Routes (`app/api/`)
- **download.py**: Media download endpoints (individual and batch ZIP)

### Models (`app/models/`)
- Pydantic schemas for request/response validation

### Utilities (`app/utils/`)
- Helper functions for error formatting
- Logger configuration

## Architecture Patterns

- **Service Layer Pattern**: Business logic separated into service modules
- **Dependency Injection**: Services are imported and used in routes
- **Async/Await**: All I/O operations use async/await for performance
- **Caching Strategy**: Aggressive caching for subreddit searches and media responses
- **Error Handling**: Centralized error handling with user-friendly messages
