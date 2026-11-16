# Google Flow — 50-Page Coloring Book Master Prompt v2
# UNIFIED STYLE — HIGH CONSISTENCY

---

## STRATEGY (اقرأ الأول)

المشكلة: Flow بيولّد كل صورة بأسلوب مختلف.
الحل: خطوتين —
1. ولّد صفحة واحدة أول (Page 1) واعتمد على نتيجتها كـ style reference
2. ابعت الـ 49 الباقيين مع reference_image من Page 1

---

## STEP 1 — Generate the STYLE MASTER (Page 1 only)

Paste this into Claude (with flow-mcp connected):

```
Generate ONE still image in Google Flow. This is the style master for a 50-page coloring book.

PROMPT:
"A coloring book page in the style of Dover Publications adult coloring books. 
Cozy cottage canopy bedroom interior. 
Pure flat black ink outlines only, no gray, no color, no shading, no gradients, no shadows. 
White background, no fill on any shape. 
Bold uniform 5pt black outlines, round stroke caps, all lines same weight. 
Simple clean vector-like line art. 
Beginner-friendly large regions to color. 
Four-poster canopy bed with draped curtains, pillows, bedside lamp, window with curtains, potted plant, oval rug. 
Square 1:1 ratio. 
No text. No watermark. No frame border."

Save this as my style reference. I will use it for all 49 remaining pages.
```

**بعد ما تاخد الصورة:**
- احفظ الـ asset ID أو title بتاعها (هيكون اسمها مثلاً "Page 1 — Canopy Bedroom")
- هنبعتها كـ `references` في الـ batch اللي بعدكده

---

## STEP 2 — Batch all 50 pages with style lock

Paste this into Claude AFTER you have Page 1's asset ID:

```
Generate 50 still images in Google Flow using flow_agent_images.
Collect into a Flow collection called "Cozy Coloring Book Vol.1".

CRITICAL STYLE RULES (apply to every single scene — never deviate):
- Dover Publications adult coloring book style
- Pure flat black outlines ONLY — no gray, no color, no shading, no gradients, no shadows, no cross-hatching
- Completely white background — no texture, no tone, no paper grain
- Bold uniform 5pt black strokes, same weight on every line, rounded caps
- Clean vector-like line art — no sketchy marks, no loose strokes
- Large simple regions between lines — beginner-friendly coloring spaces
- Simple 2D illustration — slight 3/4 isometric view or straight frontal view
- Cozy cottagecore hygge mood
- Square 1:1 ratio, centered composition, full page
- Absolutely NO text, NO watermark, NO title, NO frame, NO border
- NO photography style, NO realistic rendering, NO painterly texture

Use asset "Page 1 — Canopy Bedroom" as references for ALL 50 scenes to lock the visual style.

SCENE 1: Cozy cottage canopy bedroom — four-poster bed with draped curtains, fluffy pillows, bedside table with round lamp, tall window with flowy curtains and flower box outside, single potted plant on stand, decorative oval rug on wooden floor

SCENE 2: Living room stone fireplace — wide stone fireplace with crackling flame lines, wooden mantel with three candles and flower vase, two plump armchairs with throw blankets draped over, low oval coffee table with single teacup, cozy striped rug, hanging lantern above

SCENE 3: Window seat reading nook — wide bay window with built-in cushioned bench, three stacked throw pillows, tall bookshelves built into wall on each side filled with books, two hanging potted plants, open book resting on bench seat, curtains framing window on each side

SCENE 4: Country cottage kitchen — farmhouse apron sink centered under window, three potted herbs on windowsill, open wooden wall shelves with stacked plates, cups, and jars, two hanging pots above, small round table with two chairs, braided oval rug on floor

SCENE 5: Coffee corner — wooden wall shelf with drip coffee machine, row of five mugs hanging on hooks below shelf, small round café table with one stool, chalkboard on wall behind, single tall potted plant in corner, pendant lamp above table

SCENE 6: Home office with plants — wooden writing desk with open notebook and pen holder, arched window with climbing leafy vine, tall bookshelf beside desk packed with books, vintage desk lamp on corner, three small potted plants on desk surface, cozy armchair with cushion nearby

SCENE 7: Clawfoot bathtub bathroom — elegant clawfoot tub centered in room, vintage faucet and handles, window with sheer curtains and three candles on sill, wooden bath tray resting across tub with open book and tea mug, wall shelf with rolled towels and small plant, oval mirror on wall

SCENE 8: Attic bedroom under sloped ceiling — low angled beam ceiling, single dormer window with cushioned window seat, cozy bed with patchwork quilt and pillows, single hanging lantern from beam, stack of three books on floor, small plant on windowsill

SCENE 9: Garden conservatory — wicker two-seat sofa with round cushions, four large terracotta pots with tall leafy plants, curved glass ceiling with climbing vines, watering can on floor, wooden potting bench on side, three hanging baskets, small birdcage on stand

SCENE 10: Tiny log cabin interior — cast iron wood-burning stove with pipe going up, single multipaned window showing pine trees outside, wooden bunk bed with ladder, three shelves on wall with jars and lanterns, braided round rug, pair of boots beside front door

SCENE 11: Cottage dining room — round pedestal table with four ladder-back chairs, centerpiece with wildflower vase, tall hutch displaying stacked dishes and decorative jars, window with gingham curtains, two candles in holders on table, patterned floor rug

SCENE 12: Afternoon tea table — small round table with lace tablecloth, ceramic teapot with three cups and saucers, three-tier cake stand with pastries and macarons, cozy upholstered armchair, side table with fresh flower vase, single framed botanical print on wall

SCENE 13: Floor-to-ceiling library — towering bookshelves filling both side walls packed with books, long rolling wooden library ladder on track, deep leather reading armchair with open book, tall floor lamp beside chair, globe on side table, three stacks of books on floor

SCENE 14: Craft and sewing room — sewing machine on worktable with fabric piece under needle, four bolts of fabric on wall shelves, basket of yarn balls with knitting needles on floor, pegboard with thread spools and scissors, glass jar with buttons, wooden stool at table

SCENE 15: Cozy mudroom entry — five wooden coat hooks on wall with two hanging coats and scarves, long wooden bench with striped cushion, four pairs of boots lined up below bench, basket of umbrellas in corner, single plant on shelf, iron lantern beside front door, woven floor mat

SCENE 16: Farmhouse kitchen island — large rectangular island with three bar stools, apron farmhouse sink on wall, open shelves above with ceramic bowls and pitchers, four hanging copper pots above island, wooden cutting board with bread loaf on island, window over sink

SCENE 17: Breakfast nook bay window — U-shaped built-in bench seating with plaid cushions around square table, single tall window with morning light, stack of books on bench corner, ceramic coffee mug and croissant on table, four potted herbs in row on windowsill

SCENE 18: Cozy nursery — round crib with ruffled canopy overhead, wooden rocking horse beside crib, wall shelf with five stuffed animals, mobile with five stars and moons hanging above crib, cozy nursing rocking chair with footrest pillow, single framed botanical print on wall, soft round rug

SCENE 19: Sunlit artist studio — tall wooden easel with canvas, long shelf with art supply jars, palette and brushes on stool, tall arched window with morning light bars, rolled canvases leaning in corner, three potted plants, unfinished painting on easel

SCENE 20: Potting shed interior — wooden workbench with seedling pots and trowel, pegboard with hanging tools, wooden display of seed packet envelopes, watering can on floor, two bags of soil stacked, basket of harvested vegetables, green climbing vines on glass panes, terracotta pots on floor

SCENE 21: Pantry with preserves — five shelves floor to ceiling lined with labeled mason jars, large basket of onions and garlic on bottom shelf, three bundles of dried herbs hanging from ceiling hook, small wooden step ladder, lantern on middle shelf, braided rug on floor, wooden crate of apples

SCENE 22: Herb-drying kitchen corner — six bundles of dried lavender rosemary and chamomile hanging from ceiling wooden rack, wooden counter with mortar and pestle, six small spice jars in row, open recipe book on stand, ceramic pitcher, three potted herbs in terracotta pots on windowsill

SCENE 23: Loft sleeping nook — very low ceiling loft space with mattress and cozy bedding, string lights along the sloped ceiling, small stack of four books, round floor pillow, wooden ladder leading up to loft, simple wooden railing at edge, single small lantern

SCENE 24: Treehouse room — circular room inside a hollow tree trunk, curved wooden walls, single large circular window looking into leafy tree canopy, hammock strung between two hooks, wooden wall shelf with binoculars and pinecones, rope ladder coming up through floor hatch, leaves visible outside window

SCENE 25: Floral cottage bathroom — white pedestal sink with ornate oval mirror above, wall shelf with three candles and two small vases, clawfoot tub with floral shower curtain, botanical hexagonal tile on floor, fluffy towels on wall rack, climbing rose vine on one wall

SCENE 26: Candlelit reading corner — deep overstuffed armchair with side table, tall floor lamp with round shade, stack of five well-read books on side table, four candles in various holders on table and floor, wool throw blanket draped over chair arm, small round rug under chair, single framed quote on wall

SCENE 27: Autumn living room — fireplace with three pumpkins and gourds arranged on hearth, wooden bowl of apples on low coffee table, autumn leaf wreath on wall above mantel, cozy sofa with two plaid blankets and three pillows, dried wheat bundle in tall vase, four candles on mantel, autumn leaves on rug

SCENE 28: Winter bedroom with snow view — bed with two heavy quilts layered and many pillows, tall window showing snow-covered evergreen trees outside, oil lamp on bedside table, pair of wool socks on floor, thick rug, pine cone wreath on wall, single candle on windowsill

SCENE 29: Spring sunroom — wicker chaise lounge with floral cushion, four tall windows showing garden outside, three pots of blooming tulips and daffodils, fresh flower bouquet in vase, watering can leaning on wall, small bird on branch outside window, light linen curtains gently billowing

SCENE 30: Summer front porch — wooden rocking chair with cushion, porch swing with two pillows hanging from ceiling, three flower boxes overflowing with blooms on porch railing, hanging fern basket, pitcher of lemonade with glasses on side table, birdhouse on post, iron lantern, braided welcome mat

SCENE 31: Stone inglenook cottage — low ceiling with stone arch framing the room, wide inglenook fireplace built deep into thick stone wall, wooden settle bench inside inglenook, single oil lamp on mantel, flagstone floor with round rug, dried flowers in stoneware jug on hearth, heavy wooden beams above

SCENE 32: Hobbit hole interior — large round front door with big round iron handle and four bolt decorations, curved earthen walls with two round porthole windows, two low mushroom-shaped wooden stools, round table with single candle, two shelves carved directly into wall, cozy bed alcove behind round arch, iron lantern hanging from ceiling

SCENE 33: Witch's cottage workroom — five shelves of glass jars with herbs and powders, old leather-bound spell book open on wooden stand, small brass cauldron on three legs, six bundles of dried herbs and flowers hanging from ceiling, mortar and pestle on table, three candles in holders, sleeping black cat on chair, moonlit arched window

SCENE 34: Glamping tent interior — canvas bell tent with rolled-up side entrance, cozy bed with plush duvet pillows and throw, Persian patterned rug on floor, wooden side table with iron lantern, macramé wall hanging, single potted succulent, string of fairy lights along tent ceiling seam, pine forest visible through entrance

SCENE 35: Cozy bookshop corner — overstuffed velvet armchair, bookshelves floor to ceiling on three surrounding walls all full, wooden rolling library ladder, stack of four books on floor beside chair, sleeping cat curled on pile of books on stool, ceramic teacup on small side table, single hanging lamp above chair

SCENE 36: Cozy café nook — small round marble-top table with two café chairs, chalkboard menu on wall with simple chalk writing lines, glass pastry dome on counter with pastries, two hanging round pendant lamps, window with small flower box outside, tall potted plant in corner, hexagonal black-and-white floor tiles

SCENE 37: Mushroom cottage interior — curved rounded walls that echo mushroom cap shapes, two small round porthole windows, two mushroom-cap shaped stools at tiny round table with single candle, wall shelf with tiny jars, single hanging lantern, patchwork cushions, small fern in terracotta pot, mushrooms growing outside window in meadow

SCENE 38: Under-stair reading nook — triangular space under staircase with built-in shelves filling the slanted wall, low built-in cushioned reading bench at floor level, four throw pillows, books filling every shelf, small reading lamp on bracket, single potted trailing plant at arch entrance, cozy arched opening

SCENE 39: Vanity and dressing corner — ornate dressing table with round mirror framed in carved wood, six perfume bottles and single flower vase on tabletop, velvet button-top stool, clothing rack with three hanging dresses, tall oval standing mirror on floor, small jewelry box open on table, potted plant, soft round rug

SCENE 40: Zen meditation room — single large floor cushion on square tatami mat, low wooden altar with single lit candle and small bonsai plant, tall bamboo stalks in simple ceramic vase, shoji screen casting grid light pattern on wall, five smooth river stones in row, single incense holder with curling smoke, plain hanging scroll on wall

SCENE 41: Music room corner — upright piano with sheet music open on stand, wooden piano bench, violin in open velvet-lined case on nearby chair, wooden music stand with sheet, four shelves of music books, single window with curtains, tall house plant beside piano, single candle in holder on piano top

SCENE 42: Cottage guest room — single bed with floral patchwork quilt and two pillows, window with cushioned seat, small wooden dresser with single flower vase on top, oval mirror on wall above dresser, braided round rug, bedside lantern on small table, botanical framed print on wall, fresh folded towel on bed corner

SCENE 43: Leather armchair study by fireplace — large leather armchair angled toward stone fireplace, side table with one glass and open book, ornate fireplace with mantel clock, two tall candles, and one framed picture above, floor-to-ceiling bookshelves on both sides of fireplace, globe on a wooden stand in corner, Persian rug

SCENE 44: Kitchen with herb ceiling rack — herbs hanging in bundles from an overhead horizontal wooden rack with hooks, hand-painted floral tile backsplash, open wall shelves with colorful crockery and ceramic jugs, wooden farmhouse table with fresh bread loaf and cutting board, ceramic teapot, small window, wicker basket of vegetables on floor

SCENE 45: Barn loft conversion — very high ceiling with original heavy timber frame beams and rafters, oversized industrial-style steel-frame window letting in light, cozy sofa with plaid throw blanket and three pillows, wooden coffee table with single candle, standing floor lamp, exposed brick wall behind sofa, single cast iron radiator, large terracotta pot with tall plant

SCENE 46: Fairy tale cottage staircase room — curved staircase with twisted vine banister, two arched doorways framed with climbing flower vines, three tiny windows in unexpected places at different heights, small mushrooms growing in floor corner, four hanging lanterns at different heights from ceiling, cozy curtained reading nook behind draped fabric, magical whimsical atmosphere

SCENE 47: Japanese cozy room — low platform bed on woven tatami mat, shoji screen door with grid pattern, single ikebana flower arrangement in alcove niche, paper lantern hanging from ceiling, small bonsai on windowsill, two zabuton floor cushions around low wooden table, simple hanging scroll with brushstroke art, clean minimal composition

SCENE 48: Cozy attic studio — angled skylight window directly above writing desk, comfortable reading armchair under lowest sloped ceiling section, three stacked vintage leather suitcases beside wall, large world map pinned on wall, globe on desk corner, three stacks of books, inkwell and quill on desk surface, exposed wooden rafters above

SCENE 49: Sea-view cottage room — wide window seat looking out to ocean with lighthouse visible in distance, cozy armchair with wool cable-knit blanket draped over arm, wooden shelf with four shells, piece of driftwood, and ship in a bottle, nautical hanging lantern, braided sea-grass rug, single candle on windowsill

SCENE 50: Secret garden corner — curved stone bench nestled in garden alcove, climbing roses on wooden trellis on each side, iron lantern on stone post, circular birdbath with bird, four terracotta pots overflowing with flowers, hidden ivy-covered archway in background, old watering can leaning on bench, straw garden hat on bench, two butterflies in air
```

---

## TROUBLESHOOTING — لو الستايل اختلف

لو لاحظت إن صفحة طلعت مختلفة، ابعت في Claude:

```
Regenerate Scene [NUMBER] — apply exact same style as the reference image "Page 1 — Canopy Bedroom".
Add these negative constraints: NO color fill, NO shading, NO gray tones, NO photorealistic style, NO painterly texture.
Same prompt as before: [SCENE TEXT]
```

---

## AFTER GENERATION

```
flow_download collection "Cozy Coloring Book Vol.1" as ZIP
```

**Print specs for KDP:**
- Size: 8.5 × 8.5 inches (square — most common in this niche)
- Resolution: 300 DPI
- Bleed: 0.125 inch on all sides
- Color mode: Grayscale (not CMYK, not RGB)
- Format: PDF/X-1a
