import { writeFileSync } from 'node:fs';

export function buildMascotSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <defs>
    <!-- Filters -->
    <filter id="soft-ground-blur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="9" result="blur"/>
    </filter>

    <filter id="mask-depth-shadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="5" stdDeviation="4.5" flood-color="#1B2536" flood-opacity="0.38"/>
    </filter>

    <!-- Gradients for Octopus Volume -->
    <!-- Head Dome 3D Shading -->
    <radialGradient id="head-dome-grad" cx="44%" cy="30%" r="65%">
      <stop offset="0%" stop-color="#E8F6FF"/>
      <stop offset="30%" stop-color="#CAE9FD"/>
      <stop offset="68%" stop-color="#99D1F8"/>
      <stop offset="90%" stop-color="#73B6E8"/>
      <stop offset="100%" stop-color="#589BCE"/>
    </radialGradient>

    <!-- Lower Cheek & Underside Ambient Shadow -->
    <linearGradient id="head-ambient-shade" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#A2D7FC" stop-opacity="0"/>
      <stop offset="65%" stop-color="#7ABEF0" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#5296CC" stop-opacity="0.8"/>
    </linearGradient>

    <!-- High-Gloss Specular Highlight -->
    <linearGradient id="gloss-sheen" x1="0%" y1="0%" x2="80%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.9"/>
      <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>

    <!-- Tentacle Volumetric Gradients -->
    <radialGradient id="tentacle-cushion-center" cx="50%" cy="38%" r="55%">
      <stop offset="0%" stop-color="#E6F5FE"/>
      <stop offset="45%" stop-color="#B2E0FC"/>
      <stop offset="80%" stop-color="#80BFEE"/>
      <stop offset="100%" stop-color="#5B9ECD"/>
    </radialGradient>

    <radialGradient id="tentacle-cushion-left" cx="42%" cy="35%" r="55%">
      <stop offset="0%" stop-color="#E1F2FE"/>
      <stop offset="45%" stop-color="#A6DCFB"/>
      <stop offset="80%" stop-color="#73B4E7"/>
      <stop offset="100%" stop-color="#5192C5"/>
    </radialGradient>

    <radialGradient id="tentacle-cushion-right" cx="58%" cy="35%" r="55%">
      <stop offset="0%" stop-color="#E1F2FE"/>
      <stop offset="45%" stop-color="#A6DCFB"/>
      <stop offset="80%" stop-color="#73B4E7"/>
      <stop offset="100%" stop-color="#5192C5"/>
    </radialGradient>

    <!-- Ground Shadow Under Skirt -->
    <radialGradient id="ground-shadow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2D2847" stop-opacity="0.52"/>
      <stop offset="55%" stop-color="#463E6E" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#675E9C" stop-opacity="0"/>
    </radialGradient>

    <!-- Fine Damask & Fishnet Lace Pattern -->
    <pattern id="fine-lace-net" width="14" height="14" patternUnits="userSpaceOnUse">
      <!-- Dark semi-translucent tulle mesh foundation -->
      <rect width="14" height="14" fill="#121118" fill-opacity="0.91"/>
      <!-- Interlocking lace diagonals -->
      <path d="M 0,0 L 14,14 M 14,0 L 0,14" stroke="#2B293A" stroke-width="0.8" opacity="0.65"/>
      <!-- Delicate picot stitches -->
      <circle cx="7" cy="7" r="2" fill="#0A090E"/>
      <circle cx="7" cy="7" r="1.1" fill="#3D3A4F" opacity="0.45"/>
      <circle cx="0" cy="0" r="1.3" fill="#0A090E"/>
      <circle cx="14" cy="0" r="1.3" fill="#0A090E"/>
      <circle cx="0" cy="14" r="1.3" fill="#0A090E"/>
      <circle cx="14" cy="14" r="1.3" fill="#0A090E"/>
    </pattern>

    <!-- Satin Ribbon Shading -->
    <linearGradient id="satin-ribbon-grad" x1="0%" y1="0%" x2="100%" y2="85%">
      <stop offset="0%" stop-color="#28262E"/>
      <stop offset="25%" stop-color="#141318"/>
      <stop offset="55%" stop-color="#2C2A33"/>
      <stop offset="85%" stop-color="#121116"/>
      <stop offset="100%" stop-color="#09080B"/>
    </linearGradient>

    <linearGradient id="satin-sheen" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#69657A" stop-opacity="0.75"/>
      <stop offset="50%" stop-color="#454252" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#1A1920" stop-opacity="0"/>
    </linearGradient>

    <!-- Petal Rosette Gradients -->
    <radialGradient id="pink-petal-grad" cx="42%" cy="36%" r="62%">
      <stop offset="0%" stop-color="#F472B6"/>
      <stop offset="35%" stop-color="#E11D48"/>
      <stop offset="75%" stop-color="#9F1239"/>
      <stop offset="100%" stop-color="#4C0519"/>
    </radialGradient>
  </defs>

  <!-- ==================== BACKGROUND ==================== -->
  <rect width="800" height="800" fill="#F8FAFC" rx="16"/>

  <!-- ==================== 1. HERALDIC CREST CIRCULAR FRAME ==================== -->
  <g id="heraldic-frame">
    <!-- Star Sparkles in Corners (Diagonal Accents) -->
    <!-- Top-Left -->
    <g transform="translate(145, 145)">
      <path d="M 0,-24 Q 0,-4 18,0 Q 0,4 0,24 Q 0,4 -18,0 Q 0,-4 0,-24 Z" fill="#1C274C"/>
    </g>
    <!-- Top-Right -->
    <g transform="translate(655, 145)">
      <path d="M 0,-24 Q 0,-4 18,0 Q 0,4 0,24 Q 0,4 -18,0 Q 0,-4 0,-24 Z" fill="#1C274C"/>
    </g>
    <!-- Bottom-Left -->
    <g transform="translate(135, 615)">
      <path d="M 0,-22 Q 0,-3.5 16,0 Q 0,3.5 0,22 Q 0,3.5 -16,0 Q 0,-3.5 0,-22 Z" fill="#1C274C"/>
    </g>
    <!-- Bottom-Right -->
    <g transform="translate(665, 615)">
      <path d="M 0,-22 Q 0,-3.5 16,0 Q 0,3.5 0,22 Q 0,3.5 -16,0 Q 0,-3.5 0,-22 Z" fill="#1C274C"/>
    </g>

    <!-- Outer Solid Navy Circle -->
    <circle cx="400" cy="400" r="322" fill="none" stroke="#1C274C" stroke-width="5.5"/>

    <!-- Inner Dotted Decorative Ring -->
    <circle cx="400" cy="400" r="302" fill="none" stroke="#1C274C" stroke-width="3" stroke-dasharray="2, 9" stroke-linecap="round"/>

    <!-- Top Fleur-de-lis (Heraldic Crest at 12 o'clock) -->
    <g id="top-crest" transform="translate(400, 72) scale(0.92)">
      <!-- Central spear petal -->
      <path d="M 0,-48 C 8,-32 15,-16 12,0 C 7,8 2,13 0,15 C -2,13 -7,8 -12,0 C -15,-16 -8,-32 0,-48 Z" fill="#1C274C"/>
      <!-- Left side curl leaf -->
      <path d="M -3,5 C -13,4 -30,2 -34,-15 C -36,-26 -26,-32 -17,-26 C -7,-19 -7,-4 -2,7 Z" fill="#1C274C"/>
      <!-- Right side curl leaf -->
      <path d="M 3,5 C 13,4 30,2 34,-15 C 36,-26 26,-32 17,-26 C 7,-19 7,-4 2,7 Z" fill="#1C274C"/>
      <!-- Horizontal crossbar band -->
      <rect x="-20" y="11" width="40" height="7" rx="3.5" fill="#1C274C"/>
      <!-- Bottom pedestal base -->
      <path d="M -13,20 C -16,30 -8,35 0,36 C 8,35 16,30 13,20 Z" fill="#1C274C"/>
    </g>

    <!-- Bottom Inverted Fleur-de-lis (at 6 o'clock) -->
    <g id="bottom-crest" transform="translate(400, 728) scale(0.92) rotate(180)">
      <!-- Central spear petal -->
      <path d="M 0,-48 C 8,-32 15,-16 12,0 C 7,8 2,13 0,15 C -2,13 -7,8 -12,0 C -15,-16 -8,-32 0,-48 Z" fill="#1C274C"/>
      <!-- Left side curl leaf -->
      <path d="M -3,5 C -13,4 -30,2 -34,-15 C -36,-26 -26,-32 -17,-26 C -7,-19 -7,-4 -2,7 Z" fill="#1C274C"/>
      <!-- Right side curl leaf -->
      <path d="M 3,5 C 13,4 30,2 34,-15 C 36,-26 26,-32 17,-26 C 7,-19 7,-4 2,7 Z" fill="#1C274C"/>
      <!-- Horizontal crossbar band -->
      <rect x="-20" y="11" width="40" height="7" rx="3.5" fill="#1C274C"/>
      <!-- Bottom pedestal base -->
      <path d="M -13,20 C -16,30 -8,35 0,36 C 8,35 16,30 13,20 Z" fill="#1C274C"/>
    </g>
  </g>

  <!-- ==================== 2. SOFT GROUND SHADOW ==================== -->
  <ellipse cx="400" cy="638" rx="240" ry="28" fill="url(#ground-shadow)" filter="url(#soft-ground-blur)"/>

  <!-- ==================== 3. OCTOPUS CHARACTER ==================== -->
  <g id="octopus-character">
    <!-- Tentacles Under-Shadow Crease Backdrop -->
    <path d="M 185,555 
             C 145,585 155,635 195,648 
             C 235,660 260,638 275,612 
             C 295,650 340,660 380,652 
             C 415,660 460,650 480,612 
             C 495,638 520,660 560,648 
             C 600,635 610,585 570,555 
             Z" fill="#3B6991" opacity="0.38"/>

    <!-- Main Head Dome Body Base -->
    <path d="M 235,465 
             C 215,360 232,225 320,172 
             C 365,145 435,145 480,172 
             C 568,225 585,360 565,465 
             C 560,515 540,550 520,565 
             C 450,585 350,585 280,565 
             C 260,550 240,515 235,465 Z" 
          fill="url(#head-dome-grad)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Subtle Ambient Shading across Bottom Cheeks -->
    <path d="M 238,445 
             C 236,495 250,550 285,570 
             C 340,590 460,590 515,570 
             C 550,550 564,495 562,445 
             C 545,515 490,558 400,558 
             C 310,558 255,515 238,445 Z" 
          fill="url(#head-ambient-shade)"/>

    <!-- Puffy Bulbous Tentacles Skirt (5 Front Lobes) -->
    <!-- Tentacle 1 (Far Left Flared Out) -->
    <path d="M 248,535 
             C 218,535 172,558 162,605 
             C 152,646 195,666 230,655 
             C 265,645 280,608 275,578 
             C 270,554 258,540 248,535 Z" 
          fill="url(#tentacle-cushion-left)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 5 (Far Right Flared Out) -->
    <path d="M 552,535 
             C 582,535 628,558 638,605 
             C 648,646 605,666 570,655 
             C 535,645 520,608 525,578 
             C 530,554 542,540 552,535 Z" 
          fill="url(#tentacle-cushion-right)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 2 (Mid Left Puffy Cushion) -->
    <path d="M 268,570 
             C 255,586 250,622 272,652 
             C 292,678 338,678 358,646 
             C 372,622 368,586 348,570 
             C 322,560 292,560 268,570 Z" 
          fill="url(#tentacle-cushion-left)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 4 (Mid Right Puffy Cushion) -->
    <path d="M 532,570 
             C 545,586 550,622 528,652 
             C 508,678 462,678 442,646 
             C 428,622 432,586 452,570 
             C 478,560 508,560 532,570 Z" 
          fill="url(#tentacle-cushion-right)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Tentacle 3 (Center Chubby Lobe) -->
    <path d="M 335,575 
             C 330,605 336,640 362,664 
             C 388,680 412,680 438,664 
             C 464,640 470,605 465,575 
             C 440,565 360,565 335,575 Z" 
          fill="url(#tentacle-cushion-center)" stroke="#192843" stroke-width="5" stroke-linejoin="round"/>

    <!-- Crease Inset Shadows between Tentacles -->
    <path d="M 270,580 Q 264,612 272,632" stroke="#2B5275" stroke-width="3.5" fill="none" stroke-linecap="round"/>
    <path d="M 352,585 Q 346,622 358,648" stroke="#2B5275" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M 448,585 Q 454,622 442,648" stroke="#2B5275" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M 530,580 Q 536,612 528,632" stroke="#2B5275" stroke-width="3.5" fill="none" stroke-linecap="round"/>

    <!-- Glossy Curved Specular Highlights on Head -->
    <!-- Large Forehead Specular -->
    <ellipse cx="490" cy="215" rx="46" ry="28" transform="rotate(-26 490 215)" fill="url(#gloss-sheen)"/>
    <ellipse cx="510" cy="235" rx="16" ry="9" transform="rotate(-20 510 235)" fill="#FFFFFF" opacity="0.7"/>
    <!-- Secondary soft specular on Left Dome -->
    <ellipse cx="320" cy="225" rx="28" ry="16" transform="rotate(22 320 225)" fill="#FFFFFF" opacity="0.38"/>

    <!-- ==================== 4. DEADPAN FACE FEATURES ==================== -->
    <g id="deadpan-eyes">
      <!-- Left Eye (Deadpan / Half-Lidded) -->
      <g id="left-eye">
        <!-- White Sclera Substrate -->
        <path d="M 306,412 C 306,396 332,393 358,399 C 368,402 373,413 371,424 C 368,440 348,450 326,447 C 311,444 306,427 306,412 Z" fill="#E8F2FA"/>
        <!-- Dark Espresso / Charcoal Iris & Pupil -->
        <path d="M 308,407 C 322,402 349,402 366,406 C 370,418 364,436 350,443 C 331,446 316,439 311,429 C 308,419 307,411 308,407 Z" 
              fill="#181519" stroke="#0E0C0F" stroke-width="2.5"/>
        <!-- Eye Highlights -->
        <!-- Big top-right highlight pill -->
        <rect x="349" y="411" width="11" height="14" rx="4.5" fill="#FFFFFF"/>
        <!-- Small bottom-left highlight dot -->
        <circle cx="323" cy="433" r="2.8" fill="#FFFFFF" opacity="0.9"/>
      </g>

      <!-- Right Eye (Deadpan / Half-Lidded) -->
      <g id="right-eye">
        <!-- White Sclera Substrate -->
        <path d="M 432,399 C 458,393 484,396 484,412 C 484,427 479,444 464,447 C 442,450 422,440 419,424 C 417,413 422,402 432,399 Z" fill="#E8F2FA"/>
        <!-- Dark Espresso / Charcoal Iris & Pupil -->
        <path d="M 424,407 C 441,402 468,402 482,406 C 483,410 482,419 479,429 C 474,439 459,446 440,443 C 426,436 420,418 424,407 Z" 
              fill="#181519" stroke="#0E0C0F" stroke-width="2.5"/>
        <!-- Eye Highlights -->
        <!-- Big top-right highlight pill -->
        <rect x="466" y="411" width="11" height="14" rx="4.5" fill="#FFFFFF"/>
        <!-- Small bottom-left highlight dot -->
        <circle cx="439" cy="433" r="2.8" fill="#FFFFFF" opacity="0.9"/>
      </g>
    </g>

    <!-- Adorable Downturned Pout Frown Mouth -->
    <path d="M 385,453 C 392,443 408,443 415,453" 
          fill="none" stroke="#16253E" stroke-width="5.5" stroke-linecap="round"/>

    <!-- Soft Cheek Blush -->
    <ellipse cx="265" cy="458" rx="15" ry="8" fill="#F472B6" opacity="0.28"/>
    <ellipse cx="535" cy="458" rx="15" ry="8" fill="#F472B6" opacity="0.28"/>

    <!-- ==================== 5. INTRICATE BLACK LACE MASQUERADE MASK ==================== -->
    <g id="lace-masquerade-mask" filter="url(#mask-depth-shadow)">
      <!-- Master Mask Silhouette with Eye Holes using EvenOdd Rule -->
      <path d="
        /* Outer mask silhouette */
        M 215,362 
        C 220,336 242,305 278,292 
        C 318,276 358,294 388,322 
        C 394,328 400,330 406,328 
        C 436,294 476,276 516,292 
        C 552,305 574,336 579,362 
        C 586,398 576,448 550,478 
        C 528,504 494,508 464,478 
        C 444,458 424,435 400,435 
        C 376,435 356,458 336,478 
        C 306,508 272,504 250,478 
        C 224,448 214,398 215,362 Z 

        /* Left eye hole cutout */
        M 296,412 
        C 296,386 322,378 348,380 
        C 370,382 382,396 382,420 
        C 382,440 362,458 338,455 
        C 315,452 296,436 296,412 Z 

        /* Right eye hole cutout */
        M 418,420 
        C 418,396 430,382 452,380 
        C 478,378 504,386 504,412 
        C 504,436 485,452 462,455 
        C 438,458 418,440 418,420 Z
        " 
        fill="url(#fine-lace-net)" fill-rule="evenodd" stroke="#0E0D12" stroke-width="2.5"/>

      <!-- Center Forehead Medallion & Embroidery Filigree -->
      <path d="M 400,324 C 388,308 376,285 400,268 C 424,285 412,308 400,324 Z" fill="#0C0B0E" opacity="0.95"/>
      <circle cx="400" cy="292" r="4" fill="#3D3A4B"/>

      <!-- Left Brow Embroidery Scrolls & Leaf Motifs -->
      <path d="M 390,318 C 365,296 330,280 295,290 C 265,300 240,326 230,356" 
            fill="none" stroke="#0C0B0E" stroke-width="5.5" stroke-linecap="round"/>
      <path d="M 370,306 Q 348,284 318,290" fill="none" stroke="#282633" stroke-width="3"/>
      <path d="M 330,296 Q 298,274 268,290" fill="none" stroke="#0C0B0E" stroke-width="3.5"/>
      <circle cx="340" cy="290" r="3" fill="#282633"/>
      <circle cx="285" cy="288" r="3" fill="#282633"/>

      <!-- Right Brow Embroidery Scrolls & Leaf Motifs -->
      <path d="M 410,318 C 435,296 470,280 505,290 C 535,300 560,326 570,356" 
            fill="none" stroke="#0C0B0E" stroke-width="5.5" stroke-linecap="round"/>
      <path d="M 430,306 Q 452,284 482,290" fill="none" stroke="#282633" stroke-width="3"/>
      <path d="M 470,296 Q 502,274 532,290" fill="none" stroke="#0C0B0E" stroke-width="3.5"/>
      <circle cx="460" cy="290" r="3" fill="#282633"/>
      <circle cx="515" cy="288" r="3" fill="#282633"/>

      <!-- Delicate Scalloped Picot Edge along Upper Mask Rim -->
      <path d="
        M 220,352 
        Q 226,336 236,334 Q 246,322 256,316 Q 270,306 282,302 Q 296,293 312,292 
        Q 326,289 342,293 Q 356,299 372,310 Q 386,320 400,326 Q 414,320 428,310 
        Q 444,299 458,293 Q 474,289 488,292 Q 504,293 518,302 Q 530,306 544,316 
        Q 554,322 564,334 Q 574,336 580,352" 
        fill="none" stroke="#16151D" stroke-width="3.2" stroke-linecap="round"/>

      <!-- Delicate Scalloped Trim along Lower Rim -->
      <path d="
        M 230,422 
        Q 240,452 256,472 Q 276,498 302,498 Q 326,488 346,466 Q 366,446 386,436 
        Q 400,434 414,436 Q 434,446 454,466 Q 474,488 498,498 Q 524,498 544,472 
        Q 560,452 570,422" 
        fill="none" stroke="#16151D" stroke-width="3.5" stroke-linecap="round"/>

      <!-- Embroidered Border Framing the Eye Openings -->
      <!-- Left Eye Rim -->
      <path d="M 294,412 C 294,383 322,376 348,378 C 372,380 384,394 384,420 C 384,442 364,459 338,456 C 313,454 294,438 294,412 Z" 
            fill="none" stroke="#0E0D12" stroke-width="3.2"/>
      <!-- Right Eye Rim -->
      <path d="M 416,420 C 416,394 428,380 452,378 C 478,376 506,383 506,412 C 506,438 487,454 462,456 C 436,459 416,442 416,420 Z" 
            fill="none" stroke="#0E0D12" stroke-width="3.2"/>
    </g>

    <!-- ==================== 6. SATIN BOWS, CASCADING RIBBONS & PINK ROSETTES ==================== -->
    <!-- Left Side Temple Ornaments -->
    <g id="left-side-ornaments">
      <!-- Back Drooping Ribbon Tail -->
      <path d="M 215,382 
               C 178,412 142,462 132,535 
               C 126,566 158,550 178,512 
               C 194,482 208,432 218,396 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.2"/>
      <path d="M 138,525 Q 152,472 184,432" stroke="url(#satin-sheen)" stroke-width="3.2" fill="none"/>

      <!-- Front Cascading Fishtail Ribbon -->
      <path d="M 205,392 
               C 184,432 164,494 168,560 
               L 188,545 L 204,570 
               C 214,504 220,448 224,402 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.2"/>

      <!-- Upper Satin Bow Loop -->
      <path d="M 210,366 
               C 178,330 142,298 132,324 
               C 122,350 158,376 198,382 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.8"/>
      <path d="M 142,324 Q 164,346 194,366" stroke="url(#satin-sheen)" stroke-width="2.2" fill="none"/>

      <!-- Lower Bow Loop -->
      <path d="M 210,378 
               C 168,382 128,402 138,434 
               C 148,454 184,424 210,392 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.8"/>

      <!-- Pink Rosette (Left) -->
      <g id="left-rosette" transform="translate(205, 386)">
        <!-- Outer Magenta Petals -->
        <circle cx="0" cy="0" r="23" fill="#881337"/>
        <path d="M -20,-6 C -28,-17 -12,-28 0,-22 C 12,-28 28,-17 20,-6 C 28,6 22,24 9,22 C -4,24 -20,16 -20,-6 Z" 
              fill="url(#pink-petal-grad)" stroke="#4C0519" stroke-width="1.8"/>
        <!-- Mid-Layer Rose Petals -->
        <circle cx="0" cy="0" r="15" fill="#E11D48"/>
        <path d="M -9,-7 C -14,-14 -3,-18 4,-14 C 11,-9 11,5 4,9 C -3,14 -14,9 -9,-7 Z" fill="#FB7185"/>
        <!-- Dark Center Button -->
        <circle cx="0" cy="0" r="7.5" fill="#18151D"/>
        <circle cx="0" cy="0" r="5" fill="#0C0A0E"/>
        <circle cx="-1.5" cy="-1.5" r="1.6" fill="#FFFFFF" opacity="0.65"/>
      </g>
    </g>

    <!-- Right Side Temple Ornaments -->
    <g id="right-side-ornaments">
      <!-- Back Drooping Ribbon Tail -->
      <path d="M 585,382 
               C 622,412 658,462 668,535 
               C 674,566 642,550 622,512 
               C 606,482 592,432 582,396 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.2"/>
      <path d="M 662,525 Q 648,472 616,432" stroke="url(#satin-sheen)" stroke-width="3.2" fill="none"/>

      <!-- Front Cascading Fishtail Ribbon -->
      <path d="M 595,392 
               C 616,432 636,494 632,560 
               L 612,545 L 596,570 
               C 586,504 580,448 576,402 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.2"/>

      <!-- Upper Satin Bow Loop -->
      <path d="M 590,366 
               C 622,330 658,298 668,324 
               C 678,350 642,376 602,382 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.8"/>
      <path d="M 658,324 Q 636,346 606,366" stroke="url(#satin-sheen)" stroke-width="2.2" fill="none"/>

      <!-- Lower Bow Loop -->
      <path d="M 590,378 
               C 632,382 672,402 662,434 
               C 652,454 616,424 590,392 Z" 
            fill="url(#satin-ribbon-grad)" stroke="#0C0B0E" stroke-width="2.8"/>

      <!-- Pink Rosette (Right) -->
      <g id="right-rosette" transform="translate(595, 386)">
        <!-- Outer Magenta Petals -->
        <circle cx="0" cy="0" r="23" fill="#881337"/>
        <path d="M 20,-6 C 28,-17 12,-28 0,-22 C -12,-28 -28,-17 -20,-6 C -28,6 -22,24 -9,22 C 4,24 20,16 20,-6 Z" 
              fill="url(#pink-petal-grad)" stroke="#4C0519" stroke-width="1.8"/>
        <!-- Mid-Layer Rose Petals -->
        <circle cx="0" cy="0" r="15" fill="#E11D48"/>
        <path d="M 9,-7 C 14,-14 3,-18 -4,-14 C -11,-9 -11,5 -4,9 C 3,14 14,9 9,-7 Z" fill="#FB7185"/>
        <!-- Dark Center Button -->
        <circle cx="0" cy="0" r="7.5" fill="#18151D"/>
        <circle cx="0" cy="0" r="5" fill="#0C0A0E"/>
        <circle cx="-1.5" cy="-1.5" r="1.6" fill="#FFFFFF" opacity="0.65"/>
      </g>
    </g>
  </g>
</svg>
`;
}

writeFileSync('assets/mascot.svg', buildMascotSvg(), 'utf8');
console.log('Successfully generated assets/mascot.svg (pure vector)');
