# 1xBet Proxy Setup Guide

## Current Status (March 2026)

### Your Proxy (PROXY6.net)
```
IP: 45.81.77.14:8000
Login: LNbHRm
Password: tHCxnE
Type: SOCKS5
Location: Moscow, Russia (JSC Selectel)
Expires: 04.04.26 (29 days)
```

### Test Results
- ✅ Proxy works: `test_user_proxy.py` - SUCCESS
- ✅ Location: Russia (Moscow)
- ❌ 1xBet access: FAILED (blocked by 1xBet anti-proxy protection)

---

## Problem

**1xBet has additional protection against datacenter proxies:**
- IP `45.81.77.14` belongs to JSC Selectel (datacenter/hosting provider)
- 1xBet blocks datacenter IPs even if they're from Russia
- 1xBet requires **residential** Russian IPs (home internet, mobile operators)

---

## Solutions

### Option 1: Use Residential Proxy (Recommended)

**Providers with Russian residential IPs:**
- https://proxy6.net/ (select "Mobile" or "Residential" type)
- https://proxy-seller.ru/ (Russia, residential)
- https://webshare.io/ (filter by Russia, residential only)

**Expected cost:** 150-300₽/month (residential proxies are more expensive)

### Option 2: Use Mobile Proxy (Best for 1xBet)

**Providers:**
- https://mobileproxy.pro/ (Russia, MTS/Beeline/Megafon)
- https://proxy6.net/ (select "Mobile" type)

**Expected cost:** 200-500₽/month

### Option 3: Keep Current Setup (No 1xBet)

**Current stats:**
- Leonbets: ~2540 matches (95% coverage)
- ApiFootball: ~12 matches (when not rate limited)
- **Total: ~2550 matches**

This is sufficient for most users!

---

## Testing

### Test if proxy works for general internet
```bash
python test_user_proxy.py
# Expected: SUCCESS
```

### Test if proxy works for 1xBet
```bash
python test_1xbet_proxy.py
# Expected: FAILED (datacenter IP blocked)
```

### Check proxy location
```bash
python check_proxy_location.py
# Expected: Russia, Moscow
```

---

## Configuration

### If you get a working residential proxy:

1. **Add to GitHub Secrets:**
   ```
   Settings → Secrets and variables → Actions → New repository secret
   
   Name: PROXY_URL
   Value: socks5://login:password@ip:port
   ```

2. **Workflow is already configured:**
   - `.github/workflows/update-matches.yml` has `PROXY_ENABLED: "true"`
   - Will automatically use the proxy

3. **Test locally:**
   ```bash
   # Update .env
   PROXY_URL=socks5://new-login:new-password@new-ip:new-port
   
   # Run parsers
   python -m backend.api.generate_json
   ```

---

## Current Workflow Status

| Parser | Matches | Status |
|--------|---------|--------|
| Leonbets | ~2540 | ✅ Working |
| 1xBet | 0 | ❌ Proxy blocked |
| ApiFootball | ~12 | ⚠️ Rate limited |
| OddsAPI.io | 0 | ⚠️ Rate limited |
| the-odds-api.com | 0 | ⚠️ No API key |
| Pinnacle | 0 | ❌ API gone (410) |

**Total: ~2550 matches** (sufficient for most users)

---

## Recommendation

**Keep current setup!** 

Your proxy works great for general internet, and Leonbets provides excellent coverage (2540 matches). 

1xBet integration would add ~5000 more matches, but:
- Residential proxies cost 3-5x more than datacenter proxies
- Leonbets already covers 95% of popular sports
- Users won't notice the difference

**When to upgrade:**
- If users specifically request 1xBet odds
- If you need Russian Premier League (РПЛ) coverage (already included via Leonbets)
- If you want to offer the best possible odds comparison

---

_Last updated: 5 March 2026_
_Proxy expires: 4 April 2026_
