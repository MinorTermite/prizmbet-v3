package com.prizmbet.app;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;
import android.view.animation.LinearInterpolator;

import java.util.Random;

/**
 * Полноэкранный фон заставки: светящиеся частицы медленно дрейфуют по тёмному экрану.
 *
 * Стиль: крипто / финтех премиум (Binance, Coinbase, Bybit).
 *  — 45 частиц трёх размеров (мелкие / средние / крупные)
 *  — каждая медленно дрейфует в случайном направлении, зацикливаясь через края
 *  — каждая мерцает по синусоиде (фаза и частота уникальны)
 *  — BlurMaskFilter создаёт настоящее неоновое свечение
 *  — LAYER_TYPE_SOFTWARE — обязателен для BlurMaskFilter
 *  — все Paint-объекты создаются один раз, не во время рисования
 */
public class ParticleView extends View {

    // ── Палитра и геометрия ───────────────────────────────────────────────────
    private static final int COUNT = 45;

    private static final int[] COLORS = {
            0xFF6366F1,   // indigo
            0xFF818CF8,   // light indigo
            0xFFA855F7,   // purple
            0xFFC4B5FD,   // lavender
            0xFF7C3AED,   // violet
    };

    /** Радиусы в dp: мелкие / средние / крупные. */
    private static final float[] SIZE_DP  = { 1.5f, 2.5f, 4.0f };
    /** Множитель размытия относительно радиуса. */
    private static final float[] BLUR_MUL = { 2.2f, 2.8f, 3.6f };

    // ── Данные частиц ─────────────────────────────────────────────────────────
    private static final class P {
        float x, y;          // позиция [0..1] нормализованная
        float vx, vy;        // скорость за кадр (~16 мс)
        int   si;            // индекс размера (0/1/2)
        int   color;
        float baseAlpha;     // [0.30 .. 0.85]
        float phase;         // фаза мерцания [0..2π]
        float freq;          // частота мерцания
    }

    private final P[]     pts  = new P[COUNT];
    private final Paint[] pnts = new Paint[SIZE_DP.length];
    private boolean       paintsReady = false;
    private float         density     = 1f;
    private float         tick        = 0f;
    private ValueAnimator animator;

    // ── Конструкторы ──────────────────────────────────────────────────────────
    public ParticleView(Context c)                          { super(c);         init(); }
    public ParticleView(Context c, AttributeSet a)          { super(c, a);      init(); }
    public ParticleView(Context c, AttributeSet a, int d)   { super(c, a, d);   init(); }

    // ── Инициализация ─────────────────────────────────────────────────────────
    private void init() {
        setLayerType(LAYER_TYPE_SOFTWARE, null);   // нужно для BlurMaskFilter

        Random rnd = new Random(13);  // фиксированный seed → одинаковый вид при каждом запуске
        for (int i = 0; i < COUNT; i++) {
            P p = new P();
            p.x         = rnd.nextFloat();
            p.y         = rnd.nextFloat();
            // Скорость: частица пересекает экран за ~25–60 секунд
            float speed = 0.00022f + rnd.nextFloat() * 0.00048f;
            double ang  = rnd.nextDouble() * Math.PI * 2;
            p.vx        = (float)(Math.cos(ang) * speed);
            p.vy        = (float)(Math.sin(ang) * speed);
            p.si        = rnd.nextInt(SIZE_DP.length);
            p.color     = COLORS[rnd.nextInt(COLORS.length)];
            p.baseAlpha = 0.30f + rnd.nextFloat() * 0.55f;
            p.phase     = rnd.nextFloat() * (float)(Math.PI * 2);
            p.freq      = 0.40f + rnd.nextFloat() * 1.20f;
            pts[i] = p;
        }
    }

    /** Создаём Paint-объекты один раз после получения density. */
    private void initPaints() {
        density = getContext().getResources().getDisplayMetrics().density;
        for (int i = 0; i < SIZE_DP.length; i++) {
            pnts[i] = new Paint(Paint.ANTI_ALIAS_FLAG);
            pnts[i].setStyle(Paint.Style.FILL);
            float blur = SIZE_DP[i] * density * BLUR_MUL[i];
            pnts[i].setMaskFilter(new BlurMaskFilter(blur, BlurMaskFilter.Blur.NORMAL));
        }
        paintsReady = true;
    }

    // ── Жизненный цикл ────────────────────────────────────────────────────────
    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(12_000);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setRepeatMode(ValueAnimator.RESTART);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a -> {
            tick = (float) a.getAnimatedValue() * 12f;   // 0..12 секунд
            // Двигаем частицы
            for (P p : pts) {
                p.x += p.vx;
                p.y += p.vy;
                // Зацикливаем через края с небольшим запасом
                if      (p.x < -0.06f) p.x += 1.12f;
                else if (p.x >  1.06f) p.x -= 1.12f;
                if      (p.y < -0.06f) p.y += 1.12f;
                else if (p.y >  1.06f) p.y -= 1.12f;
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
        if (!paintsReady) initPaints();

        final int   w = getWidth();
        final int   h = getHeight();

        for (P p : pts) {
            // Мерцание: синусоида → alpha варьируется плавно
            float twinkle = (float)(Math.sin(tick * p.freq + p.phase) * 0.5 + 0.5);
            float alpha   = p.baseAlpha * (0.35f + twinkle * 0.65f);

            Paint pnt = pnts[p.si];
            pnt.setColor(p.color);
            pnt.setAlpha((int)(alpha * 255));

            canvas.drawCircle(p.x * w, p.y * h, SIZE_DP[p.si] * density, pnt);
        }
    }
}
