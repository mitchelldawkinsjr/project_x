# Development Workflow

## Environment Setup

1. **Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   - Copy `env.example` to `.env`
   - Add Reddit API credentials (optional but recommended):
     ```
     REDDIT_CLIENT_ID=your_client_id
     REDDIT_CLIENT_SECRET=your_client_secret
     ```

3. **Run Development Server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Code Organization

### Adding New Features

1. **New API Endpoint**
   - Add route in `main.py` or create new file in `app/api/`
   - Follow existing route patterns
   - Add error handling
   - Update `docs/API.md` if needed

2. **New Service Function**
   - Add to appropriate service in `app/services/`
   - Keep functions focused and testable
   - Add type hints and docstrings
   - Write tests in `tests/`

3. **Frontend Changes**
   - Modify `templates/index.html`
   - Keep JavaScript organized by feature
   - Test in multiple browsers
   - Ensure mobile responsiveness

## Testing

- Run tests: `pytest tests/`
- Test specific file: `pytest tests/test_services.py`
- Test with coverage: `pytest --cov=app tests/`

## Docker Development

- Development with hot reload:
  ```bash
  docker build -f Dockerfile.dev -t reddit-viewer:dev .
  docker run -d -p 8001:8001 -v $(pwd):/app reddit-viewer:dev
  ```

## Debugging

- Check server logs for errors
- Use browser console for frontend debugging
- Enable logger debug mode if needed
- Check Reddit API rate limits if getting 401 errors

## Common Issues

- **401 Errors**: Set Reddit API credentials in `.env`
- **CORS Errors**: Check video crossOrigin settings
- **Video Not Loading**: Check browser console, verify URL is direct MP4
- **Slow Performance**: Check cache TTL settings, enable compression

## Git Workflow

- Keep commits focused and atomic
- Write descriptive commit messages
- Don't commit `.env` file (already in `.gitignore`)
- Update README.md for significant changes
