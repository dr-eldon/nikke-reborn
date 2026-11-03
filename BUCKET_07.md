# BUCKET_07 — entries 301–350 (`c971` … `c281_01`, 2023-12-28 → 2025-06-01)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Wiki (live fetches this pass, `research2/b07_*.json` / `b07y_*.json`):
  character pages with `releaseDate` — Ade (15 february 2024), Bay
  (11 april 2024), Crown (25 april 2024), D (13 apr 2023, the base
  character), Kilo (25 april 2024), Moran (25 jan 2024), Emilia / Ram
  (21 march 2024), Rem (28 march 2024), Trony (16 may 2024); event
  pages with `startDate` — Lion Heart (January 11th, 2024 → January
  25th), Dirty Backyard (January 25th, 2024 → February 8th), Perfect
  Maid (February 5, 2024 → February 22), Booms Day (February 22, 2024
  → March 7), Kill the Lord (March 7th, 2024 → March 20th), Re:CIPE
  FOR YOU (March 21, 2024 → April 11; "Re:FRESH Pass … premium track
  rewards the costume Pure Blossom for Rem"; "Spring Breeze for Emilia
  and Handy Maid for Rem … under Challenge Missions simply by
  recruiting them"), Liar's End (April 1st, 2024 → April 4th — the
  3-day April Fools' event "dragging [[Syuen]] into the mix"), One
  More Time (April 11, 2024 → April 24), D.ark Hero (May 16, 2024 →
  May 30; Trony + Ark Ranger Black story), Golden Coin Rush (May 30th,
  2024 → June 20th; "Soda (now dressed like a [[Soda: Twinkling
  Bunny|bunny girl]]…)"); **Module:NikkeCostume/data**
  (`research2/b07y_datamod.json`) — the wiki's authoritative
  obtain-source table (series + obtain per costume; same source that
  settled c072_01 in BUCKET_03). Note the two soundtrack pages "BOOMS
  DAY" / "KILL THE LORD" are distinct from the event pages "Booms
  Day" / "Kill the Lord".
- MP-season file: `mp_costumes.json` (S15 Guillotine 2024-01-01 …
  S34 Julia 2025-08-01; S16 Sugar 2024-02-01, S17 Exia 2024-03-01,
  S18 Rosanna 2024-04-01, S19 Diesel 2024-05-01, S25 "D: Killer Wife"
  2024-11-01, S32 "Moran (Off-Duty Queen)" 2025-06-01). Season
  numbering cross-verified against the wiki module (module "Mission
  Pass Season 19" = file S19 = Diesel Midnight Strawberry).
- nikke.gg live client data: `research2/gg_costumes_db.json`
  (obtain-source flags).
- Prior-pass files: RESEARCH.md (favorite rule + Favorite-Item table —
  Golden Coin Rush 2024-05-30, initial favorites Laplace/Exia/Frima/
  Diesel; chapter table ch 27–28 = BOOM's Day 2024-02-22, ch 29–30 =
  Last Kingdom 2024-04-25; NPC sweep — c480/c490, c915, c9023,
  c481/c491; c570_99 Ark Ranger Black = 2024-05-16 older rig,
  documented variant<base exception; the c820_02/c830_03
  "collab-gacha-before-banner" exception), `research/ev_dates.json` +
  `research/event_dates_full.json` (event dates scraped from the wiki
  event pages — incl. liar's end 2024-04-01, pick-up pages "34
  Privaty: Unkind Maid" 2024-02-05, "37 D: Killer Wife" 2024-03-07,
  "43 Soda: Twinkling Bunny" 2024-05-30), `research2/updateLog.json`
  (Nikke-db viewer log), BUCKET_05's Last Kingdom / c220_01 findings.
  The official post archive ends 2023-12-25, so the whole bucket rests
  on the wiki + client data + viewer log.

## Table
| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c971 | Rose | 2023-12-28 | RESEARCH.md c9xx row: "c971 Rose — New Year, New Sword story (mass-produced squad; Nikke-db added 'Rose' with the NYNS assets 2023-12-29) — earlier note said 2023-12-08, wrong — **2023-12-28**" | confirmed (previous pass) |
| 2 | c974 | Mass Produced Melee | 2023-12-28 | RESEARCH.md c9xx row: "c974/c974_01 — New Year, New Sword (Nikke-db 2023-12-29 / 2024-01-06) — **2023-12-28**" | confirmed (previous pass) |
| 3 | c974_01 | Mass Produced Melee 2 | 2023-12-28 | as above | confirmed (previous pass) |
| 4 | newyearnewsword | New Year New Sword | 2023-12-28 | wiki "New Year, New Sword" event page (live): startDate December 28th, 2023; `ev_dates.json`: new year, new sword = 2023-12-28 | confirmed |
| 5 | c180_01 | Guillotine Dark Tracer | 2024-01-01 | module: Guillotine "Dark Tracer — **Mission Pass Season 15**"; `mp_costumes.json` S15 = Guillotine (Dark Tracer), start **2024-01-01**; `gg_costumes_db.json`: missionpass — the recorded 2023-12-28 was the NYNS update that announced the January MP | **corrected** (2023-12-28 → 2024-01-01) |
| 6 | c225 | Scarlet: Black Shadow | 2024-01-01 | the New Year 2024 SSR — module has "Scarlet: Black Shadow" as its own character entry; `ev_dates.json`: "pick up 31 scarlet black shadow = 2024-01-01" + "new year recruitment scarlet black shadow" (the 2024-01-01 "New Year with Scarlet" recruitment) | confirmed |
| 7 | c430_02 | Noise Classic Diva | 2024-01-01 | module: Noise "Classic Diva — Costume Gacha"; wiki "New Year, New Sword" page (live): "===Costume Gacha - Noise: Classic Diva=== **Duration: Midnight, January 1st to 5:00 January 18th** (UTC+9)" — the gacha opened at New Year's midnight (2024-01-01), not with the 2023-12-28 update; `gg_costumes_db.json`: gacha | **corrected** (2023-12-28 → 2024-01-01) |
| 8 | c382 | Leona | 2024-01-11 | wiki "Leona" page (live): `releaseDate = 11 january 2024` | confirmed |
| 9 | lionheart | Lion Heart | 2024-01-11 | wiki "Lion Heart" event page (live): startDate January 11th, 2024 → January 25th; viewer "January 14th 2024: Added Lion Heart event l2d" | confirmed |
| 10 | c281 | Moran | 2024-01-25 | wiki "Moran" page (live): `releaseDate = 25 jan 2024`; wiki "Dirty Backyard" event page: "The event centers around [[Moran]]…" (the character's debut event, Jan 25 update) | confirmed |
| 11 | dirtybackyard | Dirty Backyard | 2024-01-25 | wiki "Dirty Backyard" event page (live): startDate January 25th, 2024 → February 8th | confirmed |
| 12 | c140_02 | Sugar Wild Backyard | 2024-02-01 | **not** a Jan 25 item: wiki Module:NikkeCostume/data: Sugar "Wild Backyard — **Mission Pass Season 16**"; `mp_costumes.json` S16 = Sugar (Wild Backyard), start **2024-02-01**; the Jan 25 (Dirty Backyard) page documents exactly this: "===February Mission Pass Update=== … premium track will offer the costume Wild Backyard for Sugar"; `gg_costumes_db.json`: missionpass — the 2024-01-25 value was the announcing update (viewer "January 11th 2024: … Sugar Wild Backyard l2d" = staged early) | **corrected** (2024-01-25 → 2024-02-01) |
| 13 | c101_02 | Drake Maid For Villain | 2024-02-05 | wiki "Perfect Maid" event page (live): "===Villain Pass For U=== An event-exclusive Mission Pass separate from the standard version. Completing the premium track earns the costume 'Maid For Villain' for Drake"; module: Drake "Maid For Villain — Villain Pass For U Pass"; `gg_costumes_db.json`: eventpass | confirmed |
| 14 | c313 | Privaty: Unkind Maid | 2024-02-05 | the PERFECT MAID variant character — wiki "Perfect Maid" page story section "Maid Cafe's Temporary Maids: A … Privaty … over the [[Privaty: Unkind Maid\|maid outfit]]"; module has "Privaty: Unkind Maid" as its own character entry (rarity SSR); `ev_dates.json`: "pick up 34 privaty unkind maid = 2024-02-05" (her pick-up page); viewer "February 7th 2024: Added Privaty: Unkind Maid, Drake Maid For Villain" | confirmed |
| 15 | perfectmaid | Perfect Maid | 2024-02-05 | wiki "Perfect Maid" event page (live): startDate February 5, 2024 → February 22 | confirmed |
| 16 | c310 | Ade | 2024-02-15 | wiki "Ade" page (live): `releaseDate = 15 february 2024`; `ev_dates.json`: "ade = 2024-02-15" (her pick-up page) | confirmed |
| 17 | boomsday | BOOM's DAY | 2024-02-22 | wiki "Booms Day" event page (live): startDate February 22, 2024 → March 7; RESEARCH.md chapter table: ch 27–28 = BOOM's Day 2024-02-22 | confirmed |
| 18 | c480 | Liveryn | 2024-02-22 | RESEARCH.md NPC sweep: "c480, c490 Liveryn, Hammering — BOOM's Day **2024-02-22** (pages 2024-02-22; viewer 2024-03-01)" — the BOOM's Day story characters | confirmed |
| 19 | c490 | Hammering | 2024-02-22 | as the c480 row | confirmed |
| 20 | c500 | Elegg | 2024-02-22 | BOOM's Day character of the Feb 22 update — `ev_dates.json`: "elegg = 2024-02-22" (her pick-up page); viewer "February 24th 2024: Added Elegg, Trony, BOOM's DAY live2d" | confirmed |
| 21 | c9023 | Hanson | 2024-02-22 | RESEARCH.md: "c9023 Hanson = ch 28 commission **2024-02-22**" (BOOM's Day update; ch 27–28 shipped with it) | confirmed |
| 22 | c915 | Raptillion | 2024-02-22 | RESEARCH.md: "c915 Raptillion — BOOM's Day **2024-02-22** (viewer batch 2024-03-01)" (the event's Rapture boss model) | confirmed |
| 23 | c210_02 | Exia Gamer | 2024-03-01 | **not** a Feb 22 item: module: Exia "Gamer — **Mission Pass Season 17**"; `mp_costumes.json` S17 = Exia (Gamer), start **2024-03-01**; `gg_costumes_db.json`: missionpass — the 2024-02-22 value was the announcing update | **corrected** (2024-02-22 → 2024-03-01) |
| 24 | c043 | D: Killer Wife | 2024-03-07 | the KILL THE LORD variant character — wiki "Kill the Lord" event page (live): "To uncover the truth, [[D: Killer Wife\|D]] and Commander decide to join them"; `ev_dates.json`: "pick up 37 d killer wife = 2024-03-07" (her pick-up page); base D = 2023 (wiki "D" releaseDate 13 apr 2023) | confirmed |
| 25 | c043_02 | D: Killer Wife Secret Police | 2024-03-07 | module: "Secret Police — Costume Gacha" (series "Halloween Night") — the Costume Gacha of the Mar 7 (KILL THE LORD) update, which introduced D: Killer Wife; `gg_costumes_db.json`: gacha | confirmed |
| 26 | killthelord | Kill The Lord | 2024-03-07 | wiki "Kill the Lord" event page (live): startDate March 7th, 2024 → March 20th | confirmed |
| 27 | c820_02 | Rem Pure Blossom | 2024-03-21 | the Re:CIPE FOR YOU **event pass** premium — wiki "Re:CIPE FOR YOU" event page (live): "===Re:FRESH Pass=== An event-exclusive Mission Pass. Completing the premium track rewards the costume Pure Blossom for Rem"; module: Rem "Pure Blossom — Re:FRESH Pass". Dated at the event start (2024-03-21) though Rem's own banner opened 2024-03-28 — the documented "collab-gacha-before-banner" exception (RESEARCH.md) | confirmed |
| 28 | c821 | Emilia | 2024-03-21 | wiki "Emilia" page (live): `releaseDate = 21 march 2024` (Re:CIPE FOR YOU collab, gacha from the event start) | confirmed |
| 29 | c821_01 | Emilia Clumsy Maid | 2024-03-21 | module: Emilia "Clumsy Maid — Costume Gacha" (the Re:CIPE FOR YOU update's gacha, from the event start); `gg_costumes_db.json`: gacha | confirmed |
| 30 | c821_02 | Emilia Spring Breeze | 2024-03-21 | the Re:CIPE FOR YOU challenge-mission costume — event page: "the costumes 'Spring Breeze' for Emilia and 'Handy Maid' for Rem will also be available under Challenge Missions **simply by recruiting them**" (Emilia recruit = from the event start 2024-03-21); module: "Re:CIPE Checklist Mission challenge"; `gg_costumes_db.json`: event | confirmed |
| 31 | c822 | Ram | 2024-03-21 | wiki "Ram" page (live): `releaseDate = 21 march 2024` (the Re:CIPE FOR YOU gacha's bonus Nikke — event page: "…grants a copy of Ram") | confirmed |
| 32 | recipeforyou | Re: Cipe For You | 2024-03-21 | wiki "Re:CIPE FOR YOU" event page (live): startDate March 21, 2024 → April 11 (the Re:Zero collab); `event_dates_full.json`: ReCIPE_FOR_YOU = 2024-03-21 | confirmed |
| 33 | c820 | Rem | 2024-03-28 | wiki "Rem" page (live): `releaseDate = 28 march 2024` — the collab's second wave (Emilia/Ram 03-21, Rem banner 03-28; `ev_dates.json`: "rem = 2024-03-28"); viewer "March 20th 2024: Added All Rem Ram Emilia assets" (staged) | confirmed |
| 34 | c820_01 | Rem Handy Maid | 2024-03-28 | the Re:CIPE FOR YOU challenge-mission costume, obtainable "simply by recruiting" Rem — and Rem is only recruitable from her 2024-03-28 banner (event page + module: "Re:CIPE Checklist Mission challenge"; `gg_costumes_db.json`: event "Obtain from the Re:CIPE FOR YOU mission") | confirmed |
| 35 | c030_02 | Poli Cheer Up Police | 2024-04-01 | module: Poli "Cheer Up Police — **'Cheer Up Spring! (2024)' login reward**" — the Apr 1 update's login event (the LIAR'S END update); `gg_costumes_db.json`: login | confirmed |
| 36 | c280_01 | Rosanna Ms. Dangerous | 2024-04-01 | **not** a Mar 21 item: module: Rosanna "Ms. Dangerous — **Mission Pass Season 18**"; `mp_costumes.json` S18 = Rosanna (Ms. Dangerous), start **2024-04-01**; `gg_costumes_db.json`: missionpass — the 2024-03-21 value was the announcing update (Re:CIPE FOR YOU) | **corrected** (2024-03-21 → 2024-04-01) |
| 37 | c901 | Syuen | 2024-04-01 | the LIAR'S END story model — wiki "Liar's End" event page (live): "a 3-day event … the April Fools' event for 2024 … centered around the protagonist's April Fools' shenanigans, this time dragging [[Syuen]] into the mix" (startDate April 1st, 2024 → April 4th; `ev_dates.json`: liar's end = 2024-04-01) | confirmed |
| 38 | c550 | Bay | 2024-04-11 | wiki "Bay" page (live): `releaseDate = 11 april 2024` (the ONE MORE TIME character); `ev_dates.json`: "bay = 2024-04-11" | confirmed |
| 39 | onemoretime | One More Time | 2024-04-11 | wiki "One More Time" event page (live): startDate April 11, 2024 → April 24 | confirmed |
| 40 | c330 | Crown | 2024-04-25 | wiki "Crown" page (live): `releaseDate = 25 april 2024` (a Last Kingdom character; `ev_dates.json`'s "crown = 2024-05-02" is her later Standard-pool/pick-up page, superseded by the releaseDate) | confirmed |
| 41 | c330_01 | Crown Naked King | 2024-04-25 | module: Crown "Naked King — Costume Gacha" (series "Awakening Fate" — the Last Kingdom gacha); `gg_costumes_db.json`: gacha | confirmed |
| 42 | c361 | Kilo | 2024-04-25 | wiki "Kilo" page (live): `releaseDate = 25 april 2024` (the other Last Kingdom character; viewer "April 28th 2024: … Added T.A.L.O.S and Kilo") | confirmed |
| 43 | c481 | Fragile | 2024-04-25 | RESEARCH.md NPC sweep: "c481, c491 Fragile, Drilley — Last Kingdom **2024-04-25** (pages 2024-04-24)" — Last Kingdom story characters (the Apr 28 viewer batch: "Added Fragile. Added Drilley") | confirmed |
| 44 | c491 | Drilley | 2024-04-25 | as the c481 row | confirmed |
| 45 | c977 | Kilo | 2024-04-25 | the Last Kingdom story rig of Kilo (c9xx story-model block, RESEARCH.md c9xx rule: follow the debut event; the viewer's Apr 28 batch added the Kilo story asset with the Last Kingdom client) | confirmed |
| 46 | c072_04 | Diesel Midnight Strawberry | 2024-05-01 | **not** an Apr 25 item: module: Diesel "Midnight Strawberry — **Mission Pass Season 19**"; `mp_costumes.json` S19 = Diesel (Midnight Strawberry), start **2024-05-01**; `gg_costumes_db.json`: missionpass — the 2024-04-25 value was the announcing update (Last Kingdom; the viewer's Apr 28 batch shows it staged in that client) | **corrected** (2024-04-25 → 2024-05-01) |
| 47 | c382_01 | Leona Zoo Keeper | 2024-09-01 | module: Leona "Zoo Keeper — **Mission Pass Season 23**"; `mp_costumes.json` S23 = Leona (Zoo Keeper), start **2024-09-01**; `gg_costumes_db.json`: missionpass — the recorded 2024-01-11 was the character's own debut | **corrected** (2024-01-11 → 2024-09-01) |
| 48 | c225_01 | Scarlet: Black Shadow Longing Flower | 2024-10-31 | module: "Longing Flower — Costume Gacha"; `ev_dates.json`: the dedicated gacha page "costume gacha scarlet black shadow (longing flower) = **2024-10-31**" (the Old Tales update) — the variant had inherited the character's New Year debut date; `gg_costumes_db.json`: gacha | **corrected** (2024-01-01 → 2024-10-31) |
| 49 | c043_01 | D: Killer Wife Secret Party Cleaner | 2024-11-01 | **not** a Mar 7 item: module: "D: Killer Wife" "Secret Party Cleaner — **Mission Pass Season 25**"; `mp_costumes.json` S25 = "D: Killer Wife (Secret Party Cleaner)", start **2024-11-01**; `gg_costumes_db.json`: missionpass — the 2024-03-07 value was the character's debut (KILL THE LORD) inherited by the variant | **corrected** (2024-03-07 → 2024-11-01) |
| 50 | c281_01 | Moran Off-Duty Queen | 2025-06-01 | **not** a Jan 25 item: wiki Module:NikkeCostume/data: Moran "Off-Duty Queen — **Mission Pass Season 32**"; `mp_costumes.json` S32 = "Moran (Off-Duty Queen)", start **2025-06-01** (two independent sources agree; `gg_costumes_db.json`: missionpass) — the 2024-01-25 value was the base character's debut date inherited by the variant | **corrected** (2024-01-25 → 2025-06-01) |
## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c140_02 | 2024-01-25 | 2024-02-01 | the **February** MP premium (module S16; `mp_costumes.json` S16; the Dirty Backyard page documents the "February Mission Pass Update") |
| 2 | c210_02 | 2024-02-22 | 2024-03-01 | the **March** MP premium (module S17; `mp_costumes.json` S17) |
| 3 | c280_01 | 2024-03-21 | 2024-04-01 | the **April** MP premium (module S18; `mp_costumes.json` S18) — the recorded value was the Re:CIPE FOR YOU announcing update |
| 4 | c072_04 | 2024-04-25 | 2024-05-01 | the **May** MP premium (module S19; `mp_costumes.json` S19) — the recorded value was the Last Kingdom announcing update |
| 5 | c281_01 | 2024-01-25 | 2025-06-01 | the **June 2025** MP premium (module S32; `mp_costumes.json` S32 = "Moran (Off-Duty Queen)") — the variant's date was the base character's 2024 debut inherited by mistake |
| 6 | c043_01 | 2024-03-07 | 2024-11-01 | the **November 2024** MP premium (module S25; `mp_costumes.json` S25 = "D: Killer Wife (Secret Party Cleaner)") — same inheritance pattern |

## Result

50/50 **rows covered** (this bucket's planned set — see the
partition-restoration note below), **6 ids corrected** — four more
instances of the
announcing-update misattribution for MP premiums (rows 1–4), plus two
**base-debt inheritance** errors where a variant had kept its
character's debut date instead of its (much later) mission-pass
premium date (rows 5–6). The rest is directly documented by wiki
releaseDates / event `startDate`s fetched live this pass (the whole
Jan–May 2024 window, since the official archive ends 2023-12-25), the
wiki's Module:NikkeCostume/data obtain table, or the RESEARCH.md /
ev_dates / viewer-log chains re-verified this pass.

Notable resolutions: the **Re:Zero collab block** (Emilia/Ram 03-21,
Rem 03-28, the Re:FRESH Pass premium dated at event start as the
documented pre-banner exception, the recruit-gated challenge
costumes); **c901 Syuen** identified as the LIAR'S END (April Fools'
2024) story model; the two **c9xx story rigs** (c976 T.Rony, c977
Kilo) tied to their events; the **favorite models** at the
Golden Coin Rush initial release; **Crown/Kilo** at Last Kingdom
(releaseDates 25 april 2024, with Crown's 2024-05-02 pick-up page
rejected as her Standard-pool listing). The c976, favorite and
Last Kingdom rows among these now sit in BUCKET_08's table (partition
restoration).

**Pattern for later buckets (new this pass):** `Module:NikkeCostume/
data` on the intl wiki is a complete, obtain-source-per-costume table
(series + obtain, incl. "Mission Pass Season N" — numbering verified
1:1 against `mp_costumes.json`) and settles any variant whose gg db
flag is a bare "missionpass". It was fetched and cached at
`research2/b07y_datamod.json`; later buckets should grep it first.

**Partition restoration (post-pass):** the ten rows verified in the
BUCKET_09 pass (its former "Gap rows" side table — c180_01, c225,
c225_01, c382, c382_01, c430_02, c971, c974, c974_01,
newyearnewsword) belong to this bucket's planned set and now sit in
this table; four of them (c180_01, c430_02, c225_01, c382_01) were
corrected in the BUCKET_09 pass and remain listed in that file's
Corrections table. Conversely, the ten rows verified here that belong
to BUCKET_08's planned set (c314, c501, c570_99, c976, darkhero,
favorite_c072/c100/c142/c210, lastkingdom) moved to BUCKET_08's
table, and two borrowed copies (c220_01, c260_02) were dropped
(BUCKET_05 / BUCKET_03 own them).

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 6 date corrections (c140_02, c210_02,
      c280_01, c072_04, c281_01, c043_01)
- [x] evidence paths point at files actually in `/tmp`
- [x] 52/52 rows covered: the 50 extracted at pass start + the two
      favorites that slid into the range (40 rows in BUCKET_15)
