# -*- coding: utf-8 -*-
"""
Storyboard: visual beats for every section.
Anchors A("...") are sub-strings of the section's narration; they resolve to the moment that phrase is
spoken (from build/timeline.json). 'trans' = cut | flash | xf (default cross-fade).
"""
import json, os
from common import BUILD, AMBER, RED, CYAN, GREEN, WHITE


def A(sub, nth=0, off=0.0):
    return ("A", sub, nth, off)


def low(name, sub, t, **kw):
    return dict(kind="lower", name=name, sub=sub, t=t, **kw)


def big(value, t, unit="KM/H", sub=None, t_sub=None, **kw):
    d = dict(kind="big", value=value, t=t, unit=unit, **kw)
    if sub:
        d["sub"] = sub
    if t_sub is not None:
        d["t_sub"] = t_sub
    return d


def chip(text, t, x=960, y=900, color=AMBER, **kw):
    return dict(kind="chip", text=text, t=t, x=x, y=y, color=color, **kw)


def stamp(text, t, x=960, y=540, color=RED, **kw):
    return dict(kind="stamp", text=text, t=t, x=x, y=y, color=color, **kw)


def typed(text, t, x=110, y=110, **kw):
    return dict(kind="type", text=text, t=t, x=x, y=y, **kw)


def txt(text, t, x=960, y=540, **kw):
    return dict(kind="text", text=text, t=t, x=x, y=y, **kw)


def call(text, t, p, l, **kw):
    return dict(kind="callout", text=text, t=t, p=p, l=l, **kw)


VIOLET = (220, 120, 255)
SB = {}

# ----------------------------------------------------------------------------------------- cold open
SB["intro"] = [
    dict(type="photo", image="lynx_record", z=(1.75, 1.95), c0=(0.30, 0.56), c1=(0.27, 0.56), shake=1.0, darken=0.1,
         overlays=[typed("11 AUGUST 1986", A("On the evening", off=0.3))]),
    dict(type="photo", at=A("a British military helicopter tore"), trans="flash", image="lynx_record", z=(1.02, 1.14),
         c0=(0.58, 0.52), c1=(0.47, 0.52), shake=1.2, speed=0.55, speed_dir=1,
         overlays=[typed("SOMERSET, ENGLAND", A("Somerset"), y=110),
                   big(400, A("at just over 400"), sub="≈ 250 MPH", t_sub=A("About 250"), x=1440, y=830, size=170)]),
    dict(type="photo", at=A("That's not the strange part"), image="lynx_record", z=(1.5, 1.62), c0=(0.33, 0.33),
         c1=(0.36, 0.33), darken=0.25, shake=0.6),
    dict(type="fact", at=A("The strange part is what"), image="museum", text="{}", roll=(1986, 2026, A("Forty years later", off=-0.6),
         A("Forty years later", off=1.4)), size=330, color=AMBER, top="OFFICIAL HELICOPTER SPEED RECORD",
         caption="NO CONVENTIONAL HELICOPTER HAS OFFICIALLY FLOWN FASTER", t_caption=A("no conventional helicopter")),
    dict(type="fact", at=A("So what is the fastest military helicopter"), image="defiant", text="?", size=430, color=AMBER,
         caption="THE FASTEST MILITARY HELICOPTER IN THE WORLD", t_caption=A("fastest military helicopter", off=0.3)),
    dict(type="four", at=A("Ask the internet"), header="ASK THE INTERNET: FOUR ANSWERS", bg="chinook", cards=[
        dict(image="chinook", c=(0.55, 0.55), z=1.7, title="CH-47F CHINOOK", sub="TWIN-ROTOR · FIRST FLEW 1961",
             t=A("A twin-rotor heavy lifter")),
        dict(image="hind", c=(0.68, 0.40), z=1.9, title="MI-24 HIND", sub="SOVIET 'FLYING TANK'", t=A("A Soviet gunship")),
        dict(image="lynx_record", c=(0.32, 0.56), z=1.9, title="G-LYNX", sub="BRITISH RECORD-BREAKER",
             t=A("That British record-breaker")),
        dict(image="v280_heli", c=(0.6, 0.30), z=1.7, title="MV-75 CHEYENNE II", sub="REPLACING THE BLACK HAWK",
             t=A("And a strange new machine"), stamp="NOT A HELICOPTER?", t_stamp=A("might not even count"),
             color=VIOLET, stamp_color=WHITE)],
         overlays=[stamp("THEY CAN'T ALL BE RIGHT", A("They can't all be right"), y=560, t_out=A("Or can they?", off=-0.05)),
                   stamp("...OR CAN THEY?", A("Or can they?"), y=560, color=AMBER)]),
    dict(type="speedo", at=A("To find out, we need"), title="TOP SPEED", sub="EVERY HELICOPTER HITS THE SAME WALL",
         wall=dict(t=A("invisible wall")),
         markers=[dict(label="CH-47F", v=315, vtext="315", t=A("To find out", off=0.2), level=0, dur=0.8),
                  dict(label="MI-24 (1978)", v=368.4, vtext="368", t=A("To find out", off=0.7), level=1, dur=0.8),
                  dict(label="G-LYNX (1986)", v=400.87, vtext="401", t=A("To find out", off=1.2), level=2, dur=0.8),
                  dict(label="X2", v=463, vtext="463", t=A("sixty-year race"), level=0, up=False, color=CYAN, dur=1.0),
                  dict(label="V-280", v=565, vtext="565", t=A("sixty-year race", off=0.7), level=1, up=False,
                       color=VIOLET, dur=1.0, left=True)]),
    dict(type="title", at="TITLE", image="lynx_record", trans="cut"),
]

# ----------------------------------------------------------------------------------------- answer 1: Chinook
SB["chinook"] = [
    dict(type="answer", image="chinook", n=1, label="THE GUINNESS ANSWER", trans="flash"),
    dict(type="photo", at=A("According to Guinness"), image="chinook", z=(1.0, 1.12), c0=(0.5, 0.5), c1=(0.53, 0.48),
         shake=0.8, overlays=[typed("SOURCE: GUINNESS WORLD RECORDS", A("According to Guinness", off=0.2), y=110),
                              low("BOEING CH-47F CHINOOK", "USA · TWIN-ROTOR HEAVY-LIFT HELICOPTER", A("Boeing CH-47F"),
                                  t_out=A("with a top speed", off=-0.2)),
                              big(315, A("top speed of 315"), sub="196 MPH", t_sub=A("or 196", off=-0.7), x=1400, y=850)]),
    dict(type="photo", at=A("At first, that sounds like a joke"), image="chinook", z=(1.55, 1.7), c0=(0.47, 0.56),
         c1=(0.5, 0.56), shake=0.6, overlays=[chip("A FLYING SCHOOL BUS?", A("flying school bus", off=-0.3), y=930, size=56)]),
    dict(type="stats", at=A("It can carry around"), image="chinook", header="THE FLYING SCHOOL BUS", items=[
        dict(value=55, label="TROOPS", sub="OR A SLUNG ARTILLERY PIECE", t=A("fifty-five troops")),
        dict(value=1961, count=False, fmt="{:.0f}", label="FIRST FLIGHT", sub="BASIC DESIGN", t=A("first flew back")),
        dict(value=1200, fmt="{:,.0f}+", label="BUILT", t=A("More than twelve hundred")),
        dict(value=20, fmt="{:.0f}+", label="COUNTRIES", sub="STILL FLY THEM", t=A("over twenty countries"))]),
    dict(type="photo", at=A("So how does a flying bus"), image="chinook", z=(1.2, 1.32), c0=(0.5, 0.42), c1=(0.5, 0.4),
         shake=0.6, overlays=[chip("HOW DOES A BUS KEEP UP WITH GUNSHIPS?", A("So how does a flying bus", off=0.4), y=950),
                              ]),
    dict(type="tandem", at=A("Most helicopters spend"), t_left=A("Most helicopters spend"), t_tail=A("small tail rotor"),
         t_right=A("The Chinook doesn't need one"), t_cancel=A("cancel each other out"), t_power=A("so all of that power")),
    dict(type="cards", at=A("But there's a catch"), image="chinook", header="NOT EVERYONE MEASURES TOP SPEED THE SAME WAY",
         items=[dict(head="TAS", title="TRUE AIRSPEED", body="How fast the aircraft actually moves through the air.",
                     t=A("true airspeed"), color=AMBER),
                dict(head="IAS", title="INDICATED AIRSPEED", body="What the cockpit gauge reads. Changes with altitude.",
                     t=A("indicated airspeed"), color=CYAN),
                dict(head="VNE", title="NEVER-EXCEED SPEED", body="A limit the pilot should never cross, not a cruise speed.",
                     t=A("never-exceed speed"), color=RED)],
         footer="SAME AIRCRAFT · DIFFERENT NUMBERS", t_footer=A("never-exceed speed", off=1.2)),
    dict(type="photo", at=A("On paper"), image="hind", z=(1.12, 1.22), c0=(0.6, 0.45), c1=(0.64, 0.44), shake=0.8,
         darken=0.15, overlays=[chip("ON PAPER, A FEW HELICOPTERS BEAT IT", A("On paper", off=0.2), y=200, color=WHITE),
                                chip("DEPENDS ON WHOSE SPREADSHEET YOU READ", A("depending on whose"), y=900)]),
    dict(type="answer", at=A("Which brings us to answer number two"), image="hind", n=2, label="THE SOVIET ANSWER",
         trans="flash"),
]

# ----------------------------------------------------------------------------------------- answer 2: Hind
SB["hind"] = [
    dict(type="photo", image="hind", z=(1.0, 1.1), c0=(0.55, 0.45), c1=(0.6, 0.42), shake=0.8,
         overlays=[typed("USSR · 1970s", A("In the 1970s", off=0.1)),
                   low("MIL MI-24 'HIND'", "USSR · ARMORED GUNSHIP + 8 TROOPS", A("The Mil Mi-24"))]),
    dict(type="photo", at=A("Its crews nicknamed"), image="hind", z=(1.7, 1.85), c0=(0.72, 0.38), c1=(0.75, 0.38),
         shake=0.8, overlays=[chip("'THE CROCODILE'", A("crocodile"), x=600, y=860, size=60),
                              chip("'THE FLYING TANK'", A("flying tank"), x=1320, y=860, size=60, color=RED, fg=WHITE)]),
    dict(type="photo", at=A("Tanks are not supposed"), image="hind", z=(1.35, 1.45), c0=(0.7, 0.42), c1=(0.68, 0.42),
         shake=0.6, overlays=[call("SLEEK BODY", A("sleek body"), (1240, 560), (1500, 760)),
                              call("RETRACTABLE GEAR", A("retractable landing gear"), (1080, 690), (700, 860)),
                              call("TWO TURBINE ENGINES", A("two powerful turbine"), (960, 380), (520, 230))]),
    dict(type="photo", at=A("And on September 21st"), image="hind", z=(1.12, 1.24), c0=(0.6, 0.45), c1=(0.66, 0.43),
         darken=0.1, shake=0.8, overlays=[typed("21 SEPTEMBER 1978", A("September 21st"))]),
    dict(type="photo", at=A("They took a modified Hind"), image="hind", z=(1.5, 1.4), c0=(0.62, 0.45), c1=(0.6, 0.44),
         shake=0.8, speed=0.35, speed_dir=-1,
         overlays=[chip("STUB WINGS REMOVED", A("removed its stub wings"), x=520, y=880),
                   chip("COVER NAME: A-10", A("gave it the cover name"), x=1360, y=880, color=WHITE),
                   typed("MEASURED COURSE NEAR MOSCOW", A("measured course"), y=110)]),
    dict(type="photo", at=A("at 368.4"), image="hind", z=(1.05, 1.15), c0=(0.55, 0.5), c1=(0.5, 0.5), darken=0.2,
         shake=0.8, overlays=[big(368.4, A("at 368.4"), dec=1, sub="229 MPH", t_sub=A("That's 229"), x=1420, y=830, size=180),
                              stamp("WORLD RECORD", A("new absolute speed record"), x=480, y=240, color=AMBER)]),
    dict(type="photo", at=A("Its modern descendant"), image="hind", z=(1.25, 1.12), c0=(0.62, 0.45), c1=(0.6, 0.45),
         shake=0.6, overlays=[low("MIL MI-35M", "MODERN DESCENDANT · STILL AMONG THE FASTEST GUNSHIPS", A("the Mi-35M"))]),
    dict(type="records", at=A("And for eight years"), title="HELICOPTER SPEED RECORDS", sub="ABSOLUTE SPEED, FAI",
         items=[dict(year=1978, v=368.4, label="MI-24 'A-10'", vtext="368.4 KM/H", t=A("And for eight years", off=0.2))],
         overlays=[chip("8 YEARS AT THE TOP", A("the Soviets owned the title"), x=1200, y=430)]),
    dict(type="answer", at=A("Then the British decided"), image="lynx_record", n=3, label="THE RECORD ANSWER", trans="flash"),
]

# ----------------------------------------------------------------------------------------- answer 3: G-Lynx
SB["lynx"] = [
    dict(type="photo", image="lynx_record", z=(1.35, 1.45), c0=(0.33, 0.55), c1=(0.36, 0.55), shake=0.8,
         overlays=[low("WESTLAND LYNX", "UK · BRITISH ARMY & ROYAL NAVY", A("The Westland Lynx"))]),
    dict(type="photo", at=A("In 1986, Westland took"), image="lynx_record", z=(1.04, 1.14), c0=(0.55, 0.52),
         c1=(0.45, 0.52), shake=1.0, speed=0.5, speed_dir=1,
         overlays=[chip("REGISTRATION: G-LYNX", A("registration G-Lynx"), x=1450, y=200, color=WHITE),
                   stamp("ROTOR-POWERED DRAGSTER", A("rotor-powered dragster"), x=1300, y=820, color=AMBER)]),
]

SB["lynxmods"] = [
    dict(type="list", image="lynx_record", c=(0.32, 0.55), z=(1.6, 1.7), header="BUILDING A RECORD-BREAKER", items=[
        dict(text="GEM 60 ENGINES", sub="EMERGENCY RATING: ABOUT 45% MORE POWER", t=A("Rolls-Royce Gem 60")),
        dict(text="WATER-METHANOL INJECTION", sub="AN EXTRA BOOST", t=A("water-methanol")),
        dict(text="RESHAPED EXHAUSTS", sub="BONUS THRUST", t=A("reshaped the exhausts")),
        dict(text="BORROWED TAIL SURFACES", sub="FROM ANOTHER WESTLAND HELICOPTER", t=A("borrowed tail surfaces")),
        dict(text="BERP ROTOR BLADES", sub="THE REAL SECRET", t=A("But the real secret"))]),
    dict(type="berp", at=A("G-Lynx carried experimental"), t_conv=A("G-Lynx carried experimental"),
         t_berp=A("called BERP blades"), t_paddle=A("paddle-shaped tips"), t_swept=A("swept back like"),
         t_mod=A("together with the UK Ministry")),
]

SB["record"] = [
    dict(type="photo", image="lynx_record", z=(1.0, 1.1), c0=(0.5, 0.5), c1=(0.44, 0.5), shake=0.8, warmth=0.6,
         overlays=[low("TREVOR EGGINTON", "TEST PILOT", A("test pilot Trevor"), t_out=A("flight test engineer")),
                   low("DEREK CLEWS", "FLIGHT TEST ENGINEER", A("flight test engineer", off=0.2))]),
    dict(type="course", at=A("lined up on a fifteen"), t_line=A("fifteen-kilometer course"), t_run1=A("and flew it twice"),
         t_run2=A("in opposite directions"), t_wind=A("so the wind couldn't help"), t_avg=A("Their average was")),
    dict(type="photo", at=A("On one of the runs"), image="lynx_record", z=(1.08, 1.18), c0=(0.55, 0.52), c1=(0.47, 0.52),
         shake=1.2, speed=0.6, speed_dir=1,
         overlays=[big(413, A("touched almost 413"), sub="FASTEST SINGLE RUN (ALMOST)", x=1420, y=830, size=170)]),
    dict(type="speedo", at=A("It smashed the Hind"), title="ABSOLUTE SPEED RECORD", sub="HELICOPTERS",
         markers=[dict(label="MI-24 'A-10' (1978)", v=368.4, vtext="368.4", t=A("It smashed the Hind"), level=1, dur=0.8,
                       color=WHITE, left=True),
                  dict(label="G-LYNX (1986)", v=400.87, vtext="400.87", t=A("It smashed the Hind", off=0.7), level=0,
                       dur=0.9)],
         overlays=[stamp("STILL STANDS", A("and it still stands"), x=1300, y=300, color=AMBER)]),
    dict(type="fact", at=A("The FAI, the body"), image="museum", top="FAI · ABSOLUTE SPEED RECORD · HELICOPTERS",
         text="400.87 KM/H", size=210, color=AMBER, caption="WESTLAND LYNX 'G-LYNX' · 11 AUGUST 1986 · STILL CURRENT",
         t_caption=A("still lists it")),
    dict(type="photo", at=A("So officially"), image="lynx_record", z=(1.2, 1.3), c0=(0.4, 0.53), c1=(0.37, 0.53),
         shake=0.8, speed=0.3, speed_dir=1,
         overlays=[chip("OFFICIALLY: THE FASTEST HELICOPTER FLIGHT EVER", A("the fastest helicopter flight", off=0.2), y=940)]),
    dict(type="photo", at=A("And there's one detail"), image="lynx_record", z=(1.9, 2.05), c0=(0.36, 0.38),
         c1=(0.34, 0.38), shake=0.8, darken=0.15,
         overlays=[txt("MACH 0.97", A("Mach 0.97"), y=760, font="title", size=180, color=AMBER, glow=True),
                   txt("97% OF THE SPEED OF SOUND", A("ninety-seven percent"), y=900, font="cx", size=56)]),
]

# ----------------------------------------------------------------------------------------- the wall
SB["wall"] = [
    dict(type="photo", image="lynx_record", z=(1.7, 1.9), c0=(0.36, 0.36), c1=(0.38, 0.34), shake=0.8, darken=0.1),
    dict(type="rotor", at=A("In a hover"), title="THE ROTOR FROM ABOVE", sub="WESTLAND LYNX · HOVER",
         t_hover=A("the blade tips are already"), v_ramp=(A("Now fly forward", off=1.0), A("Now fly forward", off=1.01), 0, 0)),
    dict(type="rotor", at=A("On one side, the advancing"), title="FORWARD FLIGHT", sub="AIRSPEED = ROTATION ± FLIGHT SPEED",
         v_ramp=(A("On one side, the advancing", off=0.3), A("At 400 kilometers per hour", off=0.6), 0, 400),
         t_adv=A("the advancing blade"), t_ret=A("the retreating blade"), t_mach=A("right at the edge"),
         t_rev=A("The air actually flows")),
]

SB["stall"] = [
    dict(type="airfoil", mode="shock", aoa=(2, 2), title="PROBLEM 1: ADVANCING SIDE", sub="BLADE TIP NEAR MACH 1",
         t_labels=[A("shock waves start"), A("drag, vibration"), A("vibration and noise"), A("noise shoot up")],
         labels=["SHOCK WAVES", "MORE DRAG", "MORE VIBRATION", "MORE NOISE"]),
    dict(type="airfoil", at=A("On the retreating side"), mode="stall", aoa=(5, 21),
         t_tilt=(A("has to tilt"), A("Tilt it too far", off=1.2)), t_stall=A("the airflow tears away"),
         title="PROBLEM 2: RETREATING SIDE", sub="SLOW BLADE · STEEPER ANGLE",
         t_labels=[A("That's called retreating blade stall")], labels=["RETREATING BLADE STALL"]),
    dict(type="photo", at=A("The nose pitches up"), image="chinook", z=(1.15, 1.3), c0=(0.5, 0.5), c1=(0.5, 0.45),
         shake=3.0, darken=0.15,
         overlays=[chip("NOSE PITCHES UP", A("The nose pitches up"), x=520, y=200),
                   chip("THE HELICOPTER ROLLS", A("the helicopter rolls"), x=1400, y=200),
                   chip("LOSS OF CONTROL", A("the pilot can lose control"), y=900, color=RED, fg=WHITE, size=60)]),
]

SB["trap"] = [
    dict(type="trap", t_a=A("So why not spin"), t_red=A("So why not spin", off=0.2), t_b=A("Slow it down"),
         t_blue=A("Slow it down", off=0.2), t_c=A("Engineers are trapped"), t_typ=A("tops out around 300"),
         t_lynx=A("why G-Lynx needed"), t_wall=A("It's a wall")),
]

# ----------------------------------------------------------------------------------------- compound helicopters
SB["compound"] = [
    dict(type="jobs", t_lift=A("it lifts the aircraft"), t_thrust=A("pulls it forward"), t_steer=A("and steers it"),
         t_wing=A("Wings take over"), t_prop=A("and a propeller does the pushing"), t_relax=A("so the rotor can relax")),
    dict(type="photo", at=A("The US Army tried this"), image="cheyenne", z=(1.0, 1.1), c0=(0.45, 0.5), c1=(0.4, 0.5),
         shake=1.0, speed=0.35, speed_dir=1,
         overlays=[low("LOCKHEED AH-56 CHEYENNE", "USA · FIRST FLIGHT 1967", A("Lockheed AH-56")),
                   call("STUBBY WINGS", A("stubby wings"), (720, 590), (480, 330)),
                   call("PUSHER PROPELLER", A("pusher propeller", off=-0.4), (1335, 470), (1450, 250))]),
    dict(type="photo", at=A("It reached about 215"), image="cheyenne", z=(1.3, 1.4), c0=(0.35, 0.5), c1=(0.32, 0.5),
         shake=0.8, speed=0.4, speed_dir=1,
         overlays=[big(215, A("about 215 knots"), unit="KNOTS", sub="≈ 400 KM/H · LATE 1960s", x=1400, y=830, size=170)]),
    dict(type="photo", at=A("But it was expensive"), image="cheyenne", z=(1.12, 1.2), c0=(0.45, 0.5), c1=(0.45, 0.5),
         darken=0.3, shake=0.5,
         overlays=[chip("EXPENSIVE", A("expensive"), x=480, y=200, color=WHITE),
                   chip("COMPLICATED", A("complicated"), x=960, y=200, color=WHITE),
                   chip("LATE", A("and late"), x=1440, y=200, color=WHITE),
                   stamp("CANCELED · AUGUST 1972", A("the Army canceled it"), y=640)]),
    dict(type="fact", at=A("Remember that name"), image="cheyenne", text="CHEYENNE", size=250, color=AMBER,
         caption="REMEMBER THAT NAME", t_caption=A("Remember that name", off=0.4)),
]

SB["x2"] = [
    dict(type="photo", image="x2", z=(1.1, 1.0), c0=(0.5, 0.55), c1=(0.47, 0.55), shake=0.8,
         overlays=[low("SIKORSKY X2", "USA · TECHNOLOGY DEMONSTRATOR", A("Its X2 demonstrator"))]),
    dict(type="rotor", at=A("two rigid rotors stacked"), mode="coax", title="COAXIAL RIGID ROTORS",
         sub="THE ADVANCING BLADE CONCEPT",
         v_ramp=(A("two rigid rotors stacked", off=1.0), A("the X2 slowed its rotors", off=2.5), 0, 463),
         t_adv=A("there's always an advancing blade"), slow=(A("the X2 slowed its rotors"),
                                                              A("the X2 slowed its rotors", off=2.5), 600),
         overlays=[chip("PLUS A PUSHER PROPELLER IN THE TAIL", A("while a propeller in the tail"), y=1000, color=AMBER)]),
    dict(type="photo", at=A("On September 15th, 2010"), image="x2", z=(1.02, 1.12), c0=(0.55, 0.55), c1=(0.47, 0.55),
         shake=1.2, speed=0.55, speed_dir=1,
         overlays=[typed("15 SEPTEMBER 2010", A("September 15th")),
                   big(250, A("it reached 250 knots"), unit="KNOTS", sub="≈ 463 KM/H · LEVEL FLIGHT", x=1400, y=830, size=170),
                   stamp("UNOFFICIAL", A("never made official"), x=1380, y=330, color=CYAN)]),
    dict(type="photo", at=A("The team still won"), image="x2", z=(1.35, 1.45), c0=(0.42, 0.6), c1=(0.4, 0.6), shake=0.6,
         overlays=[chip("COLLIER TROPHY", A("Collier Trophy"), y=900, size=60)]),
    dict(type="records", at=A("Three years later"), title="THE SPEED RACE", sub="RECORDS VS UNOFFICIAL MARKS",
         t_line=A("Three years later", off=0.2),
         items=[dict(year=1978, v=368.4, label="MI-24", vtext="368.4", t=A("Three years later", off=0.1), dy=-80),
                dict(year=1986, v=400.87, label="G-LYNX", vtext="400.87", t=A("Three years later", off=0.1), dy=-90),
                dict(year=2010, v=463, label="X2", vtext="463", kind="unofficial", t=A("Three years later", off=0.4),
                     left=True, dy=-60),
                dict(year=2013, v=472, label="EUROCOPTER X3", vtext="472", kind="unofficial",
                     t=A("pushed that unofficial mark"), dy=-80)]),
    dict(type="photo", at=A("Sikorsky turned the X2 idea"), image="defiant", z=(1.3, 1.2), c0=(0.5, 0.45),
         c1=(0.5, 0.45), shake=0.8, darken=0.1,
         overlays=[chip("SIKORSKY S-97 RAIDER · LIGHT SCOUT", A("First the S-97 Raider"), y=200, color=WHITE)]),
    dict(type="photo", at=A("Then, together with Boeing"), image="defiant", z=(1.0, 1.1), c0=(0.5, 0.5), c1=(0.53, 0.5),
         shake=0.8, overlays=[low("SIKORSKY-BOEING SB-1 DEFIANT", "BUILT TO REPLACE THE BLACK HAWK", A("SB-1 Defiant"))]),
    dict(type="photo", at=A("In October 2021"), image="defiant", z=(1.15, 1.28), c0=(0.55, 0.5), c1=(0.47, 0.5),
         shake=1.2, speed=0.5, speed_dir=-1,
         overlays=[big(247, A("Defiant hit 247"), unit="KNOTS", sub="≈ 457 KM/H · LEVEL FLIGHT", x=1400, y=830, size=170),
                   chip("POWER STILL IN RESERVE", A("still engine power left"), x=600, y=200)]),
    dict(type="photo", at=A("In Europe, Airbus"), image="racer", z=(1.0, 1.1), c0=(0.5, 0.55), c1=(0.55, 0.55),
         shake=0.8, overlays=[low("AIRBUS RACER", "EUROPE · HIGH-SPEED DEMONSTRATOR", A("Racer demonstrator")),
                              big(444, A("reached 444"), x=1420, y=200, size=150)]),
    dict(type="speedo", at=A("The wall had been broken"), title="THE WALL IS BROKEN", sub="UNOFFICIAL / DEMONSTRATORS",
         wall=dict(t=A("The wall had been broken", off=-0.3)),
         markers=[dict(label="G-LYNX", v=400.87, vtext="400.87", t=A("The wall had been broken", off=-0.2), level=2,
                       left=True, dur=0.6),
                  dict(label="RACER", v=444, vtext="444", t=A("The wall had been broken", off=0.2), level=0, left=True, dur=0.7),
                  dict(label="DEFIANT", v=457, vtext="457", t=A("The wall had been broken", off=0.5), level=1, dur=0.7,
                       color=GREEN),
                  dict(label="X2", v=463, vtext="463", t=A("The wall had been broken", off=0.8), level=0, up=False,
                       left=True, color=CYAN, dur=0.7),
                  dict(label="X3", v=472, vtext="472", t=A("The wall had been broken", off=1.1), level=0, up=False,
                       color=CYAN, dur=0.7)],
         overlays=[chip("SO WHY ISN'T THE ARMY FLYING THEM?", A("So why isn't the Army"), y=1000, color=WHITE, size=50)]),
]

# ----------------------------------------------------------------------------------------- answer 4: tiltrotor
SB["tiltrotor"] = [
    dict(type="answer", image="v280_plane", n=4, label="THE TILTROTOR ANSWER", trans="flash"),
    dict(type="tilt", at=A("Instead of helping the rotor"), t_tilt=(A("then tilts its rotors", off=0.2),
                                                                     A("then tilts its rotors", off=2.6)),
         overlays=[chip("BELL-BOEING V-22 OSPREY · US MARINES", A("V-22 Osprey"), y=880, color=WHITE)]),
    dict(type="photo", at=A("And in December 2017"), image="v280_plane", z=(1.0, 1.1), c0=(0.5, 0.5), c1=(0.45, 0.5),
         shake=0.8, overlays=[low("BELL V-280 VALOR", "FIRST FLIGHT · DECEMBER 2017", A("the V-280 Valor"))]),
    dict(type="photo", at=A("In testing, it reached"), image="v280_plane", z=(1.2, 1.32), c0=(0.45, 0.55),
         c1=(0.38, 0.55), shake=1.2, speed=0.55, speed_dir=1,
         overlays=[big(305, A("305 knots"), unit="KNOTS", sub="≈ 565 KM/H · 350 MPH", x=1400, y=830, size=170)]),
    dict(type="speedo", at=A("faster than any helicopter has"), title="TOP SPEED", sub="TILTROTOR VS HELICOPTERS",
         wall=dict(t=A("faster than any helicopter has", off=-0.2)),
         markers=[dict(label="G-LYNX", v=400.87, vtext="400.87", t=A("faster than any helicopter has", off=-0.1),
                       level=1, dur=0.6, left=True),
                  dict(label="X3 (UNOFFICIAL)", v=472, vtext="472", t=A("faster than any helicopter has", off=0.2),
                       level=0, up=False, color=CYAN, dur=0.6, left=True),
                  dict(label="V-280 VALOR", v=565, vtext="565", t=A("faster than any helicopter has", off=0.5),
                       level=0, color=VIOLET, dur=1.0, left=True)]),
    dict(type="stats", at=A("The production version"), image="v280_heli", header="MV-75 · DESIGNED TO CARRY", items=[
        dict(value=14, label="SOLDIERS", t=A("fourteen soldiers")),
        dict(value=300, fmt="{:.0f}+", label="MPH", sub="MORE THAN 480 KM/H", t=A("more than 300 miles"))]),
    dict(type="photo", at=A("In December 2022"), image="v280_heli", z=(1.0, 1.1), c0=(0.5, 0.45), c1=(0.5, 0.42),
         shake=0.8, overlays=[typed("DECEMBER 2022", A("In December 2022", off=0.1)),
                              chip("V-280 WINS · DEFIANT LOSES", A("chose the V-280 over"), y=200, x=1400, color=WHITE),
                              txt("THE ARMY'S BIGGEST HELICOPTER DECISION IN 40 YEARS", A("biggest helicopter decision"),
                                  y=960, font="cx", size=58)]),
    dict(type="photo", at=A("Then, in February 2024"), image="racer", z=(1.25, 1.35), c0=(0.5, 0.5), c1=(0.5, 0.5),
         darken=0.35, shake=0.5, teal=0.6,
         overlays=[stamp("SCOUT PROGRAM CANCELED · FEB 2024", A("canceled its future scout"), y=480, size=70),
                   chip("'DRONES CHANGED AERIAL RECONNAISSANCE'", A("saying drones"), y=820, color=WHITE)]),
    dict(type="photo", at=A("The fastest compound helicopters"), image="x2", z=(1.2, 1.3), c0=(0.45, 0.55),
         c1=(0.45, 0.55), darken=0.35, teal=0.6, shake=0.4,
         overlays=[chip("LEFT WITHOUT A BUYER", A("left without a buyer"), y=880, color=RED, fg=WHITE, size=56)]),
    dict(type="photo", at=A("And in April 2026"), image="v280_heli", z=(1.15, 1.02), c0=(0.55, 0.38), c1=(0.5, 0.42),
         shake=0.8, overlays=[typed("APRIL 2026", A("And in April 2026", off=0.1)),
                              txt("MV-75 CHEYENNE II", A("the MV-75 Cheyenne II"), y=860, font="title", size=150,
                                  color=WHITE, glow=True)]),
    dict(type="split", at=A("It honors the Cheyenne"),
         left=dict(image="cheyenne", c=(0.4, 0.5), z=1.4, title="AH-56 CHEYENNE", sub="1967 · CANCELED 1972",
                   t=A("a nod to that canceled"), color=RED),
         right=dict(image="v280_plane", c=(0.4, 0.5), z=1.4, title="MV-75 CHEYENNE II", sub="NAMED APRIL 2026",
                    t=A("It honors the Cheyenne"))),
    dict(type="photo", at=A("More than half a century"), image="v280_plane", z=(1.0, 1.1), c0=(0.5, 0.5), c1=(0.45, 0.5),
         shake=0.6, overlays=[txt("A SECOND CHANCE", A("gets a second chance"), y=900, font="title", size=120,
                                  color=AMBER, glow=True)]),
]

# ----------------------------------------------------------------------------------------- verdict
SB["verdict"] = [
    dict(type="fact", image="lynx_record", text="IT DEPENDS", size=250, color=AMBER, trans="flash",
         caption="ON WHAT YOU CALL A HELICOPTER", t_caption=A("on what you call")),
    dict(type="four", at=A("If you want the official title"), header="THE VERDICT", bg="museum", cards=[
        dict(image="chinook", c=(0.55, 0.55), z=1.7, value="315 KM/H", title="CH-47F CHINOOK", sub="OFFICIAL · IN SERVICE",
             t=A("If you want the official title")),
        dict(image="lynx_record", c=(0.32, 0.56), z=1.9, value="400.87", title="G-LYNX", sub="FASTEST CERTIFIED FLIGHT",
             t=A("If you want the fastest helicopter flight")),
        dict(image="x2", c=(0.45, 0.6), z=1.8, value="463 KM/H", title="X2 / DEFIANT", sub="EXPERIMENTAL · UNOFFICIAL",
             t=A("If you count experimental"), color=CYAN),
        dict(image="v280_heli", c=(0.6, 0.30), z=1.7, value="565 KM/H", title="MV-75 CHEYENNE II",
             sub="TILTROTOR · NOT A HELICOPTER", t=A("And if you just want"), color=VIOLET)]),
    dict(type="rotor", at=A("Every one of them"), title="THE SAME ENEMY", sub="ONE SIDE TOO FAST, THE OTHER TOO SLOW",
         v_ramp=(A("Every one of them", off=-1.0), A("Every one of them", off=-0.9), 400, 400),
         t_adv=A("can't go faster than sound"), t_ret=A("can't slow down"), t_mach=A("can't go faster than sound", off=0.8)),
    dict(type="photo", at=A("As for the record holder"), image="museum", z=(1.0, 1.1), c0=(0.5, 0.55), c1=(0.52, 0.55),
         overlays=[low("THE HELICOPTER MUSEUM", "WESTON-SUPER-MARE, ENGLAND", A("It sits in a helicopter museum"))]),
    dict(type="photo", at=A("still waiting for a conventional"), image="museum", z=(1.45, 1.6), c0=(0.45, 0.55),
         c1=(0.42, 0.55), overlays=[txt("UNBEATEN SINCE 1986", A("to take its crown"), y=900, font="title", size=110,
                                        color=AMBER, glow=True)]),
    dict(type="end", at=A("If you enjoyed this"), t_sub=A("subscribe"), cards=[
        dict(image="chinook", c=(0.55, 0.55), z=1.5, title="CH-47F CHINOOK", sub="315 KM/H"),
        dict(image="lynx_record", c=(0.32, 0.56), z=1.6, title="G-LYNX", sub="400.87 KM/H"),
        dict(image="x2", c=(0.45, 0.6), z=1.5, title="X2 / DEFIANT", sub="463 KM/H", color=CYAN),
        dict(image="v280_heli", c=(0.6, 0.30), z=1.5, title="MV-75", sub="565 KM/H", color=VIOLET)]),
]


# =================================================================== resolution
def load_timeline():
    return json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))


def anchor_time(sec, sub, nth=0, off=0.0):
    text = sec["text"]
    i = -1
    for _ in range(nth + 1):
        i = text.find(sub, i + 1)
        if i < 0:
            raise KeyError(f"anchor not found in {sec['id']}: {sub!r}")
    cm = sec["cmap"]
    for k in range(len(cm) - 1):
        if cm[k][0] <= i <= cm[k + 1][0]:
            c0, t0 = cm[k]
            c1, t1 = cm[k + 1]
            return t0 + (t1 - t0) * (i - c0) / max(1, (c1 - c0)) + off
    return cm[-1][1] + off


def resolve(obj, sec):
    if isinstance(obj, tuple) and len(obj) == 4 and obj[0] == "A":
        return anchor_time(sec, obj[1], obj[2], obj[3])
    if isinstance(obj, dict):
        return {k: resolve(v, sec) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [resolve(v, sec) for v in obj]
    return obj


LEAD = 0.2   # visual cut slightly before the voice


def build_shots():
    tl = load_timeline()
    secs = tl["sections"]
    out = []
    for si, sec in enumerate(secs):
        specs = SB[sec["id"]]
        sec_start = sec["start"] - LEAD if si > 0 else 0.0
        resolved = []
        for sp in specs:
            sp = dict(sp)
            at = sp.pop("at", None)
            if at == "TITLE":
                t0 = sec["title_at"] - 0.1
            elif at is None:
                t0 = sec_start
            else:
                t0 = resolve(at, sec) - LEAD
            sp = resolve(sp, sec)
            resolved.append((t0, sp))
        resolved.sort(key=lambda x: x[0])
        fixed = []
        for t0, sp in resolved:
            if fixed:
                t0 = max(t0, fixed[-1][0] + 1.4)
            fixed.append((t0, sp))
        for t0, sp in fixed:
            out.append(dict(start=round(min(t0, sec["end"] - 0.8), 3), section=sec["id"], **sp))
    for k in range(len(out)):
        out[k]["end"] = out[k + 1]["start"] if k + 1 < len(out) else tl["duration"]
    return out, tl


if __name__ == "__main__":
    shots, tl = build_shots()
    for s in shots:
        flag = "  <-- SHORT" if s["end"] - s["start"] < 1.5 else ("  <-- LONG" if s["end"] - s["start"] > 16 else "")
        print(f'{s["start"]:8.2f} {s["end"] - s["start"]:6.2f}  {s["section"]:10s} {s["type"]:8s} {s.get("image", "")}{flag}')
    d = [s["end"] - s["start"] for s in shots]
    print(len(shots), "shots; mean %.1f s; duration %.1f" % (sum(d) / len(d), tl["duration"]))
