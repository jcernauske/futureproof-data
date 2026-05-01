# Language Support Decision Report

Date: 2026-04-30

Related docs:

- `docs/hackathon_rules.txt`
- `docs/rules2.txt`
- `docs/gemma4-features-hackathon-report.md`
- `docs/gemma4-feature-usage-scorecard.md`

## Decision

FutureProof will frame hackathon language support around:

1. English
2. Spanish
3. Arabic

English is the default U.S. school language. Spanish is already implemented as the first translated experience. Arabic is the best next language to support for the hackathon’s Digital Equity & Inclusivity story because it is the most common non-Spanish home language reported among U.S. public school English learner students.

This is intentionally narrow. The goal is not to claim broad 140-language product coverage. The goal is to demonstrate that FutureProof’s architecture can translate both static UI and Gemma-generated guidance for high-impact student populations while preserving canonical school, occupation, source, salary, percentage, and code values.

## Source Findings

### Public school English learner home languages

The most relevant dataset for FutureProof is not all U.S. households. It is U.S. public school students, especially English learners, because the product is positioned as student career guidance.

NCES Condition of Education, using fall 2021 EDFacts data, reports the ten most common home languages of English learners in public schools:

| Rank | Home language | EL students | Share of ELs |
|---:|---|---:|---:|
| 1 | Spanish / Castilian | 4,023,289 | 76.4% |
| 2 | Arabic | 130,917 | 2.5% |
| 3 | English | 116,771 | 2.2% |
| 4 | Chinese | 95,584 | 1.8% |
| 5 | Vietnamese | 75,070 | 1.4% |
| 6 | Portuguese | 50,205 | 1.0% |
| 7 | Russian | 39,403 | 0.7% |
| 8 | Haitian / Haitian Creole | 31,122 | 0.6% |
| 9 | Hmong | 30,181 | 0.6% |
| 10 | Urdu | 26,567 | 0.5% |

NCES notes that English can be reported as an English learner’s home language in multilingual-household or adoption-related situations. For product language expansion, the practical non-English sequence after Spanish is:

1. Arabic
2. Chinese
3. Vietnamese
4. Portuguese

NCELA/OELA’s 2022-23 summary also lists the top non-English English learner languages nationally as Spanish, Arabic, Chinese, Vietnamese, and Portuguese.

### All U.S. households are a different question

For all U.S. households, not specifically school English learners, Census-style summaries commonly rank Chinese after English and Spanish. That is useful general context, but it is less relevant to FutureProof’s school-centered equity pitch than the English learner home-language data.

## Why English, Spanish, and Arabic

### English

English remains the default product language and the language of most official U.S. education and labor-market data. It also acts as the canonical fallback for unsupported locales.

### Spanish

Spanish is the highest-impact translated language for U.S. students. In the NCES English learner data, Spanish accounts for 76.4 percent of EL public school students and 8.4 percent of total public school enrollment.

Spanish is already implemented in FutureProof:

- frontend English/Spanish string table in `frontend/src/i18n/strings.ts`
- locale type and normalizer in `frontend/src/i18n/locales.ts`
- language selector in `frontend/src/screens/ProfileScreen.tsx`
- persisted profile locale in `frontend/src/store/profileStore.ts`
- backend Gemma language instructions and localized fallbacks in `backend/app/services/locale.py`
- locale threaded through Gemma-generated guidance, boss narratives, Ask Gemma, career-pick Q&A, skill recommendations, skill pools, and next steps

### Arabic

Arabic is the strongest next language for the hackathon because it is the most common non-Spanish home language among U.S. public school English learners in the NCES data.

Arabic also pairs well with Gemma 4’s multilingual positioning. Google AI’s Gemma 4 model card describes Gemma 4 as maintaining multilingual support across 140+ languages. Supporting Arabic would show that FutureProof is using that capability for a concrete U.S. school access problem, not as a generic “many languages” claim.

## Implementation Caveat for Arabic

Arabic is higher risk than Spanish because it is right-to-left. Supporting Arabic properly requires more than adding translated strings:

- set `dir="rtl"` for Arabic views or the app shell
- verify layout mirroring for navigation, cards, menus, charts, and controls
- check text alignment and mixed Arabic/English content
- preserve official English school names, occupation titles, data-source acronyms, CIP/SOC codes, dollar amounts, and percentages
- test punctuation, truncation, wrapping, and long labels
- verify Gemma prompts preserve JSON keys and enum values in English while generating student-facing prose in Arabic

For the hackathon, Arabic should only be claimed as supported if the main demo path is manually tested end-to-end.

## Recommended Submission Framing

Use:

> FutureProof currently supports English and Spanish, and its language architecture is being extended to Arabic because Arabic is the most common non-Spanish home language among U.S. public school English learners.

Use after Arabic is implemented and tested:

> FutureProof supports English, Spanish, and Arabic across the student-facing app and Gemma-generated guidance, while preserving official school names, occupation titles, source acronyms, dollar amounts, percentages, and structured data fields.

Avoid:

- “FutureProof supports 140 languages.”
- “Arabic support is complete” unless the full golden path has been tested in RTL.
- “Automatic translation solves access.” The stronger claim is that Gemma 4 plus a controlled locale layer lets the app provide translated guidance while preserving canonical education and labor-market data.

## Sources

- NCES Condition of Education, English Learners in Public Schools: https://nces.ed.gov/programs/coe/indicator/cgf
- NCELA/OELA, “Information Elevated: The Most Common Languages of English Learners: School Year 2022-23”: https://ncela.ed.gov/resources/media-information-elevated-the-most-common-languages-of-english-learners-school-year-sy
- Google AI for Developers, Gemma 4 model card: https://ai.google.dev/gemma/docs/core/model_card_4
- Google AI for Developers, Gemma overview: https://ai.google.dev/gemma/docs
