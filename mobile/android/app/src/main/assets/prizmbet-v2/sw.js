// ── PrizmBet Service Worker ───────────────────────────────────────────────────
const VERSION     = 'v24';
const SHELL_CACHE = `prizmbet-shell-${VERSION}`;
const DATA_CACHE  = 'prizmbet-data';   // вечный, обновляется по контенту

// Статика, которую кэшируем при install (App Shell)
const SHELL_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './api.js',
    './tests.js',
    './js/app.js',
    './js/modules/bet_slip.js',
    './js/modules/filters.js',
    './js/modules/history_ui.js',
    './js/modules/notifications.js',
    './js/modules/storage.js',
    './js/modules/ui.js',
    './js/modules/utils.js',
    './css/base.min.css',
    './prizmbet-logo.webp',
    './qr_wallet.webp',
    './prizmbet-info-1.webp',
    './prizmbet-info-2.webp',
    './icon-192x192.png',
    './icon-512x512.png',
];

// ── INSTALL: предзагрузка Shell ───────────────────────────────────────────────
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(SHELL_CACHE).then(cache =>
            cache.addAll(SHELL_ASSETS).catch(err =>
                console.warn('[SW] Install - некоторые ресурсы не закэшированы:', err)
            )
        )
    );
});

// ── ACTIVATE: удаляем старые кэши ────────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(k => k !== SHELL_CACHE && k !== DATA_CACHE)
                    .map(k => caches.delete(k))
            )
        ).then(() => clients.claim())
    );
});

// ── HELPERS ───────────────────────────────────────────────────────────────────
function isDataRequest(url) {
    return url.includes('matches.json') || url.includes('matches-today.json');
}

function isShellAsset(url) {
    // Google Fonts и внешние ресурсы — пусть браузер кэширует сам
    return url.startsWith(self.location.origin) && !isDataRequest(url);
}

// Stale-While-Revalidate: сразу отдаём кэш, обновляем в фоне
function staleWhileRevalidate(request, cacheName) {
    const cachePromise = caches.open(cacheName);
    return cachePromise.then(cache =>
        cache.match(request).then(cached => {
            const networkFetch = fetch(request).then(response => {
                if (response && response.status === 200) {
                    cache.put(request, response.clone());
                }
                return response;
            }).catch(() => cached);

            return cached || networkFetch;
        })
    );
}

// Network-First с таймаутом, fallback — кэш
function networkFirst(request, cacheName, timeoutMs = 4000) {
    return caches.open(cacheName).then(cache => {
        const networkPromise = new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('timeout')), timeoutMs);
            fetch(request).then(response => {
                clearTimeout(timer);
                if (response && response.status === 200) {
                    cache.put(request, response.clone());
                }
                resolve(response);
            }).catch(err => { clearTimeout(timer); reject(err); });
        });

        return networkPromise.catch(() =>
            cache.match(request).then(cached => cached || caches.match('./index.html'))
        );
    });
}

// Cache-First: быстрая отдача статики, сеть — только если нет в кэше
function cacheFirst(request, cacheName) {
    return caches.open(cacheName).then(cache =>
        cache.match(request).then(cached => {
            if (cached) return cached;
            return fetch(request).then(response => {
                if (response && response.status === 200 && response.type === 'basic') {
                    cache.put(request, response.clone());
                }
                return response;
            }).catch(() => caches.match('./index.html'));
        })
    );
}

// ── FETCH ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = request.url;

    // Только GET
    if (request.method !== 'GET') return;

    // Данные (matches.json, matches-today.json): Stale-While-Revalidate
    // Пользователь сразу видит прошлые данные, свежие приходят в фоне
    if (isDataRequest(url)) {
        event.respondWith(staleWhileRevalidate(request, DATA_CACHE));
        return;
    }

    // App Shell и локальные ресурсы: Stale-While-Revalidate
    // (быстро отдаём из кэша, обновляем в фоне — новый код виден со следующего визита)
    if (isShellAsset(url)) {
        event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
        return;
    }

    // Всё остальное (Google Fonts, внешние CDN): сеть, без кэша
    // (браузер сам их кэширует по Cache-Control заголовкам)
});
