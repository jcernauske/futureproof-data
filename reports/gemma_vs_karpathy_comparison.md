# Gemma 4 vs Karpathy AI Exposure Score Comparison

**Overall:** FAIL

## Coverage

- Gemma 4 scored: 798 SOCs
- Karpathy scored: 389 SOCs
- Overlap: 372 SOCs (A/B comparison set)
- Union (expected Gold row count): 815

## Gate Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| 1. Pearson correlation | 0.845 | >= 0.6 | PASS |
| 2. Mean absolute diff | 1.793 | <= 2.0 | PASS |
| 3. Mean signed delta | -1.755 | [-1.0, 1.0] | FAIL |
| 4. Max category bias (n>=10) | 3.273 | <= 2.0 (n>=10) | FAIL |
| 5. Mode collapse | 26.61% on 3.0 | <= 40.0% | PASS |
| 6. Std dev floor | 1.63 | >= 1.5 | PASS |
| 7. Bucket coverage | low=58.33% mid=33.33% high=8.33% | >= 10.0% each | FAIL |
| 8. Outlier rate | 32 rows (8.6%) | <= 5.0% | FAIL |

### Category bias violations

| Category | n | Mean delta |
|----------|---|------------|
| management | 27 | -2.556 |
| business-and-financial | 23 | -2.261 |
| computer-and-information-technology | 11 | -2.727 |
| architecture-and-engineering | 32 | -2.156 |
| education-training-and-library | 15 | -2.733 |
| media-and-communication | 13 | -2.385 |
| sales | 11 | -3.273 |

## Outlier list (|Δ| ≥ 4): 32 rows

| SOC | Title | Gemma | Karpathy | Δ | Category |
|-----|-------|-------|----------|---|----------|
| 41-9012 | Models | 2 | 8 | -6 | sales |
| 15-1221 | Computer and information research scientists | 4 | 9 | -5 | computer-and-information-technology |
| 15-2021 | Mathematicians and statisticians | 4 | 9 | -5 | math |
| 41-3041 | Travel agents | 4 | 9 | -5 | sales |
| 11-2021 | Advertising, promotions, and marketing managers | 4 | 8 | -4 | management |
| 11-2022 | Sales managers | 3 | 7 | -4 | management |
| 11-2033 | Public relations and fundraising managers | 3 | 7 | -4 | management |
| 11-3131 | Training and development managers | 3 | 7 | -4 | management |
| 11-9033 | Postsecondary education administrators | 3 | 7 | -4 | management |
| 13-1075 | Labor relations specialists | 3 | 7 | -4 | business-and-financial |
| 13-1131 | Fundraisers | 3 | 7 | -4 | business-and-financial |
| 13-1151 | Training and development specialists | 3 | 7 | -4 | business-and-financial |
| 15-1241 | Computer network architects | 4 | 8 | -4 | computer-and-information-technology |
| 15-1244 | Network and computer systems administrators | 4 | 8 | -4 | computer-and-information-technology |
| 17-2061 | Computer hardware engineers | 4 | 8 | -4 | architecture-and-engineering |
| 19-1042 | Medical scientists | 3 | 7 | -4 | life-physical-and-social-science |
| 19-3033 | Psychologists | 2 | 6 | -4 | life-physical-and-social-science |
| 23-1011 | Lawyers | 4 | 8 | -4 | legal |
| 23-1022 | Arbitrators, mediators, and conciliators | 3 | 7 | -4 | legal |
| 25-2031 | High school teachers | 3 | 7 | -4 | education-training-and-library |
| 25-3011 | Adult basic and secondary education and ESL teache | 3 | 7 | -4 | education-training-and-library |
| 25-3041 | Tutors | 3 | 7 | -4 | education-training-and-library |
| 27-1011 | Art directors | 4 | 8 | -4 | arts-and-design |
| 27-2011 | Actors | 3 | 7 | -4 | entertainment-and-sports |
| 27-3031 | Public relations specialists | 4 | 8 | -4 | media-and-communication |
| 27-4015 | Broadcast, sound, and video technicians | 2 | 6 | -4 | media-and-communication |
| 27-4031 | Film and video editors and camera operators | 3 | 7 | -4 | media-and-communication |
| 29-2036 | Medical dosimetrists | 4 | 8 | -4 | healthcare |
| 41-2011 | Cashiers | 3 | 7 | -4 | sales |
| 41-3031 | Securities, commodities, and financial services sa | 4 | 8 | -4 | sales |
| 41-9031 | Sales engineers | 3 | 7 | -4 | sales |
| 53-2021 | Air traffic controllers | 3 | 7 | -4 | transportation-and-material-moving |

### Outlier rationale diff (top 10 by |Δ|)

**41-9012 — Models** (Δ -6)

- *Gemma*: The core work activities involve physical presence, creative expression, and interpersonal interaction, which are difficult for current AI to replicate in a real-world setting. While AI can assist with scheduling or information gathering, the primary value of a model lies in physical performance and human aesthetics.
- *Karpathy*: While runway and live event modeling require physical presence, the majority of modeling work results in digital or print imagery which is highly vulnerable to AI-generated synthetic media. AI can now create hyper-realistic virtual models or 'digital twins' of existing models, allowing brands to showcase clothing and products without physical photo shoots, significantly reducing the demand for human labor in commercial and catalog sectors.

**15-1221 — Computer and information research scientists** (Δ -5)

- *Gemma*: While AI can significantly automate data analysis and information retrieval, the core value of this role lies in high-level creative problem solving and decision-making. The high importance of human-edge activities like creative thinking and interpersonal relationship management provides a strong buffer against full automation.
- *Karpathy*: This occupation is fundamentally digital, involving high-level coding, algorithm design, and data analysis—all areas where AI is rapidly advancing. While these scientists are the ones building AI, the tools they create are increasingly capable of automating their own core tasks, such as writing code, simplifying algorithms, and analyzing experimental results, leading to extreme productivity gains and role restructuring.

**15-2021 — Mathematicians and statisticians** (Δ -5)

- *Gemma*: While AI can significantly assist with analyzing data, processing information, and working with computers, the core value of a mathematician lies in creative thinking and complex problem-solving. The high importance of human-edge activities like training, teaching, and decision-making provides a strong buffer against full automation.
- *Karpathy*: This occupation is almost entirely digital, involving data analysis, mathematical modeling, and coding—all domains where AI and Large Language Models excel. While high-level theoretical research and complex interdisciplinary communication require human judgment, AI can now automate significant portions of data cleaning, statistical testing, and code generation, drastically increasing individual productivity and restructuring the workflow.

**41-3041 — Travel agents** (Δ -5)

- *Gemma*: High-importance tasks like 'Working with Computers' and 'Getting Information' are highly susceptible to AI automation through automated booking and itinerary generation. However, the occupation relies heavily on human-edge activities like 'Establishing and Maintaining Interpersonal Relationships' and 'Resolving Conflicts,' which require high emotional intelligence.
- *Karpathy*: The core functions of a travel agent—researching destinations, comparing prices, building itineraries, and processing bookings—are entirely digital and involve information synthesis that AI can now perform instantly. While high-end human agents provide personalized judgment and crisis management, AI's ability to handle complex natural language queries and real-time logistics makes the vast majority of the occupation's routine tasks highly susceptible to automation.

**11-2021 — Advertising, promotions, and marketing managers** (Δ -4)

- *Gemma*: While digital tasks like working with computers and data-driven planning are highly susceptible to AI augmentation, the core value of the role lies in high-level interpersonal relationships and complex decision-making. The high importance of human-edge activities like influencing others and creative thinking provides a significant buffer against full automation.
- *Karpathy*: This occupation is predominantly digital and information-based, involving market research, data analysis, and content strategy—all areas where AI is rapidly advancing. While high-level strategic decision-making and stakeholder management provide some insulation, AI can now automate significant portions of campaign planning, creative drafting, and consumer data processing, leading to major restructuring of the role.

**11-2022 — Sales managers** (Δ -4)

- *Gemma*: While AI can assist with data-driven decision-making and communication drafting, the core high-importance activities like influencing others, building teams, and interpersonal relationship management require high-level human emotional intelligence. The role is heavily centered on real-time human judgment and social dynamics that current AI cannot replicate.
- *Karpathy*: Sales managers perform high-level knowledge work including data analysis, sales forecasting, and strategic planning, all of which are highly susceptible to AI augmentation. While the role requires significant interpersonal leadership and relationship management, much of the core digital workflow—such as monitoring CRM data, generating reports, and developing training materials—is being rapidly transformed by generative and analytical AI.

**11-2033 — Public relations and fundraising managers** (Δ -4)

- *Gemma*: While AI can significantly assist with 'Getting Information', 'Working with Computers', and data-driven donor research, the core value of the role lies in high-stakes interpersonal relationships and influencing others. The necessity for real-time human judgment and emotional intelligence in fundraising mitigates the risk of large-scale displacement.
- *Karpathy*: The core digital tasks of this role—writing press releases, drafting speeches, analyzing social media trends, and creating fundraising strategies—are highly susceptible to AI automation and enhancement. However, the role's heavy reliance on high-stakes interpersonal relationships, such as face-to-face donor meetings and managing media crises, provides a significant human-centric buffer that prevents a higher score.

**11-3131 — Training and development managers** (Δ -4)

- *Gemma*: While AI can assist with 'Working with Computers' and 'Getting Information' through content generation and data analysis, the core high-importance activities like 'Training and Teaching Others' and 'Coaching and Developing Others' require high levels of emotional intelligence and real-time human judgment. The role is heavily interpersonal and relies on building relationships, which are difficult for AI to replicate effectively.
- *Karpathy*: This role is predominantly digital and knowledge-based, involving the creation of instructional content, data-driven needs assessments, and budget management—all areas where AI is highly capable. While the role requires significant human-centric leadership and stakeholder collaboration, AI can automate the generation of training materials, personalize learning paths, and analyze program effectiveness, substantially increasing the productivity of each manager.

**11-9033 — Postsecondary education administrators** (Δ -4)

- *Gemma*: While AI can assist with information gathering and organizational planning, the core functions of this role rely heavily on high-level decision-making, interpersonal relationship management, and motivating subordinates. The high importance of human-edge activities like creative thinking and team building provides a significant buffer against full automation.
- *Karpathy*: This occupation is heavily centered on digital information processing, including reviewing applications, analyzing student data, managing budgets, and maintaining academic records—all tasks where AI can significantly increase productivity or automate routine workflows. While roles like deans and student affairs officers require high-level human judgment and interpersonal relationship management, the underlying administrative and analytical work is highly susceptible to AI integration and restructuring.

**13-1075 — Labor relations specialists** (Δ -4)

- *Gemma*: While AI can assist with 'Getting Information' and drafting communications, the core functions rely on high-stakes negotiation, real-time conflict resolution, and complex interpersonal relationship management. These activities require nuanced human judgment and emotional intelligence that current AI cannot replicate in high-pressure labor environments.
- *Karpathy*: This occupation is predominantly digital and knowledge-based, involving the drafting of contracts, policy development, and legal compliance—all areas where AI excels. While the high-stakes interpersonal negotiation and dispute resolution provide a buffer, AI will significantly automate the research, document generation, and investigative analysis components of the role.

## Fail policy

`overall_pass=False` blocks the Gold promote. Operator must either (a) revise the prompt and re-run the batch, or (b) document an explicit override rationale in the spec §6 Implementation Log before proceeding.