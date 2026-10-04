import { writeFileSync } from 'node:fs';

export function buildMascotSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <defs>
    <!-- Soft 3D Lighting for Octopus Body -->
    <radialGradient id="octo-body-grad" cx="44%" cy="26%" r="68%">
      <stop offset="0%" stop-color="#EBF6FF"/>
      <stop offset="28%" stop-color="#C5E6FD"/>
      <stop offset="65%" stop-color="#93CDF6"/>
      <stop offset="88%" stop-color="#6EB0E4"/>
      <stop offset="100%" stop-color="#5599CF"/>
    </radialGradient>

    <!-- Lower Cheeks and Underside Shading -->
    <linearGradient id="octo-underside-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#93CDF6" stop-opacity="0"/>
      <stop offset="50%" stop-color="#6BAFE2" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#4B90C8" stop-opacity="0.7"/>
    </linearGradient>

    <!-- Glossy Forehead Specular Sheen -->
    <linearGradient id="forehead-sheen" x1="0%" y1="0%" x2="100%" y2="80%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.88"/>
      <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>

    <!-- Tentacle Cushion Lobes Gradients -->
    <radialGradient id="lobe-grad-center" cx="50%" cy="32%" r="58%">
      <stop offset="0%" stop-color="#EDF7FE"/>
      <stop offset="40%" stop-color="#B8E2FD"/>
      <stop offset="80%" stop-color="#7BB9EB"/>
      <stop offset="100%" stop-color="#599ACA"/>
    </radialGradient>

    <radialGradient id="lobe-grad-left" cx="42%" cy="30%" r="58%">
      <stop offset="0%" stop-color="#E8F4FE"/>
      <stop offset="40%" stop-color="#AEE0FC"/>
      <stop offset="80%" stop-color="#73B3E6"/>
      <stop offset="100%" stop-color="#5293C4"/>
    </radialGradient>

    <radialGradient id="lobe-grad-right" cx="58%" cy="30%" r="58%">
      <stop offset="0%" stop-color="#E8F4FE"/>
      <stop offset="40%" stop-color="#AEE0FC"/>
      <stop offset="80%" stop-color="#73B3E6"/>
      <stop offset="100%" stop-color="#5293C4"/>
    </radialGradient>

    <!-- Ground Shadow Underneath Tentacles -->
    <radialGradient id="ground-shadow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#30284D" stop-opacity="0.5"/>
      <stop offset="55%" stop-color="#4B4173" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#6F649B" stop-opacity="0"/>
    </radialGradient>

    <!-- Fine Diamond Mesh for Lace Mask -->
    <pattern id="lace-mesh" width="12" height="12" patternUnits="userSpaceOnUse">
      <rect width="12" height="12" fill="#111017" fill-opacity="0.94"/>
      <path d="M 0,0 L 12,12 M 12,0 L 0,12" stroke="#2D2B3D" stroke-width="0.75" opacity="0.6"/>
      <circle cx="6" cy="6" r="1.6" fill="#09080D"/>
      <circle cx="6" cy="6" r="0.9" fill="#3D3A50" opacity="0.45"/>
      <circle cx="0" cy="0" r="1.1" fill="#09080D"/>
      <circle cx="12" cy="0" r="1.1" fill="#09080D"/>
      <circle cx="0" cy="12" r="1.1" fill="#09080D"/>
      <circle cx="12" cy="12" r="1.1" fill="#09080D"/>
    </pattern>

    <!-- Satin Ribbon Linear Gradient -->
    <linearGradient id="ribbon-satin-grad" x1="0%" y1="0%" x2="100%" y2="85%">
      <stop offset="0%" stop-color="#2D2A34"/>
      <stop offset="25%" stop-color="#15141A"/>
      <stop offset="55%" stop-color="#2B2933"/>
      <stop offset="85%" stop-color="#121117"/>
      <stop offset="100%" stop-color="#08080B"/>
    </linearGradient>

    <linearGradient id="ribbon-sheen-line" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#6B667C" stop-opacity="0.75"/>
      <stop offset="50%" stop-color="#444152" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#1A1921" stop-opacity="0"/>
    </linearGradient>

    <!-- Rosette Camellia Petal Gradient -->
    <radialGradient id="camellia-petal-grad" cx="42%" cy="36%" r="62%">
      <stop offset="0%" stop-color="#F472B6"/>
      <stop offset="35%" stop-color="#E11D48"/>
      <stop offset="75%" stop-color="#9F1239"/>
      <stop offset="100%" stop-color="#4C0519"/>
    </radialGradient>
  </defs>

  <!-- BACKGROUND -->
  <rect width="800" height="800" fill="#F8FAFC" rx="16"/>

  <!-- ==================== 1. HERALDIC CREST CIRCULAR FRAME ==================== -->
  <g id="heraldic-frame">
    <!-- Star Sparkles in Four Diagonals -->
    <path d="M 145,121 Q 145,141 163,145 Q 145,149 145,169 Q 145,149 127,145 Q 145,141 145,121 Z" fill="#1C274C"/>
    <path d="M 655,121 Q 655,141 673,145 Q 655,149 655,169 Q 655,149 637,145 Q 655,141 655,121 Z" fill="#1C274C"/>
    <path d="M 135,593 Q 135,611.5 151,615 Q 135,618.5 135,637 Q 135,618.5 119,615 Q 135,611.5 135,593 Z" fill="#1C274C"/>
    <path d="M 665,593 Q 665,611.5 681,615 Q 665,618.5 665,637 Q 665,618.5 649,615 Q 665,611.5 665,593 Z" fill="#1C274C"/>

    <!-- Outer Solid Navy Ring -->
    <circle cx="400" cy="400" r="322" fill="none" stroke="#1C274C" stroke-width="5.5"/>

    <!-- Inner Dotted Decorative Ring -->
    <circle cx="400" cy="400" r="302" fill="none" stroke="#1C274C" stroke-width="3" stroke-dasharray="2, 9" stroke-linecap="round"/>

    <!-- Top Fleur-de-lis Emblem (at 12 o'clock) -->
    <g id="top-fleur" transform="translate(400, 72) scale(0.92)">
      <path d="M 0,-48 C 8,-32 15,-16 12,0 C 7,8 2,13 0,15 C -2,13 -7,8 -12,0 C -15,-16 -8,-32 0,-48 Z" fill="#1C274C"/>
      <path d="M -3,5 C -13,4 -30,2 -34,-15 C -36,-26 -26,-32 -17,-26 C -7,-19 -7,-4 -2,7 Z" fill="#1C274C"/>
      <path d="M 3,5 C 13,4 30,2 34,-15 C 36,-26 26,-32 17,-26 C 7,-19 7,-4 2,7 Z" fill="#1C274C"/>
      <rect x="-20" y="11" width="40" height="7" rx="3.5" fill="#1C274C"/>
      <path d="M -13,20 C -16,30 -8,35 0,36 C 8,35 16,30 13,20 Z" fill="#1C274C"/>
    </g>

    <!-- Bottom Inverted Fleur-de-lis Emblem (at 6 o'clock) -->
    <g id="bottom-fleur" transform="translate(400, 728) scale(0.92) rotate(180)">
      <path d="M 0,-48 C 8,-32 15,-16 12,0 C 7,8 2,13 0,15 C -2,13 -7,8 -12,0 C -15,-16 -8,-32 0,-48 Z" fill="#1C274C"/>
      <path d="M -3,5 C -13,4 -30,2 -34,-15 C -36,-26 -26,-32 -17,-26 C -7,-19 -7,-4 -2,7 Z" fill="#1C274C"/>
      <path d="M 3,5 C 13,4 30,2 34,-15 C 36,-26 26,-32 17,-26 C 7,-19 7,-4 2,7 Z" fill="#1C274C"/>
      <rect x="-20" y="11" width="40" height="7" rx="3.5" fill="#1C274C"/>
      <path d="M -13,20 C -16,30 -8,35 0,36 C 8,35 16,30 13,20 Z" fill="#1C274C"/>
    </g>
  </g>

  <!-- ==================== 2. SOFT GROUND SHADOW ==================== -->
  <ellipse cx="400" cy="640" rx="230" ry="24" fill="url(#ground-shadow)"/>

  <!-- ==================== 3. SQUISHY CUTE OCTOPUS BODY ==================== -->
  <g id="octopus-character">
    <!-- Tentacles Crease Base Silhouette -->
    <path d="M 160,555 C 130,585 140,635 180,646 C 220,658 245,635 260,612 C 280,650 325,658 365,650 C 400,658 445,650 465,612 C 480,635 505,658 545,646 C 585,635 595,585 565,555 Z" 
          fill="#35638A" opacity="0.32"/>

    <!-- Main Head Dome: Adorable, compact, rounded squishy dome! -->
    <!-- (Forehead apex at y=135, gently rounding out to cheeks at x=210 and x=590, y=420) -->
    <path d="M 235,505 
             C 215,445 208,340 215,260 
             C 220,205 255,165 320,142 
             C 365,128 435,128 480,142 
             C 545,165 580,205 585,260 
             C 592,340 585,445 565,505 
             C 545,550 515,568 475,568 
             C 435,568 365,568 325,568 
             C 285,568 255,550 235,505 Z" 
          fill="url(#octo-body-grad)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Lower Cheeks Shading -->
    <path d="M 225,430 
             C 222,485 240,540 280,560 
             C 340,580 460,580 520,560 
             C 560,540 578,485 575,430 
             C 560,495 505,540 400,540 
             C 295,540 240,495 225,430 Z" 
          fill="url(#octo-underside-grad)"/>

    <!-- Plump Cushion Tentacles (5 Wide Chubby Lobes resting on ground) -->
    <!-- Tentacle 1 (Far Left Flared Out Lobe) -->
    <path d="M 242,530 
             C 205,530 155,555 145,600 
             C 135,640 180,660 218,650 
             C 255,640 272,605 268,575 
             C 264,550 252,535 242,530 Z" 
          fill="url(#lobe-grad-left)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 5 (Far Right Flared Out Lobe) -->
    <path d="M 558,530 
             C 595,530 645,555 655,600 
             C 665,640 620,660 582,650 
             C 545,640 528,605 532,575 
             C 536,550 548,535 558,530 Z" 
          fill="url(#lobe-grad-right)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 2 (Mid Left Plump Cushion) -->
    <path d="M 258,565 
             C 245,582 242,618 262,648 
             C 285,675 330,675 352,644 
             C 368,618 362,582 342,565 
             C 315,555 282,555 258,565 Z" 
          fill="url(#lobe-grad-left)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 4 (Mid Right Plump Cushion) -->
    <path d="M 542,565 
             C 555,582 558,618 538,648 
             C 515,675 470,675 448,644 
             C 432,618 438,582 458,565 
             C 485,555 518,555 542,565 Z" 
          fill="url(#lobe-grad-right)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 3 (Center Big Mochi Cushion) -->
    <path d="M 330,570 
             C 325,600 332,638 358,662 
             C 384,678 416,678 442,662 
             C 468,638 475,600 470,570 
             C 445,560 355,560 330,570 Z" 
          fill="url(#lobe-grad-center)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Cleft Shading between Tentacles -->
    <path d="M 260,575 Q 252,608 260,628" stroke="#254B6E" stroke-width="3.5" fill="none" stroke-linecap="round"/>
    <path d="M 345,580 Q 338,618 350,644" stroke="#254B6E" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M 455,580 Q 462,618 450,644" stroke="#254B6E" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M 540,575 Q 548,608 540,628" stroke="#254B6E" stroke-width="3.5" fill="none" stroke-linecap="round"/>

    <!-- Cute Curved Forehead Glossy Highlight (Compact & Proportional!) -->
    <ellipse cx="485" cy="185" rx="38" ry="22" transform="rotate(-24 485 185)" fill="url(#forehead-sheen)"/>
    <ellipse cx="502" cy="200" rx="13" ry="7" transform="rotate(-20 502 200)" fill="#FFFFFF" opacity="0.65"/>
    <ellipse cx="325" cy="190" rx="22" ry="12" transform="rotate(22 325 190)" fill="#FFFFFF" opacity="0.32"/>

    <!-- ==================== 4. EXPRESSIVE DEADPAN FACE ==================== -->
    <g id="deadpan-eyes">
      <!-- Left Eye (Large, Wide, Charming Half-Lidded Expression!) -->
      <g id="left-eye">
        <!-- White Sclera Substrate -->
        <path d="M 292,395 C 292,374 322,370 358,378 C 372,382 378,396 376,410 C 372,430 348,442 320,438 C 300,435 292,415 292,395 Z" fill="#E8F2FA"/>
        <!-- Big Dark Espresso Iris / Pupil (Deadpan Top Cut) -->
        <path d="M 295,388 C 314,381 350,381 372,386 C 376,402 368,426 350,434 C 326,438 306,430 300,416 C 295,404 294,394 295,388 Z" 
              fill="#181519" stroke="#0E0C0F" stroke-width="2.5"/>
        <!-- Big Crisp White Top-Right Specular Pill -->
        <rect x="350" y="392" width="14" height="18" rx="6" fill="#FFFFFF"/>
        <!-- Small Secondary Glow at Bottom-Left -->
        <circle cx="316" cy="420" r="3.2" fill="#FFFFFF" opacity="0.85"/>
      </g>

      <!-- Right Eye (Large, Wide, Charming Half-Lidded Expression!) -->
      <g id="right-eye">
        <!-- White Sclera Substrate -->
        <path d="M 424,378 C 460,370 490,374 490,395 C 490,415 482,435 462,438 C 434,442 410,430 406,410 C 404,396 410,382 424,378 Z" fill="#E8F2FA"/>
        <!-- Big Dark Espresso Iris / Pupil (Deadpan Top Cut) -->
        <path d="M 410,386 C 432,381 468,381 487,388 C 488,394 487,404 482,416 C 476,430 456,438 432,434 C 414,426 406,402 410,386 Z" 
              fill="#181519" stroke="#0E0C0F" stroke-width="2.5"/>
        <!-- Big Crisp White Top-Right Specular Pill -->
        <rect x="466" y="392" width="14" height="18" rx="6" fill="#FFFFFF"/>
        <!-- Small Secondary Glow at Bottom-Left -->
        <circle cx="432" cy="420" r="3.2" fill="#FFFFFF" opacity="0.85"/>
      </g>
    </g>

    <!-- Sweet Downturned Pout Mouth (Directly under eyes at center x=400, y=435) -->
    <path d="M 384,438 C 392,427 408,427 416,438" 
          fill="none" stroke="#16253E" stroke-width="5.5" stroke-linecap="round"/>

    <!-- Soft Rosy Blush on Cheeks -->
    <ellipse cx="255" cy="440" rx="16" ry="8.5" fill="#F472B6" opacity="0.28"/>
    <ellipse cx="545" cy="440" rx="16" ry="8.5" fill="#F472B6" opacity="0.28"/>

    <!-- ==================== 5. INTRICATE BLACK LACE MASQUERADE MASK ==================== -->
    <!-- Proportional height from y=245 (peaks) down to y=450 (cheek dip), centering the eyes -->
    <g id="lace-masquerade-mask">
      <!-- Mask Drop Shadow on Skin -->
      <path d="M 215,315 
               C 220,285 245,255 285,248 
               C 328,240 368,260 400,284 
               C 432,260 472,240 515,248 
               C 555,255 580,285 585,315 
               C 592,365 585,420 560,455 
               C 538,485 500,488 470,458 
               C 448,438 426,416 400,416 
               C 374,416 352,438 330,458 
               C 300,488 262,485 240,455 
               C 215,420 208,365 215,315 Z" 
            fill="#1B2536" opacity="0.35"/>

      <!-- Solid Foundation Mask Layer (with Eye Cutouts using EvenOdd Rule) -->
      <path d="
        M 215,310 
        C 220,280 245,250 285,243 
        C 328,235 368,255 400,279 
        C 432,255 472,235 515,243 
        C 555,250 580,280 585,310 
        C 592,360 585,415 560,450 
        C 538,480 500,483 470,453 
        C 448,433 426,411 400,411 
        C 374,411 352,433 330,453 
        C 300,483 262,480 240,450 
        C 215,415 208,360 215,310 Z 
        M 285,395 
        C 285,368 315,360 345,362 
        C 372,364 385,380 385,406 
        C 385,430 362,450 335,446 
        C 308,443 285,424 285,395 Z 
        M 415,406 
        C 415,380 428,364 455,362 
        C 485,360 515,368 515,395 
        C 515,424 492,443 465,446 
        C 438,450 415,430 415,406 Z
        " 
        fill="#121118" fill-opacity="0.92" fill-rule="evenodd" stroke="#0C0B0E" stroke-width="2.5"/>

      <!-- Fine Diamond Mesh Texture Overlay -->
      <path d="
        M 215,310 
        C 220,280 245,250 285,243 
        C 328,235 368,255 400,279 
        C 432,255 472,235 515,243 
        C 555,250 580,280 585,310 
        C 592,360 585,415 560,450 
        C 538,480 500,483 470,453 
        C 448,433 426,411 400,411 
        C 374,411 352,433 330,453 
        C 300,483 262,480 240,450 
        C 215,415 208,360 215,310 Z 
        M 285,395 C 285,368 315,360 345,362 C 372,364 385,380 385,406 C 385,430 362,450 335,446 C 308,443 285,424 285,395 Z 
        M 415,406 C 415,380 428,364 455,362 C 485,360 515,368 515,395 C 515,424 492,443 465,446 C 438,450 415,430 415,406 Z
        " 
        fill="url(#lace-mesh)" fill-rule="evenodd"/>

      <!-- Center Forehead Medallion & Baroque Embroidery -->
      <path d="M 400,280 C 388,262 376,236 400,218 C 424,236 412,262 400,280 Z" fill="#0A090C"/>
      <circle cx="400" cy="245" r="4.5" fill="#3D3A4B"/>

      <!-- Left Brow Embroidery Scrolls & Leaf Motifs -->
      <path d="M 390,272 C 362,250 325,232 285,242 C 255,252 232,278 222,308" 
            fill="none" stroke="#0A090C" stroke-width="5" stroke-linecap="round"/>
      <path d="M 368,260 Q 344,236 312,242" fill="none" stroke="#2B2836" stroke-width="3"/>
      <path d="M 325,248 Q 292,224 262,242" fill="none" stroke="#0A090C" stroke-width="3.5"/>
      <circle cx="335" cy="242" r="3" fill="#2B2836"/>
      <circle cx="278" cy="238" r="3" fill="#2B2836"/>

      <!-- Right Brow Embroidery Scrolls & Leaf Motifs -->
      <path d="M 410,272 C 438,250 475,232 515,242 C 545,252 568,278 578,308" 
            fill="none" stroke="#0A090C" stroke-width="5" stroke-linecap="round"/>
      <path d="M 432,260 Q 456,236 488,242" fill="none" stroke="#2B2836" stroke-width="3"/>
      <path d="M 475,248 Q 508,224 538,242" fill="none" stroke="#0A090C" stroke-width="3.5"/>
      <circle cx="465" cy="242" r="3" fill="#2B2836"/>
      <circle cx="522" cy="238" r="3" fill="#2B2836"/>

      <!-- Delicate Scalloped Picot Edge along Upper Mask Rim -->
      <path d="
        M 218,305 
        Q 224,288 235,285 Q 246,272 258,266 Q 272,255 286,252 Q 302,244 320,243 
        Q 336,242 352,248 Q 368,256 384,268 Q 394,275 400,280 Q 406,275 416,268 
        Q 432,256 448,248 Q 464,242 480,243 Q 498,244 514,252 Q 528,255 542,266 
        Q 554,272 565,285 Q 576,288 582,305" 
        fill="none" stroke="#181620" stroke-width="3.2" stroke-linecap="round"/>

      <!-- Delicate Scalloped Trim along Lower Rim -->
      <path d="
        M 226,395 
        Q 235,425 250,446 Q 270,474 298,474 Q 322,462 342,440 Q 364,420 384,410 
        Q 400,408 416,410 Q 436,420 458,440 Q 478,462 502,474 Q 530,474 550,446 
        Q 565,425 574,395" 
        fill="none" stroke="#181620" stroke-width="3.5" stroke-linecap="round"/>

      <!-- Embroidered Border Framing the Eye Openings -->
      <!-- Left Eye Rim -->
      <path d="M 283,395 C 283,365 315,357 345,360 C 373,362 387,378 387,406 C 387,432 364,452 335,448 C 306,445 283,426 283,395 Z" 
            fill="none" stroke="#0A090C" stroke-width="3.2"/>
      <!-- Right Eye Rim -->
      <path d="M 413,406 C 413,378 427,362 455,360 C 485,357 517,365 517,395 C 517,426 494,445 465,448 C 436,452 413,432 413,406 Z" 
            fill="none" stroke="#0A090C" stroke-width="3.2"/>
    </g>

    <!-- ==================== 6. SATIN BOWS & CASCADING RIBBONS & ROSSETTES ==================== -->
    <!-- Left Side Temple Ornaments -->
    <g id="left-side-ornaments">
      <!-- Back Drooping Ribbon Tail -->
      <path d="M 215,350 
               C 178,382 142,435 132,510 
               C 126,542 158,525 178,485 
               C 194,455 208,405 218,368 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.2"/>
      <path d="M 138,500 Q 152,448 184,408" stroke="url(#ribbon-sheen-line)" stroke-width="3" fill="none"/>

      <!-- Front Cascading Fishtail Ribbon -->
      <path d="M 205,360 
               C 184,402 164,468 168,535 
               L 188,520 L 204,545 
               C 214,478 220,422 224,375 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.2"/>

      <!-- Upper Satin Bow Loop -->
      <path d="M 210,336 
               C 178,298 142,268 132,294 
               C 122,320 158,348 198,354 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.8"/>
      <path d="M 142,294 Q 164,316 194,336" stroke="url(#ribbon-sheen-line)" stroke-width="2.2" fill="none"/>

      <!-- Lower Bow Loop -->
      <path d="M 210,348 
               C 168,352 128,374 138,406 
               C 148,426 184,396 210,364 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.8"/>

      <!-- Pink Camellia Rosette (Left) -->
      <g id="left-rosette" transform="translate(205, 356)">
        <circle cx="0" cy="0" r="24" fill="#881337"/>
        <path d="M -21,-6 C -29,-18 -13,-30 0,-23 C 13,-30 29,-18 21,-6 C 29,6 23,25 10,23 C -4,25 -21,17 -21,-6 Z" 
              fill="url(#camellia-petal-grad)" stroke="#4C0519" stroke-width="1.8"/>
        <circle cx="0" cy="0" r="16" fill="#E11D48"/>
        <path d="M -10,-8 C -15,-15 -3,-19 4,-15 C 12,-10 12,5 4,10 C -3,15 -15,10 -10,-8 Z" fill="#FB7185"/>
        <circle cx="0" cy="0" r="8" fill="#18151D"/>
        <circle cx="0" cy="0" r="5" fill="#0A080C"/>
        <circle cx="-1.6" cy="-1.6" r="1.6" fill="#FFFFFF" opacity="0.7"/>
      </g>
    </g>

    <!-- Right Side Temple Ornaments -->
    <g id="right-side-ornaments">
      <!-- Back Drooping Ribbon Tail -->
      <path d="M 585,350 
               C 622,382 658,435 668,510 
               C 674,542 642,525 622,485 
               C 606,455 592,405 582,368 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.2"/>
      <path d="M 662,500 Q 648,448 616,408" stroke="url(#ribbon-sheen-line)" stroke-width="3" fill="none"/>

      <!-- Front Cascading Fishtail Ribbon -->
      <path d="M 595,360 
               C 616,402 636,468 632,535 
               L 612,520 L 596,545 
               C 586,478 580,422 576,375 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.2"/>

      <!-- Upper Satin Bow Loop -->
      <path d="M 590,336 
               C 622,298 658,268 668,294 
               C 678,320 642,348 602,354 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.8"/>
      <path d="M 658,294 Q 636,316 606,336" stroke="url(#ribbon-sheen-line)" stroke-width="2.2" fill="none"/>

      <!-- Lower Bow Loop -->
      <path d="M 590,348 
               C 632,352 672,374 662,406 
               C 652,426 616,396 590,364 Z" 
            fill="url(#ribbon-satin-grad)" stroke="#0A090D" stroke-width="2.8"/>

      <!-- Pink Camellia Rosette (Right) -->
      <g id="right-rosette" transform="translate(595, 356)">
        <circle cx="0" cy="0" r="24" fill="#881337"/>
        <path d="M 21,-6 C 29,-18 13,-30 0,-23 C -13,-30 -29,-18 -21,-6 C -29,6 -23,25 -10,23 C 4,25 21,17 21,-6 Z" 
              fill="url(#camellia-petal-grad)" stroke="#4C0519" stroke-width="1.8"/>
        <circle cx="0" cy="0" r="16" fill="#E11D48"/>
        <path d="M 10,-8 C 15,-15 3,-19 -4,-15 C -12,-10 -12,5 -4,10 C 3,15 15,10 10,-8 Z" fill="#FB7185"/>
        <circle cx="0" cy="0" r="8" fill="#18151D"/>
        <circle cx="0" cy="0" r="5" fill="#0A080C"/>
        <circle cx="-1.6" cy="-1.6" r="1.6" fill="#FFFFFF" opacity="0.7"/>
      </g>
    </g>
  </g>
</svg>
`;
}

writeFileSync('assets/mascot.svg', buildMascotSvg(), 'utf8');
console.log('Successfully regenerated assets/mascot.svg (cute chibi proportions)');
