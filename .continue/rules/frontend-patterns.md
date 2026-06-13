# Frontend Patterns

## Template Structure

The frontend is a single-page application using:
- **Template**: `templates/index.html` (Jinja2)
- **Styling**: Inline CSS (modern, gradient design)
- **JavaScript**: Vanilla JS (no frameworks)

## Key Features

### Autocomplete Search
- Real-time subreddit search with debouncing (300ms)
- Multi-select with tags
- Keyboard navigation support

### Media Grid
- Responsive grid layout (auto-fill, min 300px)
- Lazy loading for images
- Video preload metadata
- Click to open modal

### Modal Gallery
- Full-screen media viewer
- Keyboard navigation (arrow keys, space, esc)
- Previous/next navigation
- Gallery info (current/total)

### Keyboard Shortcuts
- `/` - Focus search
- `?` - Show help
- `←`/`→` - Navigate modal
- `Space` - Next/play-pause
- `Esc` - Close modal
- `F` - Toggle favorite
- `D` - Download
- `F11` - Fullscreen

## JavaScript Patterns

### Event Handling
- Use `addEventListener` for all events
- Debounce search input
- Stop propagation for nested click handlers

### DOM Manipulation
- Create elements with `createElement`
- Use `innerHTML` for complex HTML (sanitized)
- Append to containers efficiently

### Async Operations
- Use `async/await` for API calls
- Handle errors with try/catch
- Show loading states during requests

### State Management
- `allMediaItems` - Array of all loaded media
- `currentIndex` - Current modal index
- `selectedSubreddits` - Selected subreddit tags
- `favorites` - LocalStorage favorites

## Styling Patterns

- Modern gradient backgrounds
- Card-based layouts with shadows
- Smooth transitions and hover effects
- Responsive design (mobile-friendly)
- Dark mode support (via toggle)

## Best Practices

- Always check if element exists before accessing
- Use `stopPropagation()` for nested click handlers
- Debounce search input to reduce API calls
- Show loading states during async operations
- Handle errors gracefully with user-friendly messages
- Use localStorage for persistent data (favorites)
