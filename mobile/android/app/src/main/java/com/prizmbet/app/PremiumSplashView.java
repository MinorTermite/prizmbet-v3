package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.*;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

import java.util.Random;

/**
 * Премиум-заставка в крипто-стиле — всё рисуется на Canvas, без GIF.
 *
 * Слои (снизу вверх):
 *  1. Тёмный фон #06060e
 *  2. Плавающие частицы (бренд-палитра)
 *  3. Логотип из ресурса (ic_splash_logo) + неоновый ореол
 *  4. Название "PRIZMBET" с glow, анимация снизу вверх
 *  5. Reveal-кольцо: дуга 0→360° вокруг логотипа
 *
 * Таймлайн (0..1 = 3200 мс):
 *   0.00 – 0.30  частицы проявляются
 *   0.10 – 0.45  логотип scale 0.75→1.0, fade-in
 *   0.38 – 0.62  текст slide-up + fade-in
 *   0.45 – 0.78  reveal-кольцо описывает 360°
 *   0.90         onComplete → переход в MainActivity
 */
public class PremiumSplashView extends View {

    // ── Цвета ─────────────────────────────────────────────────────────────────
    private static final int BG          = 0xFF06060E;
    private static final int ACCENT      = 0xFF6366F1;
    private static final int ACCENT_LITE = 0xFF818CF8;
    private static final int PURPLE      = 0xFFA855F7;
    private static final int WHITE       = 0xFFFFFFFF;

    // ── Таймлайн ──────────────────────────────────────────────────────────────
    private static final float TL_PART_END   = 0.30f;
    private static final float TL_LOGO_S     = 0.10f;
    private static final float TL_LOGO_E     = 0.45f;
    private static final float TL_TEXT_S     = 0.38f;
    private static final float TL_TEXT_E     = 0.62f;
    private static final float TL_RING_S     = 0.45f;
    private static final float TL_RING_E     = 0.78f;
    private static final float TL_DONE       = 0.90f;
    private static final int   ANIM_MS       = 3200;

    // ── Частицы ───────────────────────────────────────────────────────────────
    private static final int   PART_N        = 42;
    private static final int[] PART_COLORS   = { ACCENT, ACCENT_LITE, PURPLE, 0xFFC4B5FD };
    private static final float[] PART_SZ_DP  = { 1.2f, 2.0f, 3.2f };
    private static final float[] PART_BL_MUL = { 2.0f, 2.8f, 3.5f };

    private static final class Pt {
        float x, y, vx, vy, baseA, phase, freq;
        int   si, color;
    }

    private final Pt[]    pts       = new Pt[PART_N];
    private final Paint[] partPnts  = new Paint[PART_SZ_DP.length];

    // ── Логотип ───────────────────────────────────────────────────────────────
    private Bitmap logoBmp;
    private final Paint logoPaint     = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint logoGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);

    // ── Текст ─────────────────────────────────────────────────────────────────
    private final Paint txtPaint     = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint txtGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subPaint     = new Paint(Paint.ANTI_ALIAS_FLAG);

    // ── Кольцо ────────────────────────────────────────────────────────────────
    private final Paint  ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF  ringRect  = new RectF();

    // ── Состояние ─────────────────────────────────────────────────────────────
    private float     t         = 0f;
    private float     tick      = 0f;
    private boolean   doneFired = false;
    private Runnable  onComplete;
    private ValueAnimator animator;
    private float     density;

    // ── Конструкторы ──────────────────────────────────────────────────────────
    public PremiumSplashView(Context c)                       { super(c);       setup(c); }
    public PremiumSplashView(Context c, AttributeSet a)       { super(c, a);    setup(c); }
    public PremiumSplashView(Context c, AttributeSet a, int d){ super(c, a, d); setup(c); }

    /** Вызывается когда анимация подходит к концу — запускает MainActivity. */
    public void setOnCompleteListener(Runnable r) { onComplete = r; }

    // ── Инициализация ─────────────────────────────────────────────────────────

    private void setup(Context ctx) {
        setLayerType(LAYER_TYPE_SOFTWARE, null);   // нужно для BlurMaskFilter
        density = ctx.getResources().getDisplayMetrics().density;

        // Загружаем логотип
        try {
            logoBmp = BitmapFactory.decodeResource(ctx.getResources(), R.drawable.ic_splash_logo);
        } catch (Exception ignored) {}

        // ── Частицы ──
        Random rnd = new Random(19);
        for (int i = 0; i < PART_N; i++) {
            Pt p = new Pt();
            p.x     = rnd.nextFloat();
            p.y     = rnd.nextFloat();
            float spd = 0.00020f + rnd.nextFloat() * 0.00045f;
            double ang = rnd.nextDouble() * Math.PI * 2;
            p.vx    = (float)(Math.cos(ang) * spd);
            p.vy    = (float)(Math.sin(ang) * spd);
            p.si    = rnd.nextInt(PART_SZ_DP.length);
            p.color = PART_COLORS[rnd.nextInt(PART_COLORS.length)];
            p.baseA = 0.25f + rnd.nextFloat() * 0.50f;
            p.phase = rnd.nextFloat() * (float)(Math.PI * 2);
            p.freq  = 0.4f + rnd.nextFloat() * 1.2f;
            pts[i]  = p;
        }
        for (int i = 0; i < PART_SZ_DP.length; i++) {
            partPnts[i] = new Paint(Paint.ANTI_ALIAS_FLAG);
            partPnts[i].setStyle(Paint.Style.FILL);
            partPnts[i].setMaskFilter(new BlurMaskFilter(
                    PART_SZ_DP[i] * density * PART_BL_MUL[i], BlurMaskFilter.Blur.NORMAL));
        }

        // ── Логотип: glow слой (фиолетовый, размытый) ──
        logoGlowPaint.setColorFilter(new PorterDuffColorFilter(0xAA6366F1, PorterDuff.Mode.SRC_ATOP));
        logoGlowPaint.setMaskFilter(new BlurMaskFilter(36f * density, BlurMaskFilter.Blur.NORMAL));

        // ── Текст ──
        Typeface bold = Typeface.create(Typeface.DEFAULT, Typeface.BOLD);

        txtPaint.setColor(WHITE);
        txtPaint.setTextAlign(Paint.Align.CENTER);
        txtPaint.setTypeface(bold);
        txtPaint.setLetterSpacing(0.22f);

        txtGlowPaint.setColor(ACCENT);
        txtGlowPaint.setTextAlign(Paint.Align.CENTER);
        txtGlowPaint.setTypeface(bold);
        txtGlowPaint.setLetterSpacing(0.22f);
        txtGlowPaint.setMaskFilter(new BlurMaskFilter(16f * density, BlurMaskFilter.Blur.NORMAL));

        subPaint.setColor(ACCENT_LITE);
        subPaint.setTextAlign(Paint.Align.CENTER);
        subPaint.setLetterSpacing(0.18f);

        // ── Кольцо ──
        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setColor(ACCENT);
        ringPaint.setStrokeWidth(1.8f * density);
        ringPaint.setMaskFilter(new BlurMaskFilter(7f * density, BlurMaskFilter.Blur.NORMAL));
    }

    // ── Жизненный цикл ────────────────────────────────────────────────────────

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIM_MS);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a -> {
            t    = (float) a.getAnimatedValue();
            tick = t * (ANIM_MS / 1000f);
            for (Pt p : pts) {
                p.x += p.vx;  if (p.x < -0.06f) p.x += 1.12f; else if (p.x > 1.06f) p.x -= 1.12f;
                p.y += p.vy;  if (p.y < -0.06f) p.y += 1.12f; else if (p.y > 1.06f) p.y -= 1.12f;
            }
            if (!doneFired && t >= TL_DONE) {
                doneFired = true;
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

    // ── Отрисовка ─────────────────────────────────────────────────────────────

    @Override
    protected void onDraw(Canvas canvas) {
        final int   w  = getWidth(),  h  = getHeight();
        final float cx = w / 2f,      cy = h / 2f;

        // 1. Фон
        canvas.drawColor(BG);

        // 2. Частицы
        float partA = Math.min(1f, t / TL_PART_END);
        drawParticles(canvas, w, h, partA);

        // 3. Логотип + glow
        float logoP = phase(TL_LOGO_S, TL_LOGO_E, t);
        if (logoP > 0f && logoBmp != null) drawLogo(canvas, cx, cy, logoP);

        // 4. Текст
        float textP = phase(TL_TEXT_S, TL_TEXT_E, t);
        if (textP > 0f) drawText(canvas, cx, cy, textP);

        // 5. Reveal-кольцо
        float ringP = phase(TL_RING_S, TL_RING_E, t);
        if (ringP > 0f && ringP <= 1f) drawRing(canvas, cx, cy, ringP);
    }

    // ── Слои ──────────────────────────────────────────────────────────────────

    private void drawParticles(Canvas canvas, int w, int h, float alpha) {
        for (Pt p : pts) {
            float twinkle = (float)(Math.sin(tick * p.freq + p.phase) * 0.5 + 0.5);
            float a       = alpha * p.baseA * (0.35f + twinkle * 0.65f);
            Paint pnt     = partPnts[p.si];
            pnt.setColor(p.color);
            pnt.setAlpha((int)(a * 255));
            canvas.drawCircle(p.x * w, p.y * h, PART_SZ_DP[p.si] * density, pnt);
        }
    }

    private void drawLogo(Canvas canvas, float cx, float cy, float p) {
        float e    = decel(p);                  // замедленный прогресс
        float sz   = (120f + 10f * e) * density; // 120dp → 130dp по мере появления
        float logoCy = cy - 50f * density;      // центр логотипа чуть выше экрана
        float l    = cx - sz / 2f;
        float top  = logoCy - sz / 2f;

        Rect src = new Rect(0, 0, logoBmp.getWidth(), logoBmp.getHeight());

        // glow-слой (чуть крупнее, размытый фиолетовый)
        float gs = sz * 1.35f;
        float gl = cx - gs / 2f, gt = logoCy - gs / 2f;
        logoGlowPaint.setAlpha((int)(e * 170));
        canvas.drawBitmap(logoBmp, src, new RectF(gl, gt, gl + gs, gt + gs), logoGlowPaint);

        // сам логотип
        logoPaint.setAlpha((int)(e * 255));
        canvas.drawBitmap(logoBmp, src, new RectF(l, top, l + sz, top + sz), logoPaint);
    }

    private void drawText(Canvas canvas, float cx, float cy, float p) {
        float e       = decel(p);
        float logoCy  = cy - 50f * density;
        float baseY   = logoCy + 90f * density;    // ниже логотипа
        float slideY  = baseY + (1f - e) * 18f * density; // едет снизу вверх

        float tsz = 21f * density;
        txtPaint.setTextSize(tsz);
        txtGlowPaint.setTextSize(tsz);

        // glow
        txtGlowPaint.setAlpha((int)(e * 170));
        canvas.drawText("PRIZMBET", cx, slideY, txtGlowPaint);

        // основной текст
        txtPaint.setAlpha((int)(e * 255));
        canvas.drawText("PRIZMBET", cx, slideY, txtPaint);

        // подпись
        float ssz = 9.5f * density;
        subPaint.setTextSize(ssz);
        subPaint.setAlpha((int)(e * 120));
        canvas.drawText("CRYPTO  ·  SPORTS  ·  BETTING", cx, slideY + 18f * density, subPaint);
    }

    private void drawRing(Canvas canvas, float cx, float cy, float p) {
        float e       = easeInOut(p);
        float logoCy  = cy - 50f * density;
        float r       = 78f * density;
        ringRect.set(cx - r, logoCy - r, cx + r, logoCy + r);

        // Кольцо описывает 360° и постепенно тускнеет
        float fadeOut = 1f - p * 0.65f;
        ringPaint.setAlpha((int)(fadeOut * 210));
        canvas.drawArc(ringRect, -90f, 360f * e, false, ringPaint);
    }

    // ── Easing ────────────────────────────────────────────────────────────────

    /** Нормализует прогресс sub-фазы [start..end] в [0..1]. */
    private static float phase(float start, float end, float t) {
        if (t <= start) return 0f;
        if (t >= end)   return 1f;
        return (t - start) / (end - start);
    }

    /** Decelerate: быстро начинает, замедляется. */
    private static float decel(float x) { return 1f - (1f - x) * (1f - x); }

    /** Ease-in-out (sin). */
    private static float easeInOut(float x) {
        return (float)(Math.sin((x - 0.5f) * Math.PI) * 0.5 + 0.5);
    }
}
