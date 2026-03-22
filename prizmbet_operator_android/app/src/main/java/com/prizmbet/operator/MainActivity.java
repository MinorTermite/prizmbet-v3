package com.prizmbet.operator;

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
 * PrizmBet Operator Console — Android wrapper.
 *
 * Loads operator.html from APK assets with the same hybrid online/offline
 * approach as the main PrizmBet app. The operator connects to the API server
 * directly from the WebView.
 */
public class MainActivity extends AppCompatActivity {

    private static final String SITE_URL = "http://213.165.38.210/operator.html";

    private static final String[] ALLOWED_HOSTS = {
            "213.165.38.210",
            "minortermite.github.io",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
    };

    private WebView webView;
    private ProgressBar progressBar;
    private View errorView;
    private SwipeRefreshLayout swipeRefresh;
    private WebViewAssetLoader assetLoader;
    private boolean hasError = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        getWindow().setBackgroundDrawableResource(R.color.bg_primary);
        enterImmersiveMode();

        setContentView(R.layout.activity_main);

        progressBar = findViewById(R.id.progressBar);
        errorView = findViewById(R.id.errorView);
        webView = findViewById(R.id.webView);
        swipeRefresh = findViewById(R.id.swipeRefresh);

        Button retryBtn = findViewById(R.id.retryButton);
        retryBtn.setOnClickListener(v -> retry());

        configurePullToRefresh();
        buildAssetLoader();
        configureWebView();

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

    private void configurePullToRefresh() {
        swipeRefresh.setColorSchemeColors(0xFF6366F1, 0xFF818CF8);
        swipeRefresh.setProgressBackgroundColorSchemeColor(0xFF1A1A2E);

        swipeRefresh.setOnChildScrollUpCallback(
                (parent, child) -> webView.canScrollVertically(-1)
        );

        swipeRefresh.setOnRefreshListener(() -> {
            if (hasError) {
                retry();
                return;
            }
            webView.reload();
            swipeRefresh.postDelayed(() -> swipeRefresh.setRefreshing(false), 2500);
        });
    }

    /**
     * Serves static files from APK assets/operator/.
     * API calls (to the operator's backend) go through network normally.
     */
    private void buildAssetLoader() {
        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain("minortermite.github.io")
                .addPathHandler("/prizmbet-v3/", path -> {
                    // Always fetch JSON data from network
                    if (path.endsWith(".json")) {
                        return null;
                    }
                    try {
                        InputStream is = getAssets().open("operator/" + path);
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
                        return null;
                    }
                })
                .build();
    }

    private void configureWebView() {
        webView.setBackgroundColor(0xFF06060E);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        // Allow mixed content so operator can connect to local HTTP API
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        String ua = s.getUserAgentString();
        ua = ua.replace("; wv)", ")");
        s.setUserAgentString(ua + " PrizmBetOperator/1.0");

        webView.setWebViewClient(new WebViewClient() {

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String host = request.getUrl().getHost();
                if (host != null && isAllowedHost(host)) return false;
                // Allow API connections to any host (operator needs to connect to backend)
                String scheme = request.getUrl().getScheme();
                if ("http".equals(scheme) || "https".equals(scheme)) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl()));
                } catch (Exception ignored) {
                }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                hasError = false;
                progressBar.setVisibility(View.VISIBLE);

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
                swipeRefresh.setRefreshing(false);
                if (!hasError) {
                    showWebView();
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

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
