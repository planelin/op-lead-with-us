import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const mascotSvg = readFileSync('assets/mascot.svg', 'utf8');
const bannerSvg = readFileSync('assets/banner.svg', 'utf8');
const artifactDir = 'C:\\Users\\lastnut\\.gemini\\antigravity\\brain\\8cb5af0a-1128-447c-9a67-a95a1c4eeddf';
const targetHtml = join(artifactDir, 'mascot_svg_preview.html');

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>op-lead-with-us 矢量吉祥物与横幅预览</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    .svg-container svg { width: 100%; height: auto; display: block; }
  </style>
</head>
<body class="bg-[var(--background,#0F172A)] text-[var(--foreground,#F8FAFC)] antialiased p-4 md:p-8 min-h-screen">
  <div class="max-w-5xl mx-auto space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border,#334155)] pb-5">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">100% Pure Vector SVG</span>
          <span class="text-xs text-[var(--muted-foreground,#94A3B8)]">无损缩放 · 头部顶部留白优化</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground,#F8FAFC)]">op-lead-with-us 矢量主视觉 & 横幅</h1>
        <p class="text-sm text-[var(--muted-foreground,#94A3B8)] mt-1">
          根据反馈优化：章鱼头部圆顶高度降低，完整置于顶部纹章与虚线圆环之下，消除局促拥挤感。
        </p>
      </div>
    </div>

    <!-- Section 1: GitHub Banner Live Preview -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-cyan-400 flex items-center gap-2">
          <span>🚩</span> GitHub 主页横幅 (assets/banner.svg)
        </h2>
        <span class="text-xs text-[var(--muted-foreground,#94A3B8)]">1200 × 440 · 纯矢量内联</span>
      </div>
      <div class="border border-[var(--border,#334155)] rounded-2xl overflow-hidden shadow-2xl bg-[#070A12]">
        <div class="svg-container w-full">
          ${bannerSvg}
        </div>
      </div>
      <p class="text-xs text-[var(--muted-foreground,#94A3B8)]">
        ✨ 效果确认：左侧圆形徽章内，章鱼头部最高点与顶部鸢尾花及虚线圆环之间留有自然充裕的深色背景间隙，比例更加软萌从容。
      </p>
    </div>

    <!-- Section 2: Standalone Mascot Preview -->
    <div class="space-y-3 pt-4 border-t border-[var(--border,#334155)]">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-indigo-400 flex items-center gap-2">
          <span>🐙</span> 单独吉祥物矢量图 (assets/mascot.svg)
        </h2>
        <button id="bg-toggle" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] hover:bg-slate-700 transition-colors">
          切换展示背景色
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        <!-- SVG Render Stage -->
        <div id="preview-stage" class="bg-[#F8FAFC] border border-[var(--border,#334155)] rounded-2xl p-6 shadow-xl flex items-center justify-center transition-colors duration-300">
          <div class="svg-container w-full max-w-[360px] aspect-square drop-shadow-md transition-transform duration-300 hover:scale-105">
            ${mascotSvg}
          </div>
        </div>

        <!-- Details -->
        <div class="space-y-4">
          <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
            <h3 class="text-sm font-semibold text-cyan-400 flex items-center gap-2">
              <span>🎯</span> 头部弧度与重心优化 (Head Clearance)
            </h3>
            <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
              头部顶点下移至 <code class="text-cyan-300">y=196</code>，与顶部虚线圈（y=98）及鸢尾花纹章保持超过 100px 的舒展间距，彻底消除“顶破外框”的局促感，头身比更显 Q 萌软弹。
            </p>
          </div>

          <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
            <h3 class="text-sm font-semibold text-indigo-400 flex items-center gap-2">
              <span>👀</span> 超大死鱼眼与微蹙眉
            </h3>
            <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
              单眼宽 92px、高 76px，双眼中心间距 156px，鼻梁开阔；搭配上眼睑平直冷漠切线、晶莹药丸高光与眉峰折痕，死鱼眼反差萌十足。
            </p>
          </div>

          <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
            <h3 class="text-sm font-semibold text-pink-400 flex items-center gap-2">
              <span>🪑</span> 宽大饱满的麻薯触手底盘
            </h3>
            <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
              5 瓣麻薯触手跨度达 550px，向两侧自然舒展，与下移缩小的圆润头部形成稳定的“上小下大”三角形构图。
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const bgToggle = document.getElementById('bg-toggle');
    const stage = document.getElementById('preview-stage');
    const bgs = ['bg-[#F8FAFC]', 'bg-white', 'bg-[#0F172A]', 'bg-[#1E1B2E]'];
    let idx = 0;
    bgToggle.addEventListener('click', () => {
      stage.classList.remove(bgs[idx]);
      idx = (idx + 1) % bgs.length;
      stage.classList.add(bgs[idx]);
    });
  </script>
</body>
</html>`;

writeFileSync(targetHtml, html, 'utf8');
console.log('Successfully wrote ' + targetHtml);
