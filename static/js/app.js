        const form = document.getElementById('searchForm');
        const grid = document.getElementById('grid');
        const loading = document.getElementById('loading');
        const loadingMore = document.getElementById('loadingMore');
        const error = document.getElementById('error');
        const errorClose = document.getElementById('errorClose');
        const errorType = document.getElementById('errorType');
        const errorTitle = document.getElementById('errorTitle');
        const errorDetails = document.getElementById('errorDetails');
        const errorActions = document.getElementById('errorActions');
        
        // Enhanced error display function
        function showError(type, title, details, retryCallback = null) {
            // Remove existing error classes
            error.className = 'error';
            
            // Set error type and styling
            const errorTypeMap = {
                'network': { class: 'network-error', label: 'Network Error' },
                'rate-limit': { class: 'rate-limit-error', label: 'Rate Limit' },
                'api': { class: 'api-error', label: 'API Error' },
                'validation': { class: 'validation-error', label: 'Validation Error' },
                'timeout': { class: 'network-error', label: 'Timeout' },
                'unknown': { class: '', label: 'Error' }
            };
            
            const errorInfo = errorTypeMap[type] || errorTypeMap['unknown'];
            error.classList.add(errorInfo.class, 'show');
            
            errorType.textContent = errorInfo.label;
            errorTitle.textContent = title;
            errorDetails.textContent = details || '';
            
            // Clear and add action buttons
            errorActions.innerHTML = '';
            if (retryCallback) {
                const retryBtn = document.createElement('button');
                retryBtn.className = 'error-btn';
                retryBtn.textContent = 'Retry';
                retryBtn.onclick = () => {
                    error.classList.remove('show');
                    retryCallback();
                };
                errorActions.appendChild(retryBtn);
            }
            
            const closeBtn = document.createElement('button');
            closeBtn.className = 'error-btn';
            closeBtn.textContent = 'Dismiss';
            closeBtn.onclick = () => {
                error.classList.remove('show');
            };
            errorActions.appendChild(closeBtn);
        }
        
        // Close error on X button
        if (errorClose) {
            errorClose.addEventListener('click', () => {
                error.classList.remove('show');
            });
        }
        const stats = document.getElementById('stats');
        const modal = document.getElementById('modal');
        const modalContent = document.getElementById('modalContent');
        const modalMediaContainer = document.getElementById('modalMediaContainer');
        const closeBtn = document.querySelector('.close');
        const prevArrow = document.getElementById('prevArrow');
        const nextArrow = document.getElementById('nextArrow');
        const prevClickArea = document.getElementById('prevClickArea');
        const nextClickArea = document.getElementById('nextClickArea');
        const galleryInfo = document.getElementById('galleryInfo');
        
        let allMediaItems = [];
        let currentIndex = 0;
        let selectedSubreddits = [];
        let autocompleteTimeout = null;
        const PAGE_SIZE = 100; // Reddit max per request; unlimited total via pagination
        const SCRAPE_TIMEOUT_MS = 90000; // Reddit can be slow for large/multi-sub requests
        const LOAD_MORE_TIMEOUT_MS = 60000;
        const SEARCH_TIMEOUT_MS = 30000;

        function buildScrapeParams(data) {
            const params = new URLSearchParams();
            for (const [key, value] of Object.entries(data)) {
                if (value === null || value === undefined) continue;
                const text = String(value).trim();
                if (!text || text === 'null' || text === 'undefined') continue;
                params.set(key, text);
            }
            return params;
        }

        async function parseScrapeResponse(response) {
            const result = await response.json();
            if (!response.ok) {
                const detail = result.detail;
                let message = result.error || `Request failed (${response.status})`;
                if (Array.isArray(detail) && detail.length > 0) {
                    message = detail.map(item => item.msg || String(item)).join('; ');
                } else if (typeof detail === 'string') {
                    message = detail;
                }
                throw new Error(message);
            }
            return result;
        }

        let currentAfter = null;
        let currentSearchParams = null;
        let isLoadingMore = false;
        let hasMoreItems = false;
        let infiniteScrollObserver = null;
        const scrollSentinel = document.getElementById('scrollSentinel');
        
        const sourceType = document.getElementById('sourceType');
        const sourceGroup = document.getElementById('sourceGroup');
        const sortSelect = document.getElementById('sort');
        const timeFilterGroup = document.getElementById('timeFilterGroup');
        
        const CacheUtils = {
            set(key, value, ttl = null) {
                try {
                    localStorage.setItem(key, JSON.stringify({
                        value,
                        timestamp: Date.now(),
                        ttl,
                    }));
                } catch (e) {
                    console.warn('localStorage set failed:', e);
                }
            },

            get(key) {
                try {
                    const itemStr = localStorage.getItem(key);
                    if (!itemStr) return null;
                    const item = JSON.parse(itemStr);
                    if (item.ttl && (Date.now() - item.timestamp) > item.ttl) {
                        localStorage.removeItem(key);
                        return null;
                    }
                    return item.value;
                } catch (e) {
                    console.warn('localStorage get failed:', e);
                    return null;
                }
            },
        };
        
        // Show/hide time filter based on sort selection
        if (sortSelect && timeFilterGroup) {
            sortSelect.addEventListener('change', () => {
                timeFilterGroup.style.display = sortSelect.value === 'top' ? 'block' : 'none';
            });
        }
        
        // Grid size controls
        const gridSizeBtns = document.querySelectorAll('.grid-size-btn');
        gridSizeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                gridSizeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const size = btn.dataset.size;
                grid.className = 'grid ' + size;
                CacheUtils.set('gridSize', size);
            });
        });
        
        // Load grid size preference
        const savedGridSize = CacheUtils.get('gridSize') || 'normal';
        grid.className = 'grid ' + savedGridSize;
        gridSizeBtns.forEach(btn => {
            if (btn.dataset.size === savedGridSize) {
                btn.classList.add('active');
            }
        });
        const sourceInput = document.getElementById('sourceInput');
        const autocompleteContainer = document.getElementById('autocompleteContainer');
        const autocompleteInput = document.getElementById('autocompleteInput');
        const autocompleteDropdown = document.getElementById('autocompleteDropdown');
        const subredditTags = document.getElementById('subredditTags');
        const sourceHidden = document.getElementById('source');
        
        function normalizeUsername(value) {
            let name = (value || '').trim();
            const prefixes = ['/u/', 'u/', '/user/', 'user/'];
            for (const prefix of prefixes) {
                if (name.toLowerCase().startsWith(prefix)) {
                    name = name.slice(prefix.length);
                    break;
                }
            }
            return name.trim();
        }
        
        function normalizeSubreddit(value) {
            let name = (value || '').trim();
            const prefixes = ['/r/', 'r/'];
            for (const prefix of prefixes) {
                if (name.toLowerCase().startsWith(prefix)) {
                    name = name.slice(prefix.length);
                    break;
                }
            }
            return name.trim();
        }
        
        function searchSourceInApp(type, name) {
            if (!form || !sourceType) return;
            
            const normalized = type === 'user'
                ? normalizeUsername(name)
                : normalizeSubreddit(name);
            if (!normalized || normalized.toLowerCase() === 'unknown') return;
            
            sourceType.value = type;
            syncSourceTypeUI();
            
            if (type === 'user') {
                sourceInput.value = normalized;
            } else {
                selectedSubreddits = [];
                addSubreddit(normalized);
            }
            
            if (modal) {
                modal.style.display = 'none';
            }
            error.classList.remove('show');
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (typeof form.requestSubmit === 'function') {
                form.requestSubmit();
            } else {
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }
        
        function syncSourceTypeUI() {
            const isSubreddit = sourceType.value === 'subreddit';
            if (isSubreddit) {
                sourceInput.style.display = 'none';
                autocompleteContainer.style.display = 'block';
                sourceInput.removeAttribute('required');
                sourceInput.removeAttribute('name');
                sourceHidden.setAttribute('name', 'source');
                sourceHidden.removeAttribute('required');
            } else {
                const pendingName = autocompleteInput.value.trim();
                if (!sourceInput.value.trim() && pendingName) {
                    sourceInput.value = pendingName;
                }
                sourceInput.style.display = 'block';
                autocompleteContainer.style.display = 'none';
                sourceInput.setAttribute('required', '');
                sourceInput.setAttribute('name', 'source');
                sourceHidden.removeAttribute('name');
                sourceHidden.removeAttribute('required');
                sourceHidden.value = '';
                selectedSubreddits = [];
                updateSubredditTags();
            }
        }
        
        // Toggle between single input and autocomplete based on source type
        if (sourceType && sourceInput && autocompleteContainer && sourceHidden) {
            sourceType.addEventListener('change', syncSourceTypeUI);
            syncSourceTypeUI();
        }
        
        function updateSubredditTags() {
            subredditTags.innerHTML = '';
            selectedSubreddits.forEach((subreddit, index) => {
                const tag = document.createElement('div');
                tag.className = 'subreddit-tag';
                tag.innerHTML = `
                    r/${subreddit}
                    <span class="remove" data-index="${index}">&times;</span>
                `;
                tag.querySelector('.remove').addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectedSubreddits.splice(index, 1);
                    updateSubredditTags();
                    updateHiddenInput();
                });
                subredditTags.appendChild(tag);
            });
        }
        
        function updateHiddenInput() {
            sourceHidden.value = selectedSubreddits.join(',');
            // Save to localStorage
            CacheUtils.set('user_selected_subreddits', selectedSubreddits);
        }
        
        function addSubreddit(name) {
            const normalized = name.toLowerCase().trim();
            if (normalized && !selectedSubreddits.includes(normalized)) {
                selectedSubreddits.push(normalized);
                updateSubredditTags();
                updateHiddenInput();
            }
            autocompleteInput.value = '';
            autocompleteDropdown.classList.remove('show');
        }
        
        // Restore user preferences on page load
        function restoreUserPreferences() {
            const savedSubreddits = CacheUtils.get('user_selected_subreddits');
            if (savedSubreddits && Array.isArray(savedSubreddits)) {
                selectedSubreddits = savedSubreddits;
                updateSubredditTags();
                updateHiddenInput();
            }
        }
        
        // Restore preferences on page load
        restoreUserPreferences();
        
        function showAutocomplete(results) {
            autocompleteDropdown.innerHTML = '';
            
            if (results.length === 0) {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.textContent = 'No subreddits found';
                item.style.color = '#999';
                autocompleteDropdown.appendChild(item);
            } else {
                results.forEach(result => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.innerHTML = `
                        <div class="autocomplete-item-name">
                            r/${result.name}
                        </div>
                        <div class="autocomplete-item-meta">
                            ${result.subscribers ? `${result.subscribers.toLocaleString()} subscribers` : ''}
                        </div>
                        ${result.description ? `<div class="autocomplete-item-description">${result.description}</div>` : ''}
                    `;
                    item.addEventListener('click', () => {
                        addSubreddit(result.name);
                    });
                    autocompleteDropdown.appendChild(item);
                });
            }
            
            autocompleteDropdown.classList.add('show');
        }
        
        async function fetchSubredditSuggestions(query) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), SEARCH_TIMEOUT_MS);
            try {
                const response = await fetch(
                    `/api/search-subreddits?q=${encodeURIComponent(query)}`,
                    { signal: controller.signal },
                );
                if (!response.ok) return;
                const result = await response.json();
                if (result.success && result.results) {
                    showAutocomplete(result.results);
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Error fetching subreddits:', err);
                }
            } finally {
                clearTimeout(timeoutId);
            }
        }

        if (autocompleteInput) {
            autocompleteInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            clearTimeout(autocompleteTimeout);
            if (query.length < 1) {
                autocompleteDropdown.classList.remove('show');
                return;
            }
            autocompleteTimeout = setTimeout(() => fetchSubredditSuggestions(query), 150);
        });

        autocompleteInput.addEventListener('focus', () => {
            const query = autocompleteInput.value.trim();
            if (query.length >= 1) {
                clearTimeout(autocompleteTimeout);
                autocompleteTimeout = setTimeout(() => fetchSubredditSuggestions(query), 50);
            }
            });
            
            autocompleteInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && autocompleteInput.value.trim()) {
                    e.preventDefault();
                    // Try to add the current input as a subreddit
                    const query = autocompleteInput.value.trim();
                    if (query) {
                        addSubreddit(query);
                    }
                } else if (e.key === 'Escape') {
                    autocompleteDropdown.classList.remove('show');
                }
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                // Only close if clicking outside both the input and the dropdown
                if (autocompleteContainer && autocompleteDropdown && 
                    !autocompleteContainer.contains(e.target) && 
                    !autocompleteDropdown.contains(e.target) &&
                    e.target !== autocompleteInput) {
                    autocompleteDropdown.classList.remove('show');
                }
            });
        }
        
        if (form) {
            form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const sourceTypeValue = formData.get('source_type');

            let sourceValue;
            if (sourceTypeValue === 'subreddit') {
                if (autocompleteInput.value.trim() && !sourceHidden.value) {
                    addSubreddit(autocompleteInput.value.trim());
                }
                sourceValue = sourceHidden.value || autocompleteInput.value.trim();
                if (!sourceValue && autocompleteInput.value.trim()) {
                    sourceValue = autocompleteInput.value.trim();
                }
            } else {
                sourceValue = normalizeUsername(sourceInput.value);
                if (!sourceValue) {
                    showError('validation', 'Username Required', 'Enter a Reddit username (with or without u/).');
                    return;
                }
            }

            if (sourceTypeValue === 'subreddit' && (!sourceValue || !String(sourceValue).trim())) {
                showError(
                    'validation',
                    'Subreddit Required',
                    'Enter or select at least one subreddit before searching.'
                );
                return;
            }

            const data = {
                source: String(sourceValue).trim(),
                source_type: sourceTypeValue,
                limit: PAGE_SIZE,
                sort: formData.get('sort') || 'hot',
                time_filter: formData.get('time_filter') || 'all'
            };
            
            // Store search params for infinite scroll
            currentSearchParams = data;
            currentAfter = null;
            hasMoreItems = false;
            
            grid.innerHTML = '';
            error.classList.remove('show');
            loading.classList.add('show');
            loading.style.display = 'block';
            loadingMore.classList.remove('show');
            loadingMore.style.display = 'none';
            stats.textContent = '';
            
            try {
                // Add timeout to fetch request
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), SCRAPE_TIMEOUT_MS);
                
                const response = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: buildScrapeParams(data),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                const result = await parseScrapeResponse(response);
                loading.style.display = 'none';
                loading.classList.remove('show');
                
                if (result.success) {
                    allMediaItems = result.items;
                    hasMoreItems = result.has_more || false;
                    currentAfter = result.after;
                    displayMedia(result.items, true);
                    updateStats();
                    fillViewportIfNeeded();
                } else {
                    // Determine error type from result
                    const errorMsg = result.error || 'An error occurred while fetching data';
                    let errorType = 'api';
                    let errorTitle = 'Failed to Load Content';
                    let errorDetails = errorMsg;
                    
                    if (errorMsg.toLowerCase().includes('rate limit') || errorMsg.includes('429')) {
                        errorType = 'rate-limit';
                        errorTitle = 'Rate Limit Exceeded';
                        errorDetails = 'Too many requests. Please wait a moment and try again.';
                    } else if (errorMsg.toLowerCase().includes('not found') || errorMsg.includes('404')) {
                        errorType = 'validation';
                        errorTitle = 'Subreddit Not Found';
                        errorDetails = 'The subreddit or user you searched for does not exist or is private.';
                    } else if (errorMsg.toLowerCase().includes('unauthorized') || errorMsg.includes('401')) {
                        errorType = 'api';
                        errorTitle = 'Authentication Error';
                        errorDetails = 'Reddit API authentication failed. Please check your API credentials.';
                    }
                    
                    showError(errorType, errorTitle, errorDetails, () => {
                        form.dispatchEvent(new Event('submit'));
                    });
                }
            } catch (err) {
                loading.style.display = 'none';
                let errorType = 'network';
                let errorTitle = 'Connection Error';
                let errorDetails = 'Unable to connect to the server.';
                
                if (err.name === 'AbortError') {
                    errorType = 'timeout';
                    errorTitle = 'Request Timed Out';
                    errorDetails = 'Reddit is taking longer than usual. Try again, or search fewer subreddits at once.';
                } else if (err.message && err.message.includes('Failed to fetch')) {
                    errorType = 'network';
                    errorTitle = 'Network Error';
                    errorDetails = 'Please check your internet connection and try again.';
                } else {
                    errorType = 'unknown';
                    errorTitle = 'Unexpected Error';
                    errorDetails = err.message || 'An unexpected error occurred. Please try again.';
                }
                
                showError(errorType, errorTitle, errorDetails, () => {
                    form.dispatchEvent(new Event('submit'));
                });
                console.error('Error fetching data:', err);
            }
            });
        }
        
        function updateStats() {
            if (!stats) return;
            if (allMediaItems.length === 0) {
                stats.textContent = '';
                return;
            }
            const suffix = hasMoreItems ? ' · loading more as you scroll' : '';
            stats.textContent = `${allMediaItems.length} items loaded${suffix}`;
        }

        async function loadMoreItems() {
            if (isLoadingMore || !hasMoreItems || !currentSearchParams) return;
            
            isLoadingMore = true;
            loadingMore.style.display = 'block';
            loadingMore.classList.add('show');
            
            const data = {
                ...currentSearchParams,
                after: currentAfter
            };
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), LOAD_MORE_TIMEOUT_MS);
                
                const response = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: buildScrapeParams(data),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                const result = await parseScrapeResponse(response);
                loadingMore.style.display = 'none';
                loadingMore.classList.remove('show');
                
                if (result.success && result.items.length > 0) {
                    allMediaItems = [...allMediaItems, ...result.items];
                    hasMoreItems = result.has_more || false;
                    currentAfter = result.after;
                    displayMedia(result.items, false);
                    updateStats();
                    fillViewportIfNeeded();
                } else {
                    hasMoreItems = false;
                    updateStats();
                }
            } catch (err) {
                loadingMore.style.display = 'none';
                loadingMore.classList.remove('show');
                if (err.name === 'AbortError') {
                    console.error('Request timed out while loading more items');
                } else {
                    console.error('Error loading more items:', err);
                    const tempMsg = document.createElement('div');
                    tempMsg.style.cssText = 'text-align: center; color: #ff6b6b; padding: 10px; font-size: 14px;';
                    tempMsg.textContent = 'Failed to load more items. Keep scrolling to retry.';
                    loadingMore.parentNode.insertBefore(tempMsg, loadingMore.nextSibling);
                    setTimeout(() => tempMsg.remove(), 5000);
                }
            } finally {
                isLoadingMore = false;
            }
        }

        async function fillViewportIfNeeded() {
            if (!hasMoreItems || isLoadingMore) return;
            const docHeight = document.documentElement.scrollHeight;
            const viewHeight = window.innerHeight;
            if (docHeight <= viewHeight + 200) {
                await loadMoreItems();
            }
        }

        function setupInfiniteScroll() {
            if (!scrollSentinel || infiniteScrollObserver) return;

            infiniteScrollObserver = new IntersectionObserver((entries) => {
                if (entries.some(entry => entry.isIntersecting)) {
                    loadMoreItems();
                }
            }, {
                root: null,
                rootMargin: '600px',
                threshold: 0,
            });

            infiniteScrollObserver.observe(scrollSentinel);
        }

        setupInfiniteScroll();
        
        // Intersection Observer for enhanced lazy loading
        let imageObserver = null;
        
        function initImageObserver() {
            if (imageObserver) return;
            
            imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    }
                });
            }, {
                rootMargin: '100px' // Start loading 100px before image enters viewport
            });
        }
        
        function isPlayableVideo(item) {
            const urlLower = item.url.toLowerCase();
            const isRedditPreviewVideo =
                urlLower.includes('preview.redd.it') && /\bformat=(mp4|webm)(\b|[&])/i.test(urlLower);
            const isVideo = item.is_video ||
                urlLower.includes('.mp4') ||
                urlLower.includes('.webm') ||
                urlLower.includes('v.redd.it') ||
                urlLower.includes('packaged-media.redd.it') ||
                urlLower.includes('media.redgifs.com') ||
                isRedditPreviewVideo ||
                (urlLower.includes('redgifs.com') && (
                    urlLower.includes('/watch/') || urlLower.includes('.mp4') || urlLower.includes('.webm')
                ));
            const isImage = !isRedditPreviewVideo && (
                urlLower.includes('.jpg') ||
                urlLower.includes('.jpeg') ||
                urlLower.includes('.png') ||
                urlLower.includes('.webp') ||
                (urlLower.includes('.gif') && !urlLower.includes('redgifs.com') &&
                    !urlLower.includes('.mp4') && !/\bformat=(mp4|webm)(\b|[&])/i.test(urlLower))
            );
            return isVideo && !isImage;
        }

        function isRedgifsUrl(url) {
            return url.toLowerCase().includes('redgifs.com');
        }

        function extractRedgifsId(u) {
            if (!u) return null;
            let m = u.match(/(?:www\.)?redgifs\.com\/watch\/([^/?#]+)/i);
            if (m) return m[1];
            m = u.match(/media\.redgifs\.com\/([^/?#]+)\.(?:mp4|webm)/i);
            if (m) {
                let id = m[1];
                if (id.endsWith('-silent')) id = id.slice(0, -7);
                return id;
            }
            return null;
        }

        function redgifsProxySrc(mp4Url) {
            return `/api/proxy-video?url=${encodeURIComponent(mp4Url)}`;
        }

        function redgifsEmbedUrl(u) {
            const id = extractRedgifsId(u);
            return id ? `https://www.redgifs.com/ifr/${id.toLowerCase()}` : null;
        }

        function mountRedgifsIframe(container, displayUrl, options = {}) {
            const embedUrl = redgifsEmbedUrl(displayUrl);
            if (!embedUrl) return false;
            container.innerHTML = '';
            container.classList.add('has-redgifs-embed');
            const iframe = document.createElement('iframe');
            iframe.src = embedUrl;
            iframe.title = 'Redgifs video';
            iframe.loading = 'lazy';
            iframe.allow = 'autoplay; fullscreen';
            iframe.setAttribute('allowfullscreen', '');
            iframe.referrerPolicy = 'no-referrer-when-downgrade';
            if (options.pointerEventsNone) {
                iframe.style.pointerEvents = 'none';
            }
            container.appendChild(iframe);
            return true;
        }

        async function resolveRedgifsMp4Url(displayUrl) {
            const response = await fetch(`/api/resolve-redgifs?url=${encodeURIComponent(displayUrl)}`);
            if (!response.ok) return null;
            const data = await response.json();
            return data.url || null;
        }

        function wireRedgifsVideoPlayback(video, container, displayUrl, options = {}) {
            const logPrefix = options.logPrefix || 'Redgifs';
            let resolveAttempted = false;
            let iframeFallbackUsed = false;

            const tryIframeFallback = () => {
                if (iframeFallbackUsed) return;
                iframeFallbackUsed = true;
                console.warn(`${logPrefix}: falling back to Redgifs embed`);
                mountRedgifsIframe(container, displayUrl, options);
            };

            video.addEventListener('error', async () => {
                console.error(`${logPrefix} video load error:`, displayUrl, video.error);

                if (!resolveAttempted) {
                    resolveAttempted = true;
                    try {
                        const resolved = await resolveRedgifsMp4Url(displayUrl);
                        if (resolved && resolved !== displayUrl) {
                            video.src = redgifsProxySrc(resolved);
                            return;
                        }
                    } catch (err) {
                        console.warn(`${logPrefix} resolve failed:`, err);
                    }
                }

                tryIframeFallback();
            });
        }
        
        function displayMedia(items, clearGrid = true) {
            if (clearGrid) {
                grid.innerHTML = '';
            }
            
            // Initialize observer if not already done
            initImageObserver();
            
            items.forEach(item => {
                const card = document.createElement('div');
                card.className = 'media-card';
                
                const mediaContainer = document.createElement('div');
                mediaContainer.className = 'media-container';
                
                const displayUrl = item.url;
                const urlLower = displayUrl.toLowerCase();
                
                if (isPlayableVideo(item)) {
                    mediaContainer.classList.add('has-video');
                    card.classList.add('has-video');
                    const video = document.createElement('video');
                    video.muted = true;
                    video.loop = true;
                    video.playsInline = true;
                    video.preload = 'metadata';
                    video.setAttribute('playsinline', '');
                    
                    const isRedgifsDirect = isRedgifsUrl(displayUrl);
                    
                    if (isRedgifsDirect) {
                        video.src = redgifsProxySrc(displayUrl);
                        video.crossOrigin = null;
                        wireRedgifsVideoPlayback(video, mediaContainer, displayUrl, {
                            logPrefix: 'Grid',
                            pointerEventsNone: true,
                        });
                    } else {
                        // For other external domains, try with CORS
                        video.src = displayUrl;
                        if (!urlLower.includes('i.redd.it') && !urlLower.includes('v.redd.it') && !urlLower.includes('preview.redd.it') && !urlLower.includes('packaged-media.redd.it')) {
                            video.crossOrigin = 'anonymous';
                        }
                    }
                    
                    // Add error handling
                    let errorShown = false;
                    video.addEventListener('error', (e) => {
                        if (errorShown) return; // Prevent multiple error messages
                        errorShown = true;
                        
                        console.error('Video load error:', e, displayUrl, video.error);
                        if (video.error) {
                            console.error('Video error code:', video.error.code, 'Message:', video.error.message);
                        }
                    });
                    
                    // Add loading state
                    video.addEventListener('loadstart', () => {
                        video.style.opacity = '0.7';
                        errorShown = false; // Reset error flag when loading starts
                    });
                    
                    video.addEventListener('canplay', () => {
                        video.style.opacity = '1';
                    });
                    
                    // Log when video is ready
                    video.addEventListener('loadeddata', () => {
                        console.log('Video loaded successfully:', displayUrl);
                        errorShown = false; // Reset error flag on successful load
                    });
                    
                    mediaContainer.appendChild(video);
                } else {
                    const img = document.createElement('img');
                    // Use data-src for lazy loading with Intersection Observer
                    img.dataset.src = displayUrl;
                    img.alt = item.title;
                    // Set a placeholder or empty src initially
                    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"%3E%3C/svg%3E';
                    img.loading = 'lazy';
                    
                    // Add error handling with retry
                    img.addEventListener('error', (e) => {
                        console.error('Image load error:', displayUrl);
                        const errorDiv = document.createElement('div');
                        errorDiv.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px; text-align: center; min-width: 200px;';
                        const msg = document.createElement('div');
                        msg.style.marginBottom = '10px';
                        msg.textContent = '⚠️ Image failed to load';
                        const btn = document.createElement('button');
                        btn.style.cssText = 'background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;';
                        btn.textContent = 'Retry';
                        btn.onclick = () => {
                            img.src = displayUrl;
                            errorDiv.remove();
                        };
                        errorDiv.appendChild(msg);
                        errorDiv.appendChild(btn);
                        mediaContainer.appendChild(errorDiv);
                    });
                    
                    // Observe the image for lazy loading
                    imageObserver.observe(img);
                    mediaContainer.appendChild(img);
                }
                
                const permalink = item.permalink || `https://reddit.com/r/${item.subreddit}`;
                const author = item.author || 'Unknown';

                const scoreBadge = document.createElement('span');
                scoreBadge.className = 'media-score-badge';
                scoreBadge.textContent = item.score ?? 0;

                const overlay = document.createElement('div');
                overlay.className = 'media-overlay';

                const titleEl = document.createElement('div');
                titleEl.className = 'media-overlay-title';
                titleEl.textContent = item.title;

                const meta = document.createElement('div');
                meta.className = 'media-overlay-meta';

                const metaLeft = document.createElement('div');
                metaLeft.className = 'media-overlay-meta-left';

                const userLink = document.createElement('a');
                userLink.href = '#';
                userLink.className = 'user-link';
                userLink.textContent = `u/${author}`;
                userLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    searchSourceInApp('user', author);
                });

                const sep = document.createElement('span');
                sep.className = 'sep';
                sep.textContent = '•';

                const subLink = document.createElement('a');
                subLink.href = '#';
                subLink.className = 'user-link';
                subLink.textContent = `r/${item.subreddit}`;
                subLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    searchSourceInApp('subreddit', item.subreddit);
                });

                const redditLink = document.createElement('a');
                redditLink.href = permalink;
                redditLink.target = '_blank';
                redditLink.rel = 'noopener noreferrer';
                redditLink.className = 'reddit-link';
                redditLink.title = 'Open on Reddit';
                redditLink.textContent = '↗';
                redditLink.addEventListener('click', (e) => e.stopPropagation());

                metaLeft.appendChild(userLink);
                metaLeft.appendChild(sep);
                metaLeft.appendChild(subLink);
                meta.appendChild(metaLeft);
                meta.appendChild(redditLink);
                overlay.appendChild(titleEl);
                overlay.appendChild(meta);
                
                // Add favorite button to card
                const favoriteCardBtn = document.createElement('button');
                favoriteCardBtn.className = 'favorite-btn';
                favoriteCardBtn.innerHTML = FavoritesUtils.has(item.url) ? '⭐' : '☆';
                favoriteCardBtn.title = FavoritesUtils.has(item.url) ? 'Remove from favorites' : 'Add to favorites';
                favoriteCardBtn.onclick = (e) => {
                    e.stopPropagation();
                    if (FavoritesUtils.has(item.url)) {
                        FavoritesUtils.remove(item.url);
                        favoriteCardBtn.innerHTML = '☆';
                        favoriteCardBtn.title = 'Add to favorites';
                        favoriteCardBtn.classList.remove('favorited');
                    } else {
                        FavoritesUtils.add(item.url);
                        favoriteCardBtn.innerHTML = '⭐';
                        favoriteCardBtn.title = 'Remove from favorites';
                        favoriteCardBtn.classList.add('favorited');
                    }
                };
                if (FavoritesUtils.has(item.url)) {
                    favoriteCardBtn.classList.add('favorited');
                }
                mediaContainer.appendChild(favoriteCardBtn);
                mediaContainer.appendChild(scoreBadge);
                mediaContainer.appendChild(overlay);
                
                card.appendChild(mediaContainer);
                
                const gridVideo = mediaContainer.querySelector('video');
                if (gridVideo) {
                    card.addEventListener('mouseenter', () => {
                        grid.querySelectorAll('.media-container video').forEach(v => {
                            if (v !== gridVideo) {
                                v.pause();
                                v.currentTime = 0;
                            }
                        });
                        gridVideo.play().catch(() => {});
                    });
                    card.addEventListener('mouseleave', () => {
                        gridVideo.pause();
                        gridVideo.currentTime = 0;
                    });
                }
                
                card.addEventListener('click', () => {
                    const index = allMediaItems.findIndex(i => i.url === item.url);
                    openModal(index);
                });
                grid.appendChild(card);
            });
        }
        
        function openModal(index) {
            if (index < 0 || index >= allMediaItems.length) return;
            
            currentIndex = index;
            updateModalContent();
            updateNavigation();
            modal.style.display = 'block';
        }
        
        function updateModalContent() {
            if (currentIndex < 0 || currentIndex >= allMediaItems.length) return;
            
            const item = allMediaItems[currentIndex];
            modalMediaContainer.innerHTML = '';
            
            const displayUrl = item.url;
            const urlLower = displayUrl.toLowerCase();
            
            if (isPlayableVideo(item)) {
                videoControls.style.display = 'flex';
                
                const video = document.createElement('video');
                video.controls = true;
                video.muted = true;
                video.volume = 1.0;
                video.autoplay = true;
                video.loop = true;
                video.playsInline = true;
                video.playbackRate = parseFloat(playbackSpeed.value);
                
                const isRedgifsDirect = isRedgifsUrl(displayUrl);
                
                if (isRedgifsDirect) {
                    video.src = redgifsProxySrc(displayUrl);
                    video.crossOrigin = null;
                    wireRedgifsVideoPlayback(video, modalMediaContainer, displayUrl, {
                        logPrefix: 'Modal',
                    });
                } else {
                    video.src = displayUrl;
                    if (!urlLower.includes('i.redd.it') && !urlLower.includes('v.redd.it') &&
                        !urlLower.includes('preview.redd.it') && !urlLower.includes('packaged-media.redd.it')) {
                        video.crossOrigin = 'anonymous';
                    }
                }
                
                let errorShown = false;
                if (!isRedgifsDirect) video.addEventListener('error', () => {
                    if (errorShown) return;
                    errorShown = true;
                    const errorDiv = document.createElement('div');
                    errorDiv.style.cssText = 'color: white; background: rgba(0,0,0,0.7); padding: 20px; border-radius: 5px; text-align: center; cursor: pointer;';
                    errorDiv.innerHTML = 'Video failed to load.<br><small>Click to retry</small>';
                    errorDiv.onclick = () => {
                        errorDiv.remove();
                        errorShown = false;
                        video.load();
                        video.play().catch(err => console.error('Play failed:', err));
                    };
                    modalMediaContainer.appendChild(errorDiv);
                });
                
                video.addEventListener('loadeddata', () => {
                    errorShown = false;
                    if (modalInfoDimensions) {
                        modalInfoDimensions.textContent = `${video.videoWidth} × ${video.videoHeight}px`;
                    }
                    video.muted = false;
                    video.play().catch(() => {});
                });
                
                video.addEventListener('playing', () => {
                    video.muted = false;
                    video.volume = 1.0;
                }, { once: true });
                
                modalMediaContainer.appendChild(video);
            } else {
                // Hide video controls for images
                videoControls.style.display = 'none';
                
                const img = document.createElement('img');
                img.src = displayUrl;
                img.alt = item.title;
                
                // Update dimensions when image loads
                img.addEventListener('load', () => {
                    if (modalInfoDimensions) {
                        modalInfoDimensions.textContent = `${img.naturalWidth} × ${img.naturalHeight}px`;
                    }
                });
                
                img.addEventListener('error', () => {
                    if (modalInfoDimensions) {
                        modalInfoDimensions.textContent = 'Failed to load';
                    }
                });
                
                modalMediaContainer.appendChild(img);
            }
            
            // Update favorite button
            updateFavoriteButton();
            
            galleryInfo.textContent = `${currentIndex + 1} / ${allMediaItems.length}`;
        }
        
        function updateNavigation() {
            prevArrow.classList.toggle('disabled', currentIndex === 0);
            nextArrow.classList.toggle('disabled', currentIndex === allMediaItems.length - 1);
            prevClickArea.style.display = currentIndex === 0 ? 'none' : 'block';
            nextClickArea.style.display = currentIndex === allMediaItems.length - 1 ? 'none' : 'block';
        }
        
        
        function navigateNext() {
            if (currentIndex < allMediaItems.length - 1) {
                currentIndex++;
                updateModalContent();
                updateNavigation();
                // Preload next media
                if (currentIndex < allMediaItems.length - 1) {
                    const nextItem = allMediaItems[currentIndex + 1];
                    const link = document.createElement('link');
                    link.rel = 'prefetch';
                    link.href = nextItem.url;
                    document.head.appendChild(link);
                }
            }
        }
        
        function navigatePrev() {
            if (currentIndex > 0) {
                currentIndex--;
                updateModalContent();
                updateNavigation();
                // Preload previous media
                if (currentIndex > 0) {
                    const prevItem = allMediaItems[currentIndex - 1];
                    const link = document.createElement('link');
                    link.rel = 'prefetch';
                    link.href = prevItem.url;
                    document.head.appendChild(link);
                }
            }
        }
        
        prevArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            navigatePrev();
        });
        
        nextArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            navigateNext();
        });
        
        prevClickArea.addEventListener('click', (e) => {
            e.stopPropagation();
            navigatePrev();
        });
        
        nextClickArea.addEventListener('click', (e) => {
            e.stopPropagation();
            navigateNext();
        });
        
        // Favorites system
        const FavoritesUtils = {
            get() {
                try {
                    const favs = CacheUtils.get('favorites');
                    return favs || [];
                } catch (e) {
                    return [];
                }
            },
            add(url) {
                const favs = this.get();
                if (!favs.includes(url)) {
                    favs.push(url);
                    CacheUtils.set('favorites', favs);
                }
            },
            remove(url) {
                const favs = this.get();
                const index = favs.indexOf(url);
                if (index > -1) {
                    favs.splice(index, 1);
                    CacheUtils.set('favorites', favs);
                }
            },
            has(url) {
                return this.get().includes(url);
            }
        };
        
        // Dark mode
        const darkModeToggle = document.getElementById('darkModeToggle');
        const isDarkMode = () => document.body.classList.contains('dark-mode');
        const setDarkMode = (enabled) => {
            if (enabled) {
                document.body.classList.add('dark-mode');
                darkModeToggle.textContent = '☀️';
                CacheUtils.set('darkMode', true);
            } else {
                document.body.classList.remove('dark-mode');
                darkModeToggle.textContent = '🌙';
                CacheUtils.set('darkMode', false);
            }
        };
        
        // Load dark mode preference
        if (CacheUtils.get('darkMode')) {
            setDarkMode(true);
        }
        
        darkModeToggle.addEventListener('click', () => {
            setDarkMode(!isDarkMode());
        });
        
        function downloadMedia(url, filename) {
            const downloadUrl = `/api/download?url=${encodeURIComponent(url)}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = filename || 'media';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        const downloadBtn = document.getElementById('downloadBtn');
        const copyUrlBtn = document.getElementById('copyUrlBtn');
        const openRedditBtn = document.getElementById('openRedditBtn');
        const modalInfoToggle = document.getElementById('modalInfoToggle');
        const modalInfoPanel = document.getElementById('modalInfoPanel');
        const modalInfoTitle = document.getElementById('modalInfoTitle');
        const modalInfoSubreddit = document.getElementById('modalInfoSubreddit');
        const modalInfoAuthor = document.getElementById('modalInfoAuthor');
        const modalInfoScore = document.getElementById('modalInfoScore');
        const modalInfoDimensions = document.getElementById('modalInfoDimensions');
        const modalInfoUrl = document.getElementById('modalInfoUrl');
        const modalInfoCopyUrl = document.getElementById('modalInfoCopyUrl');
        const modalInfoOpenReddit = document.getElementById('modalInfoOpenReddit');
        
        downloadBtn.addEventListener('click', () => {
            if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                const item = allMediaItems[currentIndex];
                const streamUrl = item.url;
                const filename = `${item.subreddit}_${item.title.substring(0, 50).replace(/[^a-z0-9]/gi, '_')}.${streamUrl.split('.').pop().split('?')[0]}`;
                downloadMedia(streamUrl, filename);
            }
        });
        
        // Copy URL functionality
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show feedback
                const originalText = copyUrlBtn.textContent;
                copyUrlBtn.textContent = '✓ Copied!';
                setTimeout(() => {
                    copyUrlBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                copyUrlBtn.textContent = '✓ Copied!';
                setTimeout(() => {
                    copyUrlBtn.textContent = '📋 Copy URL';
                }, 2000);
            });
        }
        
        if (copyUrlBtn) {
            copyUrlBtn.addEventListener('click', () => {
                if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                    const item = allMediaItems[currentIndex];
                    copyToClipboard(item.url);
                }
            });
        }
        
        if (modalInfoCopyUrl) {
            modalInfoCopyUrl.addEventListener('click', () => {
                if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                    const item = allMediaItems[currentIndex];
                    copyToClipboard(item.url);
                }
            });
        }
        
        // Open in Reddit functionality
        if (openRedditBtn) {
            openRedditBtn.addEventListener('click', () => {
                if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                    const item = allMediaItems[currentIndex];
                    window.open(item.permalink || `https://reddit.com/r/${item.subreddit}`, '_blank');
                }
            });
        }
        
        if (modalInfoOpenReddit) {
            modalInfoOpenReddit.addEventListener('click', () => {
                if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                    const item = allMediaItems[currentIndex];
                    window.open(item.permalink || `https://reddit.com/r/${item.subreddit}`, '_blank');
                }
            });
        }
        
        // Toggle info panel
        if (modalInfoToggle) {
            modalInfoToggle.addEventListener('click', () => {
                modalInfoPanel.classList.toggle('show');
            });
        }
        
        // Favorites functionality
        const favoriteBtn = document.getElementById('favoriteBtn');
        function updateFavoriteButton() {
            if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                const item = allMediaItems[currentIndex];
                const isFavorited = FavoritesUtils.has(item.url);
                favoriteBtn.classList.toggle('favorited', isFavorited);
                favoriteBtn.textContent = isFavorited ? '⭐ Favorited' : '⭐ Favorite';
            }
        }
        
        favoriteBtn.addEventListener('click', () => {
            if (currentIndex >= 0 && currentIndex < allMediaItems.length) {
                const item = allMediaItems[currentIndex];
                if (FavoritesUtils.has(item.url)) {
                    FavoritesUtils.remove(item.url);
                } else {
                    FavoritesUtils.add(item.url);
                }
                updateFavoriteButton();
            }
        });
        
        // Fullscreen functionality
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                modal.requestFullscreen().catch(err => {
                    console.error('Error attempting to enable fullscreen:', err);
                });
            } else {
                document.exitFullscreen();
            }
        });
        
        // Update fullscreen button on change
        document.addEventListener('fullscreenchange', () => {
            fullscreenBtn.textContent = document.fullscreenElement ? '⛶ Exit Fullscreen' : '⛶ Fullscreen';
            modal.classList.toggle('fullscreen', !!document.fullscreenElement);
        });
        
        // Video playback speed
        const playbackSpeed = document.getElementById('playbackSpeed');
        const videoControls = document.getElementById('videoControls');
        playbackSpeed.addEventListener('change', (e) => {
            const video = modalMediaContainer.querySelector('video');
            if (video) {
                video.playbackRate = parseFloat(e.target.value);
            }
        });
        
        const shortcutsLegend = document.getElementById('shortcutsLegend');
        const helpBtn = document.getElementById('helpBtn');
        const shortcutsLegendClose = document.getElementById('shortcutsLegendClose');
        
        function toggleShortcutsLegend() {
            shortcutsLegend.classList.toggle('show');
        }
        
        function closeShortcutsLegend() {
            shortcutsLegend.classList.remove('show');
        }
        
        // Help button click
        if (helpBtn) {
            helpBtn.addEventListener('click', toggleShortcutsLegend);
        }
        
        // Close legend button
        if (shortcutsLegendClose) {
            shortcutsLegendClose.addEventListener('click', closeShortcutsLegend);
        }
        
        // Close legend when clicking outside
        if (shortcutsLegend) {
            shortcutsLegend.addEventListener('click', (e) => {
                if (e.target === shortcutsLegend) {
                    closeShortcutsLegend();
                }
            });
        }
        
        document.addEventListener('keydown', (e) => {
            // Don't trigger shortcuts when typing in inputs
            const activeElement = document.activeElement;
            const isInputFocused = activeElement && (
                activeElement.tagName === 'INPUT' || 
                activeElement.tagName === 'TEXTAREA' ||
                activeElement.isContentEditable
            );
            
            // Handle ? key globally (except when typing)
            if (e.key === '?' && !e.ctrlKey && !e.metaKey && !isInputFocused) {
                e.preventDefault();
                toggleShortcutsLegend();
                return;
            }
            
            // Handle / key to focus search (only when not in input)
            if (e.key === '/' && !isInputFocused && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                if (sourceType.value === 'subreddit' && autocompleteInput) {
                    autocompleteInput.focus();
                } else if (sourceInput) {
                    sourceInput.focus();
                }
                return;
            }
            
            if (modal.style.display === 'block') {
                // Prevent default for shortcuts in modal
                if (['ArrowLeft', 'ArrowRight', 'Escape', ' ', 'd', 'D', 'f', 'F', 'F11'].includes(e.key)) {
                    e.preventDefault();
                }
                
                if (e.key === 'ArrowLeft') {
                    navigatePrev();
                } else if (e.key === 'ArrowRight') {
                    navigateNext();
                } else if (e.key === 'Escape') {
                    modal.style.display = 'none';
                } else if (e.key === ' ' || e.key === 'Spacebar') {
                    e.preventDefault();
                    const video = modalMediaContainer.querySelector('video');
                    // If it's a video, toggle play/pause; otherwise go to next image
                    if (video && document.activeElement !== video) {
                        if (video.paused) {
                            video.play();
                        } else {
                            video.pause();
                        }
                    } else {
                        // Navigate to next image
                        navigateNext();
                    }
                } else if (e.key === 'd' || e.key === 'D') {
                    downloadBtn.click();
                } else if (e.key === 'f' || e.key === 'F') {
                    if (!e.shiftKey) {
                        favoriteBtn.click();
                    } else {
                        fullscreenBtn.click();
                    }
                } else if (e.key === 'F11') {
                    e.preventDefault();
                    fullscreenBtn.click();
                }
            }
        });
        
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // Swipe gestures for mobile navigation
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;
        
        modal.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });
        
        modal.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            const minSwipeDistance = 50;
            
            // Only handle horizontal swipes (ignore vertical scrolling)
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    // Swipe right - go to previous
                    navigatePrev();
                } else {
                    // Swipe left - go to next
                    navigateNext();
                }
            }
        }
