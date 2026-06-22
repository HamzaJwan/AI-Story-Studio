# UI / UX / Motion Brief

## المطلوب بصرياً

الواجهة تكون:
- عربية RTL أولاً.
- عصرية.
- جميلة.
- حركية لكن غير مزعجة.
- قريبة من حس ADC Portal من حيث الانضباط والتنظيم، لكن بأسلوب إبداعي قصصي.

## Visual Direction

### Theme
- Dark cinematic dashboard.
- أزرق عميق / بنفسجي / ذهبي خفيف.
- خلفيات gradient ناعمة.
- Cards بزوايا كبيرة.
- Glass / translucent panels بحذر.
- ظل خفيف.
- خطوط واضحة.

### Motion
استخدم Framer Motion بحركة راقية:
- fade in
- slide up
- staggered cards
- progress steps animation
- waveform placeholder animation
- scene timeline movement

لا تستخدم حركات كثيرة تشتت الكاتب.

## Main Screen — MVP

```text
┌────────────────────────────────────────┐
│ AI Story Studio                         │
│ حول قصتك العربية إلى سكريبت ومشاهد وصوت │
├────────────────────────────────────────┤
│ [Story Title]                           │
│ [Large RTL story editor]                │
│                                        │
│ Buttons:                                │
│ [تحسين كسكريبت راوي] [تقسيم لمشاهد]    │
│ [اختبار اتصال Ollama]                  │
├────────────────────────────────────────┤
│ AI Status / Provider                    │
├────────────────────────────────────────┤
│ Scene Timeline Cards                    │
│ 01 ليلة الأرق                           │
│ 02 دعوات الصباح                         │
│ ...                                     │
├────────────────────────────────────────┤
│ Output Panel                            │
│ scenes.json / narration / download later│
└────────────────────────────────────────┘
```

## Components

- AppShell
- HeroHeader
- StoryEditor
- ProviderStatusCard
- ActionBar
- SceneTimeline
- SceneCard
- OutputConsole
- StageProgress
- RiskWarningBanner

## UX Rules

1. لا تعرض كل الخيارات مرة واحدة.
2. كل مرحلة لها زر واضح.
3. لا تجعل المستخدم يظن أن الفيديو جاهز الآن.
4. ضع labels واضحة:
   - Phase 0
   - Phase 1
   - Experimental
5. أظهر تحذير أن مخرجات AI تحتاج مراجعة.
