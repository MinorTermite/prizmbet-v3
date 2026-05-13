# PrizmBet ProGuard rules
# Keep WebView JS interface (if added in the future)
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep Activity class names for manifest references
-keep public class * extends android.app.Activity
