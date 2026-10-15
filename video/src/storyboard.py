# -*- coding: utf-8 -*-
"""
Storyboard: visual beats for every section.
Anchors A("…") are sub-strings of the section's narration; they resolve to the
moment that phrase is spoken (from build/timeline.json).
"""
import json, os
from common import BUILD, GOLD, TEAL, CORAL, WHITE

ERA_AR = "مصري قديم"; ERA_CO = "قبطي"; ERA_GR = "يوناني"; ERA_RO = "روماني"; ERA_AB = "عربي"
ERA_OT = "عثماني"; ERA_MO = "حديث"


def A(sub, nth=0, off=0.0):
    return ("A", sub, nth, off)


def cap(name, side="up", t=None, label=None):
    d = dict(name=name, side=side)
    if t is not None:
        d["t"] = t
    if label:
        d["label"] = label
    return d


# governorate numbering shown in the badge
NUM = dict(cairo="١", giza="٢", alex="٣", portsaid="٤", ismailia="٥", suez="٦", damietta="٧", dakahlia="٨",
           sharqia_gharbia="٩ و ١٠", beheira="١١", qalyubia="١٢", monufia="١٣", kafrelsheikh="١٤", benisuef="١٥",
           faiyum="١٦", minya="١٧", asyut="١٨", sohag="١٩", qena="٢٠", luxor="٢١", aswan="٢٢", redsea="٢٣",
           newvalley="٢٤", matrouh="٢٥", sinai="٢٦ و ٢٧")

SB = {}

# ------------------------------------------------------------------ INTRO
SB["intro"] = [
    dict(type="image", image="intro_mars_desert", zoom_in=True,
         overlays=[dict(kind="chip", text="اسمها جاي من كوكب؟!", color=GOLD, x=960, y=930, size=60, t=A("كوكب"))]),
    dict(type="meaning", at=A("ومحافظة تانية"), bg="map:EG-FYM", word="البحر", word_size=200,
         meaning="محافظة اسمها معناه «البحر»", note="ومفيهاش أي شط على البحر!", ts=[A("ومحافظة تانية"), A("اسمها معناه"), A("وهي أصلًا")]),
    dict(type="ledger", at=A("وتالتة"), bg="gradient", header="دفاتر المساحة — من حوالي ٥٠٠ سنة",
         old="اسم قديم", new="اسم جديد", caption="اسم جاي من غلطة في الدفاتر؟!",
         ts=[A("وتالتة", off=0.3), A("غلطة"), A("دفاتر المساحة", off=0.4)]),
    dict(type="map", at=A("مصر فيها سبعة وعشرين"), frame_=(30.8, 26.9, 19.5), sweep=True, sweep_t0=0.1, sweep_dur=2.4,
         overlays=[dict(kind="text", text="٢٧ محافظة", size=120, color=GOLD, x=330, y=200, t=A("سبعة وعشرين", off=0.2))]),
    dict(type="map", at=A("رايح المنوفية"), codes=["EG-MNF"], frame_=(30.9, 28.6, 12.5),
         overlays=[dict(kind="chip", text="المنوفية", color=GOLD, x=1500, y=240, size=58, t=A("رايح المنوفية"))]),
    dict(type="map", at=A("راجع من أسيوط"), codes=["EG-AST"], frame_=(30.9, 28.6, 12.5),
         overlays=[dict(kind="chip", text="أسيوط", color=GOLD, x=1500, y=240, size=58, t=A("راجع من أسيوط"))]),
    dict(type="map", at=A("مصيّف في مطروح"), codes=["EG-MT"], frame_=(30.9, 28.6, 12.5),
         overlays=[dict(kind="chip", text="مطروح", color=GOLD, x=1500, y=240, size=58, t=A("مصيّف في مطروح"))]),
    dict(type="fact", at=A("بس عمرك سألت نفسك"), bg="map:", text="؟", big_size=420,
         caption="الأسامي دي جت منين؟", ts=[A("بس عمرك"), A("الأسامي دي")]),
    dict(type="title", at="TITLE", bg="gradient", text="ليه محافظات مصر اتسمّت بالأسماء دي؟", sub="٢٧ محافظة .. ٢٧ حكاية"),
    dict(type="image", at=A("الحقيقة"), image="intro_layers", zoom_in=False,
         overlays=[dict(kind="chip", text="مصري قديم", color=(233, 185, 73), x=1560, y=170, size=50, t=A("أسامي مصرية قديمة")),
                   dict(kind="chip", text="قبطي", color=(93, 173, 226), x=1180, y=170, size=50, t=A("نطقها القبط")),
                   dict(kind="chip", text="يوناني", color=(186, 160, 255), x=840, y=170, size=50, t=A("وغيّر فيها اليونان")),
                   dict(kind="chip", text="عربي", color=(52, 195, 143), x=500, y=170, size=50, t=A("العرب ظبطوها"))]),
    dict(type="list", at=A("وأسامي تانية جاية من حكام"), bg="map:", heading="منين جت الأسامي؟",
         items=["لغات قديمة: مصري وقبطي ويوناني", "حكام وملوك", "الجغرافيا ومكانها على الخريطة"],
         ts=[A("وأسامي تانية", off=-0.2), A("حكام وملوك"), A("الجغرافيا")]),
    dict(type="map", at=A("والنهارده هنلف"), frame_=(30.8, 26.9, 19.5), gov_labels=True, gov_label_size=22,
         skip_labels=("EG-KB", "EG-MNF", "EG-GH", "EG-PTS", "EG-DT", "EG-IS", "EG-KFS", "EG-C", "EG-LX"),
         gov_labels_t=A("والنهارده هنلف", off=0.3), gov_label_step=0.09,
         overlays=[dict(kind="text", text="يلا بينا!", size=100, color=GOLD, x=1600, y=180, t=A("فخليك معانا"))]),
]

# ------------------------------------------------------------------ CAIRO
SB["cairo"] = [
    dict(type="map", codes=["EG-C"], title="القاهرة", pins=[cap("الفسطاط", "down", A("القاهرة"))], min_span=2.0),
    dict(type="image", at=A("سنة تسعمية"), image="cairo_jawhar",
         overlays=[dict(kind="chip", text="٩٦٩ م", color=GOLD, x=230, y=140, size=56, t=A("سنة تسعمية")),
                   dict(kind="lower", title="جوهر الصقلي", sub="قائد جيوش الخليفة الفاطمي المعز لدين الله", t=A("جوهر"))]),
    dict(type="chain", at=A("وفي الأول، المدينة"), bg="cairo_jawhar", heading="الاسم الأول للمدينة",
         items=[("المنصورية", "الاسم الأول"), ("القاهرة", "الاسم اللي فضل")], ts=[A("المنصورية"), A("طب القاهرة")]),
    dict(type="image", at=A("فيه حكاية مشهورة"), image="cairo_crow_bells", pan=(0.35, -0.2),
         overlays=[dict(kind="chip", text="حكاية شعبية", color=CORAL, x=250, y=140, size=48, t=A("فيه حكاية")),
                   dict(kind="chip", text="غراب على الحبال!", color=WHITE, x=1180, y=330, size=50, t=A("نزل غراب"))]),
    dict(type="image", at=A("وفي اللحظة دي"), image="intro_mars_desert", zoom_in=False, pan=(0.3, -0.3),
         overlays=[dict(kind="chip", text="حكاية شعبية", color=CORAL, x=250, y=140, size=48, t=A("وفي اللحظة دي")),
                   dict(kind="lower", title="المريخ = «القاهر»", sub="فاتسمت المدينة القاهرة", t=A("كوكب المريخ"))]),
    dict(type="meaning", at=A("بس الأرجح"), bg="cairo_muizz", badge="الرأي الأرجح", badge_color=TEAL,
         word="القاهرة", meaning="المدينة المنتصرة اللي بتقهر أعداءها", note="المعز غيّر الاسم لما وصل مصر سنة ٩٧٣ م",
         ts=[A("بس الأرجح", off=0.3), A("يعني المدينة"), A("لما وصل مصر")]),
    dict(type="image", at=A("ومن ساعتها"), image="cairo_muizz", zoom_in=False,
         overlays=[dict(kind="lower", title="قاهرة المعز", sub="ومن هنا الاسم اللي عايش لحد النهارده", t=A("ومن ساعتها", off=0.2))]),
    dict(type="quote", at=A("وعلى فكرة"), bg="cairo_muizz", top="على فكرة", quote="«أنا نازل مصر»", attrib="يعني: أنا رايح القاهرة!",
         ts=[A("نازل مصر"), A("يقصد القاهرة")]),
]

# ------------------------------------------------------------------ GIZA
SB["giza"] = [
    dict(type="map", codes=["EG-GZ"], title="الجيزة", pins=[cap("الجيزة", "left", A("الجيزة"))]),
    dict(type="image", at=A("بعد ما عمرو"), image="giza_crossing", pan=(-0.3, 0.0),
         overlays=[dict(kind="chip", text="٦٤١ م", color=GOLD, x=230, y=140, size=56, t=A("سنة ستمية")),
                   dict(kind="lower", title="عبور النيل للبر الغربي", sub="بعد فتح حصن بابليون", t=A("عدّوا النيل"))]),
    dict(type="meaning", at=A("وكلمة الجيزة"), bg="giza_crossing", word="الجيزة", meaning="الناحية .. جانب الوادي",
         note="من نفس جذر «جاز» يعني عدّى", ts=[A("وكلمة الجيزة"), A("معناها الناحية"), A("من نفس جذر")]),
    dict(type="image", at=A("والطريف"), image="giza_pyramids",
         overlays=[dict(kind="chip", text="الأهرامات أقدم من الاسم بـ +٣٠٠٠ سنة", color=GOLD, x=960, y=930, size=58,
                        t=A("الأهرامات أكبر"))]),
]

# ------------------------------------------------------------------ ALEXANDRIA
SB["alex"] = [
    dict(type="map", codes=["EG-ALX"], title="الإسكندرية", pins=[cap("الإسكندرية", "down", A("الإسكندرية"))], min_span=2.6),
    dict(type="image", at=A("ودي حكايتها"), image="alex_founding", pan=(0.25, 0.0),
         overlays=[dict(kind="chip", text="٣٣١ ق.م", color=GOLD, x=230, y=140, size=56, t=A("سنة تلتمية")),
                   dict(kind="lower", title="الإسكندر الأكبر", sub="وقرية صيادين اسمها «راقودة»", t=A("وقف الإسكندر"))]),
    dict(type="list", at=A("والإسكندر كان عنده"), bg="alex_founding", heading="مدن اتسمّت على اسم الإسكندر",
         items=["الإسكندرية .. مصر", "إسكندرون .. تركيا", "هرات .. أفغانستان", "خُجند .. طاجيكستان"],
         ts=[A("كان بيسمي"), A("في كل حتة"), A("من مصر لحد"), A("آسيا الوسطى")]),
    dict(type="image", at=A("والمفارقة"), image="alex_founding", zoom_in=False, pan=(-0.4, 0.1),
         overlays=[dict(kind="lower", title="ساب مصر بعد شهور", sub="ومات من غير ما يشوف مدينته مكتملة", t=A("والمفارقة", off=0.2))]),
]

# ------------------------------------------------------------------ PORT SAID
SB["portsaid"] = [
    dict(type="map", codes=["EG-PTS", "EG-IS"], title="مدن القناة", frame_=(32.3, 30.75, 3.6),
         routes=[dict(pts=[(32.32, 31.26), (32.33, 30.95), (32.29, 30.60), (32.36, 30.33), (32.57, 29.95)],
                      t=A("قناة السويس", off=-0.6), dur=1.6, color=(120, 210, 255), width=8, label="قناة السويس",
                      label_dx=-150, label_dy=0)]),
    dict(type="map", at=A("أولهم بورسعيد"), codes=["EG-PTS"], title="بورسعيد", min_span=1.6,
         pins=[cap("بورسعيد", "down", A("أولهم بورسعيد", off=0.4))]),
    dict(type="image", at=A("سنة ألف تمنمية"), image="portsaid_1859",
         overlays=[dict(kind="chip", text="١٨٥٩", color=GOLD, x=230, y=140, size=60, t=A("سنة ألف تمنمية")),
                   dict(kind="lower", title="أول ضربة في حفر القناة", sub="على شط البحر المتوسط", t=A("اتضربت أول"))]),
    dict(type="chain", at=A("اسمها بور سعيد"), bg="portsaid_1859", heading="بور سعيد = ميناء سعيد",
         items=[("Port", "بالإنجليزي", "= ميناء"), ("سعيد", "محمد سعيد باشا", "والي مصر")],
         ts=[A("اسمها بور سعيد"), A("على اسم محمد")]),
    dict(type="map", at=A("وفي الأول كانت"), codes=["EG-PTS"], frame_=(32.15, 31.22, 1.15),
         labels=[dict(text="البحر المتوسط", ll=(32.12, 31.45), size=44, t=A("بين البحر")),
                 dict(text="بحيرة المنزلة", ll=(32.03, 31.2), size=42, t=A("وبحيرة المنزلة"))],
         overlays=[dict(kind="lower", title="معسكر عمال على شريط رملي", sub="بين البحر وبحيرة المنزلة", t=A("مجرد معسكر"))]),
]

# ------------------------------------------------------------------ ISMAILIA
SB["ismailia"] = [
    dict(type="map", codes=["EG-IS"], title="الإسماعيلية", frame_=(32.27, 30.6, 1.9),
         labels=[dict(text="بحيرة التمساح", ll=(32.42, 30.62), size=40, t=A("بحيرة التمساح"))],
         pins=[cap("الإسماعيلية", "left", A("اتبنت مدينة"))]),
    dict(type="chain", at=A("واتسمت على اسم الخديوي"), bg="portsaid_1859", heading="١٨٦٣",
         items=[("إسماعيل", "الخديوي"), ("الإسماعيلية", "المدينة")], ts=[A("الخديوي إسماعيل"), A("فبقت الإسماعيلية")]),
    dict(type="map", at=A("ولحد النهارده"), codes=["EG-IS"], frame_=(32.27, 30.6, 1.5),
         pins=[dict(name="الإسماعيلية", label="بيت ديليسبس", side="up", t=A("بيت ديليسبس"))]),
]

# ------------------------------------------------------------------ SUEZ
SB["suez"] = [
    dict(type="map", codes=["EG-SUZ"], title="السويس", pins=[cap("السويس", "left", A("السويس"))]),
    dict(type="chain", at=A("في العصر البطلمي"), bg="map:EG-SUZ", heading="أسامي المكان عبر العصور",
         items=[("أرسينوي", "بطلمي"), ("كليزما", ERA_RO), ("القُلزُم", ERA_AB), ("السويس", ERA_AB)],
         ts=[A("أرسينوي"), A("كليزما"), A("القُلزُم"), A("اسمها السويس")]),
    dict(type="map", at=A("لدرجة إن البحر"), frame_=(34.6, 26.2, 15.0), codes=["EG-BA", "EG-SUZ"],
         labels=[dict(text="بحر القلزم", ll=(36.6, 23.6), size=64, color=(255, 210, 120), t=A("بحر القلزم", off=-0.4))]),
    dict(type="list", at=A("وحوالين القرن"), bg="map:EG-SUZ", heading="السويس كبرت وأخدت كل حاجة",
         items=["القرن العاشر: بلدة صغيرة اسمها السويس", "خليج السويس", "قناة السويس"],
         ts=[A("وحوالين القرن"), A("اسم الخليج"), A("القناة نفسها")]),
    dict(type="fact", at=A("طب كلمة السويس"), bg="map:EG-SUZ", text="؟", big_size=420, top="معنى «السويس»",
         caption="لسه لغز .. ومحدش حسمه", ts=[A("معناها إيه"), A("مفيش إجابة")]),
]

# ------------------------------------------------------------------ DAMIETTA
SB["damietta"] = [
    dict(type="map", codes=["EG-DT"], title="دمياط", pins=[cap("دمياط", "left", A("دمياط"))], min_span=2.0),
    dict(type="chain", at=A("اليونان كانوا"), bg="map:EG-DT", heading="رحلة الاسم",
         items=[("تامياتيس", ERA_GR), ("تامياتي", ERA_CO), ("دمياط", ERA_AB)],
         ts=[A("تامياتيس"), A("تامياتي،"), A("ومن الاسم ده")]),
    dict(type="list", at=A("أما معناه الأصلي"), bg="map:EG-DT", heading="معناه إيه؟ رأيين",
         items=["بلد الشمال", "مرتبط بالإله بتاح"], ts=[A("بلد الشمال"), A("بالإله بتاح")]),
]

# ------------------------------------------------------------------ DAKAHLIA
SB["dakahlia"] = [
    dict(type="map", codes=["EG-DK"], title="الدقهلية", pins=[cap("المنصورة", "left", A("الدقهلية", off=0.5))]),
    dict(type="map", at=A("ودقهلة دي"), codes=["EG-DK"], codes2=["EG-DT"],
         pins=[dict(name="دقهلة", label="قرية دقهلة", side="up", t=A("ودقهلة دي")),
               dict(name="دمياط", side="right", t=A("محافظة دمياط"))],
         overlays=[dict(kind="lower", title="دقهلة: مركز الزرقا - محافظة دمياط", sub="مش في الدقهلية أصلًا!", t=A("مركز الزرقا"))]),
    dict(type="chain", at=A("الحكاية إن دقهلة"), bg="map:EG-DK", heading="إزاي الاسم فضل؟",
         items=[("دقهلة", "عاصمة الإقليم"), ("الدقهلية", "اسم الإقليم كله")], footer="الحدود اتغيرت والعاصمة اتنقلت .. والاسم فضل",
         ts=[A("الحكاية إن"), A("الإقليم كله")], foot_t=A("ومع الوقت")),
    dict(type="meaning", at=A("أما عاصمتها المنصورة"), bg="map:EG-DK", word="المنصورة", meaning="يعني المنتصرة",
         note="بناها السلطان الكامل الأيوبي سنة ١٢١٩ م", ts=[A("المنصورة،"), A("يعني المنتصرة"), A("فبناها")]),
    dict(type="fact", at=A("وبعدها بحوالي"), bg="map:EG-DK", text="١٢٥٠ م", big_size=230,
         caption="لويس التاسع ملك فرنسا .. محبوس في المنصورة", ts=[A("وبعدها"), A("ملك فرنسا")]),
]

# ------------------------------------------------------------------ SHARQIA + GHARBIA
SB["sharqia_gharbia"] = [
    dict(type="map", codes=["EG-SHR"], codes2=["EG-GH"], title="الشرقية والغربية", frame_=(31.3, 30.85, 3.4)),
    dict(type="map", at=A("الشرقية، لأنها"), codes=["EG-SHR"], frame_=(31.3, 30.85, 3.4),
         routes=[dict(river="Damietta Branch", t=A("شرق فرع", off=-0.3), dur=1.2, color=(120, 225, 255), width=9,
                      label="فرع دمياط", label_dx=-110, label_dy=0)],
         overlays=[dict(kind="chip", text="شرق فرع دمياط", color=GOLD, x=1540, y=220, size=54, t=A("شرق فرع"))]),
    dict(type="map", at=A("والغربية، لأنها"), codes=["EG-GH"], frame_=(31.3, 30.85, 3.4),
         routes=[dict(river="Damietta Branch", t=A("والغربية، لأنها", off=0.1), dur=0.6, color=(120, 225, 255), width=9,
                      label="فرع دمياط", label_dx=110, label_dy=0)],
         overlays=[dict(kind="chip", text="غرب فرع دمياط", color=GOLD, x=380, y=220, size=54, t=A("الناحية الغربية"))]),
    dict(type="map", at=A("وزمان كانت الغربية"), codes=["EG-GH"], codes2=["EG-KFS"], frame_=(31.0, 30.95, 2.9),
         overlays=[dict(kind="lower", title="كفر الشيخ كانت جزء من الغربية", sub="لحد ما بقت محافظة مستقلة", t=A("كفر الشيخ"))]),
    dict(type="chain", at=A("وعاصمة الشرقية"), bg="map:EG-SHR", heading="عاصمة الشرقية",
         items=[("زقزوق", "اسم عيلة"), ("الزقازيق", "المدينة")], ts=[A("عيلة اسمها"), A("قبل ما يكبر")]),
    dict(type="chain", at=A("أما عاصمة الغربية"), bg="map:EG-GH", heading="عاصمة الغربية",
         items=[("طنتدا", "الاسم القديم"), ("طنطا", "النهارده")], ts=[A("طنتدا", off=-0.4), A("طنتدا", off=0.5)]),
]

# ------------------------------------------------------------------ BEHEIRA
SB["beheira"] = [
    dict(type="map", codes=["EG-BH"], title="البحيرة",
         labels=[dict(text="بحيرة مريوط", ll=(29.93, 31.02), size=36, t=A("بحيرة مريوط")),
                 dict(text="بحيرة إدكو", ll=(30.25, 31.36), size=36, t=A("بحيرة إدكو"))],
         pins=[cap("دمنهور", "down", A("البحيرة", off=0.5))]),
    dict(type="meaning", at=A("فالعرب سموا"), bg="map:EG-BH", word="البحيرة", meaning="أرض البحيرات والمستنقعات",
         ts=[A("فالعرب"), A("الإقليم كله")]),
    dict(type="chain", at=A("أما عاصمتها دمنهور"), bg="map:EG-BH", heading="دمنهور",
         items=[("دمي إن حور", ERA_AR, "= مدينة حورس"), ("دمنهور", ERA_AB)], ts=[A("دمي إن حور"), A("يعني مدينة")]),
]

# ------------------------------------------------------------------ QALYUBIA
SB["qalyubia"] = [
    dict(type="map", codes=["EG-KB"], title="القليوبية", min_span=1.8,
         pins=[cap("قليوب", "down", A("مدينة قليوب")), cap("بنها", "up", A("بنها"))]),
    dict(type="fact", at=A("وأصل كلمة قليوب"), bg="map:EG-KB", text="قليوب = ؟", big_size=200,
         caption="أصل قديم وغامض .. ومفيش رأي محسوم", ts=[A("وأصل كلمة"), A("مفيش رأي")]),
]

# ------------------------------------------------------------------ MONUFIA
SB["monufia"] = [
    dict(type="map", codes=["EG-MNF"], title="المنوفية", min_span=2.0,
         pins=[cap("منوف", "left", A("مدينة منوف"))]),
    dict(type="chain", at=A("القبط كانوا"), bg="map:EG-MNF", heading="منوف",
         items=[("بانوف", ERA_CO), ("أونوفيس", ERA_GR), ("منوف", ERA_AB)], footer="وفيه رأي بيقول إن معناها «الأرض الطيبة»",
         ts=[A("بانوف"), A("أونوفيس"), A("وفيه رأي", off=-0.6)], foot_t=A("الأرض الطيبة", off=-0.3)),
    dict(type="chain", at=A("وفي العصر الفاطمي"), bg="map:EG-MNF", heading="العصر الفاطمي",
         items=[("منوف العليا", "إقليم"), ("منوف السفلى", "إقليم"), ("المنوفية", "إقليم واحد")],
         ts=[A("منوف العليا"), A("ومنوف السفلى"), A("إقليم واحد")]),
    dict(type="map", at=A("وفضلت منوف"), codes=["EG-MNF"], min_span=1.6,
         pins=[cap("منوف", "left", A("وفضلت منوف")), cap("شبين الكوم", "right", A("لشبين الكوم"))],
         routes=[dict(pts=[(30.95, 30.47), (31.0, 30.54)], t=A("نقل العاصمة"), dur=0.8, color=GOLD, width=8, arrow=True)]),
]

# ------------------------------------------------------------------ KAFR EL SHEIKH
SB["kafrelsheikh"] = [
    dict(type="map", codes=["EG-KFS"], title="كفر الشيخ", pins=[cap("كفر الشيخ", "down", A("كفر الشيخ", off=0.5))]),
    dict(type="meaning", at=A("فكلمة كفر"), bg="map:EG-KFS", word="كفر", meaning="يعني قرية", note="كلمة أصلها آرامي",
         ts=[A("فكلمة كفر"), A("ومعناها قرية"), A("أصلها آرامي")]),
    dict(type="quote", at=A("طب الشيخ ده مين"), bg="map:EG-KFS", top="القرن السابع الهجري", quote="الشيخ طلحة التلمساني",
         attrib="ولي صالح جه من بلاد المغرب", ts=[A("طب الشيخ ده مين", off=0.5), A("الشيخ طلحة")]),
    dict(type="chain", at=A("واستقر في قرية"), bg="map:EG-KFS", heading="رحلة الاسم",
         items=[("دنقيون", "الاسم القديم"), ("كفر الشيخ طلحة", "حوالين الشيخ"), ("كفر الشيخ", "اختصار")],
         ts=[A("دنقيون"), A("كفر الشيخ طلحة"), A("اختصروها")]),
    dict(type="chain", at=A("والطريف إنها"), bg="map:EG-KFS", heading="وفي فترة ..",
         items=[("الفؤادية", "على اسم الملك فؤاد"), ("كفر الشيخ", "بعد ثورة يوليو")],
         ts=[A("الفؤادية"), A("بعد ثورة يوليو")]),
]

# ------------------------------------------------------------------ BENI SUEF
SB["benisuef"] = [
    dict(type="map", codes=["EG-BNS"], title="بني سويف", pins=[cap("بني سويف", "left", A("بني سويف", off=0.4))]),
    dict(type="list", at=A("لو سألت أهلها"), bg="map:EG-BNS", heading="روايات شعبية",
         items=["قبيلة عربية اسمها «بني سويف»", "«بني السيوف» .. معركة بالسيوف"], colors=[CORAL, CORAL],
         ts=[A("قبيلة عربية"), A("بني السيوف")]),
    dict(type="quote", at=A("لكن المؤرخ"), bg="map:EG-BNS", top="رأي المؤرخين", quote="محمد رمزي",
         attrib="صاحب «القاموس الجغرافي للبلاد المصرية»", ts=[A("محمد رمزي"), A("القاموس")]),
    dict(type="ledger", at=A("إن اسم البلد"), bg="gradient", header="دفاتر المساحة العثمانية — القرن ١٦",
         old="منفسويه", new="بني سويف", caption="«استسهلوا» وكتبوها بني سويف!",
         ts=[A("منفسويه"), A("استسهلوا", off=-0.2), A("وكتبوها")]),
    dict(type="fact", at=A("يعني حسب الرأي"), bg="map:EG-BNS", text="!", big_size=380,
         caption="محافظة كاملة .. اسمها من تحريف في دفاتر المساحة", ts=[A("يعني حسب"), A("محافظة كاملة")]),
]

# ------------------------------------------------------------------ FAIYUM
SB["faiyum"] = [
    dict(type="map", codes=["EG-FYM"], title="الفيوم", min_span=2.2,
         labels=[dict(text="بحيرة قارون", ll=(30.6, 29.56), size=36, t=A("الفيوم", off=0.8))]),
    dict(type="chain", at=A("المصريين القدما"), bg="map:EG-FYM", heading="أصل الاسم",
         items=[("با يم", ERA_AR, "= البحر"), ("فيوم", ERA_CO), ("الفيوم", ERA_AB)],
         ts=[A("با يم"), A("نطقوها فيوم"), A("فبقت الفيوم")]),
    dict(type="map", at=A("والمقصود بحيرة"), codes=["EG-FYM"], frame_=(30.65, 29.4, 1.35),
         labels=[dict(text="بحيرة قارون", ll=(30.6, 29.53), size=46, color=(160, 220, 255), t=A("بحيرة قارون"))],
         overlays=[dict(kind="lower", title="بحيرة موريس الضخمة", sub="فاضل منها النهارده بحيرة قارون", t=A("بحيرة موريس"))]),
    dict(type="myth", at=A("وطبعًا فيه الحكاية"), bg="map:EG-FYM", myth="ألف يوم", fact="با يم = البحر",
         ts=[A("ألف يوم"), A("بس اللغة")]),
    dict(type="meaning", at=A("والفيوم كمان"), bg="map:EG-FYM", word="سوبك", meaning="إله على هيئة تمساح",
         note="واليونان سموا عاصمتها «مدينة التماسيح»", ts=[A("الإله سوبك"), A("هيئة تمساح"), A("مدينة التماسيح", off=-0.5)]),
]

# ------------------------------------------------------------------ MINYA
SB["minya"] = [
    dict(type="map", codes=["EG-MN"], title="المنيا", pins=[cap("المنيا", "left", A("للمنيا", off=0.3))]),
    dict(type="chain", at=A("أصل الاسم بيرجع"), bg="giza_pyramids", heading="أصل الاسم",
         items=[("منعت خوفو", ERA_AR, "مرضعة خوفو"), ("موني", ERA_CO, "المسكن"), ("منية", ERA_AB), ("المنيا", ERA_AB)],
         ts=[A("منعت خوفو"), A("موني"), A("كلمة منية"), A("كلمة منية", off=1.2)]),
    dict(type="list", at=A("اللي هتلاقيها"), bg="map:EG-MN", heading="«منية» في أسامي بلادنا",
         items=["ميت غمر (منية غمر)", "منية النصر", "ميت أبو غالب"], ts=[A("هتلاقيها"), A("أسامي بلاد"), A("في مصر")]),
    dict(type="quote", at=A("وفي العصر العباسي"), bg="map:EG-MN", top="العصر العباسي", quote="منية ابن خصيب",
         attrib="الخصيب بن عبد الحميد .. أيام هارون الرشيد", ts=[A("منية ابن خصيب"), A("الخصيب بن")]),
    dict(type="fact", at=A("وفي الآخر فضل"), bg="map:EG-MN", text="المنيا", big_size=260,
         caption="وده اللي فضل من كل الأسامي دي", ts=[A("كلمة واحدة"), A("كلمة واحدة", off=0.6)]),
]

# ------------------------------------------------------------------ ASYUT
SB["asyut"] = [
    dict(type="map", codes=["EG-AST"], title="أسيوط", pins=[cap("أسيوط", "left", A("وأسيوط", off=0.4))]),
    dict(type="chain", at=A("اسمها المصري القديم"), bg="map:EG-AST", heading="أصل الاسم",
         items=[("ساوتي", ERA_AR, "= الحارس"), ("سيوط", ERA_CO), ("أسيوط", ERA_AB)],
         ts=[A("ساوتي"), A("نطقوها سيوط"), A("فبقت أسيوط")]),
    dict(type="meaning", at=A("أما اليونان"), bg="map:EG-AST", word="ليكوبوليس", word_size=170, meaning="مدينة الذئب",
         note="عشان أهلها عبدوا إله على هيئة ذئب", ts=[A("ليكوبوليس"), A("مدينة الذئب"), A("عشان أهلها")]),
]

# ------------------------------------------------------------------ SOHAG
SB["sohag"] = [
    dict(type="map", codes=["EG-SHG"], title="سوهاج", pins=[cap("سوهاج", "left", A("سوهاج", off=0.5))]),
    dict(type="myth", at=A("فأكيد سمعت"), bg="map:EG-SHG", myth="سو هاج!", fact="مجرد نكتة", fact_head="الحقيقة",
         ts=[A("فأكيد سمعت", off=0.4), A("دي مجرد")]),
    dict(type="fact", at=A("الحقيقة إن أصل"), bg="map:EG-SHG", text="سوهاج = ؟", big_size=210,
         caption="أصل الكلمة لسه مش محسوم", ts=[A("الحقيقة"), A("مش محسوم")]),
    dict(type="chain", at=A("لكن المعلومة"), bg="map:EG-SHG", heading="١٩٦٠",
         items=[("مديرية جرجا", "قبل ١٩٦٠"), ("محافظة سوهاج", "بعد ١٩٦٠")], ts=[A("مديرية جرجا"), A("خدت اسمها")]),
    dict(type="map", at=A("ولما العاصمة"), codes=["EG-SHG"], min_span=1.6,
         pins=[cap("جرجا", "right", A("ولما العاصمة")), cap("سوهاج", "left", A("لمدينة سوهاج"))],
         routes=[dict(pts=[(31.89, 26.34), (31.70, 26.55)], t=A("اتنقلت"), dur=0.9, color=GOLD, width=8, arrow=True)]),
]

# ------------------------------------------------------------------ QENA
SB["qena"] = [
    dict(type="map", codes=["EG-KN"], title="قنا", pins=[cap("قنا", "left", A("وقنا", off=0.4)), cap("قفط", "right", A("قفط"))]),
    dict(type="chain", at=A("اليونان كانوا"), bg="map:EG-KN", heading="أصل الاسم",
         items=[("كايني", ERA_GR, "= الجديدة"), ("كوني", ERA_CO), ("قنا", ERA_AB)], ts=[A("كايني"), A("كوني"), A("جه اسم قنا")]),
    dict(type="map", at=A("وقنا فضلت"), codes=["EG-KN"], frame_=(33.5, 26.3, 3.6),
         pins=[cap("قنا", "left", A("وقنا فضلت")), cap("القصير", "right", A("على القصير"))],
         routes=[dict(pts=[(32.73, 26.16), (33.1, 26.05), (33.6, 26.0), (34.0, 26.1), (34.27, 26.10)], t=A("لقوافل"),
                      dur=1.5, color=GOLD, width=7, dashed=True, label="طريق القوافل", label_dy=-60)]),
]

# ------------------------------------------------------------------ LUXOR
SB["luxor"] = [
    dict(type="map", codes=["EG-LX"], title="الأقصر", min_span=1.6, pins=[cap("الأقصر", "left", A("والأقصر", off=0.4))]),
    dict(type="chain", at=A("دي كانت واست"), bg="map:EG-LX", heading="أسامي المدينة",
         items=[("واست", ERA_AR), ("طيبة", ERA_GR), ("الأقصُر", ERA_AB, "= القصور")],
         ts=[A("واست"), A("طيبة"), A("وسموها الأقصُر")]),
    dict(type="quote", at=A("ومن قبلهم"), bg="map:EG-LX", top="هوميروس", quote="«المدينة أم مية باب»",
         attrib="كده وصف طيبة الشاعر اليوناني هوميروس", ts=[A("المدينة أم"), A("الشاعر اليوناني")]),
]

# ------------------------------------------------------------------ ASWAN
SB["aswan"] = [
    dict(type="map", codes=["EG-ASN"], title="أسوان", pins=[cap("أسوان", "left", A("أسوان", off=0.4))]),
    dict(type="chain", at=A("المصريين القدما"), bg="map:EG-ASN", heading="أصل الاسم",
         items=[("سونو", ERA_AR, "= السوق"), ("سوان", ERA_CO), ("سييني", ERA_GR), ("أسوان", ERA_AB)],
         ts=[A("سونو"), A("قالوا سوان"), A("سييني"), A("فبقت أسوان")]),
    dict(type="meaning", at=A("ومن اسمها اليوناني"), bg="map:EG-ASN", word="السيينيت", word_size=170,
         meaning="صخر اسمه جاي من «سييني»", note="بيستخدمه علماء الجيولوجيا لحد النهارده",
         ts=[A("ومن اسمها اليوناني", off=0.3), A("جه اسم صخر"), A("علما الجيولوجيا")]),
]

# ------------------------------------------------------------------ RED SEA
SB["redsea"] = [
    dict(type="map", codes=["EG-BA"], title="البحر الأحمر", pins=[cap("الغردقة", "left", A("محافظة البحر الأحمر"))],
         labels=[dict(text="البحر الأحمر", ll=(36.2, 24.6), size=56, color=(255, 150, 140), t=A("اتسمت على البحر"))]),
    dict(type="list", at=A("بس ليه البحر"), bg="map:EG-BA", heading="ليه اسمه «الأحمر»؟",
         items=["طحالب بتدّي المية لون أحمر", "الجبال الحمرا اللي على شطه", "الأحمر عند شعوب قديمة = الجنوب"],
         ts=[A("أشهرها"), A("الجبال الحمرا"), A("ورأي تالت")]),
    dict(type="chain", at=A("أما عاصمتها الغردقة"), bg="map:EG-BA", heading="عاصمتها",
         items=[("الغردق", "نبات صحراوي شوكي"), ("الغردقة", "المدينة")], ts=[A("اسمه الغردق", off=-0.2), A("كان مالي")]),
]

# ------------------------------------------------------------------ NEW VALLEY
SB["newvalley"] = [
    dict(type="map", codes=["EG-WAD"], title="الوادي الجديد", pins=[cap("الخارجة", "right", A("الوادي الجديد", off=0.5))]),
    dict(type="chain", at=A("المحافظة دي كان"), bg="map:EG-WAD", heading="١٩٥٨",
         items=[("الصحراء الجنوبية", "الاسم القديم"), ("الوادي الجديد", "من ١٩٥٨")],
         ts=[A("الصحراء الجنوبية"), A("لما جمال")]),
    dict(type="map", at=A("لما جمال"), codes=["EG-WAD"], frame_=(29.8, 26.6, 9.0),
         routes=[dict(pts=[(28.85, 28.35), (28.0, 27.06), (28.95, 25.55), (30.55, 25.44), (30.8, 24.4)],
                      t=A("وادي جديد"), dur=2.0, color=(80, 230, 160), width=8, dashed=True, label="وادي موازي للنيل",
                      label_dx=-40, label_dy=-70)],
         overlays=[dict(kind="lower", title="وادي جديد موازي لوادي النيل", sub="على المية الجوفية والآبار", t=A("موازي"))]),
    dict(type="fact", at=A("وعلى فكرة"), bg="map:EG-WAD", text="", count_to=44, fmt="{}٪", top="أكبر محافظة في مصر",
         caption="من مساحة مصر كلها", ts=[A("أكبر محافظة"), A("من مساحة")]),
]

# ------------------------------------------------------------------ MATROUH
SB["matrouh"] = [
    dict(type="map", codes=["EG-MT"], title="مطروح", pins=[cap("مرسى مطروح", "down", A("مطروح", off=0.4))]),
    dict(type="chain", at=A("أيام البطالمة"), bg="map:EG-MT", heading="الاسم القديم",
         items=[("باريتونيوم", ERA_GR), ("البارتون", ERA_AB)], ts=[A("باريتونيوم"), A("البارتون")]),
    dict(type="chain", at=A("أشهر رواية"), bg="map:EG-MT", heading="رافع بن مطروح .. حاكم طرابلس",
         items=[("مرسى ابن مطروح", "القرن ٦ هـ"), ("مرسى مطروح", "مع الوقت")],
         ts=[A("مرسى ابن مطروح"), A("بقت مرسى مطروح")]),
    dict(type="meaning", at=A("وفيه رأي أبسط"), bg="map:EG-MT", word="مطروحة", meaning="يعني منبسطة",
         note="أرض مفرودة بين البحر والجبل", ts=[A("مطروحة"), A("منبسطة"), A("بين البحر")]),
]

# ------------------------------------------------------------------ SINAI
SB["sinai"] = [
    dict(type="map", codes=["EG-SIN", "EG-JS"], title="سيناء",
         pins=[cap("العريش", "down", A("شمال سيناء")), cap("الطور", "left", A("وجنوب سيناء"))]),
    dict(type="meaning", at=A("أشهر رأي"), bg="gradient", word="سين", word_size=230, meaning="إله القمر",
         note="عند الشعوب السامية القديمة", ts=[A("من سين"), A("إله القمر"), A("الشعوب السامية")]),
    dict(type="chain", at=A("أما المصريين القدما"), bg="map:EG-JS", heading="أرض الفيروز",
         items=[("تا مفكات", ERA_AR, "= أرض الفيروز"), ("أرض الفيروز", "لحد النهارده")],
         ts=[A("تا مفكات"), A("لحد النهارده: أرض")]),
    dict(type="quote", at=A("والقرآن الكريم"), bg="map:EG-JS", top="في القرآن الكريم", qfont="amiri", qsize=120,
         quote="﴿طُورِ سَيْنَاءَ﴾  ﴿وَطُورِ سِينِينَ﴾", ts=[A("طور سيناء"), A("طور سيناء")]),
]

# ------------------------------------------------------------------ OUTRO
SB["outro"] = [
    dict(type="map", frame_=(30.8, 26.9, 19.5), sweep=True, sweep_t0=0.0, sweep_dur=1.8,
         overlays=[dict(kind="text", text="٢٧ محافظة .. ٢٧ حكاية", size=84, color=GOLD, x=1380, y=150, t=A("سبعة وعشرين حكاية", off=-0.5))]),
    dict(type="list", at=A("وزي ما شفت"), bg="map:", heading="الاسم = تاريخ في كام حرف",
         items=["فرعوني ويوناني وقبطي وعربي", "حكام وأساطير", "وحتى غلطات في الكتابة"],
         ts=[A("فرعوني"), A("وحكام"), A("وحتى غلطات")]),
    dict(type="map", at=A("ومعلومة أخيرة"), codes=["EG-C"], codes2=["EG-GZ"], frame_=(31.1, 29.95, 2.6),
         pins=[cap("حلوان", "right", A("حلوان")), cap("6 أكتوبر", "left", A("وستة أكتوبر"), label="٦ أكتوبر")],
         overlays=[dict(kind="lower", title="محافظتين عاشوا ٣ سنين بس", sub="من ٢٠٠٨ لـ ٢٠١١", t=A("وبعد تلات سنين"))]),
    dict(type="fact", at=A("ودلوقتي دورك"), bg="map:", text="؟", big_size=360, top="دورك",
         caption="إنت من محافظة إيه؟ .. اكتبها في الكومنتات", ts=[A("دورك"), A("إنت من محافظة")]),
    dict(type="title", at=A("ولو الفيديو عجبك"), bg="gradient", text="لايك + اشتراك", size=170, sub="ونشوفك في سؤال جديد"),
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
    if isinstance(obj, list):
        return [resolve(v, sec) for v in obj]
    return obj


LEAD = 0.25   # visual cut slightly before the voice


def build_shots():
    tl = load_timeline()
    secs = tl["sections"]
    out = []
    for si, sec in enumerate(secs):
        specs = SB[sec["id"]]
        sec_start = sec["start"] - LEAD if si > 0 else 0.0
        resolved = []
        for k, sp in enumerate(specs):
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
        # sort by time; enforce minimum on-screen durations (first map >= 2.6 s)
        resolved.sort(key=lambda x: x[0])
        fixed = []
        for k, (t0, sp) in enumerate(resolved):
            if fixed:
                pt0, psp = fixed[-1]
                mind = 2.6 if (len(fixed) == 1 and psp["type"] == "map" and sec["id"] not in ("intro", "outro")) else \
                    (1.2 if sec["id"] == "intro" else 1.6)
                t0 = max(t0, pt0 + mind)
            fixed.append((t0, sp))
        sec_end = sec["end"]
        for k, (t0, sp) in enumerate(fixed):
            out.append(dict(start=round(min(t0, sec_end - 0.8), 3), section=sec["id"], **sp))
    # ends
    for k in range(len(out)):
        out[k]["end"] = out[k + 1]["start"] if k + 1 < len(out) else tl["duration"]
    return out, tl


if __name__ == "__main__":
    shots, tl = build_shots()
    bad = [s for s in shots if s["end"] - s["start"] < 1.0]
    for s in shots:
        flag = "  <-- SHORT" if s["end"] - s["start"] < 1.0 else ""
        print(f'{s["start"]:8.2f} {s["end"]-s["start"]:6.2f}  {s["section"]:16s} {s["type"]}{flag}')
    print(len(shots), "shots; short:", len(bad), "duration", tl["duration"])
