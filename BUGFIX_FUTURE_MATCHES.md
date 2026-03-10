# Bug Fix: Future Matches Showing as Finished

## Date: March 5, 2026

---

## 🐛 Problem

**Issue:** Match scheduled for March 8, 2026 was showing status "Завершен" (Finished) with a score.

**Root Cause:** `score_enricher.py` was adding scores from API-Football without checking if the match date was in the future. If two teams played recently and were scheduled to play again, the old score was incorrectly applied to the future match.

**Example:**
```
Club Deportivo Irapuato — Alebrijes de Oaxaca
Scheduled: March 8, 2026 01:00
Status: Завершен (WRONG!)
```

---

## ✅ Solution

### 1. Backend Fix (`score_enricher.py`)

Added date validation before adding scores:

```python
# OPTIMIZATION: Skip future matches — they can't have scores yet
if dt:
    now = datetime.now(timezone.utc)
    if dt > now:
        continue  # Match is in the future, skip
```

### 2. Frontend Fix (`filters.js`)

Enhanced finished match detection with date validation:

```javascript
function isPast(m) {
    // If has score, check date (to avoid confusing with future matches)
    if (m.score) {
        const matchDate = parseMatchDateTime(m);
        // If match already happened (more than 15 min ago) — consider finished
        return (now - matchDate) > (15 * 60 * 1000);
    }
    
    // If match started more than 2 hours ago — consider finished
    const start = parseMatchDateTime(m);
    return (now - start) > (2 * 60 * 60 * 1000);
}
```

---

## 📊 Impact

| Before | After |
|--------|-------|
| Future matches could show "Завершен" | Future matches never show "Завершен" |
| Old scores applied to new matches | Scores only applied to past matches |
| Confusing UX | Clear distinction between finished and upcoming |

---

## 🧪 Testing

1. **Check future matches:**
   - Find match scheduled for tomorrow or later
   - Verify NO score is shown
   - Verify status is NOT "Завершен"

2. **Check past matches:**
   - Find match from yesterday or earlier
   - Verify score IS shown if available
   - Verify match is at the bottom of the list

3. **Check live matches:**
   - Find match happening now
   - Verify score updates correctly
   - Verify "LIVE" badge is shown

---

## 📝 Files Changed

- `backend/score_enricher.py` — Skip future matches when adding scores
- `frontend/js/modules/filters.js` — Better finished match detection
- `frontend/matches.json` — Refreshed with correct data (2517 matches)

---

## 🔗 Related Commits

- `7e44754` — fix: prevent future matches from being marked as finished
- `0d5bc84` — perf: major loading speed optimizations

---

_Last updated: March 5, 2026_
