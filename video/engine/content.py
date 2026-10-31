"""CONTENT = the only file you edit to make a new film.

Each section is one chapter of the comparison.  Section `kind` picks the
layout, everything else is data.  Narration drives the timing: the renderer
measures the spoken audio and holds the chapter open for exactly that long.

kinds
  duel    two product cutouts face off (needs assets.left / assets.right)
  bars    two metric bars grow from the middle outwards
  swatch  procedural camouflage swatches
  ammo    two cartridges drawn to scale
  list    two checklists
  outro   closing split-screen

asset keys resolve to  assets/<key>.png  (see content.ASSET_DIR)
"""
from __future__ import annotations

META = {
    "title": "GEAR COMPARED",
    "subtitle": "USA vs CHINA — SOLDIER",
    "channel": "HIKKA / STYLE STUDY",
    "episode": "FIELD LOADOUT STUDY  /  EP. 02",
    "disclaimer": "OPEN-SOURCE DATA · ILLUSTRATIVE RENDERS",
    # short on-screen deck for the title card (the full narration is spoken,
    # not printed — long paragraphs under a title always read badly)
    "hero_a": "WHAT A SOLDIER",
    "hero_b": "ACTUALLY CARRIES",
    "hero_stat": "32 KG · USA          30 KG · CHINA",
    "deck": "Same war, same job, two completely different answers. "
            "Eighteen items, compared one by one.",
}

# side 1 = left (USA / blue), side 2 = right (CHINA / red)
SIDES = {
    "left": {
        "country": "us",
        "code": "USA",
        "flag": "us",
        "name": "UNITED STATES",
        "force": "U.S. ARMY",
        "accent": (21, 45, 88),
    },
    "right": {
        "country": "cn",
        "code": "CHN",
        "flag": "cn",
        "name": "CHINA",
        "force": "PEOPLE'S LIBERATION ARMY",
        "accent": (196, 34, 34),
    },
}

SECTIONS = [
    # ---------------------------------------------------------------- 01
    {
        "id": "01",
        "kind": "duel",
        "chapter": "THE RIFLE",
        "title": "SERVICE RIFLE",
        "standfirst": "The biggest change in a generation happens at the muzzle.",
        "assets": {"left": "m7", "right": "qbz191"},
        "names": {"left": "M7 / NGSW", "right": "QBZ-191"},
        "specs": [
            ("CALIBER", "6.8 × 51 mm", "5.8 × 42 mm"),
            ("WEIGHT", "3.8 kg", "3.4 kg"),
            ("IN SERVICE", "2024", "2019"),
        ],
        "nominal": 14.0,
        "narration": (
            "Start with the rifle, because everything else on the belt exists to feed it. "
            "America's M7 fires a brand new 6.8 millimetre round, designed to punch through "
            "modern body armour at distance. China's QBZ nineteen-one keeps the proven 5.8 "
            "millimetre cartridge, in a lighter, more compact rifle."
        ),
        "narration_ar": "نبدأ بالبندقية، لأن كل ما على الحزام موجود لإطعامها. بندقية M7 الأمريكية تطلق طلقة جديدة عيار 6.8 ملم، مصممة لاختراق الدروع الحديثة من مسافة. أما QBZ-191 الصينية فتحتفظ بعيار 5.8 ملم المثبت، في بندقية أخف وأكثر إحكاماً.",
    },
    # ---------------------------------------------------------------- 02
    {
        "id": "02",
        "kind": "ammo",
        "chapter": "THE ROUND",
        "title": "AMMUNITION",
        "standfirst": "More energy in the hand also means more weight on the shoulder.",
        "names": {"left": "6.8 × 51", "right": "5.8 × 42"},
        "bullets": {"left": 6.8, "right": 5.8},
        "specs": [
            ("MUZZLE ENERGY", "≈ 3.5 kJ", "≈ 1.9 kJ"),
            ("ROUND WEIGHT", "≈ 20 g", "≈ 12 g"),
            ("MAGAZINE", "20 rds", "30 rds"),
        ],
        "nominal": 12.0,
        "narration": (
            "The trade is energy against weight. The American round carries roughly twice "
            "the muzzle energy, and costs about twice the mass in every magazine. For the "
            "man carrying it, that is the whole argument in one number."
        ),
        "narration_ar": "المقايضة هنا هي الطاقة مقابل الوزن. الطلقة الأمريكية تحمل ضعف طاقة الفوهة تقريباً، وتكلّف ضعف الكتلة في كل مخزن. بالنسبة للجندي الذي يحملها، هذا هو جوهر الحكاية في رقم واحد.",
    },
    # ---------------------------------------------------------------- 03
    {
        "id": "03",
        "kind": "swatch",
        "chapter": "THE PATTERN",
        "title": "CAMOUFLAGE",
        "standfirst": "Two philosophies of hiding a human being in plain sight.",
        "names": {"left": "OCP", "right": "XINGKONG-21"},
        "specs": [
            ("FAMILY", "Multi-environment", "Digital / pixel"),
            ("INTRODUCED", "2015", "2019"),
            ("PALETTE", "Tan · green · brown", "Teal · grey · green"),
        ],
        "nominal": 11.0,
        "narration": (
            "Camouflage is a design argument about where you expect to fight. The US "
            "operational camouflage pattern blends tan and green for a wide range of "
            "terrain. China's star-sky pattern goes digital, tuned for its own coastlines, "
            "highlands and cities."
        ),
        "narration_ar": "التمويه موقف تصميمي من مكان القتال المتوقع. النمط الأمريكي OCP يمزج البيج والأخضر لمدى واسع من التضاريس. أما النمط الصيني «شينغ كونغ» فيذهب إلى البكسلات الرقمية، مضبوطاً على سواحله ومرتفعاته ومدنه.",
    },
    # ---------------------------------------------------------------- 04
    {
        "id": "04",
        "kind": "duel",
        "chapter": "THE HEAD",
        "title": "COMBAT HELMET",
        "standfirst": "High-cut shells trade ear coverage for a headset.",
        "assets": {"left": "helmet_us", "right": "helmet_cn"},
        "names": {"left": "IHPS", "right": "QGF-21"},
        "specs": [
            ("WEIGHT", "≈ 1.4 kg", "≈ 1.5 kg"),
            ("CUT", "High-cut", "High-cut"),
            ("MOUNTS", "NVG shroud + rails", "NVG shroud + rails"),
        ],
        "nominal": 12.0,
        "narration": (
            "Both armies have moved to the high-cut helmet. The trade is the same on both "
            "sides: less coverage around the ear, so a headset and a night vision mount can "
            "sit against the skull without pinching."
        ),
        "narration_ar": "الجيشان انتقلا إلى الخوذة عالية القطع. المقايضة واحدة على الجانبين: تغطية أقل حول الأذن، حتى تجلس السماعة وحاملة الرؤية الليلية على الجمجمة دون ضغط.",
    },
    # ---------------------------------------------------------------- 05
    {
        "id": "05",
        "kind": "duel",
        "chapter": "THE TORSO",
        "title": "BODY ARMOUR",
        "standfirst": "The plate carrier is now the load-bearing system, not just a shield.",
        "assets": {"left": "armor_us", "right": "armor_cn"},
        "names": {"left": "MSV GEN II", "right": "TYPE 21 PLATE CARRIER"},
        "specs": [
            ("PLATES", "2 × SAPI / ESAPI", "2 × Level IV"),
            ("LOADED WEIGHT", "≈ 8 kg", "≈ 7 kg"),
            ("CARRY", "Magazines · radio · med", "Magazines · radio · med"),
        ],
        "nominal": 13.0,
        "narration": (
            "Body armour has quietly become the heaviest thing a soldier wears. Both "
            "systems carry two hard plates front and back, then hang everything else from "
            "the same shell: magazines, radio, water, medical."
        ),
        "narration_ar": "الدرع الواقي أصبح بهدوء أثقل ما يلبسه الجندي. النظامان يحملان لوحين صلبين أماماً وخلفاً، ثم يعلّقان كل شيء آخر على الهيكل نفسه: مخازن، لاسلكي، ماء، إسعاف.",
    },
    # ---------------------------------------------------------------- 06
    {
        "id": "06",
        "kind": "bars",
        "chapter": "THE TORSO",
        "title": "PROTECTED AREA",
        "standfirst": "How much of the body the plate actually covers.",
        "names": {"left": "MSV GEN II", "right": "TYPE 21"},
        "bars": {
            "unit": "% OF TORSO",
            "max": 100,
            "left": 62,
            "right": 58,
            "left_label": "62",
            "right_label": "58",
        },
        "specs": [
            ("SIDE PLATES", "6 × 6 in", "6 × 8 in"),
            ("NECK / GROIN", "Optional add-on", "Optional add-on"),
            ("QUICK RELEASE", "Yes", "Yes"),
        ],
        "nominal": 11.0,
        "narration": (
            "Neither vest is a suit of armour. Both leave the shoulders, the sides and the "
            "groin largely exposed, and both rely on add-on panels when the mission asks for "
            "them. Coverage is a decision, not a constant."
        ),
        "narration_ar": "لا السترة الأمريكية ولا الصينية درع كامل. كلتاهما تترك الكتفين والجانبين والمنطقة الحوضية مكشوفة إلى حد كبير، وتعتمد على ألواح إضافية عند الحاجة. التغطية قرار، وليست ثابتاً.",
    },
    # ---------------------------------------------------------------- 07
    {
        "id": "07",
        "kind": "duel",
        "broll": {"clip": "nvg_field", "secs": 3.2, "label": "OWNING THE DARK",
                  "kicker": "FIELD · RECONSTRUCTION",
                  "credit": "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE"},
        "chapter": "THE EYES",
        "title": "NIGHT VISION",
        "standfirst": "Owning the dark is still the widest gap in infantry kit.",
        "assets": {"left": "nvg_us", "right": "nvg_cn"},
        "names": {"left": "AN/PVS-31", "right": "PLA DUAL-TUBE NVG"},
        "specs": [
            ("TUBES", "Dual, white phosphor", "Dual, green phosphor"),
            ("FIELD OF VIEW", "40°", "≈ 40°"),
            ("MOUNT", "Dovetail, helmet", "Dovetail, helmet"),
        ],
        "nominal": 13.0,
        "narration": (
            "Dual-tube night vision used to be an American privilege. It is now standard "
            "issue in China's modernised brigades as well. Twenty years ago this scene "
            "looked completely different; today the goggles are close cousins."
        ),
        "narration_ar": "الرؤية الليلية ثنائية الأنبوب كانت امتيازاً أمريكياً. اليوم أصبحت إصداراً قياسياً في الألوية الصينية الحديثة أيضاً. قبل عشرين سنة كان المشهد مختلفاً تماماً؛ اليوم المنظاران قريبان جداً.",
    },
    # ---------------------------------------------------------------- 08
    {
        "id": "08",
        "kind": "duel",
        "broll": {"clip": "optic_range", "secs": 3.0, "label": "BEHIND THE OPTIC",
                  "kicker": "FIELD · RECONSTRUCTION",
                  "credit": "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE"},
        "chapter": "THE EYES",
        "title": "DAY OPTIC",
        "standfirst": "The magnified optic became the default, not the upgrade.",
        "assets": {"left": "optic_us", "right": "optic_cn"},
        "names": {"left": "LPVO 1–8× / M157", "right": "QMK-152 3× PRISM"},
        "specs": [
            ("MAGNIFICATION", "1 – 8 ×", "3 × fixed"),
            ("RETICLE", "Etched, illuminated", "Etched, illuminated"),
            ("BATTERY", "1 × CR2032", "1 × CR2032"),
        ],
        "nominal": 11.0,
        "narration": (
            "The rifle is only half the system. America issues a variable optic that goes "
            "from one power for a doorway to eight for four hundred metres. China's answer "
            "is a simpler fixed three power prism: lighter, cheaper, and fast to train on."
        ),
        "narration_ar": "البندقية نصف المنظومة فقط. أمريكا تصرف منظاراً متغير التكبير من 1 إلى 8، والصين ترد بمنظار بريزم ثابت ثلاث مرات: أخف، أرخص، وأسرع في التدريب.",
    },
    # ---------------------------------------------------------------- 09
    {
        "id": "09",
        "kind": "list",
        "chapter": "THE VOICE",
        "title": "COMMUNICATIONS",
        "standfirst": "Who a soldier can talk to defines what a squad can do.",
        "names": {"left": "AN/PRC-163", "right": "PLA SDR"},
        "specs": [
            ("CHANNELS", "Two, simultaneous", "One or two"),
            ("BANDS", "VHF / UHF / SATCOM", "VHF / UHF"),
            ("DATA", "Yes, link to tablet", "Yes, squad network"),
        ],
        "list": {
            "left": ["Squad radio in every team", "Satellite reach for leaders", "Blue-force tracking"],
            "right": ["Squad net built around the vehicle", "Wide issue of digital sets", "Text and position reports"],
        },
        "nominal": 12.0,
        "narration": (
            "Listen closely to a modern infantry squad and you hear two networks: the local "
            "net that keeps a fire team together, and the long one that reaches command. "
            "Both armies are pushing the second down to smaller and smaller units."
        ),
        "narration_ar": "استمع إلى فصيل مشاة حديث وستسمع شبكتين: الشبكة المحلية التي تربط جماعة النار، والبعيدة التي تصل إلى القيادة. الجيشان يدفعان الثانية إلى وحدات أصغر وأصغر.",
    },
    # ---------------------------------------------------------------- 10
    {
        "id": "10",
        "kind": "duel",
        "chapter": "THE SHOULDER",
        "title": "SQUAD AUTOMATIC",
        "standfirst": "Belt-fed fire is what makes a squad hard to assault.",
        "assets": {"left": "mg_us", "right": "mg_cn"},
        "names": {"left": "M250 / NGSW-AR", "right": "QJY-201"},
        "broll": {"clip": "mg_fire", "secs": 3.4, "label": "BELT-FED FIRE",
                  "kicker": "FIELD · RECONSTRUCTION",
                  "credit": "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE"},
        "specs": [
            ("CALIBRE", "6.8 mm", "5.8 mm"),
            ("FEED", "Belt, 100 rd", "Belt, 100 rd"),
            ("WEIGHT", "≈ 6.7 kg", "≈ 7.0 kg"),
        ],
        "nominal": 11.0,
        "narration": (
            "Every fire team needs a weapon it can lean on. America replaced its decades-old "
            "squad automatic with a belt-fed light machine gun in the new calibre. China "
            "fielded its own lightweight belt-fed gun, and the two numbers land in almost "
            "the same place."
        ),
        "narration_ar": "كل جماعة نار تحتاج سلاحاً تتكئ عليه. أمريكا استبدلت رشاشها القديم بسلاح حزامي أخف بالعيار الجديد. الصين أنتجت رشاشها الحزامي الخفيف، والرقمان يقتربان من النقطة نفسها.",
    },
    # ---------------------------------------------------------------- 11
    {
        "id": "11",
        "kind": "duel",
        "chapter": "THE HAND",
        "title": "SIDEARM",
        "standfirst": "The pistol is back, and it is a full-size one.",
        "assets": {"left": "pistol_us", "right": "pistol_cn"},
        "names": {"left": "M17 / M18", "right": "QSZ-92"},
        "specs": [
            ("CALIBER", "9 × 19 mm", "5.8 × 21 mm"),
            ("CAPACITY", "17 rds", "20 rds"),
            ("FRAME", "Polymer, striker", "Polymer, hammer"),
        ],
        "nominal": 10.0,
        "narration": (
            "For years the sidearm was a status symbol for officers and machine gunners. "
            "Both armies now push a full-size pistol into more hands, mostly as the last "
            "option when a primary weapon fails."
        ),
        "narration_ar": "لسنوات كان المسدس رمزاً للمكانة عند الضباط وطاقم الرشاش. الآن يدفع الجيشان بمسدس كامل الحجم إلى أيدٍ أكثر، كخيار أخير عند تعطل السلاح الأساسي.",
    },
    # ---------------------------------------------------------------- 12
    {
        "id": "12",
        "kind": "duel",
        "chapter": "THE HAND",
        "title": "GRENADE LAUNCHER",
        "standfirst": "Forty millimetres, bolted under the barrel.",
        "assets": {"left": "gl_us", "right": "gl_cn"},
        "names": {"left": "M320  40 mm", "right": "QLG-10  35 mm"},
        "specs": [
            ("RANGE", "≈ 350 m", "≈ 400 m"),
            ("WEIGHT", "1.5 kg", "1.3 kg"),
            ("ROLE", "Bunkers · smoke · marking", "Bunkers · smoke · marking"),
        ],
        "nominal": 10.0,
        "narration": (
            "Under every second rifle sits a small cannon. The American forty millimetre and "
            "the Chinese thirty-five are used for the same three jobs: breaking a position, "
            "laying smoke, and marking a target for someone further away."
        ),
        "narration_ar": "تحت كل بندقية ثانية مدفع صغير. عيار 40 ملم الأمريكية و35 ملم الصينية يؤديان المهام الثلاث نفسها: كسر موقع، حجب بالدخان، وتمييز هدف لمن هو أبعد.",
    },
    # ---------------------------------------------------------------- 13
    {
        "id": "13",
        "kind": "stat",
        "broll": {"clip": "ration_heat", "secs": 3.2, "label": "ONE BAG = ONE MEAL",
                  "kicker": "FIELD · RECONSTRUCTION",
                  "credit": "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE"},
        "chapter": "THE STOMACH",
        "title": "FIELD RATION",
        "standfirst": "One bag, one meal, and a chemical heater inside.",
        "names": {"left": "MRE / FSR", "right": "TYPE 21 SELF-HEATING"},
        "stats": {
            "left": {"value": "1250", "unit": "kcal", "note": "Per MRE · 1.6 kg total"},
            "right": {"value": "1000", "unit": "kcal", "note": "Per pouch · flameless heater"},
        },
        "specs": [
            ("HEATING", "Flameless chemical", "Flameless chemical"),
            ("SHELF LIFE", "3 years", "3 years"),
            ("PACKAGING", "Heavy foil bag", "Foil pouch + tray"),
        ],
        "nominal": 12.0,
        "narration": (
            "A soldier burns more calories than any ration provides, which is why field food "
            "is designed around density rather than taste. The Chinese self-heating pouch is "
            "the smaller, faster meal. The American ration is the bigger, heavier one, with "
            "more snacks packed around it."
        ),
        "narration_ar": "الجندي يحرق سعرات أكثر مما يوفره أي وجبة، ولذلك صُمم الغذاء الميداني حول الكثافة لا الطعم. الكيس الصيني ذاتي التسخين هو الوجبة الأصغر والأسرع. الحصة الأمريكية أكبر وأثقل، ومعها مزيد من الوجبات الخفيفة.",
    },
    # ---------------------------------------------------------------- 14
    {
        "id": "14",
        "kind": "bars",
        "chapter": "THE STOMACH",
        "title": "WATER CARRIED",
        "standfirst": "Three litres is the number both armies plan around.",
        "names": {"left": "HYDRATION CARRIER", "right": "PLA CANTEEN + BLADDER"},
        "bars": {
            "unit": "LITRES ON THE BODY",
            "max": 5,
            "left": 3.0,
            "right": 3.0,
            "left_label": "3.0 L",
            "right_label": "3.0 L",
        },
        "specs": [
            ("TYPE", "Bladder + hose", "Canteen + bladder"),
            ("REFILL", "Wide mouth", "Narrow mouth"),
            ("WEIGHT FULL", "3.2 kg", "3.3 kg"),
        ],
        "nominal": 10.0,
        "narration": (
            "Water is the one item nobody argues about. Three litres on the body, refilled at "
            "every pause, and a full bladder adds more weight than the rifle's ammunition."
        ),
        "narration_ar": "الماء هو البند الوحيد الذي لا يختلف عليه أحد. ثلاثة لترات على الجسم، تُعاد تعبئتها عند كل توقف، ومثانة ممتلئة تضيف وزناً أكبر من ذخيرة البندقية.",
    },
    # ---------------------------------------------------------------- 15
    {
        "id": "15",
        "kind": "list",
        "chapter": "THE POCKET",
        "title": "MEDICAL",
        "standfirst": "The most important kilogram is the one you never use.",
        "names": {"left": "IFAK / M9", "right": "TYPE 21 IFAK"},
        "specs": [
            ("TOURNIQUET", "2 issued", "2 issued"),
            ("DRESSING", "Hemostatic gauze", "Hemostatic gauze"),
            ("CHEST SEAL", "Vented", "Vented"),
        ],
        "list": {
            "left": ["Tourniquets worn on the body, not the pack", "Every soldier trained to use them", "Bleeding control in under 60 s"],
            "right": ["Kit issued to the individual", "Squad medic carries the deep stock", "Emphasis on vehicle evacuation"],
        },
        "nominal": 11.0,
        "narration": (
            "Both armies learned the same lesson in the last twenty years: the individual "
            "soldier has to stop his own bleeding. Tourniquets moved from the medics bag onto "
            "the body, where a hand can reach them."
        ),
        "narration_ar": "الجيشان تعلما الدرس نفسه في العشرين سنة الماضية: الجندي نفسه يجب أن يوقف نزيفه. العاصبات انتقلت من حقيبة المسعف إلى الجسم، حيث تصلها اليد.",
    },
    # ---------------------------------------------------------------- 16
    {
        "id": "16",
        "kind": "duel",
        "chapter": "THE SKY",
        "title": "SMALL DRONES",
        "standfirst": "The newest item on the list weighs less than a rifle magazine.",
        "assets": {"left": "drone_us", "right": "drone_cn"},
        "names": {"left": "SQUAD ISR DRONE", "right": "PLA NANO DRONE"},
        "broll": {"clip": "drone_launch", "secs": 3.2, "label": "HAND-LAUNCHED ISR",
                  "kicker": "FIELD · RECONSTRUCTION",
                  "credit": "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE"},
        "specs": [
            ("RANGE", "≈ 2 km", "≈ 2 km"),
            ("PAYLOAD", "Camera / thermal", "Camera / thermal"),
            ("ISSUE", "Squad level", "Squad level"),
        ],
        "nominal": 11.0,
        "narration": (
            "Ten years ago this chapter would not exist. Today the smallest aircraft in the "
            "inventory is carried by the infantryman himself, launched by hand, and used to "
            "look over the next wall before anyone walks around it."
        ),
        "narration_ar": "قبل عشر سنوات لم يكن هذا الفصل موجوداً. اليوم أصغر طائرة في المخزون يحملها الجندي بنفسه، ويطلقها بيده، وينظر من فوق الجدار التالي قبل أن يلتف أحد حوله.",
    },
    # ---------------------------------------------------------------- 17
    {
        "id": "17",
        "kind": "bars",
        "chapter": "THE TOTAL",
        "title": "COMBAT LOAD",
        "standfirst": "Add it all up and the numbers converge.",
        "names": {"left": "FULL FIGHTING LOAD", "right": "FULL FIGHTING LOAD"},
        "bars": {
            "unit": "KILOGRAMS CARRIED",
            "max": 40,
            "left": 32.0,
            "right": 30.0,
            "left_label": "32 kg",
            "right_label": "30 kg",
        },
        "specs": [
            ("ARMOUR + HELMET", "9.4 kg", "8.5 kg"),
            ("WEAPON + AMMO", "9.1 kg", "7.2 kg"),
            ("WATER + FOOD + MED", "7.5 kg", "8.3 kg"),
        ],
        "nominal": 13.0,
        "narration": (
            "Here is the honest ending. After eighteen chapters of differences, the two "
            "soldiers arrive within a couple of kilos of each other. Thirty kilos is not a "
            "design choice; it is what a human being can still fight in."
        ),
        "narration_ar": "هذه هي النهاية الصادقة. بعد ثمانية عشر فصلاً من الاختلافات، يصل الجنديان إلى فرق كيلوين فقط. ثلاثون كيلو ليست قراراً تصميمياً؛ إنها ما يستطيع الإنسان القتال به.",
    },
    # ---------------------------------------------------------------- 18
    {
        "id": "18",
        "kind": "outro",
        "chapter": "THE CONCLUSION",
        "title": "TWO SOLDIERS",
        "standfirst": "Different doctrine, same weight, same job.",
        "assets": {"left": "soldier_us", "right": "soldier_cn"},
        "names": {"left": "U.S. ARMY", "right": "PEOPLE'S LIBERATION ARMY"},
        "specs": [
            ("DOCTRINE", "Long-range precision", "Mass and mobility"),
            ("STRENGTH", "Optics · comms · aviation", "Numbers · artillery · drones"),
            ("COMMON", "A 30 kg fighting load", "A 30 kg fighting load"),
        ],
        "nominal": 14.0,
        "narration": (
            "Two nations, two doctrines, one conclusion. The American soldier is built to "
            "see further and call for more. The Chinese soldier is built to move with mass "
            "and stay supplied. Different ideas, but the same thirty kilos on the same "
            "shoulders. If you want the next comparison, tell me in the comments."
        ),
        "narration_ar": "أمتان، عقيدتان، ونتيجة واحدة. الجندي الأمريكي مصمم ليرى أبعد ويطلب دعماً أكبر. الجندي الصيني مصمم ليتحرك بالكتلة ويبقى ممولاً. أفكار مختلفة، لكنها ثلاثون كيلو نفسها على الأكتاف نفسها. لو أردت المقارنة القادمة، اكتبها في التعليقات.",
    },
]

INTRO_NARRATION_AR = (
    "الجندي الأول يحمل اثنين وثلاثين كيلو. الثاني يحمل ثلاثين. نفس الحرب، نفس المهمة، وإجابتان مختلفتان تماماً. هذه المعدات الأمريكية في مواجهة الصينية — عنصراً بعنصر، ونبدأ من فوهة البندقية."
)

INTRO_NARRATION = (
    "One soldier carries thirty-two kilos. The other carries thirty. Same war, same job, "
    "two completely different answers. This is American gear against Chinese gear, item by "
    "item, starting at the muzzle."
)
