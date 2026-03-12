package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
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
    private static final int PARTICLE_COUNT = 44;

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
    private final RectF ringRect = new RectF();

    private Bitmap logoBitmap;
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

        for (int i = 0; i < particles.length; i++) {
            Particle particle = new Particle();
            particle.x = random.nextFloat();
            particle.y = random.nextFloat();
            particle.vx = (random.nextFloat() - 0.5f) * 0.0009f;
            particle.vy = (random.nextFloat() - 0.5f) * 0.0009f;
            particle.radius = (1.2f + random.nextFloat() * 2.8f) * density;
            particle.alpha = 0.25f + random.nextFloat() * 0.45f;
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
            tick = progress * 12f;
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
        drawAmbientOrbs(canvas, width, height);
        drawParticles(canvas, width, height);
        drawLogo(canvas, cx, cy);
        drawText(canvas, cx, cy);
        drawRevealRing(canvas, cx, cy);
    }

    private void drawAmbientOrbs(Canvas canvas, int width, int height) {
        float alpha = Math.min(1f, progress / 0.45f);
        orbPaint.setShader(new RadialGradient(width * 0.28f, height * 0.25f, width * 0.42f,
                new int[]{Color.argb((int) (alpha * 70), 144, 62, 188), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, orbPaint);

        orbPaint.setShader(new RadialGradient(width * 0.72f, height * 0.2f, width * 0.36f,
                new int[]{Color.argb((int) (alpha * 46), 226, 74, 201), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, orbPaint);

        orbPaint.setShader(new LinearGradient(0f, 0f, width, height,
                new int[]{Color.argb((int) (alpha * 24), 91, 231, 255), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, orbPaint);
    }

    private void drawParticles(Canvas canvas, int width, int height) {
        float layer = Math.min(1f, progress / 0.25f);
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
        float phase = phase(0.08f, 0.42f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = decel(phase);
        float logoCy = cy - 54f * density;
        float logoWidth = (132f + 16f * eased) * density;
        float aspect = logoBitmap.getHeight() / (float) logoBitmap.getWidth();
        float logoHeight = logoWidth * aspect;
        Rect src = new Rect(0, 0, logoBitmap.getWidth(), logoBitmap.getHeight());

        float glowWidth = logoWidth * 1.3f;
        float glowHeight = logoHeight * 1.3f;
        float glowLeft = cx - glowWidth / 2f;
        float glowTop = logoCy - glowHeight / 2f;
        logoGlowPaint.setAlpha((int) (180f * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(glowLeft, glowTop, glowLeft + glowWidth, glowTop + glowHeight), logoGlowPaint);

        float left = cx - logoWidth / 2f;
        float top = logoCy - logoHeight / 2f;
        logoPaint.setAlpha((int) (255f * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(left, top, left + logoWidth, top + logoHeight), logoPaint);
    }

    private void drawText(Canvas canvas, float cx, float cy) {
        float phase = phase(0.32f, 0.64f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = decel(phase);
        float baseline = cy + 54f * density + (1f - eased) * 18f * density;

        titlePaint.setTextSize(21f * density);
        titleGlowPaint.setTextSize(21f * density);
        titleGlowPaint.setAlpha((int) (170f * eased));
        titlePaint.setAlpha((int) (255f * eased));
        canvas.drawText("PRIZMBET", cx, baseline, titleGlowPaint);
        canvas.drawText("PRIZMBET", cx, baseline, titlePaint);

        subtitlePaint.setTextSize(9.5f * density);
        subtitlePaint.setAlpha((int) (160f * eased));
        canvas.drawText("PRIZM · WALLET · STATUS", cx, baseline + 18f * density, subtitlePaint);
    }

    private void drawRevealRing(Canvas canvas, float cx, float cy) {
        float phase = phase(0.44f, 0.78f, progress);
        if (phase <= 0f) {
            return;
        }

        float eased = easeInOut(phase);
        float centerY = cy - 54f * density;
        float radius = 82f * density;
        ringRect.set(cx - radius, centerY - radius, cx + radius, centerY + radius);
        ringPaint.setAlpha((int) (210f * (1f - phase * 0.6f)));
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
