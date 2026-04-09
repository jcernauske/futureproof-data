# SOC Code Alignment Audit: raw.bls_ooh

**Date:** 2026-04-07
**Agent:** @data-analyst
**Dataset:** data/raw/xlsx_cache/bls_ooh.xlsx
**Total Occupations:** 832

## Summary

All 832 SOC codes pass format validation (XX-XXXX pattern). No nulls, no duplicates. The dataset covers all 22 SOC major groups with detailed occupation-level codes. 134 codes follow the "9X" catch-all pattern ("all other" categories). 7 codes are rolled-up/broad occupation codes ending in 0 that combine multiple detailed occupations -- these need special handling in the Silver zone ConceptNormalizer.

## Format Validation

| Check | Result |
|-------|--------|
| Total SOC codes | 832 |
| Null SOC codes | 0 (0.0%) |
| Valid XX-XXXX format | 832 (100.0%) |
| Invalid format | 0 |
| Unique SOC codes | 832 (100.0% -- no duplicates) |

## SOC Codes by Major Group

| Code | Major Group | Count |
|------|-------------|-------|
| 11-xxxx | Management | 38 |
| 13-xxxx | Business and Financial Operations | 32 |
| 15-xxxx | Computer and Mathematical | 21 |
| 17-xxxx | Architecture and Engineering | 36 |
| 19-xxxx | Life, Physical, and Social Science | 48 |
| 21-xxxx | Community and Social Service | 17 |
| 23-xxxx | Legal | 8 |
| 25-xxxx | Educational Instruction and Library | 64 |
| 27-xxxx | Arts, Design, Entertainment, Sports, and Media | 41 |
| 29-xxxx | Healthcare Practitioners and Technical | 71 |
| 31-xxxx | Healthcare Support | 17 |
| 33-xxxx | Protective Service | 24 |
| 35-xxxx | Food Preparation and Serving Related | 17 |
| 37-xxxx | Building and Grounds Cleaning and Maintenance | 10 |
| 39-xxxx | Personal Care and Service | 32 |
| 41-xxxx | Sales and Related | 22 |
| 43-xxxx | Office and Administrative Support | 54 |
| 45-xxxx | Farming, Fishing, and Forestry | 14 |
| 47-xxxx | Construction and Extraction | 60 |
| 49-xxxx | Installation, Maintenance, and Repair | 51 |
| 51-xxxx | Production | 105 |
| 53-xxxx | Transportation and Material Moving | 50 |

## Rolled-Up / Broad Occupation Codes

These 7 codes end in `0` and represent aggregated occupations rather than detailed SOC codes. They need special handling in the Silver zone ConceptNormalizer because they will NOT have a 1:1 match in O*NET detailed codes (which use XX-XXXX.XX format at the detailed level).

| SOC Code | Occupation Title | Issue |
|----------|-----------------|-------|
| 13-1020 | Buyers and purchasing agents | Broad occupation combining detailed codes |
| 13-2020 | Property appraisers and assessors | Broad occupation combining detailed codes |
| 29-2010 | Clinical laboratory technologists and technicians | Broad occupation combining detailed codes |
| 31-1120 | Home health and personal care aides | Broad occupation combining detailed codes |
| 39-7010 | Tour and travel guides | Broad occupation combining detailed codes |
| 47-4090 | Miscellaneous construction and related workers | Miscellaneous catch-all |
| 51-2090 | Miscellaneous assemblers and fabricators | Miscellaneous catch-all |

**ConceptNormalizer implication:** These codes may need to be mapped to multiple O*NET detailed codes or handled as parent codes in the CIP-SOC crosswalk. The crosswalk typically uses 6-digit SOC codes (XX-XXXX), so these should match, but O*NET extends to 8 digits (XX-XXXX.XX) where these broad codes may not exist.

## Catch-All Categories (9X Pattern)

134 of 832 SOC codes (16.1%) follow the "9X" pattern in positions 5-6, which typically indicates "all other" catch-all categories within a minor group. These are legitimate BLS codes but represent residual occupations not separately classified.

| SOC Code | Occupation Title |
|----------|-----------------|
| 11-9199 | Managers, all other |
| 13-1199 | Business operations specialists, all other |
| 13-2099 | Financial specialists, all other |
| 15-1299 | Computer occupations, all other |
| 15-2099 | Mathematical science occupations, all other |
| 17-2199 | Engineers, all other |
| 19-1099 | Life scientists, all other |
| 19-2099 | Physical scientists, all other |
| 19-3091 | Anthropologists and archeologists |
| 19-3092 | Geographers |
| 19-3093 | Historians |
| 19-3094 | Political scientists |
| 19-3099 | Social scientists and related workers, all other |
| 19-4092 | Forensic science technicians |
| 19-4099 | Life, physical, and social science technicians, all other |
| 21-1091 | Health education specialists |
| 21-1092 | Probation officers and correctional treatment specialists |
| 21-1093 | Social and human service assistants |
| 21-1094 | Community health workers |
| 21-1099 | Community and social service specialists, all other |
| 21-2099 | Religious workers, all other |
| 23-2093 | Title examiners, abstractors, and searchers |
| 23-2099 | Legal support workers, all other |
| 25-1192 | Family and consumer sciences teachers, postsecondary |
| 25-1193 | Recreation and fitness studies teachers, postsecondary |
| 25-1194 | Career/technical education teachers, postsecondary |
| 25-1199 | Postsecondary teachers, all other |
| 25-3099 | Teachers and instructors, all other |
| 25-9099 | Educational instruction and library workers, all other |
| 27-2091 | Disc jockeys, except radio |
| 27-2099 | Entertainers and performers, sports and related workers, all other |
| 27-3091 | Interpreters and translators |
| 27-3092 | Court reporters and simultaneous captioners |
| 27-3099 | Media and communication workers, all other |
| 27-4099 | Media and communication equipment workers, all other |
| 29-1291 | Acupuncturists |
| 29-1292 | Dental hygienists |
| 29-1299 | Healthcare diagnosing or treating practitioners, all other |
| 29-2091 | Orthotists and prosthetists |
| 29-2092 | Hearing aid specialists |
| 29-2099 | Health technologists and technicians, all other |
| 29-9091 | Athletic trainers |
| 29-9092 | Genetic counselors |
| 29-9093 | Surgical assistants |
| 29-9099 | Healthcare practitioners and technical workers, all other |
| 31-9091 | Dental assistants |
| 31-9092 | Medical assistants |
| 31-9093 | Medical equipment preparers |
| 31-9094 | Medical transcriptionists |
| 31-9095 | Pharmacy aides |
| 31-9096 | Veterinary assistants and laboratory animal caretakers |
| 31-9097 | Phlebotomists |
| 31-9099 | Healthcare support workers, all other |
| 33-1091 | First-line supervisors of security workers |
| 33-1099 | First-line supervisors of protective service workers, all other |
| 33-9091 | Crossing guards and flaggers |
| 33-9092 | Lifeguards, ski patrol, and other recreational protective service workers |
| 33-9093 | Transportation security screeners |
| 33-9094 | School bus monitors |
| 33-9099 | Protective service workers, all other |
| 35-9099 | Food preparation and serving related workers, all other |
| 39-3091 | Amusement and recreation attendants |
| 39-3092 | Costume attendants |
| 39-3093 | Locker room, coatroom, and dressing room attendants |
| 39-3099 | Entertainment attendants and related workers, all other |
| 39-5091 | Makeup artists, theatrical and performance |
| 39-5092 | Manicurists and pedicurists |
| 39-5093 | Shampooers |
| 39-5094 | Skincare specialists |
| 39-9099 | Personal care and service workers, all other |
| 41-3091 | Sales representatives of services, except advertising, insurance, financial services, and travel |
| 41-9091 | Door-to-door sales workers, news and street vendors, and related workers |
| 41-9099 | Sales and related workers, all other |
| 43-2099 | Communications equipment operators, all other |
| 43-3099 | Financial clerks, all other |
| 43-4199 | Information and record clerks, all other |
| 43-9199 | Office and administrative support workers, all other |
| 45-2091 | Agricultural equipment operators |
| 45-2092 | Farmworkers and laborers, crop, nursery, and greenhouse |
| 45-2093 | Farmworkers, farm, ranch, and aquacultural animals |
| 45-2099 | Agricultural workers, all other |
| 47-4090 | Miscellaneous construction and related workers |
| 47-5099 | Extraction workers, all other |
| 49-2091 | Avionics technicians |
| 49-2092 | Electric motor, power tool, and related repairers |
| 49-2093 | Electrical and electronics installers and repairers, transportation equipment |
| 49-2094 | Electrical and electronics repairers, commercial and industrial equipment |
| 49-2095 | Electrical and electronics repairers, powerhouse, substation, and relay |
| 49-2096 | Electronic equipment installers and repairers, motor vehicles |
| 49-2097 | Audiovisual equipment installers and repairers |
| 49-2098 | Security and fire alarm systems installers |
| 49-3091 | Bicycle repairers |
| 49-3092 | Recreational vehicle service technicians |
| 49-3093 | Tire repairers and changers |
| 49-9091 | Coin, vending, and amusement machine servicers and repairers |
| 49-9092 | Commercial divers |
| 49-9094 | Locksmiths and safe repairers |
| 49-9095 | Manufactured building and mobile home installers |
| 49-9096 | Riggers |
| 49-9097 | Signal and track switch repairers |
| 49-9098 | Helpers--installation, maintenance, and repair workers |
| 49-9099 | Installation, maintenance, and repair workers, all other |
| 51-2090 | Miscellaneous assemblers and fabricators |
| 51-3091 | Food and tobacco roasting, baking, and drying machine operators and tenders |
| 51-3092 | Food batchmakers |
| 51-3093 | Food cooking machine operators and tenders |
| 51-3099 | Food processing workers, all other |
| 51-4191 | Heat treating equipment setters, operators, and tenders, metal and plastic |
| 51-4192 | Layout workers, metal and plastic |
| 51-4193 | Plating machine setters, operators, and tenders, metal and plastic |
| 51-4194 | Tool grinders, filers, and sharpeners |
| 51-4199 | Metal workers and plastic workers, all other |
| 51-6091 | Extruding and forming machine setters, operators, and tenders, synthetic and glass fibers |
| 51-6092 | Fabric and apparel patternmakers |
| 51-6093 | Upholsterers |
| 51-6099 | Textile, apparel, and furnishings workers, all other |
| 51-7099 | Woodworkers, all other |
| 51-8091 | Chemical plant and system operators |
| 51-8092 | Gas plant operators |
| 51-8093 | Petroleum pump system operators, refinery operators, and gaugers |
| 51-8099 | Plant and system operators, all other |
| 51-9191 | Adhesive bonding machine operators and tenders |
| 51-9192 | Cleaning, washing, and metal pickling equipment operators and tenders |
| 51-9193 | Cooling and freezing equipment operators and tenders |
| 51-9194 | Etchers and engravers |
| 51-9195 | Molders, shapers, and casters, except metal and plastic |
| 51-9196 | Paper goods machine setters, operators, and tenders |
| 51-9197 | Tire builders |
| 51-9198 | Helpers--production workers |
| 51-9199 | Production workers, all other |
| 53-3099 | Motor vehicle operators, all other |
| 53-4099 | Rail transportation workers, all other |
| 53-6099 | Transportation workers, all other |
| 53-7199 | Material moving workers, all other |

**Important distinction:** Not all 9X-pattern codes are catch-alls. Many are specific occupations that happen to fall in the 90-99 range within their minor group (e.g., 29-1292 Dental hygienists, 19-3094 Political scientists). Only codes with titles containing "all other" are true catch-alls. Of the 134 codes matching the 9X pattern, approximately 46 are "all other" categories and the remaining 88 are specific occupations.

## Cross-Reference Notes for Silver Zone

### O*NET Alignment (XX-XXXX.XX format)
- Our 832 SOC codes use the 6-digit XX-XXXX format
- O*NET uses 8-digit XX-XXXX.XX format, extending each SOC code with a 2-digit suffix
- Most of our codes will match O*NET as XX-XXXX.00 (the base occupation)
- The 7 rolled-up/broad codes (ending in 0) may NOT have direct O*NET equivalents
- ConceptNormalizer should use prefix matching (our XX-XXXX matches O*NET XX-XXXX.XX)

### CIP-to-SOC Crosswalk
- The NCES/BLS CIP-SOC crosswalk maps CIP codes (from College Scorecard) to SOC codes
- The crosswalk uses 6-digit SOC codes, matching our format exactly
- Many-to-many relationship: one CIP code can map to multiple SOC codes and vice versa
- The 46 "all other" catch-all SOC codes may have limited or no CIP mappings in the crosswalk
- The 7 rolled-up codes should be checked against the crosswalk for explicit mappings

## Complete SOC Code Reference

832 unique SOC codes, sorted by code. See table below.

| SOC Code | Occupation Title |
|----------|-----------------|
| 11-1011 | Chief executives |
| 11-1021 | General and operations managers |
| 11-1031 | Legislators |
| 11-2011 | Advertising and promotions managers |
| 11-2021 | Marketing managers |
| 11-2022 | Sales managers |
| 11-2032 | Public relations managers |
| 11-2033 | Fundraising managers |
| 11-3012 | Administrative services managers |
| 11-3013 | Facilities managers |
| 11-3021 | Computer and information systems managers |
| 11-3031 | Financial managers |
| 11-3051 | Industrial production managers |
| 11-3061 | Purchasing managers |
| 11-3071 | Transportation, storage, and distribution managers |
| 11-3111 | Compensation and benefits managers |
| 11-3121 | Human resources managers |
| 11-3131 | Training and development managers |
| 11-9013 | Farmers, ranchers, and other agricultural managers |
| 11-9021 | Construction managers |
| 11-9031 | Education and childcare administrators, preschool and daycare |
| 11-9032 | Education administrators, kindergarten through secondary |
| 11-9033 | Education administrators, postsecondary |
| 11-9039 | Education administrators, all other |
| 11-9041 | Architectural and engineering managers |
| 11-9051 | Food service managers |
| 11-9071 | Gambling managers |
| 11-9072 | Entertainment and recreation managers, except gambling |
| 11-9081 | Lodging managers |
| 11-9111 | Medical and health services managers |
| 11-9121 | Natural sciences managers |
| 11-9131 | Postmasters and mail superintendents |
| 11-9141 | Property, real estate, and community association managers |
| 11-9151 | Social and community service managers |
| 11-9161 | Emergency management directors |
| 11-9171 | Funeral home managers |
| 11-9179 | Personal service managers, all other |
| 11-9199 | Managers, all other |
| 13-1011 | Agents and business managers of artists, performers, and athletes |
| 13-1020 | Buyers and purchasing agents |
| 13-1031 | Claims adjusters, examiners, and investigators |
| 13-1032 | Insurance appraisers, auto damage |
| 13-1041 | Compliance officers |
| 13-1051 | Cost estimators |
| 13-1071 | Human resources specialists |
| 13-1074 | Farm labor contractors |
| 13-1075 | Labor relations specialists |
| 13-1081 | Logisticians |
| 13-1082 | Project management specialists |
| 13-1111 | Management analysts |
| 13-1121 | Meeting, convention, and event planners |
| 13-1131 | Fundraisers |
| 13-1141 | Compensation, benefits, and job analysis specialists |
| 13-1151 | Training and development specialists |
| 13-1161 | Market research analysts and marketing specialists |
| 13-1199 | Business operations specialists, all other |
| 13-2011 | Accountants and auditors |
| 13-2020 | Property appraisers and assessors |
| 13-2031 | Budget analysts |
| 13-2041 | Credit analysts |
| 13-2051 | Financial and investment analysts |
| 13-2052 | Personal financial advisors |
| 13-2053 | Insurance underwriters |
| 13-2054 | Financial risk specialists |
| 13-2061 | Financial examiners |
| 13-2071 | Credit counselors |
| 13-2072 | Loan officers |
| 13-2081 | Tax examiners and collectors, and revenue agents |
| 13-2082 | Tax preparers |
| 13-2099 | Financial specialists, all other |
| 15-1211 | Computer systems analysts |
| 15-1212 | Information security analysts |
| 15-1221 | Computer and information research scientists |
| 15-1231 | Computer network support specialists |
| 15-1232 | Computer user support specialists |
| 15-1241 | Computer network architects |
| 15-1242 | Database administrators |
| 15-1243 | Database architects |
| 15-1244 | Network and computer systems administrators |
| 15-1251 | Computer programmers |
| 15-1252 | Software developers |
| 15-1253 | Software quality assurance analysts and testers |
| 15-1254 | Web developers |
| 15-1255 | Web and digital interface designers |
| 15-1299 | Computer occupations, all other |
| 15-2011 | Actuaries |
| 15-2021 | Mathematicians |
| 15-2031 | Operations research analysts |
| 15-2041 | Statisticians |
| 15-2051 | Data scientists |
| 15-2099 | Mathematical science occupations, all other |
| 17-1011 | Architects, except landscape and naval |
| 17-1012 | Landscape architects |
| 17-1021 | Cartographers and photogrammetrists |
| 17-1022 | Surveyors |
| 17-2011 | Aerospace engineers |
| 17-2021 | Agricultural engineers |
| 17-2031 | Bioengineers and biomedical engineers |
| 17-2041 | Chemical engineers |
| 17-2051 | Civil engineers |
| 17-2061 | Computer hardware engineers |
| 17-2071 | Electrical engineers |
| 17-2072 | Electronics engineers, except computer |
| 17-2081 | Environmental engineers |
| 17-2111 | Health and safety engineers, except mining safety engineers and inspectors |
| 17-2112 | Industrial engineers |
| 17-2121 | Marine engineers and naval architects |
| 17-2131 | Materials engineers |
| 17-2141 | Mechanical engineers |
| 17-2151 | Mining and geological engineers, including mining safety engineers |
| 17-2161 | Nuclear engineers |
| 17-2171 | Petroleum engineers |
| 17-2199 | Engineers, all other |
| 17-3011 | Architectural and civil drafters |
| 17-3012 | Electrical and electronics drafters |
| 17-3013 | Mechanical drafters |
| 17-3019 | Drafters, all other |
| 17-3021 | Aerospace engineering and operations technologists and technicians |
| 17-3022 | Civil engineering technologists and technicians |
| 17-3023 | Electrical and electronic engineering technologists and technicians |
| 17-3024 | Electro-mechanical and mechatronics technologists and technicians |
| 17-3025 | Environmental engineering technologists and technicians |
| 17-3026 | Industrial engineering technologists and technicians |
| 17-3027 | Mechanical engineering technologists and technicians |
| 17-3028 | Calibration technologists and technicians |
| 17-3029 | Engineering technologists and technicians, except drafters, all other |
| 17-3031 | Surveying and mapping technicians |
| 19-1011 | Animal scientists |
| 19-1012 | Food scientists and technologists |
| 19-1013 | Soil and plant scientists |
| 19-1021 | Biochemists and biophysicists |
| 19-1022 | Microbiologists |
| 19-1023 | Zoologists and wildlife biologists |
| 19-1029 | Biological scientists, all other |
| 19-1031 | Conservation scientists |
| 19-1032 | Foresters |
| 19-1041 | Epidemiologists |
| 19-1042 | Medical scientists, except epidemiologists |
| 19-1099 | Life scientists, all other |
| 19-2011 | Astronomers |
| 19-2012 | Physicists |
| 19-2021 | Atmospheric and space scientists |
| 19-2031 | Chemists |
| 19-2032 | Materials scientists |
| 19-2041 | Environmental scientists and specialists, including health |
| 19-2042 | Geoscientists, except hydrologists and geographers |
| 19-2043 | Hydrologists |
| 19-2099 | Physical scientists, all other |
| 19-3011 | Economists |
| 19-3022 | Survey researchers |
| 19-3032 | Industrial-organizational psychologists |
| 19-3033 | Clinical and counseling psychologists |
| 19-3034 | School psychologists |
| 19-3039 | Psychologists, all other |
| 19-3041 | Sociologists |
| 19-3051 | Urban and regional planners |
| 19-3091 | Anthropologists and archeologists |
| 19-3092 | Geographers |
| 19-3093 | Historians |
| 19-3094 | Political scientists |
| 19-3099 | Social scientists and related workers, all other |
| 19-4012 | Agricultural technicians |
| 19-4013 | Food science technicians |
| 19-4021 | Biological technicians |
| 19-4031 | Chemical technicians |
| 19-4042 | Environmental science and protection technicians, including health |
| 19-4043 | Geological technicians, except hydrologic technicians |
| 19-4044 | Hydrologic technicians |
| 19-4051 | Nuclear technicians |
| 19-4061 | Social science research assistants |
| 19-4071 | Forest and conservation technicians |
| 19-4092 | Forensic science technicians |
| 19-4099 | Life, physical, and social science technicians, all other |
| 19-5011 | Occupational health and safety specialists |
| 19-5012 | Occupational health and safety technicians |
| 21-1012 | Educational, guidance, and career counselors and advisors |
| 21-1013 | Marriage and family therapists |
| 21-1015 | Rehabilitation counselors |
| 21-1018 | Substance abuse, behavioral disorder, and mental health counselors |
| 21-1019 | Counselors, all other |
| 21-1021 | Child, family, and school social workers |
| 21-1022 | Healthcare social workers |
| 21-1023 | Mental health and substance abuse social workers |
| 21-1029 | Social workers, all other |
| 21-1091 | Health education specialists |
| 21-1092 | Probation officers and correctional treatment specialists |
| 21-1093 | Social and human service assistants |
| 21-1094 | Community health workers |
| 21-1099 | Community and social service specialists, all other |
| 21-2011 | Clergy |
| 21-2021 | Directors, religious activities and education |
| 21-2099 | Religious workers, all other |
| 23-1011 | Lawyers |
| 23-1012 | Judicial law clerks |
| 23-1021 | Administrative law judges, adjudicators, and hearing officers |
| 23-1022 | Arbitrators, mediators, and conciliators |
| 23-1023 | Judges, magistrate judges, and magistrates |
| 23-2011 | Paralegals and legal assistants |
| 23-2093 | Title examiners, abstractors, and searchers |
| 23-2099 | Legal support workers, all other |
| 25-1011 | Business teachers, postsecondary |
| 25-1021 | Computer science teachers, postsecondary |
| 25-1022 | Mathematical science teachers, postsecondary |
| 25-1031 | Architecture teachers, postsecondary |
| 25-1032 | Engineering teachers, postsecondary |
| 25-1041 | Agricultural sciences teachers, postsecondary |
| 25-1042 | Biological science teachers, postsecondary |
| 25-1043 | Forestry and conservation science teachers, postsecondary |
| 25-1051 | Atmospheric, earth, marine, and space sciences teachers, postsecondary |
| 25-1052 | Chemistry teachers, postsecondary |
| 25-1053 | Environmental science teachers, postsecondary |
| 25-1054 | Physics teachers, postsecondary |
| 25-1061 | Anthropology and archeology teachers, postsecondary |
| 25-1062 | Area, ethnic, and cultural studies teachers, postsecondary |
| 25-1063 | Economics teachers, postsecondary |
| 25-1064 | Geography teachers, postsecondary |
| 25-1065 | Political science teachers, postsecondary |
| 25-1066 | Psychology teachers, postsecondary |
| 25-1067 | Sociology teachers, postsecondary |
| 25-1069 | Social sciences teachers, postsecondary, all other |
| 25-1071 | Health specialties teachers, postsecondary |
| 25-1072 | Nursing instructors and teachers, postsecondary |
| 25-1081 | Education teachers, postsecondary |
| 25-1082 | Library science teachers, postsecondary |
| 25-1111 | Criminal justice and law enforcement teachers, postsecondary |
| 25-1112 | Law teachers, postsecondary |
| 25-1113 | Social work teachers, postsecondary |
| 25-1121 | Art, drama, and music teachers, postsecondary |
| 25-1122 | Communications teachers, postsecondary |
| 25-1123 | English language and literature teachers, postsecondary |
| 25-1124 | Foreign language and literature teachers, postsecondary |
| 25-1125 | History teachers, postsecondary |
| 25-1126 | Philosophy and religion teachers, postsecondary |
| 25-1192 | Family and consumer sciences teachers, postsecondary |
| 25-1193 | Recreation and fitness studies teachers, postsecondary |
| 25-1194 | Career/technical education teachers, postsecondary |
| 25-1199 | Postsecondary teachers, all other |
| 25-2011 | Preschool teachers, except special education |
| 25-2012 | Kindergarten teachers, except special education |
| 25-2021 | Elementary school teachers, except special education |
| 25-2022 | Middle school teachers, except special and career/technical education |
| 25-2023 | Career/technical education teachers, middle school |
| 25-2031 | Secondary school teachers, except special and career/technical education |
| 25-2032 | Career/technical education teachers, secondary school |
| 25-2051 | Special education teachers, preschool |
| 25-2052 | Special education teachers, kindergarten and elementary school |
| 25-2057 | Special education teachers, middle school |
| 25-2058 | Special education teachers, secondary school |
| 25-2059 | Special education teachers, all other |
| 25-3011 | Adult basic education, adult secondary education, and english as a second language instructors |
| 25-3021 | Self-enrichment teachers |
| 25-3031 | Substitute teachers, short-term |
| 25-3041 | Tutors |
| 25-3099 | Teachers and instructors, all other |
| 25-4011 | Archivists |
| 25-4012 | Curators |
| 25-4013 | Museum technicians and conservators |
| 25-4022 | Librarians and media collections specialists |
| 25-4031 | Library technicians |
| 25-9021 | Farm and home management educators |
| 25-9031 | Instructional coordinators |
| 25-9044 | Teaching assistants, postsecondary |
| 25-9045 | Teaching assistants, except postsecondary |
| 25-9099 | Educational instruction and library workers, all other |
| 27-1011 | Art directors |
| 27-1012 | Craft artists |
| 27-1013 | Fine artists, including painters, sculptors, and illustrators |
| 27-1014 | Special effects artists and animators |
| 27-1019 | Artists and related workers, all other |
| 27-1021 | Commercial and industrial designers |
| 27-1022 | Fashion designers |
| 27-1023 | Floral designers |
| 27-1024 | Graphic designers |
| 27-1025 | Interior designers |
| 27-1026 | Merchandise displayers and window trimmers |
| 27-1027 | Set and exhibit designers |
| 27-1029 | Designers, all other |
| 27-2011 | Actors |
| 27-2012 | Producers and directors |
| 27-2021 | Athletes and sports competitors |
| 27-2022 | Coaches and scouts |
| 27-2023 | Umpires, referees, and other sports officials |
| 27-2031 | Dancers |
| 27-2032 | Choreographers |
| 27-2041 | Music directors and composers |
| 27-2042 | Musicians and singers |
| 27-2091 | Disc jockeys, except radio |
| 27-2099 | Entertainers and performers, sports and related workers, all other |
| 27-3011 | Broadcast announcers and radio disc jockeys |
| 27-3023 | News analysts, reporters, and journalists |
| 27-3031 | Public relations specialists |
| 27-3041 | Editors |
| 27-3042 | Technical writers |
| 27-3043 | Writers and authors |
| 27-3091 | Interpreters and translators |
| 27-3092 | Court reporters and simultaneous captioners |
| 27-3099 | Media and communication workers, all other |
| 27-4011 | Audio and video technicians |
| 27-4012 | Broadcast technicians |
| 27-4014 | Sound engineering technicians |
| 27-4015 | Lighting technicians |
| 27-4021 | Photographers |
| 27-4031 | Camera operators, television, video, and film |
| 27-4032 | Film and video editors |
| 27-4099 | Media and communication equipment workers, all other |
| 29-1011 | Chiropractors |
| 29-1021 | Dentists, general |
| 29-1022 | Oral and maxillofacial surgeons |
| 29-1023 | Orthodontists |
| 29-1024 | Prosthodontists |
| 29-1029 | Dentists, all other specialists |
| 29-1031 | Dietitians and nutritionists |
| 29-1041 | Optometrists |
| 29-1051 | Pharmacists |
| 29-1071 | Physician assistants |
| 29-1081 | Podiatrists |
| 29-1122 | Occupational therapists |
| 29-1123 | Physical therapists |
| 29-1124 | Radiation therapists |
| 29-1125 | Recreational therapists |
| 29-1126 | Respiratory therapists |
| 29-1127 | Speech-language pathologists |
| 29-1128 | Exercise physiologists |
| 29-1129 | Therapists, all other |
| 29-1131 | Veterinarians |
| 29-1141 | Registered nurses |
| 29-1151 | Nurse anesthetists |
| 29-1161 | Nurse midwives |
| 29-1171 | Nurse practitioners |
| 29-1181 | Audiologists |
| 29-1211 | Anesthesiologists |
| 29-1212 | Cardiologists |
| 29-1213 | Dermatologists |
| 29-1214 | Emergency medicine physicians |
| 29-1215 | Family medicine physicians |
| 29-1216 | General internal medicine physicians |
| 29-1217 | Neurologists |
| 29-1218 | Obstetricians and gynecologists |
| 29-1221 | Pediatricians, general |
| 29-1222 | Physicians, pathologists |
| 29-1223 | Psychiatrists |
| 29-1224 | Radiologists |
| 29-1229 | Physicians, all other |
| 29-1241 | Ophthalmologists, except pediatric |
| 29-1242 | Orthopedic surgeons, except pediatric |
| 29-1243 | Pediatric surgeons |
| 29-1249 | Surgeons, all other |
| 29-1291 | Acupuncturists |
| 29-1292 | Dental hygienists |
| 29-1299 | Healthcare diagnosing or treating practitioners, all other |
| 29-2010 | Clinical laboratory technologists and technicians |
| 29-2031 | Cardiovascular technologists and technicians |
| 29-2032 | Diagnostic medical sonographers |
| 29-2033 | Nuclear medicine technologists |
| 29-2034 | Radiologic technologists and technicians |
| 29-2035 | Magnetic resonance imaging technologists |
| 29-2036 | Medical dosimetrists |
| 29-2042 | Emergency medical technicians |
| 29-2043 | Paramedics |
| 29-2051 | Dietetic technicians |
| 29-2052 | Pharmacy technicians |
| 29-2053 | Psychiatric technicians |
| 29-2055 | Surgical technologists |
| 29-2056 | Veterinary technologists and technicians |
| 29-2057 | Ophthalmic medical technicians |
| 29-2061 | Licensed practical and licensed vocational nurses |
| 29-2072 | Medical records specialists |
| 29-2081 | Opticians, dispensing |
| 29-2091 | Orthotists and prosthetists |
| 29-2092 | Hearing aid specialists |
| 29-2099 | Health technologists and technicians, all other |
| 29-9021 | Health information technologists and medical registrars |
| 29-9091 | Athletic trainers |
| 29-9092 | Genetic counselors |
| 29-9093 | Surgical assistants |
| 29-9099 | Healthcare practitioners and technical workers, all other |
| 31-1120 | Home health and personal care aides |
| 31-1131 | Nursing assistants |
| 31-1132 | Orderlies |
| 31-1133 | Psychiatric aides |
| 31-2011 | Occupational therapy assistants |
| 31-2012 | Occupational therapy aides |
| 31-2021 | Physical therapist assistants |
| 31-2022 | Physical therapist aides |
| 31-9011 | Massage therapists |
| 31-9091 | Dental assistants |
| 31-9092 | Medical assistants |
| 31-9093 | Medical equipment preparers |
| 31-9094 | Medical transcriptionists |
| 31-9095 | Pharmacy aides |
| 31-9096 | Veterinary assistants and laboratory animal caretakers |
| 31-9097 | Phlebotomists |
| 31-9099 | Healthcare support workers, all other |
| 33-1011 | First-line supervisors of correctional officers |
| 33-1012 | First-line supervisors of police and detectives |
| 33-1021 | First-line supervisors of firefighting and prevention workers |
| 33-1091 | First-line supervisors of security workers |
| 33-1099 | First-line supervisors of protective service workers, all other |
| 33-2011 | Firefighters |
| 33-2021 | Fire inspectors and investigators |
| 33-2022 | Forest fire inspectors and prevention specialists |
| 33-3011 | Bailiffs |
| 33-3012 | Correctional officers and jailers |
| 33-3021 | Detectives and criminal investigators |
| 33-3031 | Fish and game wardens |
| 33-3041 | Parking enforcement workers |
| 33-3051 | Police and sheriff's patrol officers |
| 33-3052 | Transit and railroad police |
| 33-9011 | Animal control workers |
| 33-9021 | Private detectives and investigators |
| 33-9031 | Gambling surveillance officers and gambling investigators |
| 33-9032 | Security guards |
| 33-9091 | Crossing guards and flaggers |
| 33-9092 | Lifeguards, ski patrol, and other recreational protective service workers |
| 33-9093 | Transportation security screeners |
| 33-9094 | School bus monitors |
| 33-9099 | Protective service workers, all other |
| 35-1011 | Chefs and head cooks |
| 35-1012 | First-line supervisors of food preparation and serving workers |
| 35-2011 | Cooks, fast food |
| 35-2012 | Cooks, institution and cafeteria |
| 35-2013 | Cooks, private household |
| 35-2014 | Cooks, restaurant |
| 35-2015 | Cooks, short order |
| 35-2019 | Cooks, all other |
| 35-2021 | Food preparation workers |
| 35-3011 | Bartenders |
| 35-3023 | Fast food and counter workers |
| 35-3031 | Waiters and waitresses |
| 35-3041 | Food servers, nonrestaurant |
| 35-9011 | Dining room and cafeteria attendants and bartender helpers |
| 35-9021 | Dishwashers |
| 35-9031 | Hosts and hostesses, restaurant, lounge, and coffee shop |
| 35-9099 | Food preparation and serving related workers, all other |
| 37-1011 | First-line supervisors of housekeeping and janitorial workers |
| 37-1012 | First-line supervisors of landscaping, lawn service, and groundskeeping workers |
| 37-2011 | Janitors and cleaners, except maids and housekeeping cleaners |
| 37-2012 | Maids and housekeeping cleaners |
| 37-2019 | Building cleaning workers, all other |
| 37-2021 | Pest control workers |
| 37-3011 | Landscaping and groundskeeping workers |
| 37-3012 | Pesticide handlers, sprayers, and applicators, vegetation |
| 37-3013 | Tree trimmers and pruners |
| 37-3019 | Grounds maintenance workers, all other |
| 39-1013 | First-line supervisors of gambling services workers |
| 39-1014 | First-line supervisors of entertainment and recreation workers, except gambling services |
| 39-1022 | First-line supervisors of personal service workers |
| 39-2011 | Animal trainers |
| 39-2021 | Animal caretakers |
| 39-3011 | Gambling dealers |
| 39-3012 | Gambling and sports book writers and runners |
| 39-3019 | Gambling service workers, all other |
| 39-3021 | Motion picture projectionists |
| 39-3031 | Ushers, lobby attendants, and ticket takers |
| 39-3091 | Amusement and recreation attendants |
| 39-3092 | Costume attendants |
| 39-3093 | Locker room, coatroom, and dressing room attendants |
| 39-3099 | Entertainment attendants and related workers, all other |
| 39-4011 | Embalmers |
| 39-4012 | Crematory operators |
| 39-4021 | Funeral attendants |
| 39-4031 | Morticians, undertakers, and funeral arrangers |
| 39-5011 | Barbers |
| 39-5012 | Hairdressers, hairstylists, and cosmetologists |
| 39-5091 | Makeup artists, theatrical and performance |
| 39-5092 | Manicurists and pedicurists |
| 39-5093 | Shampooers |
| 39-5094 | Skincare specialists |
| 39-6011 | Baggage porters and bellhops |
| 39-6012 | Concierges |
| 39-7010 | Tour and travel guides |
| 39-9011 | Childcare workers |
| 39-9031 | Exercise trainers and group fitness instructors |
| 39-9032 | Recreation workers |
| 39-9041 | Residential advisors |
| 39-9099 | Personal care and service workers, all other |
| 41-1011 | First-line supervisors of retail sales workers |
| 41-1012 | First-line supervisors of non-retail sales workers |
| 41-2011 | Cashiers |
| 41-2012 | Gambling change persons and booth cashiers |
| 41-2021 | Counter and rental clerks |
| 41-2022 | Parts salespersons |
| 41-2031 | Retail salespersons |
| 41-3011 | Advertising sales agents |
| 41-3021 | Insurance sales agents |
| 41-3031 | Securities, commodities, and financial services sales agents |
| 41-3041 | Travel agents |
| 41-3091 | Sales representatives of services, except advertising, insurance, financial services, and travel |
| 41-4011 | Sales representatives, wholesale and manufacturing, technical and scientific products |
| 41-4012 | Sales representatives, wholesale and manufacturing, except technical and scientific products |
| 41-9011 | Demonstrators and product promoters |
| 41-9012 | Models |
| 41-9021 | Real estate brokers |
| 41-9022 | Real estate sales agents |
| 41-9031 | Sales engineers |
| 41-9041 | Telemarketers |
| 41-9091 | Door-to-door sales workers, news and street vendors, and related workers |
| 41-9099 | Sales and related workers, all other |
| 43-1011 | First-line supervisors of office and administrative support workers |
| 43-2011 | Switchboard operators, including answering service |
| 43-2021 | Telephone operators |
| 43-2099 | Communications equipment operators, all other |
| 43-3011 | Bill and account collectors |
| 43-3021 | Billing and posting clerks |
| 43-3031 | Bookkeeping, accounting, and auditing clerks |
| 43-3041 | Gambling cage workers |
| 43-3051 | Payroll and timekeeping clerks |
| 43-3061 | Procurement clerks |
| 43-3071 | Tellers |
| 43-3099 | Financial clerks, all other |
| 43-4011 | Brokerage clerks |
| 43-4021 | Correspondence clerks |
| 43-4031 | Court, municipal, and license clerks |
| 43-4041 | Credit authorizers, checkers, and clerks |
| 43-4051 | Customer service representatives |
| 43-4061 | Eligibility interviewers, government programs |
| 43-4071 | File clerks |
| 43-4081 | Hotel, motel, and resort desk clerks |
| 43-4111 | Interviewers, except eligibility and loan |
| 43-4121 | Library assistants, clerical |
| 43-4131 | Loan interviewers and clerks |
| 43-4141 | New accounts clerks |
| 43-4151 | Order clerks |
| 43-4161 | Human resources assistants, except payroll and timekeeping |
| 43-4171 | Receptionists and information clerks |
| 43-4181 | Reservation and transportation ticket agents and travel clerks |
| 43-4199 | Information and record clerks, all other |
| 43-5011 | Cargo and freight agents |
| 43-5021 | Couriers and messengers |
| 43-5031 | Public safety telecommunicators |
| 43-5032 | Dispatchers, except police, fire, and ambulance |
| 43-5041 | Meter readers, utilities |
| 43-5051 | Postal service clerks |
| 43-5052 | Postal service mail carriers |
| 43-5053 | Postal service mail sorters, processors, and processing machine operators |
| 43-5061 | Production, planning, and expediting clerks |
| 43-5071 | Shipping, receiving, and inventory clerks |
| 43-5111 | Weighers, measurers, checkers, and samplers, recordkeeping |
| 43-6011 | Executive secretaries and executive administrative assistants |
| 43-6012 | Legal secretaries and administrative assistants |
| 43-6013 | Medical secretaries and administrative assistants |
| 43-6014 | Secretaries and administrative assistants, except legal, medical, and executive |
| 43-9021 | Data entry keyers |
| 43-9022 | Word processors and typists |
| 43-9031 | Desktop publishers |
| 43-9041 | Insurance claims and policy processing clerks |
| 43-9051 | Mail clerks and mail machine operators, except postal service |
| 43-9061 | Office clerks, general |
| 43-9071 | Office machine operators, except computer |
| 43-9081 | Proofreaders and copy markers |
| 43-9111 | Statistical assistants |
| 43-9199 | Office and administrative support workers, all other |
| 45-1011 | First-line supervisors of farming, fishing, and forestry workers |
| 45-2011 | Agricultural inspectors |
| 45-2021 | Animal breeders |
| 45-2041 | Graders and sorters, agricultural products |
| 45-2091 | Agricultural equipment operators |
| 45-2092 | Farmworkers and laborers, crop, nursery, and greenhouse |
| 45-2093 | Farmworkers, farm, ranch, and aquacultural animals |
| 45-2099 | Agricultural workers, all other |
| 45-3031 | Fishing and hunting workers |
| 45-4011 | Forest and conservation workers |
| 45-4021 | Fallers |
| 45-4022 | Logging equipment operators |
| 45-4023 | Log graders and scalers |
| 45-4029 | Logging workers, all other |
| 47-1011 | First-line supervisors of construction trades and extraction workers |
| 47-2011 | Boilermakers |
| 47-2021 | Brickmasons and blockmasons |
| 47-2022 | Stonemasons |
| 47-2031 | Carpenters |
| 47-2041 | Carpet installers |
| 47-2042 | Floor layers, except carpet, wood, and hard tiles |
| 47-2043 | Floor sanders and finishers |
| 47-2044 | Tile and stone setters |
| 47-2051 | Cement masons and concrete finishers |
| 47-2053 | Terrazzo workers and finishers |
| 47-2061 | Construction laborers |
| 47-2071 | Paving, surfacing, and tamping equipment operators |
| 47-2072 | Pile driver operators |
| 47-2073 | Operating engineers and other construction equipment operators |
| 47-2081 | Drywall and ceiling tile installers |
| 47-2082 | Tapers |
| 47-2111 | Electricians |
| 47-2121 | Glaziers |
| 47-2131 | Insulation workers, floor, ceiling, and wall |
| 47-2132 | Insulation workers, mechanical |
| 47-2141 | Painters, construction and maintenance |
| 47-2142 | Paperhangers |
| 47-2151 | Pipelayers |
| 47-2152 | Plumbers, pipefitters, and steamfitters |
| 47-2161 | Plasterers and stucco masons |
| 47-2171 | Reinforcing iron and rebar workers |
| 47-2181 | Roofers |
| 47-2211 | Sheet metal workers |
| 47-2221 | Structural iron and steel workers |
| 47-2231 | Solar photovoltaic installers |
| 47-3011 | Helpers--brickmasons, blockmasons, stonemasons, and tile and marble setters |
| 47-3012 | Helpers--carpenters |
| 47-3013 | Helpers--electricians |
| 47-3014 | Helpers--painters, paperhangers, plasterers, and stucco masons |
| 47-3015 | Helpers--pipelayers, plumbers, pipefitters, and steamfitters |
| 47-3016 | Helpers--roofers |
| 47-3019 | Helpers, construction trades, all other |
| 47-4011 | Construction and building inspectors |
| 47-4021 | Elevator and escalator installers and repairers |
| 47-4031 | Fence erectors |
| 47-4041 | Hazardous materials removal workers |
| 47-4051 | Highway maintenance workers |
| 47-4061 | Rail-track laying and maintenance equipment operators |
| 47-4071 | Septic tank servicers and sewer pipe cleaners |
| 47-4090 | Miscellaneous construction and related workers |
| 47-5011 | Derrick operators, oil and gas |
| 47-5012 | Rotary drill operators, oil and gas |
| 47-5013 | Service unit operators, oil and gas |
| 47-5022 | Excavating and loading machine and dragline operators, surface mining |
| 47-5023 | Earth drillers, except oil and gas |
| 47-5032 | Explosives workers, ordnance handling experts, and blasters |
| 47-5041 | Continuous mining machine operators |
| 47-5043 | Roof bolters, mining |
| 47-5044 | Loading and moving machine operators, underground mining |
| 47-5049 | Underground mining machine operators, all other |
| 47-5051 | Rock splitters, quarry |
| 47-5071 | Roustabouts, oil and gas |
| 47-5081 | Helpers--extraction workers |
| 47-5099 | Extraction workers, all other |
| 49-1011 | First-line supervisors of mechanics, installers, and repairers |
| 49-2011 | Computer, automated teller, and office machine repairers |
| 49-2021 | Radio, cellular, and tower equipment installers and repairers |
| 49-2022 | Telecommunications equipment installers and repairers, except line installers |
| 49-2091 | Avionics technicians |
| 49-2092 | Electric motor, power tool, and related repairers |
| 49-2093 | Electrical and electronics installers and repairers, transportation equipment |
| 49-2094 | Electrical and electronics repairers, commercial and industrial equipment |
| 49-2095 | Electrical and electronics repairers, powerhouse, substation, and relay |
| 49-2096 | Electronic equipment installers and repairers, motor vehicles |
| 49-2097 | Audiovisual equipment installers and repairers |
| 49-2098 | Security and fire alarm systems installers |
| 49-3011 | Aircraft mechanics and service technicians |
| 49-3021 | Automotive body and related repairers |
| 49-3022 | Automotive glass installers and repairers |
| 49-3023 | Automotive service technicians and mechanics |
| 49-3031 | Bus and truck mechanics and diesel engine specialists |
| 49-3041 | Farm equipment mechanics and service technicians |
| 49-3042 | Mobile heavy equipment mechanics, except engines |
| 49-3043 | Rail car repairers |
| 49-3051 | Motorboat mechanics and service technicians |
| 49-3052 | Motorcycle mechanics |
| 49-3053 | Outdoor power equipment and other small engine mechanics |
| 49-3091 | Bicycle repairers |
| 49-3092 | Recreational vehicle service technicians |
| 49-3093 | Tire repairers and changers |
| 49-9011 | Mechanical door repairers |
| 49-9012 | Control and valve installers and repairers, except mechanical door |
| 49-9021 | Heating, air conditioning, and refrigeration mechanics and installers |
| 49-9031 | Home appliance repairers |
| 49-9041 | Industrial machinery mechanics |
| 49-9043 | Maintenance workers, machinery |
| 49-9044 | Millwrights |
| 49-9045 | Refractory materials repairers, except brickmasons |
| 49-9051 | Electrical power-line installers and repairers |
| 49-9052 | Telecommunications line installers and repairers |
| 49-9061 | Camera and photographic equipment repairers |
| 49-9062 | Medical equipment repairers |
| 49-9063 | Musical instrument repairers and tuners |
| 49-9064 | Watch and clock repairers |
| 49-9069 | Precision instrument and equipment repairers, all other |
| 49-9071 | Maintenance and repair workers, general |
| 49-9081 | Wind turbine service technicians |
| 49-9091 | Coin, vending, and amusement machine servicers and repairers |
| 49-9092 | Commercial divers |
| 49-9094 | Locksmiths and safe repairers |
| 49-9095 | Manufactured building and mobile home installers |
| 49-9096 | Riggers |
| 49-9097 | Signal and track switch repairers |
| 49-9098 | Helpers--installation, maintenance, and repair workers |
| 49-9099 | Installation, maintenance, and repair workers, all other |
| 51-1011 | First-line supervisors of production and operating workers |
| 51-2011 | Aircraft structure, surfaces, rigging, and systems assemblers |
| 51-2021 | Coil winders, tapers, and finishers |
| 51-2028 | Electrical, electronic, and electromechanical assemblers, except coil winders, tapers, and finishers |
| 51-2031 | Engine and other machine assemblers |
| 51-2041 | Structural metal fabricators and fitters |
| 51-2051 | Fiberglass laminators and fabricators |
| 51-2061 | Timing device assemblers and adjusters |
| 51-2090 | Miscellaneous assemblers and fabricators |
| 51-3011 | Bakers |
| 51-3021 | Butchers and meat cutters |
| 51-3022 | Meat, poultry, and fish cutters and trimmers |
| 51-3023 | Slaughterers and meat packers |
| 51-3091 | Food and tobacco roasting, baking, and drying machine operators and tenders |
| 51-3092 | Food batchmakers |
| 51-3093 | Food cooking machine operators and tenders |
| 51-3099 | Food processing workers, all other |
| 51-4021 | Extruding and drawing machine setters, operators, and tenders, metal and plastic |
| 51-4022 | Forging machine setters, operators, and tenders, metal and plastic |
| 51-4023 | Rolling machine setters, operators, and tenders, metal and plastic |
| 51-4031 | Cutting, punching, and press machine setters, operators, and tenders, metal and plastic |
| 51-4032 | Drilling and boring machine tool setters, operators, and tenders, metal and plastic |
| 51-4033 | Grinding, lapping, polishing, and buffing machine tool setters, operators, and tenders, metal and plastic |
| 51-4034 | Lathe and turning machine tool setters, operators, and tenders, metal and plastic |
| 51-4035 | Milling and planing machine setters, operators, and tenders, metal and plastic |
| 51-4041 | Machinists |
| 51-4051 | Metal-refining furnace operators and tenders |
| 51-4052 | Pourers and casters, metal |
| 51-4061 | Model makers, metal and plastic |
| 51-4062 | Patternmakers, metal and plastic |
| 51-4071 | Foundry mold and coremakers |
| 51-4072 | Molding, coremaking, and casting machine setters, operators, and tenders, metal and plastic |
| 51-4081 | Multiple machine tool setters, operators, and tenders, metal and plastic |
| 51-4111 | Tool and die makers |
| 51-4121 | Welders, cutters, solderers, and brazers |
| 51-4122 | Welding, soldering, and brazing machine setters, operators, and tenders |
| 51-4191 | Heat treating equipment setters, operators, and tenders, metal and plastic |
| 51-4192 | Layout workers, metal and plastic |
| 51-4193 | Plating machine setters, operators, and tenders, metal and plastic |
| 51-4194 | Tool grinders, filers, and sharpeners |
| 51-4199 | Metal workers and plastic workers, all other |
| 51-5111 | Prepress technicians and workers |
| 51-5112 | Printing press operators |
| 51-5113 | Print binding and finishing workers |
| 51-6011 | Laundry and dry-cleaning workers |
| 51-6021 | Pressers, textile, garment, and related materials |
| 51-6031 | Sewing machine operators |
| 51-6041 | Shoe and leather workers and repairers |
| 51-6042 | Shoe machine operators and tenders |
| 51-6051 | Sewers, hand |
| 51-6052 | Tailors, dressmakers, and custom sewers |
| 51-6061 | Textile bleaching and dyeing machine operators and tenders |
| 51-6062 | Textile cutting machine setters, operators, and tenders |
| 51-6063 | Textile knitting and weaving machine setters, operators, and tenders |
| 51-6064 | Textile winding, twisting, and drawing out machine setters, operators, and tenders |
| 51-6091 | Extruding and forming machine setters, operators, and tenders, synthetic and glass fibers |
| 51-6092 | Fabric and apparel patternmakers |
| 51-6093 | Upholsterers |
| 51-6099 | Textile, apparel, and furnishings workers, all other |
| 51-7011 | Cabinetmakers and bench carpenters |
| 51-7021 | Furniture finishers |
| 51-7031 | Model makers, wood |
| 51-7032 | Patternmakers, wood |
| 51-7041 | Sawing machine setters, operators, and tenders, wood |
| 51-7042 | Woodworking machine setters, operators, and tenders, except sawing |
| 51-7099 | Woodworkers, all other |
| 51-8011 | Nuclear power reactor operators |
| 51-8012 | Power distributors and dispatchers |
| 51-8013 | Power plant operators |
| 51-8021 | Stationary engineers and boiler operators |
| 51-8031 | Water and wastewater treatment plant and system operators |
| 51-8091 | Chemical plant and system operators |
| 51-8092 | Gas plant operators |
| 51-8093 | Petroleum pump system operators, refinery operators, and gaugers |
| 51-8099 | Plant and system operators, all other |
| 51-9011 | Chemical equipment operators and tenders |
| 51-9012 | Separating, filtering, clarifying, precipitating, and still machine setters, operators, and tenders |
| 51-9021 | Crushing, grinding, and polishing machine setters, operators, and tenders |
| 51-9022 | Grinding and polishing workers, hand |
| 51-9023 | Mixing and blending machine setters, operators, and tenders |
| 51-9031 | Cutters and trimmers, hand |
| 51-9032 | Cutting and slicing machine setters, operators, and tenders |
| 51-9041 | Extruding, forming, pressing, and compacting machine setters, operators, and tenders |
| 51-9051 | Furnace, kiln, oven, drier, and kettle operators and tenders |
| 51-9061 | Inspectors, testers, sorters, samplers, and weighers |
| 51-9071 | Jewelers and precious stone and metal workers |
| 51-9081 | Dental laboratory technicians |
| 51-9082 | Medical appliance technicians |
| 51-9083 | Ophthalmic laboratory technicians |
| 51-9111 | Packaging and filling machine operators and tenders |
| 51-9123 | Painting, coating, and decorating workers |
| 51-9124 | Coating, painting, and spraying machine setters, operators, and tenders |
| 51-9141 | Semiconductor processing technicians |
| 51-9151 | Photographic process workers and processing machine operators |
| 51-9161 | Computer numerically controlled tool operators |
| 51-9162 | Computer numerically controlled tool programmers |
| 51-9191 | Adhesive bonding machine operators and tenders |
| 51-9192 | Cleaning, washing, and metal pickling equipment operators and tenders |
| 51-9193 | Cooling and freezing equipment operators and tenders |
| 51-9194 | Etchers and engravers |
| 51-9195 | Molders, shapers, and casters, except metal and plastic |
| 51-9196 | Paper goods machine setters, operators, and tenders |
| 51-9197 | Tire builders |
| 51-9198 | Helpers--production workers |
| 51-9199 | Production workers, all other |
| 53-1041 | Aircraft cargo handling supervisors |
| 53-1047 | First-line supervisors of transportation and material moving workers, except aircraft cargo handling supervisors |
| 53-2011 | Airline pilots, copilots, and flight engineers |
| 53-2012 | Commercial pilots |
| 53-2021 | Air traffic controllers |
| 53-2022 | Airfield operations specialists |
| 53-2031 | Flight attendants |
| 53-3011 | Ambulance drivers and attendants, except emergency medical technicians |
| 53-3031 | Driver/sales workers |
| 53-3032 | Heavy and tractor-trailer truck drivers |
| 53-3033 | Light truck drivers |
| 53-3051 | Bus drivers, school |
| 53-3052 | Bus drivers, transit and intercity |
| 53-3053 | Shuttle drivers and chauffeurs |
| 53-3054 | Taxi drivers |
| 53-3099 | Motor vehicle operators, all other |
| 53-4011 | Locomotive engineers |
| 53-4013 | Rail yard engineers, dinkey operators, and hostlers |
| 53-4022 | Railroad brake, signal, and switch operators and locomotive firers |
| 53-4031 | Railroad conductors and yardmasters |
| 53-4041 | Subway and streetcar operators |
| 53-4099 | Rail transportation workers, all other |
| 53-5011 | Sailors and marine oilers |
| 53-5021 | Captains, mates, and pilots of water vessels |
| 53-5022 | Motorboat operators |
| 53-5031 | Ship engineers |
| 53-6011 | Bridge and lock tenders |
| 53-6021 | Parking attendants |
| 53-6031 | Automotive and watercraft service attendants |
| 53-6032 | Aircraft service attendants |
| 53-6041 | Traffic technicians |
| 53-6051 | Transportation inspectors |
| 53-6061 | Passenger attendants |
| 53-6099 | Transportation workers, all other |
| 53-7011 | Conveyor operators and tenders |
| 53-7021 | Crane and tower operators |
| 53-7031 | Dredge operators |
| 53-7041 | Hoist and winch operators |
| 53-7051 | Industrial truck and tractor operators |
| 53-7061 | Cleaners of vehicles and equipment |
| 53-7062 | Laborers and freight, stock, and material movers, hand |
| 53-7063 | Machine feeders and offbearers |
| 53-7064 | Packers and packagers, hand |
| 53-7065 | Stockers and order fillers |
| 53-7071 | Gas compressor and gas pumping station operators |
| 53-7072 | Pump operators, except wellhead pumpers |
| 53-7073 | Wellhead pumpers |
| 53-7081 | Refuse and recyclable material collectors |
| 53-7121 | Tank car, truck, and ship loaders |
| 53-7199 | Material moving workers, all other |
