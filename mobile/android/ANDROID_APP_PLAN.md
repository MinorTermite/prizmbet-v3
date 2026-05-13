# PRIZMBET Android App Plan

## 1. PWA Audit (2026-03-07)

| Check | Status | Notes |
|-------|--------|-------|
| manifest.json | FIXED | Was: single webp icon, `purpose: "any maskable"` (invalid). Now: separate PNG 192+512, separate `any` and `maskable` entries |
| Service Worker | OK | sw.js v24, SWR strategy, proper caching |
| display: standalone | OK | Already set |
| theme_color | OK | #06060e |
| background_color | OK | #06060e |
| start_url | OK | "." |
| HTTPS | OK | GitHub Pages |
| Mobile responsive | OK | viewport meta, mobile-first CSS |
| Icons 192x192 PNG | ADDED | icon-192x192.png generated from prizmbet-logo.webp |
| Icons 512x512 PNG | ADDED | icon-512x512.png generated from prizmbet-logo.webp |
| apple-touch-icon | ADDED | link tag in index.html |
| favicon | ADDED | link tag in index.html |
| assetlinks.json | NOT DONE | Requires signing key SHA-256 fingerprint |

## 2. Strategy: WebView now, TWA later

**Why WebView first:**
- TWA requires `assetlinks.json` with SHA-256 fingerprint of the signing key
- Signing key is created during the release build process (external step)
- GitHub Pages needs `.well-known/assetlinks.json` deployed
- WebView gives a working APK immediately for testing

**Why TWA is better (for later):**
- Full Chrome engine (not WebView subset)
- Proper Service Worker support
- Push notifications work natively
- localStorage shared with Chrome
- Google Play verification badge (verified domain)
- Better performance

## 3. Files created

| File | Purpose |
|------|---------|
| `prizmbet_android/gradle.properties` | AndroidX config |
| `prizmbet_android/app/src/main/res/drawable/progress_bar.xml` | Accent progress bar |
| `prizmbet_android/app/src/main/res/drawable/btn_retry.xml` | Retry button shape |
| `prizmbet_android/app/src/main/res/values/colors.xml` | Color constants |
| `prizmbet_android/app/src/main/res/mipmap-*/ic_launcher.png` | App icons (5 densities) |
| `prizmbet_android/app/src/main/res/mipmap-*/ic_launcher_round.png` | Round icons (5 densities) |
| `frontend/icon-192x192.png` | PWA icon 192x192 |
| `frontend/icon-512x512.png` | PWA icon 512x512 |
| `prizmbet_android/README.md` | This documentation |
| `prizmbet_android/ANDROID_APP_PLAN.md` | This plan |

## 4. Files modified

| File | Change | Risk |
|------|--------|------|
| `prizmbet_android/app/.../MainActivity.java` | Full rewrite: WebChromeClient, error screen, retry, domain allowlist, back nav, immersive | None (isolated Android code) |
| `prizmbet_android/app/.../AndroidManifest.xml` | Added VIBRATE/NETWORK_STATE permissions, icon refs, usesCleartextTraffic=false | None |
| `prizmbet_android/app/build.gradle` | SDK 35, Java 11, updated deps, enabled ProGuard for release | None |
| `prizmbet_android/build.gradle` | AGP 8.7.3 | None |
| `prizmbet_android/app/.../activity_main.xml` | FrameLayout with WebView + ProgressBar + error view | None |
| `prizmbet_android/app/.../styles.xml` | Dark theme matching site | None |
| `prizmbet_android/app/.../strings.xml` | App name + error strings | None |
| `frontend/manifest.json` | Fixed icons (PNG, separate any/maskable), added orientation | Safe: PWA metadata only |
| `frontend/index.html` | Added apple-touch-icon, favicon link tags | Safe: head metadata only |
| `frontend/sw.js` | v23 -> v24, added icon PNGs to cache list | Safe: cache list update |

## 5. TWA migration steps (future)

1. **Create signing key:**
   ```bash
   keytool -genkey -v -keystore prizmbet-release.jks \
     -keyalg RSA -keysize 2048 -validity 10000 -alias prizmbet
   ```

2. **Get SHA-256 fingerprint:**
   ```bash
   keytool -list -v -keystore prizmbet-release.jks -alias prizmbet
   ```

3. **Create assetlinks.json:**
   ```json
   [{
     "relation": ["delegate_permission/common.handle_all_urls"],
     "target": {
       "namespace": "android_app",
       "package_name": "com.prizmbet.app",
       "sha256_cert_fingerprints": ["YOUR_SHA256_HERE"]
     }
   }]
   ```

4. **Deploy to GitHub Pages:**
   Place at `frontend/.well-known/assetlinks.json`
   (GitHub Pages serves `.well-known` directory)

5. **Option A: Bubblewrap (recommended)**
   ```bash
   npm install -g @nickersoft/bubblewrap-cli
   bubblewrap init --manifest https://minortermite.github.io/prizmbet-v2/manifest.json
   bubblewrap build
   ```

6. **Option B: Manual TWA**
   Add `com.google.androidbrowserhelper:androidbrowserhelper:2.5.0` dependency
   and configure TWA in AndroidManifest.xml.

## 6. Google Play release checklist

- [ ] App icon: adaptive icon with foreground/background layers
- [ ] Signing key: create and store securely (never commit to git)
- [ ] Version: bump versionCode for each release
- [ ] Privacy policy URL (required by Google Play)
- [ ] Build AAB: `./gradlew bundleRelease`
- [ ] Screenshots: phone + tablet (min 2 each)
- [ ] Feature graphic: 1024x500 PNG
- [ ] Short description (80 chars max)
- [ ] Full description (4000 chars max)
- [ ] Content rating questionnaire
- [ ] Target audience declaration
