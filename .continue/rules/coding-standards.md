# Coding Standards

## Python Code Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return types
- Use async/await for all I/O operations (HTTP requests, file operations)
- Use f-strings for string formatting
- Keep functions focused and single-purpose

## Naming Conventions

- **Files**: Use snake_case (e.g., `reddit_service.py`)
- **Functions**: Use snake_case (e.g., `get_media_url()`)
- **Classes**: Use PascalCase (e.g., `MediaService`)
- **Constants**: Use UPPER_SNAKE_CASE (e.g., `REDDIT_CLIENT_ID`)
- **Variables**: Use snake_case (e.g., `media_url`)

## Code Organization

- Group imports: standard library, third-party, local imports
- Keep functions under 50 lines when possible
- Extract complex logic into separate functions
- Add docstrings to all public functions and classes

## Error Handling

- Use try/except blocks for external API calls
- Log errors with context using the logger utility
- Return user-friendly error messages via JSONResponse
- Never expose internal error details to users

## Async Patterns

```python
# Good: Use async/await
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Avoid: Blocking calls
def fetch_data(url: str) -> dict:
    response = requests.get(url)  # Don't do this
    return response.json()
```

## Service Layer Pattern

- Keep business logic in service modules
- Services should be stateless and reusable
- Use dependency injection for external clients (Reddit, HTTP)
- Return structured data (dicts, Pydantic models)

## Testing

- Write tests for all service functions
- Use pytest for testing
- Mock external API calls in tests
- Test error cases, not just happy paths
