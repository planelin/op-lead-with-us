import { readFileSync, writeFileSync } from 'node:fs';
import { buildMascotSvg } from './build-mascot-svg.mjs';

export function buildBannerSvg() {
  const mascotSvg = buildMascotSvg();

  // Extract <defs> from mascotSvg
  const defsMatch = /<defs>([\s\S]*?)<\/defs>/.exec(mascotSvg);
  const mascotDefs = defsMatch ? defsMatch[1] : '';

  // Extract graphics elements from mascotSvg (everything between </defs> and </svg>, excluding the background rect)
  const bodyMatch = /<\/defs>[\s\S]*?<rect width="800" height="800" fill="#F8FAFC" rx="16"\/>([\s\S]*?)<\/svg>/.exec(mascotSvg);
  const mascotBody = bodyMatch ? bodyMatch[1] : '';

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 440" width="100%" height="440">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070A12"/>
      <stop offset="50%" stop-color="#0B0F19"/>
      <stop offset="100%" stop-color="#0D1527"/>
    </linearGradient>

    <!-- Text & Glow Gradients -->
    <linearGradient id="text-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="40%" stop-color="#F1F5F9"/>
      <stop offset="70%" stop-color="#C084FC"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>

    <linearGradient id="accent-cyan-purple" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#A855F7"/>
      <stop offset="50%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#34D399"/>
    </linearGradient>

    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="soft-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="40" result="blur"/>
    </filter>

    <!-- Circular clip for mascot frame -->
    <clipPath id="mascot-frame-clip">
      <circle cx="220" cy="220" r="160"/>
    </clipPath>

    <!-- Injected Vector Mascot Definitions -->
    ${mascotDefs}
  </defs>

  <!-- Deep Obsidian Background -->
  <rect width="1200" height="440" rx="16" fill="url(#bg-grad)"/>

  <!-- Ambient Light Orbs -->
  <circle cx="220" cy="220" r="190" fill="#38BDF8" opacity="0.15" filter="url(#soft-glow)"/>
  <circle cx="850" cy="180" r="240" fill="#9333EA" opacity="0.10" filter="url(#soft-glow)"/>

  <!-- Subtle Tech Grid Lines -->
  <g opacity="0.05" stroke="#FFFFFF" stroke-width="1">
    <line x1="0" y1="88" x2="1200" y2="88"/>
    <line x1="0" y1="176" x2="1200" y2="176"/>
    <line x1="0" y1="264" x2="1200" y2="264"/>
    <line x1="0" y1="352" x2="1200" y2="352"/>
    <line x1="460" y1="0" x2="460" y2="440"/>
    <line x1="780" y1="0" x2="780" y2="440"/>
    <line x1="1020" y1="0" x2="1020" y2="440"/>
  </g>

  <!-- ==================== LEFT: PURE VECTOR SVG MASCOT ==================== -->
  <g>
    <!-- Outer Glow Ring -->
    <circle cx="220" cy="220" r="170" fill="none" stroke="url(#accent-cyan-purple)" stroke-width="2.5" opacity="0.8" filter="url(#glow)"/>
    <circle cx="220" cy="220" r="176" fill="none" stroke="#38BDF8" stroke-width="1" opacity="0.4" stroke-dasharray="6,6"/>

    <!-- Circular Backdrop for Mascot -->
    <circle cx="220" cy="220" r="160" fill="#0C1222"/>

    <!-- Inlined Pure Vector Mascot Graphic (Centered at 220, 220) -->
    <g transform="translate(45, 45) scale(0.4375)" clip-path="url(#mascot-frame-clip-off)">
      ${mascotBody}
    </g>

    <!-- Star Ornaments on Ring -->
    <polygon points="220,40 223,47 230,50 223,53 220,60 217,53 210,50 217,47" fill="#38BDF8" filter="url(#glow)"/>
    <polygon points="220,400 223,407 230,410 223,413 220,420 217,413 210,410 217,407" fill="#A855F7" filter="url(#glow)"/>
    <polygon points="40,220 47,223 50,230 53,223 60,220 53,217 50,210 47,217" fill="#C084FC"/>
    <polygon points="400,220 407,223 410,230 413,223 420,220 413,217 410,210 407,217" fill="#38BDF8"/>
  </g>

  <!-- ==================== RIGHT: TYPOGRAPHY ==================== -->
  <g transform="translate(460, 85)">
    <!-- Top Pill Badge -->
    <rect x="0" y="0" width="280" height="28" rx="14" fill="#1E293B" stroke="#38BDF8" stroke-width="1.2" opacity="0.9"/>
    <circle cx="16" cy="14" r="4.5" fill="#38BDF8" filter="url(#glow)"/>
    <text x="30" y="19" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" font-weight="700" letter-spacing="1.2" fill="#E2E8F0">
      GOOGLE ANTIGRAVITY NATIVE
    </text>

    <!-- Main Project Name Heading -->
    <text x="0" y="92" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="68" font-weight="900" letter-spacing="-1.5" fill="url(#text-grad)">
      op-lead<tspan fill="url(#accent-cyan-purple)">-with-us</tspan>
    </text>

    <!-- Subtitle / Tagline -->
    <text x="2" y="132" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="600" fill="#94A3B8">
      Claude Opus 5.5 Plans · Gemini 3.8 Flash Executes · Zero Quota Anxiety
    </text>

    <!-- Minimalist Synth Keyboard & Wave Accent -->
    <g transform="translate(0, 160)">
      <!-- Keyboard Keys -->
      <g fill="#F8FAFC" opacity="0.85">
        <rect x="0" y="0" width="10" height="32" rx="2"/>
        <rect x="13" y="0" width="10" height="32" rx="2"/>
        <rect x="26" y="0" width="10" height="32" rx="2"/>
        <rect x="39" y="0" width="10" height="32" rx="2"/>
        <rect x="52" y="0" width="10" height="32" rx="2"/>
        <rect x="65" y="0" width="10" height="32" rx="2"/>
        <rect x="78" y="0" width="10" height="32" rx="2"/>
        <!-- Black keys -->
        <rect x="7" y="0" width="7" height="19" rx="1.5" fill="#0F172A"/>
        <rect x="20" y="0" width="7" height="19" rx="1.5" fill="#0F172A"/>
        <rect x="46" y="0" width="7" height="19" rx="1.5" fill="#0F172A"/>
        <rect x="59" y="0" width="7" height="19" rx="1.5" fill="#0F172A"/>
        <rect x="72" y="0" width="7" height="19" rx="1.5" fill="#0F172A"/>
      </g>
      <!-- Soundwave flowing from keys -->
      <path d="M 95,16 Q 160,-15 230,16 T 370,16 T 510,16 T 650,16" fill="none" stroke="url(#accent-cyan-purple)" stroke-width="3" stroke-linecap="round" filter="url(#glow)"/>
      <path d="M 95,16 Q 160,35 230,16 T 370,16 T 510,16 T 650,16" fill="none" stroke="#C084FC" stroke-width="1.5" stroke-dasharray="4,6" opacity="0.6"/>
      <text x="245" y="2" font-size="16" fill="#38BDF8" filter="url(#glow)">♪</text>
      <text x="395" y="30" font-size="14" fill="#C084FC" filter="url(#glow)">♫</text>
      <text x="540" y="5" font-size="15" fill="#34D399" filter="url(#glow)">#</text>
    </g>

    <!-- Bottom Feature Badges -->
    <g transform="translate(0, 225)">
      <rect x="0" y="0" width="180" height="34" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <text x="14" y="22" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="600" fill="#38BDF8">
        ⚡ 70%+ Opus Saved
      </text>

      <rect x="195" y="0" width="200" height="34" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <text x="210" y="22" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="600" fill="#C084FC">
        🔒 Pure Native Subagents
      </text>

      <rect x="410" y="0" width="170" height="34" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <text x="424" y="22" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="600" fill="#34D399">
        🚀 Zero External Setup
      </text>
    </g>
  </g>
</svg>
`;

  writeFileSync('assets/banner.svg', svg, 'utf8');
  console.log('Successfully built assets/banner.svg with PURE VECTOR mascot!');
}

if (process.argv[1] && process.argv[1].includes('build-banner')) {
  buildBannerSvg();
}
