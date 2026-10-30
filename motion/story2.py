"""Beat sheet v2 — «قصّة جليبيب»: narrative motion design, not subtitles.

Every beat is a composed scene: dominant kinetic phrase, supporting line,
iconographic motif, colour mood and a punch-in. Times follow the voiceover.
"""

DURATION = 181.0

BEATS = [
    dict(kind="title", t0=0.20, t1=3.30, mood="calm",
         kicker="من صحيح مسلم", main="قصّة جليبيب",
         sub="صحابيّ… لا حسبَ ولا نسبَ ولا مال"),

    dict(kind="hero", t0=3.40, t1=7.60, mood="dark",
         kicker="لا يُعرف له نسبٌ", main="ولا أهل… ولا قوم",
         icon="groups", size=190),

    dict(kind="hero", t0=7.70, t1=13.70, mood="dark",
         main="دميمُ الخِلقة", sub="لم يكن له من الجمالِ نصيب", size=200),

    dict(kind="icon", t0=13.90, t1=18.50, mood="calm", icon="menu_book",
         main="دائمَ الذكرِ لربّه", sub="لا يفارقُ الصفَّ الأوّل"),

    dict(kind="icon", t0=18.60, t1=25.20, mood="warm", icon="mosque",
         main="يراه النبيُّ ﷺ في المسجد", sub="أعزبَ… لم يتزوّج", size=116),

    dict(kind="quote", t0=25.30, t1=31.70, mood="warm",
         label="قال له النبيُّ صلّى الله عليه وسلّم",
         text="«يا جليبيب… ألا تتزوّج؟»", size=132),

    dict(kind="hero", t0=31.80, t1=35.10, mood="calm",
         main="ومن يُزوّجني؟", sub="لا حسبَ لي ولا نسبَ ولا مال", size=190),

    dict(kind="caption", t0=35.20, t1=38.60, mood="calm", icon="forum",
         main="فسأله مرّةً ثانية… وثالثة", sub="وكان الجوابُ هو الجواب"),

    dict(kind="icon", t0=38.70, t1=47.20, mood="warm", icon="door_front",
         main="اذهب إلى بيتِ فلانٍ من الأنصار", sub="وقل: رسولُ اللهِ يخطبُ ابنتك",
         size=104, y=1140),

    dict(kind="hero", t0=47.30, t1=52.50, mood="warm",
         main="طرقَ الباب", sub="وبلّغ الرسالة", size=210),

    dict(kind="quote", t0=52.60, t1=58.00, mood="warm",
         label="قال جليبيب", text="«رسولُ اللهِ يخطبُ ابنتك»", size=126),

    dict(kind="hero", t0=58.00, t1=63.80, mood="calm",
         main="شافعٌ… أم آمر؟", sub="وهو يخطبُ ابنتك", size=180),

    dict(kind="hero", t0=63.90, t1=69.80, mood="calm",
         main="أمرُ رسولِ الله", sub="لا يُرَدّ", size=170, subcolor="E9C27A"),

    dict(kind="caption", t0=69.90, t1=76.50, mood="calm", icon="campaign",
         main="فدخل جليبيب… وبلّغ أمَّ الفتاة"),

    dict(kind="hero", t0=76.60, t1=82.40, mood="warm",
         main="لا أُزوّجه", sub="غضبت أمُّها", size=210, color="D98B7F"),

    dict(kind="quote", t0=82.50, t1=91.10, mood="warm",
         label="قالت الفتاة", text="«أتردّانِ على رسولِ اللهِ\\Nأمرَه؟»", size=120),

    dict(kind="caption", t0=91.20, t1=95.20, mood="calm", icon="handshake",
         main="افعلوا ما أمر… فإنّه لن يُضيّعني"),

    dict(kind="hero", t0=95.30, t1=99.60, mood="warm",
         main="فرضي الأبوان", sub="وتمّ الأمر", icon="favorite", size=185),

    dict(kind="caption", t0=99.70, t1=104.50, mood="calm", icon="school",
         main="وكان درسًا: الزواجُ بالدِّينِ والخُلُق"),

    dict(kind="caption", t0=104.60, t1=107.20, mood="pray", icon="folded_hands",
         main="فدعا لهما النبيُّ ﷺ"),

    dict(kind="quote", t0=107.30, t1=111.40, mood="pray",
         label="دعاء النبيّ صلّى الله عليه وسلّم",
         text="«اللهم صبِّ عليهما الخيرَ صبًّا\\Nولا تجعل عيشَهما كَدًّا»", size=104),

    dict(kind="hero", t0=111.50, t1=116.50, mood="battle",
         main="ثم جاءت المعركة", icon="swords", size=175),

    dict(kind="caption", t0=116.60, t1=119.30, mood="battle", icon="bolt",
         main="وجاء معها الامتحان"),

    dict(kind="icon", t0=119.40, t1=125.20, mood="battle", icon="shield",
         main="في الصفِّ الأوّل", sub="جاهزًا للقتال"),

    dict(kind="hero", t0=125.30, t1=129.10, mood="battle",
         main="قامت المعركة", size=200),

    dict(kind="caption", t0=129.20, t1=131.50, mood="battle", icon="flag",
         main="وانتصر المسلمون نصرًا مؤزّرًا"),

    dict(kind="caption", t0=131.60, t1=135.20, mood="calm", icon="groups",
         main="وقف النبيُّ ﷺ يتفقّدُ أصحابه"),

    dict(kind="caption", t0=135.30, t1=138.60, mood="calm", icon="checklist",
         main="فيُعدّون له الشهداء", sub="واحدًا واحدًا"),

    dict(kind="caption", t0=138.70, t1=141.80, mood="calm", icon="group_off",
         main="حتى قالوا: ما بقيَ أحد"),

    dict(kind="quote", t0=141.90, t1=146.70, mood="warm",
         label="قال صلّى الله عليه وسلّم", text="«إنّي أفتقدُ جليبيبًا»", size=132),

    dict(kind="caption", t0=146.80, t1=150.40, mood="calm", icon="help",
         main="قالوا: لا نعلم يا رسولَ الله"),

    dict(kind="caption", t0=150.50, t1=152.40, mood="calm", icon="search",
         main="قال: قوموا معي نبحثُ عنه"),

    dict(kind="hero", t0=152.50, t1=156.40, mood="calm",
         main="فبحثوا… حتى وجدوه", icon="location_on", size=165),

    dict(kind="caption", t0=156.50, t1=158.90, mood="battle", icon="star",
         main="وجدوه شهيدًا في أرضِ المعركة"),

    dict(kind="quote", t0=159.00, t1=161.70, mood="battle",
         label="قال رسول الله صلّى الله عليه وسلّم",
         text="«قتل سبعةً… ثم قتلوه»", size=124),

    dict(kind="caption", t0=161.80, t1=165.10, mood="warm", icon="favorite",
         main="فحمله النبيُّ ﷺ… وضمّ رأسَه إلى صدره", size=88),

    dict(kind="quote", t0=165.20, t1=170.20, mood="warm",
         label="قال رسول الله صلّى الله عليه وسلّم",
         text="«هذا منّي… وأنا منه»", size=136),

    dict(kind="caption", t0=170.40, t1=172.20, mood="calm", icon="landscape",
         main="وأمر أن يُحفرَ له قبر"),

    dict(kind="caption", t0=172.40, t1=174.10, mood="calm", icon="back_hand",
         main="فحمله بيده… ووضعه في القبر", size=88),

    dict(kind="caption", t0=174.30, t1=176.40, mood="calm", icon="volunteer_activism",
         main="وصَلّى عليه… ولم يُغسَّل"),

    dict(kind="caption", t0=176.50, t1=177.70, mood="calm", icon="star",
         main="لأنّه شهيد", size=110),

    dict(kind="end", t0=177.90, t1=181.00, mood="end",
         label="من صحيح مسلم", main="وهكذا… عاش مجهولًا\\Nومات شهيدًا"),
]

# chapters shown in the top overlay: (t_start, label)
CHAPTERS = [
    (0.0,   "١ · رجلٌ لا يعرفه أحد"),
    (25.3,  "٢ · الخطبة والزواج"),
    (111.5, "٣ · المعركة والبحث"),
    (159.0, "٤ · هذا منّي وأنا منه"),
]
