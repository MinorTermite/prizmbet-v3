package com.prizmbet.app;

import android.content.Intent;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.MimeTypeMap;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import androidx.webkit.WebViewAssetLoader;

import java.io.IOException;
import java.io.InputStream;

/**
 * PrizmBet Android wrapper.
 *
 * Features implemented:
 *  - SwipeRefreshLayout: свайп вниз → обновляет данные матчей
 *  - WebViewAssetLoader: статика из APK assets/, JSON с сети
 *  - App Shortcuts: Football / Esports / Refresh
 *  - UA fix: убирает "wv" маркер (сайт видит обычный Chrome)
 *  - Offline error screen с кнопкой Повторить
 *  - Фон WebView = #06060e (единый с SplashActivity — нет цветовой вспышки)
 */
public class MainActivity extends AppCompatActivity {

    private static final String SITE_URL     = "https://minortermite.github.io/prizmbet-v2/";
    public  static final String EXTRA_SHORTCUT = "shortcut_action";

    private static final String[] ALLOWED_HOSTS = {
            "minortermite.github.io",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
    };

    // ── Views ──────────────────────────────────────────────────────────────────
    private WebView             webView;
    private ProgressBar         progressBar;
    private View                errorView;
    private SwipeRefreshLayout  swipeRefresh;

    // ── State ──────────────────────────────────────────────────────────────────
    private WebViewAssetLoader assetLoader;
    /** Pending shortcut action applied via JS once page is ready. */
    private String pendingShortcut = null;
    private boolean hasError = false;

    // ── Lifecycle ──────────────────────────────────────────────────────────────

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        // Фон окна = #06060e, совпадает с SplashActivity → нет цветовой вспышки
        getWindow().setBackgroundDrawableResource(R.color.bg_primary);
        enterImmersiveMode();

        setContentView(R.layout.activity_main);

        // Refs
        progressBar  = findViewById(R.id.progressBar);
        errorView    = findViewById(R.id.errorView);
        webView      = findViewById(R.id.webView);
        swipeRefresh = findViewById(R.id.swipeRefresh);

        Button retryBtn = findViewById(R.id.retryButton);
        retryBtn.setOnClickListener(v -> retry());

        // ③ Pull-to-refresh
        configurePullToRefresh();

        // ④ WebViewAssetLoader
        buildAssetLoader();
        configureWebView();

        // App Shortcut intent
        pendingShortcut = getIntent().getStringExtra(EXTRA_SHORTCUT);

        webView.clearCache(true);
        webView.loadUrl(SITE_URL);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (errorView.getVisibility() == View.VISIBLE) {
                    finish();
                } else if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });
    }

    /** Called when app already runs and a shortcut is tapped. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String action = intent.getStringExtra(EXTRA_SHORTCUT);
        if (action != null) {
            pendingShortcut = action;
            applyShortcut(action);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        enterImmersiveMode();
    }

    @Override
    protected void onPause() {
        webView.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.destroy();
        }
        super.onDestroy();
    }

    // ── Pull-to-refresh ────────────────────────────────────────────────────────

    private void configurePullToRefresh() {
        // Цветовая схема в стиле бренда
        swipeRefresh.setColorSchemeColors(0xFF6366F1, 0xFF818CF8);
        swipeRefresh.setProgressBackgroundColorSchemeColor(0xFF1A1A2E);

        // Только при прокрутке до самого верха WebView срабатывает свайп
        swipeRefresh.setOnChildScrollUpCallback(
                (parent, child) -> webView.canScrollVertically(-1)
        );

        swipeRefresh.setOnRefreshListener(() -> {
            if (hasError) {
                // Страница с ошибкой — полная перезагрузка; spinner скроется в onPageFinished
                retry();
                return;
            }
            // Обновляем только данные матчей через JS, страницу не перезагружаем
            webView.evaluateJavascript(
                    "(function(){ if(window.refreshData) window.refreshData(); })();",
                    null
            );
            // Скрываем индикатор через ~2.5 сек (время сетевого запроса)
            swipeRefresh.postDelayed(() -> swipeRefresh.setRefreshing(false), 2500);
        });
    }

    // ── Asset Loader ───────────────────────────────────────────────────────────

    /**
     * Статические файлы (HTML/JS/CSS/картинки) отдаются из APK assets/prizmbet-v2/.
     * matches.json и matches-today.json — всегда с сети (живые данные).
     */
    private void buildAssetLoader() {
        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain("minortermite.github.io")
                .addPathHandler("/prizmbet-v2/", path -> {
                    if (path.endsWith("matches.json") || path.endsWith("matches-today.json")) {
                        return null; // → network
                    }
                    try {
                        InputStream is = getAssets().open("prizmbet-v2/" + path);
                        String ext = path.contains(".")
                                ? path.substring(path.lastIndexOf('.') + 1).toLowerCase()
                                : "";
                        String mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
                        if (mime == null) mime = "application/octet-stream";
                        String charset = (mime.contains("javascript") || mime.contains("css")
                                || mime.contains("html") || mime.contains("json"))
                                ? "UTF-8" : null;
                        return new WebResourceResponse(mime, charset, is);
                    } catch (IOException e) {
                        return null; // не нашли в assets — идёт в сеть
                    }
                })
                .build();
    }

    // ── WebView Configuration ──────────────────────────────────────────────────

    private void configureWebView() {
        // Фон совпадает с SplashActivity (#06060e) — нет белой/чёрной вспышки при загрузке
        webView.setBackgroundColor(0xFF06060E);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT); // стандартный кэш для стабильности
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);

        // Убираем "wv" маркер — сайт видит обычный Chrome
        String ua = s.getUserAgentString();
        ua = ua.replace("; wv)", ")");
        s.setUserAgentString(ua);

        webView.setWebViewClient(new WebViewClient() {

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String host = request.getUrl().getHost();
                if (host != null && isAllowedHost(host)) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl()));
                } catch (Exception ignored) { }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                hasError = false;
                progressBar.setVisibility(View.VISIBLE);

                // Заглушка Notification API чтобы JS не падал
                view.evaluateJavascript(
                        "(function(){" +
                        "  if(typeof Notification==='undefined'){" +
                        "    window.Notification={permission:'denied'," +
                        "      requestPermission:function(){return Promise.resolve('denied');}," +
                        "      show:function(){}};" +
                        "  }" +
                        "})();", null);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);  // сброс pull-to-refresh спиннера

                if (!hasError) {
                    showWebView();
                }
                // Применяем shortcut после загрузки DOM
                if (pendingShortcut != null) {
                    applyShortcut(pendingShortcut);
                    pendingShortcut = null;
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    hasError = true;
                    swipeRefresh.setRefreshing(false);
                    showError("Ошибка загрузки. Проверьте соединение.");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress >= 100) progressBar.setVisibility(View.GONE);
            }
        });
    }

    // ── App Shortcuts ──────────────────────────────────────────────────────────

    private void applyShortcut(String action) {
        String js;
        switch (action) {
            case "football":
                js = "(function(){ var t=document.querySelector('.tab[data-sport=\"football\"]'); if(t) t.click(); })();";
                break;
            case "esports":
                js = "(function(){ var t=document.querySelector('.tab[data-sport=\"esports\"]'); if(t) t.click(); })();";
                break;
            case "refresh":
                js = "(function(){ if(window.refreshData) window.refreshData(); })();";
                break;
            default:
                return;
        }
        webView.evaluateJavascript(js, null);
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private boolean isAllowedHost(String host) {
        for (String a : ALLOWED_HOSTS) {
            if (host.equals(a) || host.endsWith("." + a)) return true;
        }
        return false;
    }

    private void showError(String message) {
        webView.setVisibility(View.GONE);
        swipeRefresh.setVisibility(View.GONE);
        errorView.setVisibility(View.VISIBLE);
        progressBar.setVisibility(View.GONE);
        TextView tv = findViewById(R.id.errorMessage);
        if (tv != null) tv.setText(message);
    }

    private void showWebView() {
        errorView.setVisibility(View.GONE);
        swipeRefresh.setVisibility(View.VISIBLE);
        webView.setVisibility(View.VISIBLE);
    }

    private void retry() {
        swipeRefresh.setVisibility(View.VISIBLE);
        showWebView();
        webView.loadUrl(SITE_URL);
    }

    private boolean isOnline() {
        ConnectivityManager cm = getSystemService(ConnectivityManager.class);
        if (cm == null) return false;
        Network net = cm.getActiveNetwork();
        if (net == null) return false;
        NetworkCapabilities caps = cm.getNetworkCapabilities(net);
        return caps != null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
