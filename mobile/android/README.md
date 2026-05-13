# PRIZMBET Android

Android WebView wrapper for [PRIZMBET](https://minortermite.github.io/prizmbet-v2/).

## Current mode: WebView (TWA-ready)

The app loads the PWA hosted on GitHub Pages inside a fullscreen WebView.
Architecture prepared for future migration to Trusted Web Activity (TWA).

## Features

- Fullscreen immersive mode (no status bar, no navigation bar)
- Loading progress bar (accent color #6366f1)
- Error screen with retry button (no internet)
- Domain allowlist (only project domains load inside the app)
- External links open in browser
- Back button navigates WebView history
- Portrait lock
- Hardware accelerated WebView
- Dark theme matching the site (#06060e)
- App icons generated from prizmbet-logo.webp (all mipmap densities)

## Open in Android Studio

1. Open Android Studio
2. File > Open > select the `prizmbet_android/` folder
3. Wait for Gradle sync to complete
4. Run on device/emulator

## Build debug APK

```bash
cd prizmbet_android
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## Build release APK/AAB

```bash
# First, create a signing key (one time):
keytool -genkey -v -keystore prizmbet-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias prizmbet

# Then build:
cd prizmbet_android
./gradlew assembleRelease
# or for Google Play:
./gradlew bundleRelease
```

## Configuration

| What | Where |
|------|-------|
| Site URL | `MainActivity.java` > `SITE_URL` |
| Allowed domains | `MainActivity.java` > `ALLOWED_HOSTS` |
| Package name | `app/build.gradle` > `applicationId` |
| App name | `res/values/strings.xml` > `app_name` |
| Icons | `res/mipmap-*/ic_launcher.png` |
| Theme colors | `res/values/styles.xml` |
| Version | `app/build.gradle` > `versionCode` / `versionName` |

## Project structure

```
prizmbet_android/
  build.gradle              — root Gradle config (AGP 8.7.3)
  settings.gradle           — project name
  gradle.properties         — AndroidX, JVM args
  app/
    build.gradle            — app config (SDK 35, Java 11)
    proguard-rules.pro      — ProGuard keep rules
    src/main/
      AndroidManifest.xml   — permissions, activity, icon
      java/.../MainActivity.java — WebView + error handling + back nav
      res/
        layout/activity_main.xml — WebView + ProgressBar + error screen
        drawable/progress_bar.xml — accent progress drawable
        drawable/btn_retry.xml    — retry button shape
        values/strings.xml        — app name, error messages
        values/styles.xml         — dark theme
        values/colors.xml         — color constants
        mipmap-mdpi/              — 48x48 launcher icon
        mipmap-hdpi/              — 72x72 launcher icon
        mipmap-xhdpi/             — 96x96 launcher icon
        mipmap-xxhdpi/            — 144x144 launcher icon
        mipmap-xxxhdpi/           — 192x192 launcher icon
```

## Limitations

- WebView, not TWA: localStorage is isolated from Chrome browser
- Service Worker support depends on Android WebView version (Chrome 70+)
- Push notifications not supported in WebView (need TWA or FCM bridge)
- No offline-first: if SW doesn't cache properly, error screen shows

## TWA migration path

See `ANDROID_APP_PLAN.md` for the full migration plan.
