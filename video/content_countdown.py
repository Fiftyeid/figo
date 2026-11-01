"""CONTENT — 19 AIRCRAFT JAPAN FLIES, COUNTED.

The countdown edit of EP.03: same nineteen airframes, same stage, but read as
a ranked list instead of a chaptered tour.  One entry per cut, a big rank
number, the type name, and the two facts that matter (role + how many).

`vo` is the narration line; the measured clip length drives how long the
entry holds, exactly like the chaptered film.
"""
from __future__ import annotations

INTRO_VO = ("Nineteen aircraft. Every type Japan's military flies in 2026 — "
            "counted, one by one.")

END_VO = "Nineteen types. One fleet. One island nation."

# asset, name, role, count, vo
ENTRIES = [
    ("fleet/f15j", "F-15J EAGLE", "AIR SUPERIORITY", "200 IN SERVICE",
     "Number one. Two hundred Eagles, licence-built by Mitsubishi since 1981, "
     "still the backbone of Japanese air defence."),
    ("fleet/f2", "MITSUBISHI F-2", "ANTI-SHIP STRIKE", "90 IN SERVICE",
     "Ninety F-2s: a bigger wing, heavy anti-ship missiles, built to break up a "
     "landing fleet offshore."),
    ("fleet/f35", "F-35 LIGHTNING II", "STEALTH MULTIROLE", "147 PLANNED",
     "One hundred and forty-seven F-35s planned, with the B models going to sea "
     "on Izumo and Kaga."),
    ("fleet/ah1s", "AH-1S COBRA", "TANK KILLER", "34 IN SERVICE",
     "Only thirty-four Cobras left. The anti-tank helicopter Japan is quietly "
     "retiring."),
    ("fleet/ah64d", "AH-64D APACHE", "HEAVY GUNSHIP", "12 IN SERVICE",
     "Twelve Apaches, after costs soared and licence production was halted early."),
    ("fleet/ch47j", "CH-47J CHINOOK", "HEAVY LIFT", "SINCE 1986",
     "The Chinook has lifted for Japan since 1986 — artillery, troops, and water "
     "over Fukushima."),
    ("fleet/sh60k", "SH-60K SEAHAWK", "ANTI-SUBMARINE", "SHIP-BORNE",
     "The Seahawk hunts submarines from destroyers, lowering its dipping sonar "
     "into the water."),
    ("fleet/v22", "V-22 OSPREY", "TILTROTOR ASSAULT", "CAMP SAGA",
     "By August 2025 the whole Osprey fleet had moved to Camp Saga, closer to the "
     "brigade it carries."),
    ("fleet/p1", "P-1", "MARITIME PATROL", "40 IN SERVICE",
     "Forty P-1s: four engines, fly-by-light controls, and the first patrol "
     "aircraft built entirely in Japan."),
    ("fleet/p3c", "P-3C ORION", "MARITIME PATROL", "24 IN SERVICE",
     "The Orion hunted Soviet submarines through the Cold War. Twenty-four remain."),
    ("fleet/c2", "KAWASAKI C-2", "JET TRANSPORT", "HEAVY AIRLIFT",
     "The C-2 is the homegrown jet airlifter, built to carry heavy vehicles "
     "between scattered islands."),
    ("fleet/c130", "C-130H HERCULES", "TACTICAL AIRLIFT", "SINCE 1984",
     "The Hercules has served since 1984, and some now refuel rescue helicopters "
     "in flight."),
    ("fleet/kc767", "KC-767", "AERIAL REFUELLING", "FIRST TANKER",
     "Japan's first tanker, which quietly gave the force a reach it had never had."),
    ("fleet/kc46", "KC-46A PEGASUS", "REFUEL / CARGO", "AT MIHO",
     "And the newer Pegasus, whose camera-guided boom has had teething problems."),
    ("fleet/e767", "E-767 AWACS", "AIRBORNE RADAR", "4 AIRFRAMES",
     "Four E-767s lift a radar dome over the horizon and turn the fleet into one "
     "network."),
    ("fleet/e2d", "E-2D HAWKEYE", "CARRIER AEW", "18 ON ORDER",
     "Eighteen E-2Ds on order, doing the same job from smaller decks."),
    ("fleet/t4", "KAWASAKI T-4", "PILOT TRAINING", "SINCE 1988",
     "The T-4 has trained Japanese pilots for four decades, at a fraction of a "
     "fighter's cost."),
    ("fleet/us2", "SHINMAYWA US-2", "SEA RESCUE", "LANDS ON WATER",
     "The US-2 lands on open ocean to pull people out — and flies supplies to "
     "Antarctica."),
    ("fleet/rq4", "RQ-4B GLOBAL HAWK", "STRATEGIC ISR", "NO PILOT ABOARD",
     "And the Global Hawk: higher, and up longer, than anything with a pilot "
     "aboard."),
]
