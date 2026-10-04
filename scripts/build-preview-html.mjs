import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const svg = readFileSync('assets/mascot.svg', 'utf8');
const artifactDir = 'C:\\Users\\lastnut\\.gemini\\antigravity\\brain\\8cb5af0a-1128-447c-9a67-a95a1c4eeddf';
const targetHtml = join(artifactDir, 'mascot_svg_preview.html');

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>op-lead-with-us 矢量吉祥物预览</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    .svg-container svg { width: 100%; height: 100%; display: block; }
  </style>
</head>
<body class="bg-[var(--background,#0F172A)] text-[var(--foreground,#F8FAFC)] antialiased p-4 md:p-8 min-h-screen">
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border,#334155)] pb-5">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">100% Pure Vector SVG</span>
          <span class="text-xs text-[var(--muted-foreground,#94A3B8)]">21.9 KB · 无损缩放</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground,#F8FAFC)]">op-lead-with-us 矢量吉祥物重绘</h1>
        <p class="text-sm text-[var(--muted-foreground,#94A3B8)] mt-1">
          纯 SVG 矢量几何重绘 · 黑色蕾丝半面假面 · 鸢尾花纹章边框 · 极速轻量加载
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button id="bg-toggle" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] hover:bg-slate-700 transition-colors">
          切换展示背景色
        </button>
      </div>
    </div>

    <!-- Main Viewport Card -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
      <!-- SVG Render Stage -->
      <div id="preview-stage" class="bg-[#F8FAFC] border border-[var(--border,#334155)] rounded-2xl p-6 shadow-xl flex items-center justify-center transition-colors duration-300">
        <div class="svg-container w-full max-w-[360px] aspect-square drop-shadow-md transition-transform duration-300 hover:scale-105">
          ${svg}
        </div>
      </div>

      <!-- Feature Highlights -->
      <div class="space-y-4">
        <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
          <h3 class="text-sm font-semibold text-cyan-400 flex items-center gap-2">
            <span>🎭</span> 黑色蕾丝假面眼罩 (Lace Mask)
          </h3>
          <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
            采用 SVG <code class="text-cyan-300">&lt;pattern&gt;</code> 钻石菱格镂空透气网底与植物藤蔓刺绣花纹，精细保留眼部开孔与锁边花边（Picot Trim），在章鱼脸颊形成自然阴影。
          </p>
        </div>

        <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
          <h3 class="text-sm font-semibold text-indigo-400 flex items-center gap-2">
            <span>🐙</span> 灵动可爱的死鱼眼与下弯嘴
          </h3>
          <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
            半闭眼平视眼睑（Deadpan / Tired Expression），双层高光点缀；中间点缀精致的倒弧小弯嘴与腮红，传达出“从容指挥、优雅平淡”的独特个性。
          </p>
        </div>

        <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
          <h3 class="text-sm font-semibold text-pink-400 flex items-center gap-2">
            <span>🎀</span> 缎面丝带与双侧粉色山茶花
          </h3>
          <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
            耳际装饰黑色双环缎面蝴蝶结与飘逸燕尾丝带，点缀多重渐变花瓣粉色山茶花与深色花蕊，层次感丰富。
          </p>
        </div>

        <div class="bg-[var(--card,#1E293B)] border border-[var(--border,#334155)] rounded-xl p-4">
          <h3 class="text-sm font-semibold text-amber-400 flex items-center gap-2">
            <span>⚜️</span> 鸢尾花纹章圆环徽记 (Heraldic Seal)
          </h3>
          <p class="text-xs text-[var(--muted-foreground,#94A3B8)] mt-1.5 leading-relaxed">
            外围藏青色正圆与点状装饰环，正上方与正下方点缀经典矢量法式鸢尾花徽记（Fleur-de-lis），四角辅以星芒，仪式感与科技感并存。
          </p>
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
