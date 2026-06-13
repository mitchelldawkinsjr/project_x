# Reddit Image/GIF Viewer

A fast and lightweight web application for browsing images and GIFs from Reddit subreddits.

## Features

### Core Features
- 🔍 **Subreddit Search**: Intelligent autocomplete for subreddit discovery
- 🖼️ **Media Browsing**: View images, GIFs, and videos from Reddit
- ⌨️ **Keyboard Shortcuts**: Navigate efficiently with keyboard controls
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🌙 **Dark Mode**: Toggle between light and dark themes

### Enhanced Features
- ⬇️ **Download Support**: Download individual files or batch download as ZIP
- ⭐ **Favorites**: Save your favorite media items
- 📋 **Copy URLs**: Quick copy-to-clipboard functionality
- 🔗 **Direct Links**: Open media in Reddit with one click
- ℹ️ **Media Info**: View dimensions, source, and metadata
- 📊 **Progress Indicators**: Real-time loading progress
- 🔄 **Error Handling**: User-friendly error messages with retry options
- 💾 **Caching**: Fast response times with intelligent caching

### Keyboard Shortcuts
- `/` - Focus search input
- `?` - Show keyboard shortcuts help
- `←` / `→` - Navigate between images in modal
- `Space` - Next image (or play/pause video)
- `Esc` - Close modal
- `F` - Toggle favorite
- `D` - Download current image
- `F11` - Toggle fullscreen

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set up Reddit API credentials:
   - Create a Reddit app at https://www.reddit.com/prefs/apps
   - Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"
   ```
   
   Note: The app works without credentials using public read-only access, but with rate limits.

## Usage

1. Start the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 3005 --reload
```

2. Open your browser and navigate to:
```
http://localhost:3005
```

3. Enter a subreddit name (e.g., `pics`, `aww`, `gifs`) or a username
4. Select the source type (Subreddit or User)
5. Click Search — results load continuously as you scroll (no item cap)

## Examples

- **Subreddit**: `pics`, `aww`, `gifs`, `funny`
- **User**: Any Reddit username

## API Documentation

See [docs/API.md](docs/API.md) for complete API documentation.

## Testing

Run tests with pytest:
```bash
pytest tests/
```

## Project Structure

```
project_x/
├── app/
│   ├── api/          # API routes
│   ├── services/     # Business logic services
│   ├── models/       # Pydantic models
│   └── utils/        # Utility functions
├── static/           # CSS and JavaScript assets
├── templates/        # HTML templates
├── tests/            # Test files
└── main.py           # FastAPI application
```

## Requirements

- Python 3.8+
- FastAPI
- PRAW (Python Reddit API Wrapper)
- aiohttp

## Docker Deployment

### Using Docker Compose (Recommended)

1. Create a `.env` file with your Reddit API credentials (optional):
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

2. Build and run with Docker Compose:
```bash
docker-compose up -d
```

3. Access the app at `http://localhost:4444`

4. View logs:
```bash
docker-compose logs -f
```

5. Stop the container:
```bash
docker-compose down
```

### Using Docker directly

1. Build the image:
```bash
docker build -t reddit-viewer .
```

2. Run the container:
```bash
docker run -d \
  --name reddit-viewer \
  -p 4444:4444 \
  -e REDDIT_CLIENT_ID=your_client_id \
  -e REDDIT_CLIENT_SECRET=your_client_secret \
  reddit-viewer
```

3. Access the app at `http://localhost:4444`

### Development with Docker

For development with hot reload:
```bash
docker build -f Dockerfile.dev -t reddit-viewer:dev .
docker run -d \
  --name reddit-viewer-dev \
  -p 4444:4444 \
  -v $(pwd):/app \
  reddit-viewer:dev
```

## Notes

- The app uses lazy loading and caching for better performance
- Videos, GIFs, and images are all supported
- Click on any media item to view it in full screen modal
- Use keyboard shortcuts for efficient navigation (press `?` for help)
