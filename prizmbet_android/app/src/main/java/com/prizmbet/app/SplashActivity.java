package com.prizmbet.app;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.splashscreen.SplashScreen;

import java.util.concurrent.atomic.AtomicBoolean;

public class SplashActivity extends AppCompatActivity {

    private final AtomicBoolean launched = new AtomicBoolean(false);
    private static final int FALLBACK_MS = 5000;

    private PremiumSplashView premiumSplash;

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

        premiumSplash = findViewById(R.id.premiumSplash);

        // Auto-launch when animation completes — no entry panel
        premiumSplash.setOnCompleteListener(this::launchMain);
        premiumSplash.postDelayed(this::launchMain, FALLBACK_MS);
    }

    private void launchMain() {
        if (!launched.compareAndSet(false, true)) return;

        Intent intent = new Intent(this, MainActivity.class);
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
