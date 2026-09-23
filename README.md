# 📋 حقيبة الشهادات: CoA + COO + CoPP

مجموعة كاملة من **النماذج الرسمية والمراجع** لثلاث شهادات أساسية في تجارة الأدوية والمستحضرات الصيدلانية،
مجمّعة من الإنترنت من جهات رسمية (WHO / FDA) وشركات حقيقية، ومُعاد بناؤها كملفات جاهزة للطباعة والتعديل.

---

## الشهادات الثلاثة في سطور

| | **CoA** — شهادة التحليل | **COO** — شهادة المنشأ | **CoPP / CPP** — شهادة المنتج الدوائي |
|---|---|---|---|
| **اسمها الكامل** | Certificate of Analysis | Certificate of Origin | Certificate of a Pharmaceutical Product |
| **بتثبت إيه؟** | إن تشغيلة (Batch) معينة مطابقة للمواصفات: نتائج كل اختبار مقابل الحدود المسموحة | بلد تصنيع/إنتاج البضاعة | وضع المنتج الدوائي والترخيص في بلد التصدير + حالة الـGMP لموقع التصنيع |
| **مين اللي بيصدرها؟** | مصنع المنتج أو معمل رقابة جودة مستقل | الغرفة التجارية المعتمدة (وفي مصر GOEIC) — بتوقع وتختم بعد فحص الفاتورة | **سلطة الدواء في بلد التصدير فقط** (FDA / EMA states / MHRA / EDA...) — مش الشركة |
| **بتطلبها مين؟** | العميل / الرقابة عند التسليم والتسجيل | جمارك بلد الاستيراد | سلطة التسجيل الدوائي في بلد الاستيراد |
| **للواحدة ولا للتشغيلة؟** | لكل تشغيلة (Batch) | لكل شحنة | للمنتج الواحد (بكل تركيزه وشكله الصيدلاني) |

> 🆕 **عايز روابط تحميل شهادات حقيقية من مواقع الشركات؟**
> افتح [`certificates/DOWNLOAD_LINKS_FROM_COMPANIES.md`](certificates/DOWNLOAD_LINKS_FROM_COMPANIES.md) —
> فيه أدوات الشهادات الرسمية لـ BD و Cardinal Health و Thermo Fisher و Sigma-Aldrich/Merck و Medline
> + روابط PDF مباشرة لشهادات حقيقية + كل روابط FDA/WHO للـCoPP.

---

## محتوى المجلدات

### 🧪 `certificates/CoA/` — شهادة التحليل
| الملف | الوصف |
|---|---|
| `WHO_Model_CoA_template.html` | **النموذج الرسمي من WHO (TRS 1010, Annex 4)** — جاهز للطباعة A4 والتعديل |
| `WHO_Model_CoA_TRS1010_Annex4.md` | النص الكامل لإرشادات الـWHO + جدول النموذج |
| `Atlas_Bio_CoA_example.md` | مثال حقيقي من شركة أمريكية (Atlas Biologicals) منشور على موقعها |
| `IPEC-Americas_CoA_required_elements.md` | العناصر المطلوبة في CoA المواد الخام وفق دليل IPEC-Americas |

### 🌍 `certificates/COO/` — شهادة المنشأ
| الملف | الوصف |
|---|---|
| `Certificate_of_Origin_US_blank.html` | نموذج الـ**US Certificate of Origin** القياسي (نسخة UPS) — جاهز للطباعة |
| `COO_guide.md` | دليل شامل: الأنواع، الجهات المُصدرة، الحقول، سياق مصر (GOEIC / GAFTA / EUR.1) + نص نموذج Mohawk التفصيلي |
| `example_images/` | صور مرجعية لشهادات منشأ حقيقية من غرف تجارية |

### 💊 `certificates/CoPP/` — شهادة المنتج الدوائي
| الملف | الوصف |
|---|---|
| `WHO_CPP_template.html` | **نموذج WHO الرسمي الكامل** للشهادة (الأقسام 1 و2A و2B و3 و4) — جاهز للطباعة |
| `WHO_CPP_model_certificate.md` | النص الرسمي الكامل + الملاحظات التفسيرية من موقع WHO |
| `FDA_CPP_program_Form3613b.md` | إزاي تجيب CPP من الـFDA الأمريكية (نموذج 3613b / CDER eCATS) والمتطلبات |
| `WHO_Model_GMP_Certificate_TRS908.md` | بونص: نموذج WHO لشهادة الـGMP للمصنع (غالبًا بتتطلب مع الـCPP) |

---

## إزاي تستخدم النماذج المطبوعة؟

1. افتح ملف الـHTML في أي متصفح.
2. عدّل البيانات مباشرة في الملف (أو اطبعه واملأه).
3. `Ctrl+P` → **Save as PDF** لتحويله PDF جاهز — تنسيق A4 مضبوط للطباعة.

## ⚠️ نقطة مهمة جدًا: لو محتاج شهادات **فعلية** لمنتج حقيقي

النماذج هنا **مرجعية** (للتعارف على الشكل والمحتوى ومراجعة ما يصلك من الموردين). الشهادات الفعلية
لازم تتصدر من الجهة المختصة:

- **CoA** → تُطلب من **الشركة المصنعة** لكل تشغيلة (كل مصنع محترم عنده نظام إصدارها لعملائه).
- **COO** → الغرفة التجارية المعتمدة في بلد التصدير (أو GOEIC للصادرات المصرية).
- **CoPP** → تتطلبها من **صاحب الترخيص (MAH)** اللي بيقدم بدوره لسلطة الدواء في بلده
  (مثلًا FDA عبر نموذج 3613b). الشركة المصنعة **لا تستطيع** إصدارها بنفسها.
- للتحقق من صحة CPP أمريكية: FDA Export Certificate Validator — ومعظم السلطات عندها نظام تحقق إلكتروني.

## المصادر (كلها متاحة للعامة على الإنترنت)

- WHO Model CoA — TRS 1010 Annex 4:
  <https://www.who.int/docs/default-source/medicines/norms-and-standards/guidelines/quality-control/trs1010-annex4-who-model-certificate-analysis.pdf>
- WHO Model CPP (الصفحة الرسمية):
  <https://www.who.int/teams/regulation-prequalification/regulation-and-safety/regulatory-convergence-networks/certification-scheme/model-certificate-of-a-pharmaceutical-product>
- WHO Model GMP Certificate — TRS 908 Annex 5 (CDN الرسمي)
- FDA CPP program presentation: <https://www.fda.gov/media/91749/download>
- US Certificate of Origin (UPS): <https://www.ups.com/media/en/cert_of_origin.pdf>
- Mohawk Global COO template: <https://mohawkglobal.com/wp-content/uploads/2020/05/Certificate-of-origin.pdf>
- Atlas Biologicals CoA example: <https://www.atlasbio.com/wp-content/uploads/2020/04/Atlas-Bio-COA-example.pdf>
- IPEC-Americas CoA guide: <https://www.jpec.gr.jp/document/CertificateofAnalysisGuide2000.pdf>
- IFPMA CPP Training Toolkit 2021: <https://www.ifpma.org/wp-content/uploads/2023/01/i2023_IFPMA-CPP-Network-Training-Toolkit-September-2021.pdf>

---

> 💬 لو محتاج كمان: نماذج عربية، نسخة من نموذج EUR.1 / شهادة المنشأ العربية (GAFTA)،
> أو دمج النماذج دي في نظام/تطبيق — قولي.
