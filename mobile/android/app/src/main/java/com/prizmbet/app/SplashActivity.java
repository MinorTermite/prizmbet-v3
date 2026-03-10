package com.prizmbet.app;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.splashscreen.SplashScreen;

import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Премиум-заставка в крипто-стиле.
 *
 * Всё рисуется на Canvas в PremiumSplashView — никакого GIF, никаких рамок.
 * Визуальный поток:
 *   OS splash (Theme.Prizmbet.Starting, мгновенно)
 *   → PremiumSplashView: частицы + логотип с glow + текст + reveal-кольцо (3.2 с)
 *   → fade → MainActivity (#06060e + WebView)
 */
public class SplashActivity extends AppCompatActivity {

    private final AtomicBoolean launched = new AtomicBoolean(false);

    /** Максимальное ожидание (на случай сбоя анимации). */
    private static final int FALLBACK_MS = 5000;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        SplashScreen.installSplashScreen(this);
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        enterImmersiveMode();
        getWindow().setBackgroundDrawableResource(R.color.bg_primary);

        setContentView(R.layout.activity_splash);

        PremiumSplashView splash = findViewById(R.id.premiumSplash);

        // Переход в MainActivity по окончании анимации (~2.9 с)
        splash.setOnCompleteListener(this::launchMain);

        // Запасной таймер — на случай если анимация не сработала
        splash.postDelayed(this::launchMain, FALLBACK_MS);
    }

    private void launchMain() {
        if (!launched.compareAndSet(false, true)) return;

        Intent intent = new Intent(this, MainActivity.class);

        // Прокидываем shortcut_action если запуск был через App Shortcut
        String shortcut = getIntent().getStringExtra(MainActivity.EXTRA_SHORTCUT);
        if (shortcut != null) intent.putExtra(MainActivity.EXTRA_SHORTCUT, shortcut);

        startActivity(intent);
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
        finish();
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
