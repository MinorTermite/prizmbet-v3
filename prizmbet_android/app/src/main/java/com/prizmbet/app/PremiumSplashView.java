package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

import androidx.appcompat.content.res.AppCompatResources;

import java.util.Random;

public class PremiumSplashView extends View {

    private static final int BG = 0xFF06060E;
    private static final int ACCENT = 0xFF903EBC;
    private static final int ACCENT_LITE = 0xFFC684F1;
    private static final int PINK = 0xFFE24AC9;
    private static final int CYAN = 0xFF5BE7FF;
    private static final int WHITE = 0xFFF8F7FF;
    private static final int ANIM_MS = 3200;
    private static final float COMPLETE_AT = 0.90f;
    private static final int PARTICLE_COUNT = 32;

    private static final class Particle {
        float x;
        float y;
        float vx;
        float vy;
        float radius;
        float alpha;
        float phase;
        int color;
    }

    private final Random random = new Random(19);
    private final Particle[] particles = new Particle[PARTICLE_COUNT];
    private final Paint particlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint logoPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint logoGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint titlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint titleGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subtitlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint orbPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint posterOverlayPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint posterFramePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF ringRect = new RectF();
    private final RectF posterRect = new RectF();
    private final Matrix posterMatrix = new Matrix();

    private Bitmap logoBitmap;
    private Bitmap posterBitmap;
    private ValueAnimator animator;
    private Runnable onComplete;
    private float progress = 0f;
    private float tick = 0f;
    private float density = 1f;
    private boolean completeFired = false;

    public PremiumSplashView(Context context) {
        super(context);
        setup(context);
    }

    public PremiumSplashView(Context context, AttributeSet attrs) {
        super(context, attrs);
        setup(context);
    }

    public PremiumSplashView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        setup(context);
    }

    public void setOnCompleteListener(Runnable runnable) {
        onComplete = runnable;
    }

    private void setup(Context context) {
        setLayerType(LAYER_TYPE_SOFTWARE, null);
        density = context.getResources().getDisplayMetrics().density;

        Drawable drawable = AppCompatResources.getDrawable(context, R.drawable.ic_prizm_mark);
        if (drawable != null) {
            logoBitmap = drawableToBitmap(drawable, (int) (240f * density), (int) (208f * density));
        }
        posterBitmap = BitmapFactory.decodeResource(context.getResources(), R.drawable.splash_poster_v3);

        particlePaint.setStyle(Paint.Style.FILL);
        particlePaint.setMaskFilter(new BlurMaskFilter(10f * density, BlurMaskFilter.Blur.NORMAL));

        logoGlowPaint.setMaskFilter(new BlurMaskFilter(32f * density, BlurMaskFilter.Blur.NORMAL));
        logoGlowPaint.setColor(ACCENT);

        Typeface headlineTypeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD);

        titlePaint.setColor(WHITE);
        titlePaint.setTextAlign(Paint.Align.CENTER);
        titlePaint.setTypeface(headlineTypeface);
        titlePaint.setLetterSpacing(0.18f);

        titleGlowPaint.setColor(ACCENT_LITE);
        titleGlowPaint.setTextAlign(Paint.Align.CENTER);
        titleGlowPaint.setTypeface(headlineTypeface);
        titleGlowPaint.setLetterSpacing(0.18f);
        titleGlowPaint.setMaskFilter(new BlurMaskFilter(18f * density, BlurMaskFilter.Blur.NORMAL));

        subtitlePaint.setColor(CYAN);
        subtitlePaint.setTextAlign(Paint.Align.CENTER);
        subtitlePaint.setLetterSpacing(0.14f);

        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeWidth(2.2f * density);
        ringPaint.setColor(ACCENT_LITE);
        ringPaint.setMaskFilter(new BlurMaskFilter(8f * density, BlurMaskFilter.Blur.NORMAL));

        posterFramePaint.setStyle(Paint.Style.STROKE);
        posterFramePaint.setStrokeWidth(1.5f * density);
        posterFramePaint.setColor(Color.argb(120, 255, 178, 87));
        posterFramePaint.setMaskFilter(new BlurMaskFilter(6f * density, BlurMaskFilter.Blur.NORMAL));

        for (int i = 0; i < particles.length; i++) {
            Particle particle = new Particle();
            particle.x = random.nextFloat();
            particle.y = random.nextFloat();
            particle.vx = (random.nextFloat() - 0.5f) * 0.0009f;
            particle.vy = (random.nextFloat() - 0.5f) * 0.0009f;
            particle.radius = (1.2f + random.nextFloat() * 2.4f) * density;
            particle.alpha = 0.18f + random.nextFloat() * 0.34f;
            particle.phase = random.nextFloat() * 6.2831855f;
            particle.color = pickParticleColor(i);
            particles[i] = particle;
        }
    }

    private int pickParticleColor(int index) {
        switch (index % 4) {
            case 0:
                return ACCENT;
            case 1:
                return ACCENT_LITE;
            case 2:
                return PINK;
            default:
                return CYAN;
        }
    }

    private Bitmap drawableToBitmap(Drawable drawable, int width, int height) {
        Bitmap bitmap = Bitmap.createBitmap(Math.max(width, 1), Math.max(height, 1), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        drawable.setBounds(0, 0, canvas.getWidth(), canvas.getHeight());
        drawable.draw(canvas);
        return bitmap;
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIM_MS);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(valueAnimator -> {
            progress = (float) valueAnimator.getAnimatedValue();
            tick = progress * 10f;
            advanceParticles();
            if (!completeFired && progress >= COMPLETE_AT) {
                completeFired = true;
                if (onComplete != null) {
                    post(onComplete);
                }
            }
            invalidate();
        });
        animator.start();
    }

    @Override
    protected void onDetachedFromWindow() {
        if (animator != null) {
            animator.cancel();
        }
        super.onDetachedFromWindow();
    }

    private void advanceParticles() {
        for (Particle particle : particles) {
            particle.x += particle.vx;
            particle.y += particle.vy;
            if (particle.x < -0.05f) particle.x = 1.05f;
            if (particle.x > 1.05f) particle.x = -0.05f;
            if (particle.y < -0.05f) particle.y = 1.05f;
            if (particle.y > 1.05f) particle.y = -0.05f;
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int width = getWidth();
        int height = getHeight();
        float cx = width / 2f;
        float cy = height / 2f;

        canvas.drawColor(BG);
        drawPoster(canvas, width, height);
        drawAmbientOrbs(canvas, width, height);
        drawParticles(canvas, width, height);
        drawLogo(canvas, cx, cy);
        drawText(canvas, cx, cy);
        drawRevealRing(canvas, cx, cy);
    }

    private void drawPoster(Canvas canvas, int width, int height) {
        if (posterBitmap == null) {
            return;
        }

        float appear = phase(0.0f, 0.28f, progress);
        float zoom = 1.04f + (1f - decel(progress)) * 0.08f;
        float scale = Math.max(width / (float) posterBitmap.getWidth(), height / (float) posterBitmap.getHeight()) * zoom;
        float drawWidth = posterBitmap.getWidth() * scale;
        float drawHeight = posterBitmap.getHeight() * scale;
        float left = (width - drawWidth) / 2f;
        float top = (height - drawHeight) / 2f;

        posterMatrix.reset();
        posterMatrix.postScale(scale, scale);
        posterMatrix.postTranslate(left, top);

        logoPaint.setAlpha((int) (255f * Math.max(0.75f, appear)));
        canvas.drawBitmap(posterBitmap, posterMatrix, logoPaint);

        posterOverlayPaint.setShader(new LinearGradient(
                0f,
                0f,
                0f,
                height,
                new int[]{Color.argb(170, 4, 3, 8), Color.argb(70, 8, 6, 18), Color.argb(210, 5, 4, 8)},
                new float[]{0f, 0.45f, 1f},
                Shader.TileMode.CLAMP
        ));
        canvas.drawRect(0f, 0f, width, height, posterOverlayPaint);

        posterOverlayPaint.setShader(new RadialGradient(
                width * 0.5f,
                height * 0.42f,
                Math.max(width, height) * 0.62f,
                new int[]{Color.TRANSPARENT, Color.argb(150, 6, 6, 14)},
                new float[]{0.32f, 1f},
                Shader.TileMode.CLAMP
        ));
        canvas.drawRect(0f, 0f, width, height, posterOverlayPaint);

        float inset = 18f * density;
        posterRect.set(inset, inset, width - inset, height - inset);
        canvas.drawRoundRect(posterRect, 22f * density, 22f * density, posterFramePaint);
    }

    private void drawAmbientOrbs(Canvas canvas, int width, int height) {
        float alpha = Math.min(1f, progress / 0.45f);
        orbPaint.setShader(new RadialGradient(width * 0.24f, height * 0.18f, width * 0.42f,
                new int[]{Color.argb((int) (alpha * 52), 144, 62, 188), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, orbPaint);

        orbPaint.setShader(new RadialGradient(width * 0.78f, height * 0.76f, width * 0.35f,
                new int[]{Color.argb((int) (alpha * 44), 226, 74, 201), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, orbPaint);
    }

    private void drawParticles(Canvas canvas, int width, int height) {
        float layer = Math.min(1f, progress / 0.24f);
        for (Particle particle : particles) {
            float twinkle = (float) ((Math.sin(tick + particle.phase) + 1f) * 0.5f);
            particlePaint.setColor(particle.color);
            particlePaint.setAlpha((int) (255f * particle.alpha * layer * (0.35f + twinkle * 0.65f)));
            canvas.drawCircle(particle.x * width, particle.y * height, particle.radius, particlePaint);
        }
    }

    private void drawLogo(Canvas canvas, float cx, float cy) {
        if (logoBitmap == null) {
            return;
        }
        float phase = phase(0.18f, 0.48f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = decel(phase);
        float logoCy = cy - 178f * density;
        float logoWidth = (42f + 6f * eased) * density;
        float aspect = logoBitmap.getHeight() / (float) logoBitmap.getWidth();
        float logoHeight = logoWidth * aspect;
        Rect src = new Rect(0, 0, logoBitmap.getWidth(), logoBitmap.getHeight());

        float glowWidth = logoWidth * 1.6f;
        float glowHeight = logoHeight * 1.6f;
        float glowLeft = cx - glowWidth / 2f;
        float glowTop = logoCy - glowHeight / 2f;
        logoGlowPaint.setAlpha((int) (160f * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(glowLeft, glowTop, glowLeft + glowWidth, glowTop + glowHeight), logoGlowPaint);

        float left = cx - logoWidth / 2f;
        float top = logoCy - logoHeight / 2f;
        logoPaint.setAlpha((int) (255f * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(left, top, left + logoWidth, top + logoHeight), logoPaint);
    }

    private void drawText(Canvas canvas, float cx, float cy) {
        float phase = phase(0.34f, 0.68f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = decel(phase);
        float titleY = cy + 232f * density + (1f - eased) * 18f * density;
        float subtitleY = titleY + 20f * density;

        titlePaint.setTextSize(18f * density);
        titleGlowPaint.setTextSize(18f * density);
        titleGlowPaint.setAlpha((int) (150f * eased));
        titlePaint.setAlpha((int) (240f * eased));
        canvas.drawText("SMART FLOW READY", cx, titleY, titleGlowPaint);
        canvas.drawText("SMART FLOW READY", cx, titleY, titlePaint);

        subtitlePaint.setTextSize(8.8f * density);
        subtitlePaint.setAlpha((int) (150f * eased));
        canvas.drawText("PRIZM · INTENT · WALLET STATUS", cx, subtitleY, subtitlePaint);
    }

    private void drawRevealRing(Canvas canvas, float cx, float cy) {
        float phase = phase(0.50f, 0.82f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = easeInOut(phase);
        float centerY = cy - 178f * density;
        float radius = 32f * density;
        ringRect.set(cx - radius, centerY - radius, cx + radius, centerY + radius);
        ringPaint.setAlpha((int) (190f * (1f - phase * 0.6f)));
        canvas.drawArc(ringRect, -90f, 360f * eased, false, ringPaint);
    }

    private static float phase(float start, float end, float value) {
        if (value <= start) return 0f;
        if (value >= end) return 1f;
        return (value - start) / (end - start);
    }

    private static float decel(float value) {
        return 1f - (1f - value) * (1f - value);
    }

    private static float easeInOut(float value) {
        return (float) (Math.sin((value - 0.5f) * Math.PI) * 0.5f + 0.5f);
    }
}