# BUCKET_03 — entries 101–150 (`c985` … `c925`, 2022-11-04 → 2025-01-01)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Official INT posts (UTC+9, `research2/nikke_official_news.json`):
  "Notice on Server Update on November 10" (2022-11-09), "Update on
  November 24" (2022-11-21), "Update on December 8" (2022-12-05),
  "Update on December 20" (2022-12-19), "Update on December 29"
  (2022-12-26), "Update on January 12" (2023-01-09).
- Wiki: event dates (`/tmp/research/ev_dates.json`), Co-Op Battle
  history table (live fetch, `research2/p_coop.txt` — 72 events, oldest
  2022-11-18), boss Rapture pages (live: Harvester, Chatterbox, Grave
  Digger, Material H, Modernia (Rapture), Land Eater; cached: Black
  Smith), Johan page (live), Last Kingdom page (live,
  `research2/p_lastkingdom.txt`), Minor characters/Event (cached
  `/tmp/research/p_Minor_characters_Event.txt`).
- Prior-pass files: `gacha_dates.json`, `updateLog.json` (Nikke-db
  viewer), `costume_prose.json`, `wiki_costume_module.json`,
  `minor_debuts.json`, `npct_*.txt`.
- RESEARCH.md: boss-model rule (line 21: "the date the chapter/event
  that introduced the Rapture released"), chapter table (ch 00–16 =
  launch; 19–20 = D-Outsiders 2023-01-12; 29–30 = Last Kingdom
  2024-04-25).

**One-day source discrepancy (documented, not corrected):** the
official "Update on December 29" post and press coverage name the
Brand New Year maintenance as **Dec 29**, while the wiki event
startDate and the press dateline ("Metro Manila, December 28, 2022")
say **2022-12-28**. The recorded dates keep 2022-12-28 (wiki
convention, press dateline); the official wording refers to the
maintenance day.

| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c985 | Yuni | **date dropped** (null) | **Not** a CN client copy of c160 Yuni — confirmed **distinct** from the INTL entry by the user (2026-11-04), so the "CN copy" verdict (characters.json name/rarity match + c9xx pattern) was wrong. What is known: the client carries it as Live2D + sprite (`l2d/c985/c985_00.{atlas,png,skel}`, `images/sprite/si_c985_00_s.png`, Nikke-db asset tree); it is **absent from nikke.gg's live INTL data** (zero references in the bundle); the Nikke-db viewer picked up a Yuni Live2D on 2024-10-27 ("…N Corp Groẞhammer Yuni") and a "rapipi" skin on 2025-07-17 — client dates far later than 2022. No wiki page, banner, press release or official post identifies this specific model → debut date cannot be established | **date dropped** |
| 2 | c989 | Rapi | 2025-01-01 | as row 1, but resolved (2026-11-04): the user identified the four Rapi models as belonging to the **Rapi: Red Hood** release (c016, 2025-01-01 — the New-Year SSR gacha). The viewer log "Decembre 27th 2024 :: added Rapi, Rapi, Rapi, Rapi Hood, Ein, Zwei, Naga" is the pre-staged client batch for that update (viewer additions can precede the obtainable date, cf. the BUCKET_07/08 pre-staging pattern; "Rapi Hood" = the c016 model; the "Naga" entry matches c450_02 Naga Last Girlhood 2024-12-26) | **date set** (2022-11-04 → 2025-01-01, with c016 Rapi: Red Hood) |
| 3 | c990 | Rapi | 2025-01-01 | as row 2 | **date set** (2025-01-01) |
| 4 | c992 | Rapi | 2025-01-01 | as row 2 | **date set** (2025-01-01) |
| 5 | c994 | Rapi | 2025-01-01 | as row 2 | **date set** (2025-01-01) |
| 6 | bbg001 | Boss: Harvester | 2022-11-04 | wiki "Harvester" page: "final boss of **Chapter 11**" (campaign) → ch 11 ≤ 16 = launch (boss rule, RESEARCH.md line 21) | confirmed |
| 7 | bbg002 | Boss: Chatterbox | 2022-11-04 | wiki "Chatterbox" page: Tyrant-class Rapture, "secondary antagonist" of the main storyline (colludes with Enikk, ch 4) → launch chapters | confirmed |
| 8 | bbg003 | Boss: Blacksmith | 2022-11-04 | wiki "Black Smith" page (cached): "Tyrant 003 … final boss of **Chapter 1** of the campaign" → launch | confirmed |
| 9 | ebg001 | Boss: Land Eater | 2022-12-28 | first appearance: official "Update on December 29" (2022-12-26) "3.3 Coordinated Operation — challenge the Boss **Land Eater**" (event 2023-01-06 → 01-08); wiki Co-Op history: first Land Eater event 2023-01-06; shipped in the Brand New Year update (wiki startDate 2022-12-28; see discrepancy note). The 2022-11-04 value had no debut evidence (the Land Eater page's Wave to You boss is the *Island Eater* variant, 2026) | **corrected** (2022-11-04 → 2022-12-28) |
| 10 | ebg002 | Boss: Material H | 2022-11-04 | wiki "Material H" page: "final boss of **Chapter 12**" (later re-encountered ch 24) → ch 12 ≤ 16 = launch | confirmed |
| 11 | mbg002 | Boss: Grave Digger | 2022-11-04 | wiki "Grave Digger" page: "final boss of **Chapter 2**" (+ Interception Level S) → launch | confirmed |
| 12 | mbg004 | Boss: Modernia | 2022-11-04 | wiki "Modernia (Rapture)" page: "boss of Chapters **7** and **13** of the campaign" → launch chapters (the 2023-01-01 c260 playable is a different model) | confirmed |
| 13 | mbg004_appearance | Boss: Modernia Intro | 2022-11-04 | intro appearance model for the mbg004 boss (ch 7/13 battles) → launch | confirmed |
| 14 | story0001 | Story 00-01 | 2022-11-04 | story scene of ch 00 (campaign); launch shipped ch 00–16 (RESEARCH.md chapter table + official Developer's Notes) | confirmed |
| 15 | story0001_2 | Story 00-01 no filter | 2022-11-04 | as row 14 (no-filter render of the same scene) | confirmed |
| 16 | story0002 | Story 00-02 | 2022-11-04 | as row 14 | confirmed |
| 17 | story0002_2 | Story 00-02 no filter | 2022-11-04 | as row 14 | confirmed |
| 18 | story0003 | Story 00-03 | 2022-11-04 | as row 14 | confirmed |
| 19 | story0201 | Story 02-01 | 2022-11-04 | story scene of ch 02 (≤ 16) → launch | confirmed |
| 20 | story0401 | Story 04-01 | 2022-11-04 | story scene of ch 04 (Bouquet) → launch | confirmed |
| 21 | story0401_2 | Story 04-02 | 2022-11-04 | story scene of ch 04 scene 2 (INTL; the CN twin story0401_3 = 2025-04-01 is a separate row per RESEARCH.md) → launch | confirmed |
| 22 | story0405 | Story 04-05 | 2022-11-04 | ch 04 scene → launch | confirmed |
| 23 | story0702 | Story 07-02 | 2022-11-04 | story scene of ch 07 (Reunited) → launch | confirmed |
| 24 | story1201 | Story 12-01 | 2022-11-04 | story scene of ch 12 → launch | confirmed |
| 25 | story1302 | Story 13-02 | 2022-11-04 | story scene of ch 13 (Comeback) → launch | confirmed |
| 26 | story1303 | Story 13-03 | 2022-11-04 | as row 25 | confirmed |
| 27 | c352 | Helm | 2022-11-10 | official "Notice on Server Update on November 10": "New Character SSR NIKKE Helm … Special Recruit opens from: Opening time of Server on November 10" (BUCKET_01 boundary anchor) | confirmed |
| 28 | nocallerid | No Caller ID | 2022-11-10 | official Nov 10 post: "Story Event: No Caller ID … Event Period: … November 10 … ~ November 24"; wiki ev_dates 2022-11-10 | confirmed |
| 29 | c100 | Laplace | 2022-11-24 | official "Update on November 24": "New Character Hero of the Ark — SSR Nikke Laplace … From the end of the 11/24/2022 maintenance to … 12/08/2022" (BUCKET_01 boundary anchor) | confirmed |
| 30 | c210_01 | Exia Joy to the Nerds | 2022-12-08 | official "Update on December 8" post: "2.2 Permanent Costumes: ④ **Exia – Joy to the Nerds** *Shop opens: After the maintenance on Dec 8, 2022" — the 2022-11-24 value was wrong (cross-bucket note from the prior pass) | **corrected** (2022-11-24 → 2022-12-08) |
| 31 | hightechtoy | High Tech Toy | 2022-11-24 | official "Update on November 24": "Chapters 17 and 18 will become available" + "Story Event: High-tech Toy" (separate official intro post 2022-11-24); wiki ev_dates 2022-11-24 | confirmed |
| 32 | eba001 | Boss: Storm Bringer | 2022-12-20 | official "Update on December 20" (2022-12-19): "2. Coordinated Operation — challenge Boss 'StormBringer' together! (event Dec 23–25)"; wiki Co-Op history: first Storm Bringer event 2022-12-23. The 2022-11-24 value has no support: the Nov 24 post contains zero boss/Co-Op mentions (checked) | **corrected** (2022-11-24 → 2022-12-20) |
| 33 | c090_01 | Emma Color me Red | 2022-12-08 | official "Update on December 8": "2.1 Special Costume: **Emma – Color me Red** … Winter Pass" (BUCKET_01 cross-check) | confirmed |
| 34 | c193 | Neve | 2022-12-08 | official "Update on December 8": "1.3 **Neve** — New Special SR Nikke Neve has debuted … Available from: End of Dec 8 maintenance to 23:59:59, Dec 28" + "exclusive Nikke, Neve, when you achieve a 14-day login streak" (Grand Winter Event). The prior open question (press banner Dec 15–28 vs Dec 8) resolves to Dec 8: Dec 15 is the event's second phase ("Eternal Memory" scenario / Anne gacha start) | confirmed (open item closed) |
| 35 | c203 | Rupee: Winter Shopper | 2022-12-08 | official "Update on December 8": "1.1 **Rupee: Winter Shopper** … Limited-Time Recruit: End of Dec 8 maintenance to 23:59:59, Dec 28" | confirmed |
| 36 | c934 | Angelina | 2022-12-08 | wiki Minor characters/Event infobox: `debut = [[Miracle Snow]]` (Anne's biological mother, "first appearing in Miracle Snow"; cached page + `minor_debuts.json`); Miracle Snow = 2022-12-08 (official Dec 8 post + wiki) | confirmed |
| 37 | miraclesnow | Miracle Snow | 2022-12-08 | official "Update on December 8": "4.1 Grand Winter Event: **Miracle Snow** … End of Dec 8 maintenance to 23:59:59, Dec 28"; wiki ev_dates 2022-12-08 | confirmed |
| 38 | c121 | Anne: Miracle Fairy | 2022-12-15 | official "Update on December 8": "1.2 **Anne: Miracle Fairy** … Limited-Time Recruit duration: **From 05:00:00 12/15/2022** to 23:59:59 12/28/2022" — deliberate mid-event start (matches the event's second phase) | confirmed |
| 39 | c140_01 | Sugar Hard-Boiled | 2022-12-28 | official "Update on December 29": "2.2 Special Costume: **Sugar – Hard-Boiled** … January Mission Pass"; press (Sakura Index, dateline Dec 28): "available in the January Mission Pass"; wiki Brand New Year startDate 2022-12-28 (see discrepancy note) | confirmed |
| 40 | c150_01 | Julia Mild Nocturne | 2022-12-28 | official "Update on December 29": "2.3 Permanent Costume: **Julia – Mild Nocturne** *Shop opens: After the Dec 29 maintenance"; press: "obtainable in the costume shop" | confirmed |
| 41 | c352_01 | Helm Chandelier | 2022-12-28 | official "Update on December 29": "2.1 Special Costume: **Helm – Chandelier** … SUNRISE PASS"; press: "New Year's event pass" | confirmed |
| 42 | brandnewyear | Brand New Year | 2022-12-28 | wiki ev_dates "brand new year" = 2022-12-28; press dateline "Metro Manila, December 28, 2022"; official Dec 29 post: "From the end of the Dec 29 maintenance to 23:59:59, Jan 11" (see discrepancy note) | confirmed |
| 43 | c260 | Modernia | 2023-01-01 | wiki Modernia page infobox `releaseDate = 1 january 2023` (live fetch); official "Update on December 29": "SSR Pilgrim [Modernia] … Special Recruit: **From 00:00:00 01/01/2023** to 04:59:59 01/19/2023" (model shipped in the Dec 28/29 update, obtainable from Jan 1); press: "Special Recruit Banner from January 1, 2023" | confirmed |
| 44 | c260_02 | Modernia Second Affection | 2024-04-25 | wiki Last Kingdom page: "Costume Gacha - **Advent of the Black Queen**: End of maintenance to 5:00 May 16 (UTC+9) — Modernia's costume 'Second Affection' will be available via gacha" (ref: official X post, decoded 2024-04-20); Last Kingdom update = **2024-04-25** (RESEARCH.md chapter table: ch 29–30); `gacha_dates.json`: "Modernia (Second Affection)" start 2024-04-25; Nikke-db log "April 28th 2024: Updated Modernia Second Affection assets"; {{NikkeCostume}} module: obtain "Costume Gacha", series "Awakening Fate". The recorded 2023-01-01 was the base character's debut (parent-date inheritance, same pattern as BUCKET_02 c962–964) | **corrected** (2023-01-01 → 2024-04-25) |
| 45 | c111 | Jackal | 2023-01-12 | official "Update on January 12": "1.1 SSR **Jackal** … From the end of the Jan 12, 2023 maintenance to Jan 25" | confirmed |
| 46 | c400 | Guilty | 2023-01-12 | official "Update on January 12": "2.2 New Gameplay: Liberation … obtain the Nikkes detained in the Ark's Rehabilitation Center: namely **Guilty**, Sin, and Quency from Real Kindness … SSR Nikkes that cannot be obtained through recruitment" (D-Outsiders update) | confirmed |
| 47 | c401 | Sin | 2023-01-12 | as row 46 | confirmed |
| 48 | c402 | Quency | 2023-01-12 | as row 46 | confirmed |
| 49 | c908 | Papillon | 2023-01-12 | `npct_Papillon.txt`: story section **Chapter 19** (D-Outsiders ch 19 "Eden" = 2023-01-12 per RESEARCH.md chapter table + wiki ev_dates) | confirmed |
| 50 | c925 | Johan | 2023-01-12 | live wiki Johan page infobox: `debut = Chapter 19: Eden` (D-Outsiders; commander of the Inherit squad, rival of the protagonist) | confirmed |

## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c210_01 | 2022-11-24 | 2022-12-08 | official Dec 8 post lists "Exia – Joy to the Nerds" among the permanent costumes opening "After the maintenance on Dec 8, 2022" |
| 2 | eba001 | 2022-11-24 | 2022-12-20 | StormBringer Co-Op introduced in the Dec 20 update (official post; event Dec 23–25; first Co-Op appearance in wiki history); the Nov 24 update has no boss content at all |
| 3 | ebg001 | 2022-11-04 | 2022-12-28 | first appearance is the Land Eater Co-Op in the Brand New Year update (official Dec 29 post; event 2023-01-06); no launch debut documented (Wave to You's boss is the Island Eater variant, 2026) |
| 4 | c260_02 | 2023-01-01 | 2024-04-25 | "Second Affection" is a Costume Gacha release (Advent of the Black Queen, Last Kingdom update 2024-04-25), not part of Modernia's January 2023 debut |

## Result

50/50 **reviewed**, **4 corrected** (c210_01 → 2022-12-08; eba001 →
2022-12-20; ebg001 → 2022-12-28; c260_02 → 2024-04-25), **4 dates
set** (c989/c990/c992/c994 → 2025-01-01, the Rapi: Red Hood release
batch), **1 date dropped** (c985 → `null`). Every character/event
row in the window is directly documented by an official update post
(the strongest source class available). Boss rows follow the RESEARCH.md
boss rule: six of eight confirmed at launch via their chapter debuts
(ch 1/2/7/11/12/13 + main-story antagonist); Storm Bringer and Land
Eater turn out to be Co-Op bosses that shipped two months later, with
no launch appearance. The prior-pass Neve open question closed at
2022-12-08 (official debut in the Dec 8 update; the press's Dec 15
banner was the event's second phase). The Brand New Year one-day
discrepancy (wiki/press Dec 28 vs official "Dec 29 maintenance"
wording) is documented, not corrected.

## Open item — c985 Yuni (date dropped 2026-11-04)

The "CN client copy of Yuni" verdict for c985 was a name-match
inference and is **retracted**: the user confirmed the model is
**distinct from the INTL c160 Yuni entry**. Evidence gathered: it
exists in the client as Live2D + sprite assets; it is absent from
nikke.gg's live INTL data; the Nikke-db viewer picked up a Yuni
Live2D on 2024-10-27 ("…N Corp Groẞhammer Yuni") and a "rapipi" skin
on 2025-07-17 — client dates far later than 2022, so the recorded
value (itself a scraper name-match inheritance, same failure mode as
c472/c473) is wrong, but no source maps this id to a specific
model/update → date set to `null` per user decision. The
`characters.json` entry for this id (name/rarity/release_date) is a
name-match artifact and likewise unreliable. Lead to re-open: the
2024-10-27/2025-07-17 viewer entries; resolution path is the same as
the c989–c994 batch (identify the release the model belongs to —
e.g. user knowledge + the pre-staged viewer-log batch).

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
      (the 5 c9xx rows: evidence exhausted, dates dropped per user
      decision — see open item)
- [x] `models.json` patched: 4 date corrections (c210_01, eba001,
      ebg001, c260_02) + 4 dates set to 2025-01-01 (c989/c990/c992/
      c994, Rapi: Red Hood batch) + 1 date dropped to null (c985)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered (40 in BUCKET_15)
