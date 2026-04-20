# Performance Tuning — VPS Checklist

Audit notes from 2026-04-20. All numbers measured against `https://prizmbet.net`.

## Current state

| Metric | Value | Status |
| --- | --- | --- |
| `Content-Encoding: gzip` on JSON/CSS/JS | **absent** | ❌ |
| `Cache-Control` on static assets | **absent** | ❌ |
| `matches.json` transfer size | 142 KB (uncompressed) | ❌ |
| Active parsers | Leonbets only (4 of 5 skipped) | ❌ |
| Leonbets per-cycle cap | 200 events (hard-coded) | now env-configurable |

First-paint bandwidth for a cold visitor: **~275 KB** of critical JSON/CSS/JS.
With gzip: **~54 KB** (–80 %).

## 1. nginx — enable gzip + caching

Add to the `server { ... }` block of `/etc/nginx/sites-enabled/prizmbet.net`
(or wherever the main server is defined). Safe to drop in verbatim.

```nginx
# -------- gzip compression --------
gzip on;
gzip_vary on;
gzip_comp_level 5;
gzip_min_length 256;
gzip_proxied any;
gzip_types
    text/plain
    text/css
    text/xml
    application/json
    application/javascript
    application/xml
    application/manifest+json
    image/svg+xml;

# -------- long cache for fingerprinted/static assets --------
location ~* \.(css|js|svg|woff2?|ttf|eot|webp|png|gif|jpg|jpeg|ico)$ {
    expires 7d;
    add_header Cache-Control "public, max-age=604800";
    access_log off;
}

# -------- short cache for live match feed --------
location = /matches.json {
    expires 1m;
    add_header Cache-Control "public, max-age=60, must-revalidate";
}
location = /matches-today.json {
    expires 1m;
    add_header Cache-Control "public, max-age=60, must-revalidate";
}
location ^~ /matches/ {
    expires 1m;
    add_header Cache-Control "public, max-age=60, must-revalidate";
}

# -------- always revalidate HTML (lets deploys roll out instantly) --------
location = / {
    add_header Cache-Control "no-cache";
}
location ~* \.html$ {
    add_header Cache-Control "no-cache";
}
```

After editing:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

Verify with:
```bash
curl -sI -H "Accept-Encoding: gzip" https://prizmbet.net/matches.json | grep -i "encoding\|cache"
# expected: Content-Encoding: gzip  /  Cache-Control: public, max-age=60, must-revalidate
```

Expected effect: `matches.json` 142 KB → ~25 KB, `smart-flow.css` 52 KB → ~10 KB,
`bet_slip.js` 43 KB → ~10 KB.

## 2. Parser env vars

Add to `/etc/systemd/system/prizmbet-backend.service` (under `[Service]` as
`Environment=KEY=value`) or to the `.env` file the service reads, whichever
your setup uses.

### Mandatory (nothing extra is parsed without these)

```ini
# Leonbets — now tunable without redeploy
LEONBETS_MAX_FETCH=400        # was hard-coded 200; bump to 400–600 for more coverage
LEONBETS_BATCH=20             # events fetched concurrently per round

# Enable the 1xBet parser (disabled by default)
ENABLE_XBET=true
```

### Paid API keys (optional but recommended — +300…500 matches/day)

```ini
ODDS_API_KEY=xxxxxxxxxxxx            # the-odds-api.com (free tier: ~500 req/mo)
ODDS_API_IO_KEY=xxxxxxxxxxxx         # odds-api.io (alternative provider)
API_FOOTBALL_KEY=xxxxxxxxxxxx        # api-sports.io (free tier: ~100 req/day)
PINNACLE_LOGIN=xxxxxxxxxxxx          # pinnacle.com API creds (requires active account)
PINNACLE_PASSWORD=xxxxxxxxxxxx
```

After setting:
```bash
sudo systemctl daemon-reload
sudo systemctl restart prizmbet-backend
journalctl -u prizmbet-backend -n 50 --no-pager | grep '\[generate_json\]'
# look for lines like "OddsAPI: 87 matches" instead of "OddsAPI: skipped"
```

## 3. Frontend — use per-sport segments

After this release `frontend/matches/<sport>.json` + `frontend/matches/index.json`
are produced alongside the existing `matches.json`. Pages that render one
sport only (`tennis.html`, `popular.html`, `marathon.html`) can load their
segment instead of the full feed:

| Page | Full feed | Segment |
| --- | --- | --- |
| `tennis.html` | `matches.json` (142 KB) | `matches/tennis.json` (~40 KB) |
| `popular.html` | `matches.json` | `matches/football.json` (~35 KB) |
| `index.html` | `matches.json` (keep — shows all sports) | — |

With gzip on top these segments become **6–10 KB**. Swap the fetch URL on
each page and the landing experience tightens by ~1 RTT on mobile.

## 4. Expected outcome

| Change | Before | After |
| --- | --- | --- |
| Home page critical payload | 275 KB | 54 KB |
| Sport-specific pages | 275 KB | ~15 KB |
| Active parsers | 1 of 5 | 5 of 5 |
| Matches per refresh | ~200 | 400–700 |
| First contentful paint (3G) | ~3.5 s | ~0.7 s |
