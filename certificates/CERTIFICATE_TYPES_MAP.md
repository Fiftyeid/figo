# 🗺️ خريطة الشهادات المطلوبة للبنود — CoA · COO · CoPP · FDA/SRA · WHO Prequal

> القايمة دي معمولة لمتطلبات مناقصات/تسجيل المستهلكات الطبية (Consumables).
> لكل شهادة: **بتتصدر من مين + بتتجاب إزاي + الروابط العامة**.

---

## نظرة سريعة

| الشهادة | بتتصدر من مين | لكل شحنة/تشغيلة؟ | طريقة الحصول |
|---|---|---|---|
| **CoA** شهادة التحليل | الشركة المصنعة (معمل الضبط الداخلي أو معمل خارجي) | ✅ لكل Lot | أداة الشهادات في موقع الشركة أو بالطلب |
| **COO** شهادة المنشأ | المصنّع + توثيق الغرفة التجارية في بلد التصدير | ✅ لكل شحنة | من المورّد + الغرفة التجارية / GOEIC |
| **CoPP** شهادة المنتج الدوائي | سلطة الدواء في بلد التصدير (FDA/EMA/EDA...) | ❌ للمنتج الواحد | من صاحب الترخيص (MAH) — **للأدوية فقط** |
| **FDA / SRA** | FDA الأمريكية أو أي سلطة صارمة (CE/_notified body، Health Canada، TGA...) | ❌ للمنتج | قواعد بيانات عامة — تحميل فوري |
| **WHO Prequal** | منظمة الصحة العالمية | ❌ للمنتج | قوايم معلنة على موقع WHO — تحميل/بحث فوري |

---

## 1) CoA — Certificate of Analysis (شهادة التحليل)

- **مين بيصدرها:** الشركة المصنعة لكل تشغيلة (Lot) — من معمل الـQC الداخلي أو معمل خارجي معتمد.
- **إزاي تجيبها:** من أدوات الشهادات في مواقع الشركات (شوف `DOWNLOAD_LINKS_FROM_COMPANIES.md`):
  - BD: <https://regdocs.bd.com/regdocs/qcinfo> (كتالوج + لوت)
  - Cardinal Health: <https://certificates.cardinalhealth.com/> (منتج + لوت)
  - Sigma-Aldrich/Merck: <https://b2b.sigmaaldrich.com/US/en/documents-search?tab=coa>
  - Medline CoC: <https://coc.medline.com/irj/CertificateOfConformance> (أوردر + صنف + لوت)
- **ملاحظة للمناقصات:** بيطلبوها عادة **Sample/Model CoA** (شهادة تشغيلة حديثة كنموذج) مش لكل شحنة وقت التقديم.

## 2) COO — Certificate of Origin (شهادة المنشأ)

- **مين بيصدرها:** المصنّع بيطلع إقرار منشأ + **الغرفة التجارية المعتمدة في بلد التصدير** بتوثّقه بختمها (للجمارك).
- **إزاي تجيبها:** من المورّد/المصنّع، وهو بيوثّقها من غرفة التجارة عنده.
- بعض الشركات منشورة عندها:
  - Sigma-Aldrich CoO أونلاين: <https://b2b.sigmaaldrich.com/US/en/documents-search?tab=coo>
  - Cardinal Health: حقل Country of Origin جوه الـCoA نفسه
- **في مصر (للتصدير):** GOEIC / اتحاد الغرف التجارية.

## 3) CoPP — Certificate of Pharmaceutical Product

> ⚠️ **مهم جدًا:** الشهادة دي **للأدوية والمستحضرات الصيدلانية فقط** — بتتصدر من
> **سلطة الدواء في بلد التصدير** (FDA، وكالات الاتحاد الأوروبي، MHRA، Swissmedic...).
>
> لو البنود كلها **مستهلكات طبية** (قفازات، سرنجات، قساطر، خيوط جراحة...) فالـCoPP
> **مش بتتصدر ليها أصلًا** — البديل المطلوب في المناقصات عادةً هو CE / FDA 510(k) / ISO 13485.
> لو القايمة فيها بنود دوائية (محاليل وريدية، أدوية...) ساعتها الـCoPP مطلوبة من الـMAH.

- النموذج الرسمي: <https://www.who.int/teams/regulation-prequalification/regulation-and-safety/regulatory-convergence-networks/certification-scheme/model-certificate-of-a-pharmaceutical-product>
- تقديم عبر FDA (للمنتجات الأمريكية): CDER eCATS — <https://www.fda.gov/drugs/guidance-compliance-regulatory-information/human-drug-exports>

## 4) FDA / SRA — موافقة الجهات التنظيمية الصارمة

للمستهلكات الطبية دي أسهل حاجة لأنها **معلنة للعامة**:

| الوثيقة | يعني إيه | إزاي تطلعها |
|---|---|---|
| **FDA 510(k) Clearance** | إخطار تسويق قبل البيع في أمريكا | قاعدة بيانات عامة: ابحث بالاسم/الشركة وحمّل خطاب الـClearance PDF |
| **FDA Establishment Registration + Product Listing** | تسجيل المصنع وقيد المنتج عند FDA | قاعدة بيانات عامة بالاسم — إثبات التسجيل |
| **CE Mark / EC Certificate** | اعتماد أوروبي من Notified Body | من المورّد (شهادة EC + إعلان مطابقة DoC) |
| **ISO 13485** | نظام إدارة جودة المصنّع | من المورّد — وبعض الشركات منشورته (زي Medline) |

**الروابط العامة (بحث وتحميل فوري، بدون تسجيل):**
- بحث 510(k): <https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm>
- تسجيل المصانع وقائمة المنتجات: <https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRL/rl.cfm>
- GUDID (قاعدة بيانات الأجهزة): <https://accessgudid.nlm.nih.gov/>
- شهادات ISO/MDSAP لشركة Medline (مثال منشور): <https://www.medline.com/about-us/quality-assurance/>

## 5) WHO Prequal — أهلية منظمة الصحة العالمية

- **للأجهزة والمستهلكات الطبية:** برنامج **WHO PQS** (Performance, Quality and Safety) —
  مثلاً السرنجات ذات التعطيل التلقائي (Auto-Disable) والخزانات اللوحية... قايمة معلنة:
  <https://extranet.who.int/prequal/medical-devices>
- **للأدوية:** قايمة WHO Prequalification of Medicines: <https://list.essentialmeds.org/>
- **للمستحضرات التشخيصية (IVDs):** قايمات معلنة كذلك في نفس البوابة.
- ✅ البحث فيها بالاسم/الشركة مجاني — والمطابقة بتطلع إثبات إن المنتج مُقيّم من WHO.

---

## إزاي أشتغل على قايمة البنود بتاعتك

أول ما تبعت **Annex A** (قايمة البنود والمواصفات):
1. هرتّب كل بند: اسم المنتج + الشركة المصنعة/الماركة المطلوبة.
2. لكل بند هحدد: هل هو **جهاز/مستهلك** (CoPP لا تنطبق) ولا **دواء** (CoPP مطلوبة).
3. هجيب لكل بند من قواعد البيانات العامة:
   - رقم الـ510(k) وخطاب الـClearance لو أمريكي
   - حالة الـCE/Notified Body لو أوروبي
   - حالة WHO PQS لو مقيّم
4. واللي محتاج طلب من الشركة (CoA نموذجي + COO + شهادة مطابقة) هجهزلك **جدول طلبات جاهز** تبعتوه للمورّدين.

> 📎 ارفع الملف تاني (PDF أو حتى صورة/نص) وانا أبدأ فورًا.
