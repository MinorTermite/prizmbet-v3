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
 * 2026 Cybernetic cryptographic splash.
 *
 * Layers:
 * 1. Deep space gradient background with scan lines
 * 2. Hex data stream (vertical matrix rain)
 * 3. Orbital rings system around logo
 * 4. Blockchain lattice mesh with pulsing nodes
 * 5. Holographic logo with chromatic aberration glow
 * 6. Glitch title with reveal animation
 * 7. Rolling hash + verification bar
 * 8. Cinematic outro fade
 */
public class PremiumSplashView extends View {

    // ── Palette — dark carbon base with electric accents ──
    private static final int BG_DEEP    = 0xFF020208;
    private static final int BG_MID     = 0xFF08081A;
    private static final int ELECTRIC   = 0xFF00F0FF;   // primary cyan
    private static final int NEON_VIOLET= 0xFFBF5AF2;   // iOS purple
    private static final int PLASMA     = 0xFF6366F1;    // indigo
    private static final int HOLO_GREEN = 0xFF30D158;    // success green
    private static final int HOLO_PINK  = 0xFFFF375F;    // danger accent
    private static final int WHITE      = 0xFFF5F5FF;
    private static final int GHOST      = 0xFF4A4A6A;
    private static final int ANIM_MS    = 3800;
    private static final float COMPLETE_AT = 0.85f;

    // Hex rain config
    private static final int HEX_COLS = 22;
    private static final int HEX_ROWS = 8;
    private static final String HEX = "0123456789ABCDEF";

    // Mesh config
    private static final int MESH_NODES = 18;
    private static final int ORBIT_SEGMENTS = 3;
    private static final int PARTICLE_COUNT = 55;

    // ── Data classes ──
    private static final class HexDrop {
        float x, y, speed, alpha, size;
        String ch;
        boolean bright;
    }

    private static final class MeshNode {
        float x, y, baseX, baseY, radius, phase;
        int color;
        boolean active;
    }

    private static final class Spark {
        float x, y, vx, vy, radius, alpha, phase, life;
        int color;
    }

    // ── Fields ──
    private final Random rng = new Random(2026);
    private final HexDrop[] drops = new HexDrop[HEX_COLS * HEX_ROWS];
    private final MeshNode[] mesh = new MeshNode[MESH_NODES];
    private final Spark[] sparks = new Spark[PARTICLE_COUNT];

    private final Paint bgPaint    = new Paint();
    private final Paint scanPaint  = new Paint();
    private final Paint hexPaint   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint meshPaint  = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint meshGlow   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint linePaint  = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint sparkPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint  = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringGlow   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint logoPaint  = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint logoGlow1  = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint logoGlow2  = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Paint titlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint titleGlow  = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subPaint   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint hashPaint  = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint barPaint   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint orbPaint   = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint outroPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint vignetPaint= new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF tmpRect    = new RectF();

    private Bitmap logoBitmap;
    private ValueAnimator animator;
    private Runnable onComplete;
    private float progress = 0f;
    private float tick = 0f;
    private float density = 1f;
    private boolean completeFired = false;
    private String currentHash = "";

    public PremiumSplashView(Context c) { super(c); init(c); }
    public PremiumSplashView(Context c, AttributeSet a) { super(c, a); init(c); }
    public PremiumSplashView(Context c, AttributeSet a, int d) { super(c, a, d); init(c); }

    public void setOnCompleteListener(Runnable r) { onComplete = r; }

    private void init(Context ctx) {
        setLayerType(LAYER_TYPE_SOFTWARE, null);
        density = ctx.getResources().getDisplayMetrics().density;

        Drawable d = AppCompatResources.getDrawable(ctx, R.drawable.ic_prizm_mark);
        if (d != null) logoBitmap = toBitmap(d, (int)(220*density), (int)(192*density));

        Typeface mono = Typeface.create("monospace", Typeface.BOLD);
        Typeface sans = Typeface.create("sans-serif-medium", Typeface.BOLD);

        hexPaint.setTypeface(mono);
        hexPaint.setTextAlign(Paint.Align.CENTER);

        meshPaint.setStyle(Paint.Style.FILL);
        meshGlow.setStyle(Paint.Style.FILL);
        meshGlow.setMaskFilter(new BlurMaskFilter(20*density, BlurMaskFilter.Blur.NORMAL));

        linePaint.setStyle(Paint.Style.STROKE);
        linePaint.setStrokeWidth(0.6f*density);

        sparkPaint.setStyle(Paint.Style.FILL);
        sparkPaint.setMaskFilter(new BlurMaskFilter(8*density, BlurMaskFilter.Blur.NORMAL));

        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeCap(Paint.Cap.ROUND);

        ringGlow.setStyle(Paint.Style.STROKE);
        ringGlow.setMaskFilter(new BlurMaskFilter(16*density, BlurMaskFilter.Blur.NORMAL));

        logoGlow1.setMaskFilter(new BlurMaskFilter(36*density, BlurMaskFilter.Blur.NORMAL));
        logoGlow1.setColor(ELECTRIC);
        logoGlow2.setMaskFilter(new BlurMaskFilter(48*density, BlurMaskFilter.Blur.NORMAL));
        logoGlow2.setColor(NEON_VIOLET);

        titlePaint.setTypeface(sans);
        titlePaint.setTextAlign(Paint.Align.CENTER);
        titlePaint.setLetterSpacing(0.28f);
        titlePaint.setColor(WHITE);

        titleGlow.setTypeface(sans);
        titleGlow.setTextAlign(Paint.Align.CENTER);
        titleGlow.setLetterSpacing(0.28f);
        titleGlow.setColor(ELECTRIC);
        titleGlow.setMaskFilter(new BlurMaskFilter(18*density, BlurMaskFilter.Blur.NORMAL));

        subPaint.setTypeface(mono);
        subPaint.setTextAlign(Paint.Align.CENTER);
        subPaint.setLetterSpacing(0.12f);

        hashPaint.setTypeface(mono);
        hashPaint.setTextAlign(Paint.Align.CENTER);

        barPaint.setStyle(Paint.Style.FILL);

        scanPaint.setStyle(Paint.Style.FILL);

        // Init hex drops
        for (int i = 0; i < drops.length; i++) {
            HexDrop h = new HexDrop();
            h.x = (i % HEX_COLS) / (float)HEX_COLS;
            h.y = -rng.nextFloat() * 2.5f;
            h.speed = 0.0025f + rng.nextFloat() * 0.005f;
            h.alpha = 0.05f + rng.nextFloat() * 0.18f;
            h.ch = String.valueOf(HEX.charAt(rng.nextInt(16)));
            h.size = (8f + rng.nextFloat() * 4f) * density;
            h.bright = rng.nextFloat() < 0.08f;
            drops[i] = h;
        }

        // Init mesh nodes — distributed in a wider field
        for (int i = 0; i < MESH_NODES; i++) {
            MeshNode n = new MeshNode();
            double ang = (i/(double)MESH_NODES) * Math.PI*2 + rng.nextDouble()*0.6;
            double dist = 0.18 + rng.nextDouble()*0.30;
            n.baseX = 0.5f + (float)(Math.cos(ang)*dist);
            n.baseY = 0.40f + (float)(Math.sin(ang)*dist*0.65);
            n.x = n.baseX; n.y = n.baseY;
            n.radius = (2f + rng.nextFloat()*3f) * density;
            n.phase = rng.nextFloat() * 6.28f;
            n.color = pickMeshColor(i);
            n.active = false;
            mesh[i] = n;
        }

        // Init sparks
        for (int i = 0; i < PARTICLE_COUNT; i++) {
            Spark s = new Spark();
            s.x = rng.nextFloat();
            s.y = rng.nextFloat();
            s.vx = (rng.nextFloat()-0.5f) * 0.0006f;
            s.vy = (rng.nextFloat()-0.5f) * 0.0006f;
            s.radius = (0.6f + rng.nextFloat()*2.2f) * density;
            s.alpha = 0.08f + rng.nextFloat() * 0.22f;
            s.phase = rng.nextFloat() * 6.28f;
            s.life = 0.6f + rng.nextFloat() * 0.4f;
            s.color = pickSparkColor(i);
            sparks[i] = s;
        }
    }

    private int pickMeshColor(int i) {
        switch (i % 5) {
            case 0: return ELECTRIC;
            case 1: return NEON_VIOLET;
            case 2: return PLASMA;
            case 3: return HOLO_GREEN;
            default: return ELECTRIC;
        }
    }

    private int pickSparkColor(int i) {
        switch (i % 6) {
            case 0: return ELECTRIC;
            case 1: return NEON_VIOLET;
            case 2: return PLASMA;
            case 3: return HOLO_GREEN;
            case 4: return HOLO_PINK;
            default: return WHITE;
        }
    }

    private Bitmap toBitmap(Drawable d, int w, int h) {
        Bitmap bmp = Bitmap.createBitmap(Math.max(w,1), Math.max(h,1), Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        d.setBounds(0, 0, w, h);
        d.draw(c);
        return bmp;
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIM_MS);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(va -> {
            progress = (float) va.getAnimatedValue();
            tick = progress * 14f;
            advanceDrops();
            advanceSparks();
            advanceMesh();
            updateHash();
            if (!completeFired && progress >= COMPLETE_AT) {
                completeFired = true;
                if (onComplete != null) post(onComplete);
            }
            invalidate();
        });
        animator.start();
    }

    @Override protected void onDetachedFromWindow() {
        if (animator != null) animator.cancel();
        super.onDetachedFromWindow();
    }

    // ── Simulation ──

    private void advanceDrops() {
        for (HexDrop h : drops) {
            h.y += h.speed;
            if (h.y > 1.3f) {
                h.y = -rng.nextFloat()*0.4f;
                h.ch = String.valueOf(HEX.charAt(rng.nextInt(16)));
                h.bright = rng.nextFloat() < 0.08f;
            }
        }
    }

    private void advanceSparks() {
        for (Spark s : sparks) {
            s.x += s.vx; s.y += s.vy;
            if (s.x < -0.05f) s.x = 1.05f;
            if (s.x > 1.05f) s.x = -0.05f;
            if (s.y < -0.05f) s.y = 1.05f;
            if (s.y > 1.05f) s.y = -0.05f;
        }
    }

    private void advanceMesh() {
        float p = phase(0.10f, 0.55f, progress);
        for (int i = 0; i < mesh.length; i++) {
            MeshNode n = mesh[i];
            n.active = p > (i/(float)MESH_NODES);
            // Subtle drift
            float drift = (float)Math.sin(tick*0.8 + n.phase) * 0.008f;
            n.x = n.baseX + drift;
            n.y = n.baseY + (float)Math.cos(tick*0.6 + n.phase) * 0.005f;
        }
    }

    private void updateHash() {
        int len = (int)(progress * 64);
        StringBuilder sb = new StringBuilder();
        Random hr = new Random((long)(progress*1000));
        for (int i = 0; i < Math.min(len, 20); i++) {
            sb.append(HEX.charAt(hr.nextInt(16)));
        }
        currentHash = sb.toString();
    }

    // ── Draw pipeline ──

    @Override protected void onDraw(Canvas canvas) {
        int w = getWidth(), h = getHeight();
        float cx = w/2f, cy = h*0.38f;

        drawBackground(canvas, w, h);
        drawScanLines(canvas, w, h);
        drawAmbientOrbs(canvas, w, h);
        drawHexRain(canvas, w, h);
        drawMeshNetwork(canvas, w, h);
        drawSparks(canvas, w, h);
        drawOrbitRings(canvas, cx, cy);
        drawLogo(canvas, cx, cy);
        drawTitle(canvas, cx, cy);
        drawHashBar(canvas, cx, w, h);
        drawVignette(canvas, w, h);
        drawOutro(canvas, w, h);
    }

    private void drawBackground(Canvas c, int w, int h) {
        bgPaint.setShader(new LinearGradient(0, 0, 0, h,
                new int[]{BG_DEEP, BG_MID, 0xFF040414, BG_DEEP},
                new float[]{0f, 0.35f, 0.7f, 1f}, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, bgPaint);
    }

    private void drawScanLines(Canvas c, int w, int h) {
        float a = Math.min(1f, progress/0.3f) * 0.035f;
        scanPaint.setColor(Color.argb((int)(255*a), 0, 240, 255));
        float gap = 3f * density;
        for (float y = 0; y < h; y += gap) {
            c.drawRect(0, y, w, y + 1, scanPaint);
        }

        // Moving scan beam
        if (progress < 0.7f) {
            float beamY = (tick * 80f) % (h + 100) - 50;
            scanPaint.setShader(new LinearGradient(0, beamY-30*density, 0, beamY+30*density,
                    new int[]{Color.TRANSPARENT, Color.argb(30, 0, 240, 255), Color.TRANSPARENT},
                    null, Shader.TileMode.CLAMP));
            c.drawRect(0, beamY-30*density, w, beamY+30*density, scanPaint);
            scanPaint.setShader(null);
        }
    }

    private void drawAmbientOrbs(Canvas c, int w, int h) {
        float a = Math.min(1f, progress/0.35f);

        // Top-left electric cyan orb
        orbPaint.setShader(new RadialGradient(w*0.15f, h*0.12f, w*0.55f,
                new int[]{Color.argb((int)(a*30), 0, 240, 255), Color.TRANSPARENT},
                null, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, orbPaint);

        // Center violet orb
        orbPaint.setShader(new RadialGradient(w*0.55f, h*0.38f, w*0.4f,
                new int[]{Color.argb((int)(a*35), 191, 90, 242), Color.TRANSPARENT},
                null, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, orbPaint);

        // Bottom-right plasma orb
        orbPaint.setShader(new RadialGradient(w*0.85f, h*0.75f, w*0.45f,
                new int[]{Color.argb((int)(a*20), 99, 102, 241), Color.TRANSPARENT},
                null, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, orbPaint);

        orbPaint.setShader(null);
    }

    private void drawHexRain(Canvas c, int w, int h) {
        float appear = Math.min(1f, progress/0.15f);
        float fade = progress > 0.7f ? 1f - phase(0.7f, 0.9f, progress) : 1f;
        float layer = appear * fade;
        if (layer <= 0) return;

        for (HexDrop d : drops) {
            if (d.y < 0 || d.y > 1f) continue;
            float edge = Math.min(1f, Math.min(d.y*6f, (1f-d.y)*6f));
            int color = d.bright ? ELECTRIC : HOLO_GREEN;
            hexPaint.setColor(color);
            hexPaint.setAlpha((int)(255 * (d.bright ? 0.5f : d.alpha) * layer * edge));
            hexPaint.setTextSize(d.size);
            float px = d.x*w + w/(float)HEX_COLS/2f;
            c.drawText(d.ch, px, d.y*h, hexPaint);
        }
    }

    private void drawMeshNetwork(Canvas c, int w, int h) {
        float appear = phase(0.08f, 0.45f, progress);
        if (appear <= 0) return;

        // Connections
        for (int i = 0; i < mesh.length; i++) {
            if (!mesh[i].active) continue;
            for (int j = i+1; j < mesh.length; j++) {
                if (!mesh[j].active) continue;
                float dx = mesh[i].x - mesh[j].x;
                float dy = mesh[i].y - mesh[j].y;
                float dist = (float)Math.sqrt(dx*dx + dy*dy);
                if (dist < 0.30f) {
                    float la = (1f - dist/0.30f) * appear * 0.25f;
                    float pulse = (float)(0.5f + 0.5f * Math.sin(tick*1.5 + i + j));
                    linePaint.setColor(ELECTRIC);
                    linePaint.setAlpha((int)(255 * la * pulse));
                    c.drawLine(mesh[i].x*w, mesh[i].y*h, mesh[j].x*w, mesh[j].y*h, linePaint);
                }
            }
        }

        // Nodes
        for (MeshNode n : mesh) {
            if (!n.active) continue;
            float pulse = (float)((Math.sin(tick*2.5 + n.phase) + 1f) * 0.5f);
            float r = n.radius * (0.7f + pulse*0.5f);

            meshGlow.setColor(n.color);
            meshGlow.setAlpha((int)(60 * appear * pulse));
            c.drawCircle(n.x*w, n.y*h, r*4f, meshGlow);

            meshPaint.setColor(n.color);
            meshPaint.setAlpha((int)(200 * appear));
            c.drawCircle(n.x*w, n.y*h, r, meshPaint);

            meshPaint.setColor(WHITE);
            meshPaint.setAlpha((int)(160 * appear * pulse));
            c.drawCircle(n.x*w, n.y*h, r*0.35f, meshPaint);
        }
    }

    private void drawSparks(Canvas c, int w, int h) {
        float layer = Math.min(1f, progress/0.2f);
        for (Spark s : sparks) {
            float twinkle = (float)((Math.sin(tick*1.2 + s.phase) + 1f) * 0.5f);
            float vis = layer * s.alpha * (0.2f + twinkle*0.8f);
            if (progress > s.life) vis *= Math.max(0f, 1f - (progress - s.life)*5f);
            sparkPaint.setColor(s.color);
            sparkPaint.setAlpha((int)(255 * vis));
            c.drawCircle(s.x*w, s.y*h, s.radius, sparkPaint);
        }
    }

    private void drawOrbitRings(Canvas c, float cx, float cy) {
        float appear = phase(0.15f, 0.50f, progress);
        if (appear <= 0) return;

        float rot = tick * 20f;

        // Outer ring — segmented, rotating
        float r1 = 82f * density;
        tmpRect.set(cx-r1, cy-r1, cx+r1, cy+r1);
        ringPaint.setStrokeWidth(2f*density);
        ringGlow.setStrokeWidth(7f*density);

        int segs = 10;
        float segAng = 360f / segs;
        for (int i = 0; i < segs; i++) {
            float start = rot + i*segAng + 3f;
            float sweep = segAng - 6f;
            float sa = appear * (0.3f + 0.7f*(float)Math.abs(Math.sin(tick*1.5 + i*0.7)));

            int col = i%3==0 ? ELECTRIC : i%3==1 ? NEON_VIOLET : PLASMA;
            ringGlow.setColor(col);
            ringGlow.setAlpha((int)(80*sa));
            c.drawArc(tmpRect, start, sweep, false, ringGlow);

            ringPaint.setColor(col);
            ringPaint.setAlpha((int)(220*sa));
            c.drawArc(tmpRect, start, sweep, false, ringPaint);
        }

        // Middle ring — counter-rotating, dashed
        float r2 = 66f * density;
        tmpRect.set(cx-r2, cy-r2, cx+r2, cy+r2);
        ringPaint.setStrokeWidth(1.2f*density);
        for (int i = 0; i < 16; i++) {
            float start = -rot*0.6f + i*22.5f + 2f;
            float sweep = 16f;
            float sa = appear * (float)Math.abs(Math.sin(tick*1.8 + i));
            ringPaint.setColor(HOLO_GREEN);
            ringPaint.setAlpha((int)(100*sa));
            c.drawArc(tmpRect, start, sweep, false, ringPaint);
        }

        // Inner ring — fast, thin
        float r3 = 52f * density;
        tmpRect.set(cx-r3, cy-r3, cx+r3, cy+r3);
        ringPaint.setStrokeWidth(0.8f*density);
        for (int i = 0; i < 24; i++) {
            float start = rot*1.4f + i*15f + 1f;
            float sweep = 10f;
            float sa = appear * 0.4f * (float)Math.abs(Math.sin(tick*2.2 + i*0.5));
            ringPaint.setColor(ELECTRIC);
            ringPaint.setAlpha((int)(120*sa));
            c.drawArc(tmpRect, start, sweep, false, ringPaint);
        }

        ringPaint.setStrokeWidth(2f*density);
    }

    private void drawLogo(Canvas c, float cx, float cy) {
        if (logoBitmap == null) return;
        float appear = phase(0.20f, 0.50f, progress);
        if (appear <= 0) return;

        float eased = decel(appear);
        float scale = 0.8f + eased*0.2f;
        float logoW = 44f * density * scale;
        float aspect = logoBitmap.getHeight() / (float)logoBitmap.getWidth();
        float logoH = logoW * aspect;
        android.graphics.Rect src = new android.graphics.Rect(0, 0, logoBitmap.getWidth(), logoBitmap.getHeight());

        // Chromatic aberration glow — violet layer offset
        float glowW2 = logoW*2.2f;
        float glowH2 = logoH*2.2f;
        float offset = 3f * density * eased;
        logoGlow2.setAlpha((int)(90*eased));
        c.drawBitmap(logoBitmap, src, new RectF(
                cx-glowW2/2+offset, cy-glowH2/2,
                cx+glowW2/2+offset, cy+glowH2/2), logoGlow2);

        // Cyan glow layer
        float glowW1 = logoW*2f;
        float glowH1 = logoH*2f;
        logoGlow1.setAlpha((int)(120*eased));
        c.drawBitmap(logoBitmap, src, new RectF(
                cx-glowW1/2-offset*0.5f, cy-glowH1/2,
                cx+glowW1/2-offset*0.5f, cy+glowH1/2), logoGlow1);

        // Sharp logo
        logoPaint.setAlpha((int)(255*eased));
        c.drawBitmap(logoBitmap, src, new RectF(
                cx-logoW/2, cy-logoH/2,
                cx+logoW/2, cy+logoH/2), logoPaint);
    }

    private void drawTitle(Canvas c, float cx, float cy) {
        float appear = phase(0.35f, 0.60f, progress);
        if (appear <= 0) return;

        float eased = decel(appear);
        float y = cy + 100f*density + (1f-eased)*18f*density;

        titlePaint.setTextSize(18f*density);
        titleGlow.setTextSize(18f*density);

        // Glitch effect: slight offset during reveal
        float glitch = appear < 0.5f ? (float)Math.sin(tick*20) * 2f * density * (1f-appear*2) : 0f;

        // Glow
        titleGlow.setAlpha((int)(100*eased));
        c.drawText("PRIZMBET", cx + glitch, y, titleGlow);

        // Text
        titlePaint.setAlpha((int)(250*eased));
        c.drawText("PRIZMBET", cx, y, titlePaint);

        // Subtitle with typing reveal
        subPaint.setTextSize(8f*density);
        subPaint.setColor(GHOST);
        float subAppear = phase(0.45f, 0.70f, progress);
        if (subAppear > 0) {
            String full = "CRYPTO \u00B7 PREDICTION \u00B7 ANALYTICS";
            int reveal = (int)(full.length() * subAppear);
            String shown = full.substring(0, Math.min(reveal, full.length()));
            subPaint.setAlpha((int)(180 * Math.min(1f, subAppear*2)));
            c.drawText(shown, cx, y + 20f*density, subPaint);

            // Cursor blink
            if (subAppear < 1f && (int)(tick*8)%2 == 0) {
                float tw = subPaint.measureText(shown);
                barPaint.setColor(ELECTRIC);
                barPaint.setAlpha(180);
                c.drawRect(cx+tw/2+2*density, y+8*density, cx+tw/2+4*density, y+20*density, barPaint);
            }
        }
    }

    private void drawHashBar(Canvas c, float cx, int w, int h) {
        float appear = phase(0.50f, 0.78f, progress);
        if (appear <= 0 || currentHash.isEmpty()) return;

        float y = h * 0.68f;

        // Label
        hashPaint.setTextSize(7f*density);
        hashPaint.setColor(ELECTRIC);
        hashPaint.setAlpha((int)(50*appear));
        c.drawText("BLOCK VERIFICATION", cx, y - 18*density, hashPaint);

        // Hash
        hashPaint.setTextSize(10f*density);
        hashPaint.setColor(HOLO_GREEN);
        hashPaint.setAlpha((int)(90*appear));
        c.drawText("0x" + currentHash, cx, y, hashPaint);

        // Progress bar underneath
        float barW = 140f * density;
        float barH = 2f * density;
        float barX = cx - barW/2;
        float barY = y + 12*density;

        // Background
        barPaint.setColor(GHOST);
        barPaint.setAlpha((int)(30*appear));
        c.drawRoundRect(barX, barY, barX+barW, barY+barH, barH, barH, barPaint);

        // Fill
        float fillW = barW * Math.min(1f, progress/0.75f);
        barPaint.setShader(new LinearGradient(barX, barY, barX+fillW, barY,
                new int[]{ELECTRIC, NEON_VIOLET}, null, Shader.TileMode.CLAMP));
        barPaint.setAlpha((int)(200*appear));
        c.drawRoundRect(barX, barY, barX+fillW, barY+barH, barH, barH, barPaint);
        barPaint.setShader(null);
    }

    private void drawVignette(Canvas c, int w, int h) {
        vignetPaint.setShader(new RadialGradient(w/2f, h*0.4f, w*0.85f,
                new int[]{Color.TRANSPARENT, Color.argb(120, 2, 2, 8)},
                new float[]{0.5f, 1f}, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, vignetPaint);
    }

    private void drawOutro(Canvas c, int w, int h) {
        float outro = phase(0.80f, 1f, progress);
        if (outro <= 0) return;
        int a = (int)(180 * easeInOut(outro));
        outroPaint.setShader(new LinearGradient(0, 0, 0, h,
                new int[]{Color.argb(a, 2, 2, 8), Color.argb((int)(a*0.2f), 2, 2, 8), Color.argb(a, 2, 2, 8)},
                new float[]{0f, 0.4f, 1f}, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, w, h, outroPaint);
    }

    // ── Easing ──
    private float phase(float s, float e, float v) {
        return v<=s ? 0f : v>=e ? 1f : (v-s)/(e-s);
    }
    private float decel(float v) {
        float t = Math.max(0,Math.min(1,v));
        return 1f-(1f-t)*(1f-t);
    }
    private float easeInOut(float v) {
        float t = Math.max(0,Math.min(1,v));
        return (float)(t<0.5 ? 4*t*t*t : 1-Math.pow(-2*t+2,3)/2);
    }
}
