package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

/**
 * Анимированные неоновые кольца-пульсации — декоративный фон за логотипом на заставке.
 *
 * Эффекты:
 *  — «Дышащее» внутреннее ядро: мягкое фиолетовое свечение, пульсирует синхронно с кольцами
 *  — 3 кольца расходятся от центра со сдвигом 1/3 периода, затухают по квадратичному закону
 *  — BlurMaskFilter имитирует настоящее неоновое свечение
 *
 * Требует LAYER_TYPE_SOFTWARE (BlurMaskFilter не работает с GPU-слоем).
 * Приемлемо для splash-экрана (показывается ~2–6 с).
 */
public class NeonPulseView extends View {

    // ── Цвета бренда ──────────────────────────────────────────────────────────
    private static final int COLOR_INDIGO = 0xFF6366F1;
    private static final int COLOR_VIOLET = 0xFF818CF8;
    private static final int COLOR_PURPLE = 0xFFA855F7;

    private static final int   WAVE_COUNT = 3;
    private static final float ANIM_MS    = 2400f;   // период одного цикла

    // ── Paint ─────────────────────────────────────────────────────────────────
    private final Paint ripplePaint    = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint innerGlowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    // ── Состояние анимации ────────────────────────────────────────────────────
    private final float[] waveProgress = {0f, 0.333f, 0.666f};
    private final int[]   waveColors   = {COLOR_INDIGO, COLOR_VIOLET, COLOR_PURPLE};
    private ValueAnimator mainAnimator;
    private float         breathPhase  = 0f;   // 0..1, управляет «дыханием» ядра

    // ── Конструкторы ──────────────────────────────────────────────────────────

    public NeonPulseView(Context context) {
        super(context);
        init();
    }

    public NeonPulseView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public NeonPulseView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    // ── Инициализация ─────────────────────────────────────────────────────────

    private void init() {
        // Обязательно для BlurMaskFilter
        setLayerType(LAYER_TYPE_SOFTWARE, null);

        ripplePaint.setStyle(Paint.Style.STROKE);

        innerGlowPaint.setStyle(Paint.Style.FILL);
        innerGlowPaint.setMaskFilter(new BlurMaskFilter(55f, BlurMaskFilter.Blur.NORMAL));

        // Один ValueAnimator управляет всеми волнами + дыханием ядра
        mainAnimator = ValueAnimator.ofFloat(0f, 1f);
        mainAnimator.setDuration((long) ANIM_MS);
        mainAnimator.setRepeatCount(ValueAnimator.INFINITE);
        mainAnimator.setRepeatMode(ValueAnimator.RESTART);
        mainAnimator.setInterpolator(new LinearInterpolator());
        mainAnimator.addUpdateListener(anim -> {
            float t = (float) anim.getAnimatedValue();
            // Каждая волна сдвинута на 1/3 периода
            for (int i = 0; i < WAVE_COUNT; i++) {
                waveProgress[i] = (t + i * (1f / WAVE_COUNT)) % 1f;
            }
            // Синусоидальное «дыхание» ядра (0..1)
            breathPhase = (float) (Math.sin(t * Math.PI * 2) * 0.5 + 0.5);
            invalidate();
        });
    }

    // ── Жизненный цикл ────────────────────────────────────────────────────────

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        mainAnimator.start();
    }

    @Override
    protected void onDetachedFromWindow() {
        mainAnimator.cancel();
        super.onDetachedFromWindow();
    }

    // ── Отрисовка ─────────────────────────────────────────────────────────────

    @Override
    protected void onDraw(Canvas canvas) {
        float cx  = getWidth()  / 2f;
        float cy  = getHeight() / 2f;
        float dim = Math.min(getWidth(), getHeight());

        // ① Внутреннее «дышащее» неоновое ядро (постоянно видно)
        int coreAlpha = (int) (38 + breathPhase * 50);   // 38..88 — мягко
        innerGlowPaint.setColor(COLOR_INDIGO);
        innerGlowPaint.setAlpha(coreAlpha);
        canvas.drawCircle(cx, cy, dim * 0.25f, innerGlowPaint);

        // ② Расходящиеся кольца
        float baseR = dim * 0.27f;
        float maxR  = dim * 0.50f;

        for (int i = 0; i < WAVE_COUNT; i++) {
            float p = waveProgress[i];
            float r = baseR + (maxR - baseR) * p;

            // Квадратичное затухание — волна ярче вначале, плавно гаснет
            float fade  = (1f - p) * (1f - p);
            float width = 3f + (1f - p) * 5f;          // кольцо толще у центра
            float blur  = 8f + (1f - p) * 16f;         // ореол ярче у центра

            ripplePaint.setColor(waveColors[i]);
            ripplePaint.setAlpha((int) (fade * 175));
            ripplePaint.setStrokeWidth(width);
            ripplePaint.setMaskFilter(new BlurMaskFilter(blur, BlurMaskFilter.Blur.NORMAL));

            canvas.drawCircle(cx, cy, r, ripplePaint);
        }
    }
}
