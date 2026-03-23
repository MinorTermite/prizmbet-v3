package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

import androidx.appcompat.content.res.AppCompatResources;

import java.util.Random;

/**
 * Cryptographic-style animated splash screen.
 *
 * Features:
 * - Falling hex-code rain (matrix-style)
 * - Blockchain node network with connecting lines
 * - Animated hash visualization ring
 * - Pulsing PRIZM logo with glow
 * - Digital particle field
 */
public class PremiumSplashView extends View {

    private static final int BG = 0xFF06060E;
    private static final int ACCENT = 0xFF903EBC;
    private static final int ACCENT_LITE = 0xFFC684F1;
    private static final int CYAN = 0xFF00E5FF;
    private static final int GREEN = 0xFF39FF14;
    private static final int WHITE = 0xFFF0F0FF;
    private static final int ANIM_MS = 3600;
    private static final float COMPLETE_AT = 0.88f;

    // Hex rain
    private static final int HEX_COLUMNS = 18;
    private static final String HEX_CHARS = "0123456789ABCDEF";

    // Blockchain nodes
    private static final int NODE_COUNT = 12;

    // Particles
    private static final int PARTICLE_COUNT = 40;

    // ── Data classes ──────────────────────────────
    private static final class HexDrop {
        float x, y, speed, alpha;
        String ch;
        float size;
    }

    private static final class Node {
        float x, y, radius, pulsePhase;
        int color;
        boolean active;
    }

    private static final class Particle {
        float x, y, vx, vy, radius, alpha, phase;
        int color;
    }

    // ── Fields ────────────────────────────────────
    private final Random rng = new Random(42);
    private final HexDrop[] hexDrops = new HexDrop[HEX_COLUMNS * 6];
    private final Node[] nodes = new Node[NODE_COUNT];
    private final Particle[] particles = new Particle[PARTICLE_COUNT];

    private final Paint bgPaint = new Paint();
    private final Paint hexPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint nodePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint nodeGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint linePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint particlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint logoPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint logoGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint titlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint titleGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subtitlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint hashPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint orbPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint outroPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint gridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF ringRect = new RectF();
    private final Path hexPath = new Path();

    private Bitmap logoBitmap;
    private ValueAnimator animator;
    private Runnable onComplete;
    private float progress = 0f;
    private float tick = 0f;
    private float density = 1f;
    private boolean completeFired = false;
    private String currentHash = "";

    public PremiumSplashView(Context context) { super(context); setup(context); }
    public PremiumSplashView(Context context, AttributeSet attrs) { super(context, attrs); setup(context); }
    public PremiumSplashView(Context context, AttributeSet attrs, int defStyleAttr) { super(context, attrs, defStyleAttr); setup(context); }

    public void setOnCompleteListener(Runnable runnable) { onComplete = runnable; }

    private void setup(Context context) {
        setLayerType(LAYER_TYPE_SOFTWARE, null);
        density = context.getResources().getDisplayMetrics().density;

        // Load logo
        Drawable drawable = AppCompatResources.getDrawable(context, R.drawable.ic_prizm_mark);
        if (drawable != null) {
            logoBitmap = drawableToBitmap(drawable, (int) (200f * density), (int) (174f * density));
        }

        // Hex rain paint
        Typeface mono = Typeface.create("monospace", Typeface.NORMAL);
        hexPaint.setTypeface(mono);
        hexPaint.setTextAlign(Paint.Align.CENTER);

        // Node paints
        nodePaint.setStyle(Paint.Style.FILL);
        nodeGlowPaint.setStyle(Paint.Style.FILL);
        nodeGlowPaint.setMaskFilter(new BlurMaskFilter(16f * density, BlurMaskFilter.Blur.NORMAL));

        linePaint.setStyle(Paint.Style.STROKE);
        linePaint.setStrokeWidth(0.8f * density);

        // Particle paint
        particlePaint.setStyle(Paint.Style.FILL);
        particlePaint.setMaskFilter(new BlurMaskFilter(6f * density, BlurMaskFilter.Blur.NORMAL));

        // Ring paint
        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeWidth(2.5f * density);
        ringPaint.setStrokeCap(Paint.Cap.ROUND);

        ringGlowPaint.setStyle(Paint.Style.STROKE);
        ringGlowPaint.setStrokeWidth(6f * density);
        ringGlowPaint.setMaskFilter(new BlurMaskFilter(12f * density, BlurMaskFilter.Blur.NORMAL));

        // Logo glow
        logoGlowPaint.setMaskFilter(new BlurMaskFilter(28f * density, BlurMaskFilter.Blur.NORMAL));
        logoGlowPaint.setColor(ACCENT);

        // Title paints
        Typeface bold = Typeface.create(Typeface.DEFAULT, Typeface.BOLD);
        titlePaint.setColor(WHITE);
        titlePaint.setTextAlign(Paint.Align.CENTER);
        titlePaint.setTypeface(bold);
        titlePaint.setLetterSpacing(0.22f);

        titleGlowPaint.setColor(CYAN);
        titleGlowPaint.setTextAlign(Paint.Align.CENTER);
        titleGlowPaint.setTypeface(bold);
        titleGlowPaint.setLetterSpacing(0.22f);
        titleGlowPaint.setMaskFilter(new BlurMaskFilter(14f * density, BlurMaskFilter.Blur.NORMAL));

        subtitlePaint.setColor(ACCENT_LITE);
        subtitlePaint.setTextAlign(Paint.Align.CENTER);
        subtitlePaint.setTypeface(mono);
        subtitlePaint.setLetterSpacing(0.08f);

        hashPaint.setTypeface(mono);
        hashPaint.setTextAlign(Paint.Align.CENTER);

        // Grid
        gridPaint.setStyle(Paint.Style.STROKE);
        gridPaint.setStrokeWidth(0.5f * density);

        // Init hex drops
        for (int i = 0; i < hexDrops.length; i++) {
            HexDrop d = new HexDrop();
            d.x = (i % HEX_COLUMNS) / (float) HEX_COLUMNS;
            d.y = -rng.nextFloat() * 2f;
            d.speed = 0.003f + rng.nextFloat() * 0.006f;
            d.alpha = 0.08f + rng.nextFloat() * 0.22f;
            d.ch = String.valueOf(HEX_CHARS.charAt(rng.nextInt(16)));
            d.size = (9f + rng.nextFloat() * 5f) * density;
            hexDrops[i] = d;
        }

        // Init nodes
        for (int i = 0; i < nodes.length; i++) {
            Node n = new Node();
            // Distribute nodes around center in an arc pattern
            double angle = (i / (double) NODE_COUNT) * Math.PI * 2.0 + rng.nextDouble() * 0.5;
            double dist = 0.22 + rng.nextDouble() * 0.22;
            n.x = 0.5f + (float) (Math.cos(angle) * dist);
            n.y = 0.42f + (float) (Math.sin(angle) * dist * 0.7);
            n.radius = (2.5f + rng.nextFloat() * 2.5f) * density;
            n.pulsePhase = rng.nextFloat() * 6.28f;
            n.color = (i % 3 == 0) ? CYAN : (i % 3 == 1) ? ACCENT_LITE : GREEN;
            n.active = false;
            nodes[i] = n;
        }

        // Init particles
        for (int i = 0; i < particles.length; i++) {
            Particle p = new Particle();
            p.x = rng.nextFloat();
            p.y = rng.nextFloat();
            p.vx = (rng.nextFloat() - 0.5f) * 0.0007f;
            p.vy = (rng.nextFloat() - 0.5f) * 0.0007f;
            p.radius = (0.8f + rng.nextFloat() * 2f) * density;
            p.alpha = 0.12f + rng.nextFloat() * 0.28f;
            p.phase = rng.nextFloat() * 6.28f;
            p.color = pickColor(i);
            particles[i] = p;
        }
    }

    private int pickColor(int i) {
        switch (i % 4) {
            case 0: return ACCENT;
            case 1: return CYAN;
            case 2: return ACCENT_LITE;
            default: return GREEN;
        }
    }

    private Bitmap drawableToBitmap(Drawable drawable, int w, int h) {
        Bitmap bmp = Bitmap.createBitmap(Math.max(w, 1), Math.max(h, 1), Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        drawable.setBounds(0, 0, c.getWidth(), c.getHeight());
        drawable.draw(c);
        return bmp;
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIM_MS);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(va -> {
            progress = (float) va.getAnimatedValue();
            tick = progress * 12f;
            advanceHexRain();
            advanceParticles();
            updateNodes();
            updateHash();
            if (!completeFired && progress >= COMPLETE_AT) {
                completeFired = true;
                if (onComplete != null) post(onComplete);
            }
            invalidate();
        });
        animator.start();
    }

    @Override
    protected void onDetachedFromWindow() {
        if (animator != null) animator.cancel();
        super.onDetachedFromWindow();
    }

    private void advanceHexRain() {
        for (HexDrop d : hexDrops) {
            d.y += d.speed;
            if (d.y > 1.2f) {
                d.y = -rng.nextFloat() * 0.3f;
                d.ch = String.valueOf(HEX_CHARS.charAt(rng.nextInt(16)));
                d.alpha = 0.08f + rng.nextFloat() * 0.22f;
            }
        }
    }

    private void advanceParticles() {
        for (Particle p : particles) {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < -0.05f) p.x = 1.05f;
            if (p.x > 1.05f) p.x = -0.05f;
            if (p.y < -0.05f) p.y = 1.05f;
            if (p.y > 1.05f) p.y = -0.05f;
        }
    }

    private void updateNodes() {
        float nodeProgress = phase(0.15f, 0.65f, progress);
        for (int i = 0; i < nodes.length; i++) {
            nodes[i].active = nodeProgress > (i / (float) NODE_COUNT);
        }
    }

    private void updateHash() {
        int len = (int) (progress * 64);
        StringBuilder sb = new StringBuilder();
        Random hashRng = new Random((long) (progress * 1000));
        for (int i = 0; i < Math.min(len, 16); i++) {
            sb.append(HEX_CHARS.charAt(hashRng.nextInt(16)));
        }
        currentHash = sb.toString();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth();
        int h = getHeight();
        float cx = w / 2f;
        float cy = h * 0.40f;

        canvas.drawColor(BG);
        drawGrid(canvas, w, h);
        drawAmbientOrbs(canvas, w, h);
        drawHexRain(canvas, w, h);
        drawNodeNetwork(canvas, w, h);
        drawParticles(canvas, w, h);
        drawHashRing(canvas, cx, cy);
        drawLogo(canvas, cx, cy);
        drawTitle(canvas, cx, cy);
        drawHashVisualization(canvas, cx, h);
        drawOutro(canvas, w, h);
    }

    private void drawGrid(Canvas canvas, int w, int h) {
        float appear = Math.min(1f, progress / 0.3f) * 0.06f;
        gridPaint.setColor(Color.argb((int) (255 * appear), 0, 229, 255));
        float spacing = 48f * density;
        for (float x = 0; x < w; x += spacing) {
            canvas.drawLine(x, 0, x, h, gridPaint);
        }
        for (float y = 0; y < h; y += spacing) {
            canvas.drawLine(0, y, w, y, gridPaint);
        }
    }

    private void drawAmbientOrbs(Canvas canvas, int w, int h) {
        float alpha = Math.min(1f, progress / 0.4f);

        orbPaint.setShader(new RadialGradient(w * 0.2f, h * 0.15f, w * 0.5f,
                new int[]{Color.argb((int) (alpha * 40), 0, 229, 255), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, w, h, orbPaint);

        orbPaint.setShader(new RadialGradient(w * 0.8f, h * 0.7f, w * 0.4f,
                new int[]{Color.argb((int) (alpha * 35), 144, 62, 188), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, w, h, orbPaint);

        orbPaint.setShader(new RadialGradient(w * 0.5f, h * 0.4f, w * 0.35f,
                new int[]{Color.argb((int) (alpha * 25), 57, 255, 20), Color.TRANSPARENT},
                new float[]{0f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, w, h, orbPaint);
    }

    private void drawHexRain(Canvas canvas, int w, int h) {
        float appear = Math.min(1f, progress / 0.2f);
        for (HexDrop d : hexDrops) {
            if (d.y < 0 || d.y > 1f) continue;
            float fadeEdge = Math.min(1f, Math.min(d.y * 5f, (1f - d.y) * 5f));
            hexPaint.setColor(GREEN);
            hexPaint.setAlpha((int) (255 * d.alpha * appear * fadeEdge));
            hexPaint.setTextSize(d.size);
            float px = d.x * w + w / (float) HEX_COLUMNS / 2f;
            float py = d.y * h;
            canvas.drawText(d.ch, px, py, hexPaint);
        }
    }

    private void drawNodeNetwork(Canvas canvas, int w, int h) {
        float appear = phase(0.10f, 0.50f, progress);
        if (appear <= 0) return;

        // Draw connections first
        for (int i = 0; i < nodes.length; i++) {
            if (!nodes[i].active) continue;
            for (int j = i + 1; j < nodes.length; j++) {
                if (!nodes[j].active) continue;
                float dx = nodes[i].x - nodes[j].x;
                float dy = nodes[i].y - nodes[j].y;
                float dist = (float) Math.sqrt(dx * dx + dy * dy);
                if (dist < 0.35f) {
                    float lineAlpha = (1f - dist / 0.35f) * appear * 0.3f;
                    linePaint.setColor(CYAN);
                    linePaint.setAlpha((int) (255 * lineAlpha));
                    canvas.drawLine(
                            nodes[i].x * w, nodes[i].y * h,
                            nodes[j].x * w, nodes[j].y * h,
                            linePaint
                    );
                }
            }
        }

        // Draw nodes
        for (Node n : nodes) {
            if (!n.active) continue;
            float pulse = (float) ((Math.sin(tick * 2 + n.pulsePhase) + 1f) * 0.5f);
            float r = n.radius * (0.8f + pulse * 0.4f);

            // Glow
            nodeGlowPaint.setColor(n.color);
            nodeGlowPaint.setAlpha((int) (80 * appear * pulse));
            canvas.drawCircle(n.x * w, n.y * h, r * 3f, nodeGlowPaint);

            // Core
            nodePaint.setColor(n.color);
            nodePaint.setAlpha((int) (220 * appear));
            canvas.drawCircle(n.x * w, n.y * h, r, nodePaint);

            // Bright center
            nodePaint.setColor(WHITE);
            nodePaint.setAlpha((int) (180 * appear * pulse));
            canvas.drawCircle(n.x * w, n.y * h, r * 0.4f, nodePaint);
        }
    }

    private void drawParticles(Canvas canvas, int w, int h) {
        float layer = Math.min(1f, progress / 0.2f);
        for (Particle p : particles) {
            float twinkle = (float) ((Math.sin(tick + p.phase) + 1f) * 0.5f);
            particlePaint.setColor(p.color);
            particlePaint.setAlpha((int) (255f * p.alpha * layer * (0.3f + twinkle * 0.7f)));
            canvas.drawCircle(p.x * w, p.y * h, p.radius, particlePaint);
        }
    }

    private void drawHashRing(Canvas canvas, float cx, float cy) {
        float appear = phase(0.20f, 0.55f, progress);
        if (appear <= 0) return;

        float radius = 72f * density;
        ringRect.set(cx - radius, cy - radius, cx + radius, cy + radius);

        // Outer rotating segmented ring
        float rotation = tick * 25f;
        int segments = 8;
        float segAngle = 360f / segments;
        float gap = 8f;

        for (int i = 0; i < segments; i++) {
            float startAngle = rotation + i * segAngle + gap / 2f;
            float sweepAngle = segAngle - gap;
            float segAlpha = appear * (0.4f + 0.6f * (float) Math.abs(Math.sin(tick + i * 0.8f)));

            // Glow
            ringGlowPaint.setColor(i % 2 == 0 ? CYAN : ACCENT_LITE);
            ringGlowPaint.setAlpha((int) (100 * segAlpha));
            canvas.drawArc(ringRect, startAngle, sweepAngle, false, ringGlowPaint);

            // Core
            ringPaint.setColor(i % 2 == 0 ? CYAN : ACCENT_LITE);
            ringPaint.setAlpha((int) (220 * segAlpha));
            canvas.drawArc(ringRect, startAngle, sweepAngle, false, ringPaint);
        }

        // Inner ring (counter-rotate)
        float innerRadius = 58f * density;
        RectF innerRect = new RectF(cx - innerRadius, cy - innerRadius, cx + innerRadius, cy + innerRadius);
        for (int i = 0; i < 12; i++) {
            float startAngle = -rotation * 0.7f + i * 30f + 4f;
            float sweepAngle = 22f;
            ringPaint.setColor(GREEN);
            ringPaint.setAlpha((int) (80 * appear * (float) Math.abs(Math.sin(tick * 1.5 + i))));
            ringPaint.setStrokeWidth(1.2f * density);
            canvas.drawArc(innerRect, startAngle, sweepAngle, false, ringPaint);
        }
        ringPaint.setStrokeWidth(2.5f * density);
    }

    private void drawLogo(Canvas canvas, float cx, float cy) {
        if (logoBitmap == null) return;
        float appear = phase(0.25f, 0.55f, progress);
        if (appear <= 0) return;

        float eased = decel(appear);
        float scale = 0.85f + eased * 0.15f;
        float logoW = 42f * density * scale;
        float aspect = logoBitmap.getHeight() / (float) logoBitmap.getWidth();
        float logoH = logoW * aspect;
        android.graphics.Rect src = new android.graphics.Rect(0, 0, logoBitmap.getWidth(), logoBitmap.getHeight());

        // Glow
        float glowW = logoW * 2f;
        float glowH = logoH * 2f;
        logoGlowPaint.setAlpha((int) (140 * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(cx - glowW / 2, cy - glowH / 2, cx + glowW / 2, cy + glowH / 2), logoGlowPaint);

        // Logo
        logoPaint.setAlpha((int) (255 * eased));
        canvas.drawBitmap(logoBitmap, src, new RectF(cx - logoW / 2, cy - logoH / 2, cx + logoW / 2, cy + logoH / 2), logoPaint);
    }

    private void drawTitle(Canvas canvas, float cx, float cy) {
        float appear = phase(0.40f, 0.70f, progress);
        if (appear <= 0) return;

        float eased = decel(appear);
        float titleY = cy + 92f * density + (1f - eased) * 14f * density;

        titlePaint.setTextSize(16f * density);
        titleGlowPaint.setTextSize(16f * density);

        // Glow
        titleGlowPaint.setAlpha((int) (120 * eased));
        canvas.drawText("PRIZMBET", cx, titleY, titleGlowPaint);

        // Text
        titlePaint.setAlpha((int) (240 * eased));
        canvas.drawText("PRIZMBET", cx, titleY, titlePaint);

        // Subtitle
        subtitlePaint.setTextSize(8.5f * density);
        subtitlePaint.setAlpha((int) (140 * eased));
        float subY = titleY + 18f * density;
        canvas.drawText("CRYPTO · PREDICTION · ANALYTICS", cx, subY, subtitlePaint);
    }

    private void drawHashVisualization(Canvas canvas, float cx, float h) {
        float appear = phase(0.50f, 0.80f, progress);
        if (appear <= 0 || currentHash.isEmpty()) return;

        float y = h * 0.72f;
        hashPaint.setTextSize(10f * density);
        hashPaint.setColor(GREEN);
        hashPaint.setAlpha((int) (100 * appear));

        // Show rolling hash
        String display = "0x" + currentHash;
        canvas.drawText(display, cx, y, hashPaint);

        // Small label above
        hashPaint.setTextSize(7f * density);
        hashPaint.setColor(CYAN);
        hashPaint.setAlpha((int) (60 * appear));
        canvas.drawText("SHA-256 VERIFY", cx, y - 16f * density, hashPaint);
    }

    private void drawOutro(Canvas canvas, int w, int h) {
        float outro = phase(0.82f, 1f, progress);
        if (outro <= 0) return;
        int alpha = (int) (120 * easeInOut(outro));
        outroPaint.setShader(new LinearGradient(0, 0, 0, h,
                new int[]{Color.argb(alpha, 4, 4, 10), Color.argb((int) (alpha * 0.3f), 4, 4, 10), Color.argb(alpha, 4, 4, 10)},
                new float[]{0f, 0.45f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, w, h, outroPaint);
    }

    // ── Easing helpers ──────────────────────────
    private float phase(float start, float end, float v) {
        if (v <= start) return 0f;
        if (v >= end) return 1f;
        return (v - start) / (end - start);
    }

    private float decel(float v) {
        float t = Math.max(0f, Math.min(1f, v));
        return 1f - (1f - t) * (1f - t);
    }

    private float easeInOut(float v) {
        float t = Math.max(0f, Math.min(1f, v));
        return (float) (t < 0.5f ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
    }
}
