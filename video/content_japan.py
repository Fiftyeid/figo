"""CONTENT — JAPAN AIR FLEET 2026.

Same engine, same chrome as the USA-vs-CHINA film, but the subject is a
single country's inventory, so each chapter is a small roster of types and
the hero airframe rotates through them while the chapter's narration runs.

    kind "fleet" -> scene_fleet (engine/fleet.py)

Narration lives in NARRATION below so one file still drives voiceover,
subtitles and the .srt export.  Numbers follow open-source reporting
(March 2026 where the source video states a figure).
"""
from __future__ import annotations

META = {
    "title": "AIR FLEET 2026",
    "subtitle": "JAPAN — SELF-DEFENSE FORCES",
}

SECTIONS = [
    # ---------------------------------------------------------------- 01
    {
        "id": "01",
        "kind": "fleet",
        "chapter": "FIGHTERS",
        "standfirst": "The air-defence core, and the stealth wing replacing it.",
        "items": [
            {"name": "F-15J EAGLE", "cue": "f-15j", "short": "F-15J", "asset": "fleet/f15j",
             "kpi": "200 IN SERVICE", "role": "AIR SUPERIORITY", "tag": "SINCE 1981"},
            {"name": "MITSUBISHI F-2", "cue": "the f-2", "short": "F-2", "asset": "fleet/f2",
             "kpi": "90 IN SERVICE", "role": "ANTI-SHIP STRIKE", "tag": "SINCE 2000"},
            {"name": "F-35 LIGHTNING II", "cue": "f-35", "short": "F-35", "asset": "fleet/f35",
             "kpi": "147 PLANNED", "role": "STEALTH MULTIROLE", "tag": "A AND B MODELS"},
        ],
        "narration": (
            "Japan is an island nation, and its air force is built to cover open sea, "
            "far-flung islands and very long distances. Start with the fighters. "
            "Two hundred F-15J Eagles still form the backbone, licence-built by Mitsubishi, "
            "meeting Chinese and Russian aircraft near Japanese airspace almost every day. "
            "The F-2 is the anti-ship striker: a larger wing, heavy missiles, designed to "
            "break up a landing fleet far offshore. And the F-35 quietly changes the maths — "
            "one of the largest fleets outside America, with the short-takeoff B models "
            "destined for the converted carriers Izumo and Kaga."
        ),
    },
    # ---------------------------------------------------------------- 02
    {
        "id": "02",
        "kind": "fleet",
        "chapter": "ATTACK HELICOPTERS",
        "standfirst": "The one part of the fleet Japan is quietly letting go.",
        "items": [
            {"name": "AH-1S COBRA", "cue": "ah-1s", "short": "AH-1S", "asset": "fleet/ah1s",
             "kpi": "34 IN SERVICE", "role": "TANK KILLER", "tag": "FUJI-BUILT"},
            {"name": "AH-64D APACHE", "cue": "ah-64d", "short": "AH-64D", "asset": "fleet/ah64d",
             "kpi": "12 IN SERVICE", "role": "HEAVY GUNSHIP", "tag": "FLEET CUT SHORT"},
        ],
        "narration": (
            "Attack helicopters are the part of the fleet Japan is letting go. "
            "The AH-1S Cobra was the ground force's tank killer, bought to blunt a Soviet "
            "landing on Hokkaido; only thirty-four were left in March 2026. "
            "The AH-64D Apache was meant to be the heavy fist — twelve were kept, after "
            "costs soared and licence production was halted early. "
            "Both were built for a fight that drones now do more cheaply, and Japan has "
            "already started retiring the units that fly them."
        ),
    },
    # ---------------------------------------------------------------- 03
    {
        "id": "03",
        "kind": "fleet",
        "chapter": "HELICOPTERS",
        "standfirst": "Lift, rescue, and the rotor that hunts submarines.",
        "items": [
            {"name": "CH-47J CHINOOK", "cue": "ch-47j", "short": "CH-47J", "asset": "fleet/ch47j",
             "kpi": "SINCE 1986", "role": "HEAVY LIFT", "tag": "KAWASAKI-BUILT"},
            {"name": "SH-60K SEAHAWK", "cue": "sh-60k", "short": "SH-60K", "asset": "fleet/sh60k",
             "kpi": "DIPPING SONAR", "role": "ANTI-SUBMARINE", "tag": "SHIP-BORNE"},
            {"name": "V-22 OSPREY", "cue": "v-22", "short": "V-22", "asset": "fleet/v22",
             "kpi": "CAMP SAGA", "role": "TILTROTOR ASSAULT", "tag": "MOVED 2025"},
        ],
        "narration": (
            "Then the workhorses. The CH-47J Chinook has been Japan's heavy lifter since "
            "nineteen eighty-six — artillery, troops, relief supplies, and in twenty eleven, "
            "water dropped on the crippled Fukushima reactors. "
            "The SH-60K Seahawk hunts submarines from destroyers and helicopter carriers, "
            "lowering a dipping sonar into the water around Japan. "
            "And the V-22 Osprey finally left its temporary base: by August 2025 the whole "
            "fleet had moved to Camp Saga in Kyushu, close to the amphibious brigade it "
            "was bought to carry along the southwestern island chain."
        ),
    },
    # ---------------------------------------------------------------- 04
    {
        "id": "04",
        "kind": "fleet",
        "chapter": "PATROL AIRCRAFT",
        "standfirst": "Long-range eyes over the sea lanes, flown for hours at a time.",
        "items": [
            {"name": "P-1", "cue": "the kawasaki p-1", "short": "P-1", "asset": "fleet/p1",
             "kpi": "40 IN SERVICE", "role": "MARITIME PATROL", "tag": "ALL-JAPANESE JET"},
            {"name": "P-3C ORION", "cue": "p-3c", "short": "P-3C", "asset": "fleet/p3c",
             "kpi": "24 IN SERVICE", "role": "MARITIME PATROL", "tag": "COLD WAR VETERAN"},
        ],
        "narration": (
            "Out over the sea lanes, Japan flies some of the longest patrol missions in the "
            "world. The P-3C Orion hunted Soviet submarines through the Cold War; only "
            "twenty-four remain as a homegrown jet takes over. "
            "The Kawasaki P-1 is that jet — four engines, fly-by-light controls, and the "
            "first patrol aircraft designed and built entirely in Japan. Forty were in "
            "service in March 2026, though spare-parts shortages have reportedly grounded "
            "some of them. Between them, these two types watch the water between Japan, "
            "its islands and the wider Pacific."
        ),
    },
    # ---------------------------------------------------------------- 05
    {
        "id": "05",
        "kind": "fleet",
        "chapter": "TRANSPORTS & TANKERS",
        "standfirst": "The aircraft that move the fleet, and the fuel that keeps it flying.",
        "items": [
            {"name": "KAWASAKI C-2", "cue": "the c-2", "short": "C-2", "asset": "fleet/c2",
             "kpi": "HEAVY AIRLIFT", "role": "JET TRANSPORT", "tag": "SINCE 2016"},
            {"name": "C-130H HERCULES", "cue": "c-130h", "short": "C-130H", "asset": "fleet/c130",
             "kpi": "SINCE 1984", "role": "TACTICAL AIRLIFT", "tag": "TWO SERVICES"},
            {"name": "KC-767", "cue": "kc-767", "short": "KC-767", "asset": "fleet/kc767",
             "kpi": "FIRST TANKER", "role": "AERIAL REFUELLING", "tag": "SINCE 2008"},
            {"name": "KC-46A PEGASUS", "cue": "kc-46a", "short": "KC-46A", "asset": "fleet/kc46",
             "kpi": "NEW GENERATION", "role": "REFUEL / CARGO", "tag": "AT MIHO"},
        ],
        "narration": (
            "To move troops, fuel and cargo across a very long country, Japan relies on the "
            "airlift wing. The C-2 is the homegrown jet airlifter, designed by Kawasaki to "
            "carry heavy vehicles between scattered islands. The C-130H has served since "
            "nineteen eighty-four, and some now refuel rescue helicopters in flight. "
            "Around them sit the tankers: the KC-767, Japan's first, which quietly gave the "
            "force a reach it had never had, and the newer KC-46A Pegasus, whose "
            "camera-guided boom has had teething problems in American service."
        ),
    },
    # ---------------------------------------------------------------- 06
    {
        "id": "06",
        "kind": "fleet",
        "chapter": "EYES IN THE SKY",
        "standfirst": "No weapons, no markings — and they decide how the fight is fought.",
        "items": [
            {"name": "E-767 AWACS", "cue": "four e-767s", "short": "E-767", "asset": "fleet/e767",
             "kpi": "4 AIRFRAMES", "role": "AIRBORNE RADAR", "tag": "WIDE-AREA WATCH"},
            {"name": "E-2D HAWKEYE", "cue": "e-2d", "short": "E-2D", "asset": "fleet/e2d",
             "kpi": "18 ON ORDER", "role": "CARRIER AEW", "tag": "SMALLER DECKS"},
        ],
        "narration": (
            "Some of the most important aircraft in the fleet carry no weapons at all. "
            "Four E-767s lift a radar dome high over the horizon and turn the air force "
            "into a single network: every fighter, every ship, every rescue helicopter "
            "seeing what the aircraft above them can see. "
            "The E-2D Advanced Hawkeye does the same job from smaller decks, watching the "
            "water between Japan and its islands. Neither type fires a shot, and both "
            "decide how the fight is fought."
        ),
    },
    # ---------------------------------------------------------------- 07
    {
        "id": "07",
        "kind": "fleet",
        "chapter": "TRAINERS & SPECIAL MISSION",
        "standfirst": "The aircraft that make pilots — and the one that lands on open ocean.",
        "items": [
            {"name": "KAWASAKI T-4", "cue": "the t-4", "short": "T-4", "asset": "fleet/t4",
             "kpi": "JET TRAINER", "role": "PILOT TRAINING", "tag": "SINCE 1988"},
            {"name": "SHINMAYWA US-2", "cue": "us-2", "short": "US-2", "asset": "fleet/us2",
             "kpi": "FLYING BOAT", "role": "SEA RESCUE", "tag": "LANDS ON WATER"},
        ],
        "narration": (
            "Not every aircraft in the fleet is built to fight. The T-4 has trained "
            "Japanese pilots for four decades, and still does the job at a fraction of the "
            "cost of a fighter. The US-2 flying boat is the strange one: it lands on open "
            "ocean to pull people out of the sea, and a transport version flies supplies to "
            "Japan's research base in Antarctica. Both are reminders that a military fleet "
            "is mostly made of everything that is not combat."
        ),
    },
    # ---------------------------------------------------------------- 08
    {
        "id": "08",
        "kind": "fleet",
        "chapter": "DRONES",
        "standfirst": "The newest wing, and the quietest.",
        "items": [
            {"name": "RQ-4B GLOBAL HAWK", "cue": "rq-4b", "short": "RQ-4B", "asset": "fleet/rq4",
             "kpi": "HIGH ALTITUDE", "role": "STRATEGIC ISR", "tag": "NO PILOT ABOARD"},
        ],
        "narration": (
            "Last, the newest wing. The RQ-4B Global Hawk flies higher and stays up longer "
            "than anything with a pilot aboard, watching the sea lanes for hours at a time. "
            "It is a small fleet doing a big job — the same job the P-3C once did, and the "
            "same job drones are now taking from Japan's retiring gunships. "
            "That is the shape of the fleet in 2026: fewer airframes, longer reach, and more "
            "of the work done by aircraft that never carry a person."
        ),
    },
]

INTRO_NARRATION = (
    "Japan is an island nation with a fleet built for distance. Here is every aircraft "
    "its military is flying in 2026 — the fighters, the gunships, the patrol planes, the "
    "tankers, the trainers and the drones."
)

# narration actually used for the voiceover pass (one file per id, plus intro)
NARRATION = {sec["id"]: sec["narration"] for sec in SECTIONS}

if __name__ == "__main__":
    for _s in SECTIONS:
        print(_s["id"], _s["chapter"], len(_s["narration"].split()), "words")
