package com.prizmbet.app;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.splashscreen.SplashScreen;

import java.util.concurrent.atomic.AtomicBoolean;

public class SplashActivity extends AppCompatActivity {

    private final AtomicBoolean launched = new AtomicBoolean(false);
    private static final int FALLBACK_MS = 5000;

    private PremiumSplashView premiumSplash;
    private View entryScrim;
    private View entryPanel;
    private boolean entryShown = false;

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
        entryScrim = findViewById(R.id.entryScrim);
        entryPanel = findViewById(R.id.entryPanel);
        Button enterButton = findViewById(R.id.enterButton);

        if (enterButton != null) {
            enterButton.setOnClickListener(v -> launchMain());
        }
        if (entryPanel != null) {
            entryPanel.setOnClickListener(v -> { /* block click-through */ });
        }

        premiumSplash.setOnCompleteListener(this::showEntryScreen);
        premiumSplash.postDelayed(this::showEntryScreen, FALLBACK_MS);
    }

    private void showEntryScreen() {
        if (entryShown) return;
        entryShown = true;

        if (entryScrim != null) {
            entryScrim.setVisibility(View.VISIBLE);
            entryScrim.setAlpha(0f);
            entryScrim.animate()
                    .alpha(1f)
                    .setDuration(420)
                    .start();
        }

        if (premiumSplash != null) {
            premiumSplash.animate()
                    .alpha(0.82f)
                    .scaleX(1.035f)
                    .scaleY(1.035f)
                    .setDuration(520)
                    .start();
        }

        if (entryPanel != null) {
            entryPanel.setVisibility(View.VISIBLE);
            entryPanel.setAlpha(0f);
            entryPanel.setTranslationY(42f);
            entryPanel.animate()
                    .alpha(1f)
                    .translationY(0f)
                    .setDuration(460)
                    .setStartDelay(120)
                    .start();
        }
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
