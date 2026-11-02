"""USAF vs PLAAF 2026 — content, in the shape of the first film.

Same schema as ``engine.content``: sections of `kind` (duel / bars / outro),
narration that drives the timing, and a left/right pair per section. What
changes is the subject and the numbers; the layout code is untouched, which is
the point — this film has to look like the soldier comparison, not near it.

Figures are deliberately coarse: fleet counts move every few months, so the
film says "about 180" where the open sources disagree, and the on-screen pills
carry the same rounded number. Everything here is open-source material.
"""
from __future__ import annotations

META_VS = {
    "title": "AIR POWER 2026",
    "subtitle": "USA vs CHINA — FIGHTER FLEET",
    "channel": "HIKKA / STYLE STUDY",
    "episode": "FIGHTER FLEET STUDY  /  EP. 04",
    "disclaimer": "OPEN-SOURCE DATA · ILLUSTRATIVE RENDERS",
    "hero_a": "TWO AIR FORCES,",
    "hero_b": "ONE SKY",
    "hero_stat": "USA · 2,400 FIGHTERS      CHINA · 2,000 FIGHTERS",
    "deck": "Same mission, two completely different bets. Ten types, compared one by one.",
    # which two aircraft hold the intro, and when each one pops forward
    "hero_sprites": (("left", "versus/f22", 430, 0.35),
                     ("right", "versus/j20", 1490, 2.20)),
}

SIDES_VS = {
    "left": {
        "country": "us",
        "code": "USA",
        "flag": "us",
        "name": "UNITED STATES",
        "force": "US AIR FORCE",
        "accent": (21, 45, 88),
    },
    "right": {
        "country": "cn",
        "code": "CHN",
        "flag": "cn",
        "name": "CHINA",
        "force": "PEOPLE'S LIBERATION ARMY AIR FORCE",
        "accent": (196, 34, 34),
    },
}

SECTIONS_VS = [
    {
        "id": "01",
        "kind": "duel",
        "chapter": "STEALTH",
        "title": "THE HEAVYWEIGHTS",
        "standfirst": "Two answers to one problem: see first, be seen last.",
        "assets": {"left": "versus/f22", "right": "versus/j20"},
        "names": {"left": "F-22 RAPTOR", "right": "J-20 MIGHTY DRAGON"},
        "specs": [
            ("ROLE", "Air superiority", "Long-range interceptor"),
            ("IN SERVICE", "2005", "2017"),
            ("FLEET", "≈ 180", "≈ 250"),
        ],
        "nominal": 15.0,
        "narration": (
            "Start with the aircraft both air forces are built around. America's F-22 was "
            "designed to win a war that never came: supercruise, thrust vectoring and a radar "
            "signature the size of a marble. China's J-20 is a bigger, later bet. Canards, two "
            "engines, and long-range missiles meant to hit tankers and radar planes from far "
            "outside the fight."
        ),
    },
    {
        "id": "02",
        "kind": "duel",
        "chapter": "STEALTH",
        "title": "THE MASS-PRODUCED ONE",
        "standfirst": "One airframe, three services, a thousand airframes.",
        "assets": {"left": "versus/f35a", "right": "versus/j35"},
        "names": {"left": "F-35A LIGHTNING II", "right": "J-35"},
        "specs": [
            ("BUILT", "≈ 1,100", "≈ 60"),
            ("ROLE", "Sensor fusion", "Carrier / multirole"),
            ("STATUS", "In service", "Entering service"),
        ],
        "nominal": 14.0,
        "narration": (
            "The F-35 is the opposite idea: instead of one perfect fighter, build one airframe "
            "in enormous numbers and let software make it several aircraft. China's answer is "
            "the J-35, a smaller stealth fighter aimed at carrier decks and export customers. "
            "It is years behind in numbers — and that gap is the whole contest."
        ),
    },
    {
        "id": "03",
        "kind": "duel",
        "chapter": "WORKHORSES",
        "title": "THE HEAVY STRIKE",
        "standfirst": "The types that do most of the flying and the bombing.",
        "assets": {"left": "versus/f15ex", "right": "versus/j16"},
        "names": {"left": "F-15EX EAGLE II", "right": "J-16"},
        "specs": [
            ("PAYLOAD", "≈ 13,400 kg", "≈ 12,000 kg"),
            ("ROLE", "Missile truck", "Strike / anti-ship"),
            ("IN SERVICE", "2024", "2015"),
        ],
        "nominal": 14.0,
        "narration": (
            "Stealth opens the door; these two carry the bombs through it. The F-15EX is the "
            "oldest design in this film and still carries the most: thirteen tonnes of munitions "
            "and hypersonic missiles the F-35 cannot fit. China's J-16 is the same idea built "
            "around the Flanker, with a strike radar and a long anti-ship reach."
        ),
    },
    {
        "id": "04",
        "kind": "duel",
        "chapter": "WORKHORSES",
        "title": "THE LIGHT FIGHTERS",
        "standfirst": "Cheap, agile, and bought in the thousands for a reason.",
        "assets": {"left": "versus/f16v", "right": "versus/j10c"},
        "names": {"left": "F-16C BLOCK 70", "right": "J-10C"},
        "specs": [
            ("FLEET", "≈ 900", "≈ 500"),
            ("WING", "Conventional", "Delta + canard"),
            ("ROLE", "Multirole", "Multirole"),
        ],
        "nominal": 13.0,
        "narration": (
            "Both countries kept buying light fighters for the same reason: you can afford a "
            "thousand of them. The Viper has been upgraded for forty years and still sells. The "
            "J-10C is China's first genuinely independent design in this class, with an active "
            "electronically scanned radar and a delta wing."
        ),
    },
    {
        "id": "05",
        "kind": "bars",
        "chapter": "THE NUMBERS",
        "title": "FLEET SIZE",
        "standfirst": "Total combat aircraft. The gap is real, and it is closing.",
        "names": {"left": "UNITED STATES", "right": "CHINA"},
        "bars": {"max": 4000, "left": 2400, "right": 2000,
                 "left_label": "≈ 2,400", "right_label": "≈ 2,000"},
        "nominal": 12.0,
        "narration": (
            "Here is the number that matters. America flies roughly twenty-four hundred combat "
            "aircraft; China roughly two thousand. The US has held that lead for decades, but "
            "it is not growing — and China's is, by around a hundred airframes a year."
        ),
    },
    {
        "id": "06",
        "kind": "bars",
        "chapter": "THE NUMBERS",
        "title": "FIFTH GENERATION",
        "standfirst": "Stealth fighters built and delivered.",
        "names": {"left": "UNITED STATES", "right": "CHINA"},
        "bars": {"max": 1200, "left": 1150, "right": 300,
                 "left_label": "≈ 1,150", "right_label": "≈ 300"},
        "nominal": 12.0,
        "narration": (
            "On stealth the gap is much wider. The United States has delivered well over a "
            "thousand fifth-generation fighters. China has built somewhere near three hundred "
            "J-20s — the largest non-American stealth fleet in the world, and the one growing "
            "fastest."
        ),
    },
    {
        "id": "07",
        "kind": "duel",
        "chapter": "THE ECOSYSTEM",
        "title": "EYES IN THE SKY",
        "standfirst": "Fighters are only as good as the radar looking past them.",
        "assets": {"left": "versus/e7", "right": "versus/kj500"},
        "names": {"left": "E-7A WEDGETAIL", "right": "KJ-500"},
        "specs": [
            ("RADAR", "AESA, fixed", "Rotodome, AESA"),
            ("STATUS", "Entering service", "≈ 50 in service"),
            ("BASE", "Airliner", "Transport airframe"),
        ],
        "nominal": 14.0,
        "narration": (
            "An aircraft carrier of the sky is an early warning radar. America is retiring the "
            "E-3 and moving to the E-7 Wedgetail, a fixed AESA beam on an airliner. China built "
            "the KJ-500 for the job, fifty of them in service, with a radome the size of a "
            "destroyer's mast."
        ),
    },
    {
        "id": "08",
        "kind": "duel",
        "chapter": "THE ECOSYSTEM",
        "title": "FUEL AND REACH",
        "standfirst": "Every metric above depends on this one.",
        "assets": {"left": "fleet/kc46", "right": "versus/kj500"},
        "names": {"left": "KC-46A PEGASUS", "right": "YY-20"},
        "specs": [
            ("FLEET", "≈ 90", "≈ 30"),
            ("TYPE", "Boom tanker", "Pods and boom"),
            ("RANGE", "Global", "Regional to growing"),
        ],
        "nominal": 14.0,
        "narration": (
            "This is the quiet one. America's refuelling fleet turns every fighter into a "
            "long-range aircraft, and it operates across the whole world. China's YY-20 is new, "
            "small, and built for a fight near home — which is exactly the fight it plans."
        ),
    },
    {
        "id": "09",
        "kind": "outro",
        "chapter": "VERDICT",
        "title": "THE BIG PICTURE",
        "standfirst": "One force is deep. The other is young.",
        "assets": {"left": "versus/f22", "right": "versus/j20"},
        "names": {"left": "F-22 RAPTOR", "right": "J-20"},
        "specs": [
            ("DEPTH", "Combat hours", "Newest fleet"),
            ("REACH", "Global basing", "Home airspace"),
            ("TRAJECTORY", "Flat", "Rising"),
        ],
        "nominal": 16.0,
        "narration": (
            "So who wins? Neither, in a number. America has more aircraft, more tankers, more "
            "combat hours and allies to fly from. China has the newest fleet, the fastest "
            "production line, and the advantage of fighting in its own airspace. The honest "
            "answer is that the gap is narrowing — and the next ten years decide it."
        ),
    },
]
END_VO = "Same sky. Two answers. And ten years to find out which one was right."
