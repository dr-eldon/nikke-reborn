# BUCKET_06 — entries 251–300 (`c070_02` … `c082_02`, 2022-11-18 → 2023-12-28)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Official INT posts (UTC+9, `research2/nikke_official_news.json` — the
  archive runs 2022-09-02 → 2023-12-25, so it also covers the launch
  posts): "Developer's Notes" (2022-11-03, director's launch note),
  "Notice on Server Update on November 10" (2022-11-09), "Update on
  November 24" (2022-11-21), "Update on September 1" (2023-08-28),
  "Update on September 21" (2023-09-18), "Update on November 2"
  (2023-10-30), "Update on November 23" (2023-11-20), "Update on
  December 7" (2023-12-04, title has a trailing space in the archive),
  "Update on December 13" (2023-12-12), "Update on December 28"
  (2023-12-25), October/December Developer's Notes. **The Oct 5 and
  Oct 19 update posts are absent from the archive** (the October dev
  note was delayed and covers November instead) — the Oct window is
  verified via wiki releaseDates + event pages + the Nikke-db viewer
  log + the nikke.gg client data.
- MP-season file: `mp_costumes.json` (S11 Brid 2023-09-01, S12 Novel
  2023-10-01, S13 Privaty 2023-11-01, S14 Noir 2023-12-01).
- nikke.gg live client data: `research2/gg_costumes_db.json`.
- Wiki (live fetches this pass): "Naga" (releaseDate 5 october 2023),
  "Tia" (12 october 2023), "Quiry" (19 october 2023), "Dazzling
  Cupid" (startDate October 5th, 2023 → October 19th), "A.C.P.U.!
  FREEZE!" (`research2/p_acpu.json`, startDate October 19th →
  November 1st; "follows the story of Quiry"), "OuteR: Automata"
  (`research2/p_outrer.json`, September 1st → 28th; 9S appears in its
  story), "NEVERLAND" (`research2/p_NEVERLAND.json`, December 7th →
  28th; Part II opens 5:00 Dec 14; "Bunny Lucky Pass … premium track
  offers the costume 'White Rabbit' for Blanc"; Snowfall Oasis
  "Unlocked after clearing Stage I-5"), "Co-Op Battle" (cached
  `research2/p_coop.txt`, full event table parsed this pass) +
  Minor characters/Event tab (cached: Lumi/Lena — `debut =
  [[NEVERLAND]]`).
- Prior-pass files: RESEARCH.md (chapter table — ch 25–26 = Red Ash
  2023-11-02; NPC/collab sweeps — c813 9S, dazzlingcupid, c250–c255,
  ghosts = NEVERLAND, c270_01 = Bunny Lucky Pass), `research2/updateLog.json`
  (Nikke-db viewer log).

## Table

| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c070_02 | Brid Black Moon | 2023-09-01 | official "Update on September 1": "2.5 Special Costume: Brid - Black Moon … can be obtained from **September Mission Pass**" (sale from the Sept 1 maintenance end, per 5.3); `mp_costumes.json` S11 = 2023-09-01; `gg_costumes_db.json`: missionpass | confirmed |
| 2 | c810 | 2B | 2023-09-01 | official "Update on September 1": "1.1 SSR 2B — the android from YoRHa … Limited-Time Recruitment: From the end of the September 1, 2023 maintenance" (OuteR:Automata collab) | confirmed |
| 3 | c810_01 | 2B Metamorphic Damage | 2023-09-01 | official: "2.2 Special Costume: 2B - Metamorphic Damage — To obtain: Own SSR 2B … Fulfill the OuteR:Automata Challenge requirements" (challenge + 2B both from Sept 1); `gg_costumes_db.json`: "Obtained from OUTER AUTOMATA event missions" | confirmed |
| 4 | c810_02 | 2B YoRHa Uniform 1 | 2023-09-01 | official: "2.1 Special Costume: 2B - YoRHa Uniform 1 … from Costume Gacha" (sale opens with the Sept 1 update); `gg_costumes_db.json`: gacha | confirmed |
| 5 | c812 | Pascal | 2023-09-01 | official: "1.3 SR Pascal … can be obtained in the collab event, OuteR:Automata. * Duration to obtain: From the end of the September 1, 2023 maintenance to 4:59:59, September 28, 2023" (event-exclusive character) | confirmed |
| 6 | c813 | 9S | 2023-09-01 | wiki "OuteR: Automata" event page (live): the collab story features "a female named 2B and a male named 9S" (minor character of the collab event; RESEARCH.md collab table: "c813 9S — OuteR:Automata, 2023-09-01") — a story model of the Sept 1 event | confirmed |
| 7 | outerautomata | Outer Automata | 2023-09-01 | official "Update on September 1": "3.1 NieR:Automata Grand Collaboration Event - OuteR:Automata * From the end of September 1, 2023 maintenance to 4:59:59, September 28, 2023"; wiki event page: startDate September 1st, 2023 | confirmed |
| 8 | c811 | A2 | 2023-09-08 | official "Update on September 1": "1.2 SSR A2 … **Limited-Time Recruitment duration: From 5:00:00, September 8, 2023** to 4:59:59, September 28, 2023" — pre-staged in the Sept 1 client, first obtainable at the gacha start (the Noir/Neon/Mica convention) | confirmed |
| 9 | c811_01 | A2 Metamorphic Damage | 2023-09-08 | official: "2.4 Special Costume: A2 - Metamorphic Damage — To obtain: **Own SSR A2** … Fulfill the OuteR:Automata Challenge requirements" — the challenge runs from Sept 1 but the A2 ownership gate makes it first obtainable when A2 is (Sept 8); `gg_costumes_db.json`: OUTER AUTOMATA event missions | confirmed |
| 10 | c811_02 | A2 YoRHa Uniform Prototype | 2023-09-08 | official: "2.3 … can be obtained from **YoRHa Pass**" + "5.2 YoRHa Pass Event duration: **From 5:00:00, September 8, 2023** to 4:59:59, September 28, 2023 … Win A2's special costume, YoRHa Uniform Prototype, once you reach the maximum level"; `gg_costumes_db.json`: eventpass | confirmed |
| 11 | c212_02 | Novel Detective Nurse | 2023-10-01 | **not** a Sept 21 item: official "Update on September 21": "2.1 Special Costume: Novel - Detective Nurse … can be obtained from an **October Mission Pass**"; `mp_costumes.json` S12 = Novel (Detective Nurse), start **2023-10-01** (MP season-start rule) — the 2023-09-21 value was the announcing update | **corrected** (2023-09-21 → 2023-10-01) |
| 12 | c321 | Marciana | 2023-09-21 | official "Update on September 21": "1.1 SSR Marciana — M.M.R. Vocational School's perfect teacher … Special Recruit: From the end of the September 21, 2023 maintenance" | confirmed |
| 13 | schooloflock | School Of Lock | 2023-09-21 | official "Update on September 21": "3.1 New Story Event: SCHOOL OF LOCK * From the end of September 21, 2023 maintenance to 4:59:59 October 5, 2023" | confirmed |
| 14 | c072_02 | Diesel Strawberry Flower | 2023-10-05 | `gg_costumes_db.json`: "72/Strawberry Flower — **login** (Obtained from Login Event)" — the Oct 5 update's login event (Dazzling Cupid window); viewer log "October 5th 2023: Added Diesel Strawberry Flower live2d" (asset of the Oct 5 client). The Oct 5 post is absent from the archive | confirmed |
| 15 | c450 | Naga | 2023-10-05 | wiki "Naga" page (live): `releaseDate = 5 october 2023`; viewer log "October 3rd 2023: … Added … Naga, Tia …" (pre-staged before the Oct 5 update); Dazzling Cupid event (Oct 5–19) with a Naga variant model (row 17) | confirmed |
| 16 | dazzlingcupid_tia | Dazzling Cupid: Tia | 2023-10-05 | wiki "Dazzling Cupid" event page (live): startDate October 5th, 2023 → October 19th; RESEARCH.md: "dazzlingcupid_tia/naga → Dazzling Cupid 2023-10-05"; viewer "October 7th 2023: Added Dazzling Cupid eventscenes" | confirmed |
| 17 | dazzlingcupid_naga | Dazzling Cupid: Naga | 2023-10-05 | as row 16 | confirmed |
| 18 | c451 | Tia | 2023-10-12 | wiki "Tia" page (live): `releaseDate = 12 october 2023` (the second wave of the Dazzling Cupid window, pre-staged with Naga in the Oct 5 client per the viewer's Oct 3 batch — gacha-start convention) | confirmed |
| 19 | c033 | Quiry | 2023-10-19 | wiki "Quiry" page (live): `releaseDate = 19 october 2023`; wiki "A.C.P.U.! FREEZE!" event page (live): startDate October 19th — "follows the story of Quiry"; viewer "October 19th 2023: Added Quiry, Privaty Banquet Princess to live 2d" (the Oct 19 post is absent from the archive) | confirmed |
| 20 | c170_02 | Privaty Banquet Princess | 2023-11-01 | **not** an Oct 19 shop costume: `gg_costumes_db.json`: "170/Banquet Princess — **missionpass**"; `mp_costumes.json` S13 = Privaty (Banquet Princess), start **2023-11-01** → the November monthly MP premium (the announcing Oct 19 post is absent from the archive; the viewer's Oct 19 batch shows it staged in that update) | **corrected** (2023-10-19 → 2023-11-01) |
| 21 | acpufreeze | ACPU FREEZE | 2023-10-19 | wiki "A.C.P.U.! FREEZE!" event page (live): "the 21st story event … startDate=October 19th, 2023" (event model of the Oct 19 update) | confirmed |
| 22 | mbg001 | Boss: Alteisen | 2022-11-18 | **not** an Oct 2023 model: the director's launch dev note (2022-11-03): "coordinated operations … will be **rolled out sequentially**" after launch — Co-Op was not a launch feature, and the Nov 10 update post (the closest documented update before the first Co-Op) lists no Co-Op content; the first documented appearance = the first Co-Op, **18 november 2022** (oldest row of the wiki Co-Op table, "Alteisen MK.VI"); the full client dump contains exactly **one** Alteisen boss model (mbg001), so the Nov 2022 Co-Ops used this model. The 2023-10-19 value is the client re-patch date (the 2023-10-20 "Alteisen MK.VI\|code=water" Co-Op reuses the same model). Resolves the BUCKET_03 carry-over item | **corrected** (2023-10-19 → 2022-11-18) |
| 23 | c224 | Snow White: Innocent Days | 2023-11-02 | official "Update on November 2": "1.2 SSR Snow White: Innocent Days … can be obtained at the 1ST ANNIVERSARY PARTY, RED ASH event(s), and 14 Days Login" (1st-anniversary character; variant-character debut) | confirmed |
| 24 | c230_01 | Harran Banquet Witch | 2023-11-02 | official "Update on November 2": "2.2 Special Costume: Harran - Banquet Witch … can be obtained from a **1ST ANNIVERSARY PASS**" (event pass of this update); `gg_costumes_db.json`: eventpass | confirmed |
| 25 | c233_01 | Dorothy Nostalgia | 2023-11-02 | official "Update on November 2": "2.1 Special Costume: Dorothy - Nostalgia … head to Costume Gacha"; `gg_costumes_db.json`: gacha | confirmed |
| 26 | c250 | Mass Produced Red | 2023-11-02 | RESEARCH.md: "c250–c255 Mass Produced ×6 — Red Ash **2023-11-02** (viewer batch 2023-11-16)"; viewer log "November 16th 2023: Added Mass Produced Red l2d" (asset of the Nov 2 client — the 1st-anniversary Red Ash story / MEMORY OF GODDESS minigame mass-produced Nikke models) | confirmed |
| 27 | c251 | Mass Produced Blue | 2023-11-02 | as row 26 | confirmed |
| 28 | c252 | Mass Produced Orange | 2023-11-02 | as row 26 | confirmed |
| 29 | c253 | Mass Produced Green | 2023-11-02 | as row 26 | confirmed |
| 30 | c254 | Mass Produced Purple | 2023-11-02 | as row 26 | confirmed |
| 31 | c255 | Mass Produced White | 2023-11-02 | as row 26 | confirmed |
| 32 | c470 | Red Hood | 2023-11-02 | official "Update on November 2": "1.1 SSR Red Hood — the red wolf of Goddess Squad, joins Special Recruit" (1st-anniversary character, from the end of the Nov 2 maintenance) | confirmed |
| 33 | c470_01 | Red Hood Nonsense Red | 2023-11-02 | `gg_costumes_db.json`: "470/Nonsense Red — **event** (Obtained from an event)" — the 1st-anniversary event costume of the Nov 2 update (no separate gacha/shop window in the Nov 2 post) | confirmed |
| 34 | c470_02 | Red Hood Retro Days | 2023-11-02 | `gg_costumes_db.json`: "470/Retro Days — **gacha** (Costume Gacha)" — sale opens with the Nov 2 update | confirmed |
| 35 | redash1 | RED ASH 1 | 2023-11-02 | official "Update on November 2": "3.1 New Story Event: RED ASH" (event models) | confirmed |
| 36 | redash2 | RED ASH 2 | 2023-11-02 | as row 35 | confirmed |
| 37 | story2501 | Story 25-01 | 2023-11-02 | official "Update on November 2": "5.1 Main Scenario Update — Added Chapters 25 and 26" (RESEARCH.md chapter table: ch 25–26 = Red Ash 2023-11-02) | confirmed |
| 38 | story2602 | Story 26-02 | 2023-11-02 | as row 37 | confirmed |
| 39 | c192 | Tove | 2023-11-23 | official "Update on November 23": "1.1 SSR Tove — Unlimited squad's newbie … joins the battlefield" (from the end of the Nov 23 maintenance) | confirmed |
| 40 | c271_01 | Noir Black Rabbit | 2023-12-01 | **not** a Nov 23 item: official "Update on November 23": "2.1 Special Costume: Noir - Black Rabbit … can be obtained from the **December Mission Pass**"; `mp_costumes.json` S14 = Noir (Black Rabbit), start **2023-12-01**; `gg_costumes_db.json`: missionpass (the Nov 23 viewer batch shows it staged in that update) | **corrected** (2023-11-23 → 2023-12-01) |
| 41 | alonesurvivor | Alone Survivor | 2023-11-23 | official "Update on November 23": "3.1 New Story Event: ALONE SURVIVOR * From the end of the November 23, 2023 maintenance to 4:59:59, December 7, 2023" | confirmed |
| 42 | c194 | Ludmilla: Winter Owner | 2023-12-07 | official "Update on December 7": "1.1 SSR Ludmilla: Winter Owner … Limited-Time Recruitment: From the end of the December 7, 2023 maintenance" (variant-character debut; the Dec 7 post's title has a trailing space in the archive) | confirmed |
| 43 | c270_01 | Blanc White Rabbit | 2023-12-07 | wiki "NEVERLAND" event page (cached): "===Bunny Lucky Pass=== An event exclusive Mission Pass separate from the monthly version. The premium track … offers the costume 'White Rabbit' for Blanc" → event date (Dec 7 start); `gg_costumes_db.json`: eventpass; viewer "December 9th 2023: … added Blanc White Rabbit, added Neverland eventscene" (RESEARCH.md CN-pass correction 2023-05-18 → 2023-12-07 re-confirmed) | confirmed |
| 44 | neverland | Neverland | 2023-12-07 | wiki "NEVERLAND" event page: `startDate = December 7th, 2023` → December 28th; the Dec 7 update shipped the event (Dec 13 post: "Story Event NEVERLAND Story II on December 14") | confirmed |
| 45 | c967 | Ghost - Lumi | 2023-12-07 | the ghosts debut in NEVERLAND's **Snowfall Oasis** minigame (wiki Minor characters/Event: Lumi "debut = [[NEVERLAND]]", "A Soldier OW from NEVERLAND's Snowfall Oasis minigame"; `minor_debuts.json`: Lumi/Lena → NEVERLAND) — the minigame is "Unlocked after clearing Stage I-5" and Part I stages open at the end of the Dec 7 maintenance, so it is reachable from the event start. The event-NPC convention = event start (cf. c939 Doban, c945 Katie) | **corrected** (2023-12-08 → 2023-12-07) |
| 46 | c968 | Ghost - Lua | 2023-12-07 | as row 45 (Lua = Lumi's sister, same minigame) | **corrected** (2023-12-08 → 2023-12-07) |
| 47 | c969 | Ghost - Lena | 2023-12-07 | as row 45 (Lena = Lumi's sister) | **corrected** (2023-12-08 → 2023-12-07) |
| 48 | c970 | Lumi | 2023-12-07 | as row 45 (the non-ghost Lumi model of the same minigame; `minor_debuts.json`: "Lumi": "NEVERLAND") | **corrected** (2023-12-08 → 2023-12-07) |
| 49 | c062 | Mica: Snow Buddy | 2023-12-14 | official "Update on December 7": "1.2 SSR Mica: Snow Buddy … **Special Recruit duration: From 5:00:00, December 14, 2023** to 23:59:59, December 31, 2023" — pre-staged in the Dec 7 client, first obtainable at the gacha start (the Dec 13 post confirms the Dec 14 content: NEVERLAND Story II opens Dec 14) | confirmed |
| 50 | c082_02 | Liter Cute Sunflower | 2023-12-28 | official "Update on December 28": "2.3 Special Costume: Liter - Cute Sunflower … can be obtained from a **SUNRISE PASS**" (the NEW YEAR, NEW SWORD event pass; `gg_costumes_db.json`: eventpass; viewer "December 29th 2023: … Liter Cute Sunflower … New Year New Sword live2d") | confirmed |

## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c212_02 | 2023-09-21 | 2023-10-01 | the **October** MP premium (official Sept 21 post: "October Mission Pass"; `mp_costumes.json` S12) — the recorded value was the announcing update |
| 2 | c170_02 | 2023-10-19 | 2023-11-01 | the **November** MP premium (`gg_costumes_db.json` missionpass; `mp_costumes.json` S13) — the announcing Oct 19 post is absent from the archive |
| 3 | c271_01 | 2023-11-23 | 2023-12-01 | the **December** MP premium (official Nov 23 post: "December Mission Pass"; `mp_costumes.json` S14) |
| 4 | mbg001 | 2023-10-19 | 2022-11-18 | the Co-Op boss shipped with the post-launch Co-Op rollout (director's launch note: Co-Op "rolled out sequentially" after launch; first Co-Op = 2022-11-18 per the Co-Op table; the single Alteisen model in the full client dump is the one the 2022 Co-Ops used) — the recorded value was the 2023-10-20 code=water Co-Op re-patch |
| 5–8 | c967–c969, c970 | 2023-12-08 | 2023-12-07 | the Lumi/Lua/Lena models debut in NEVERLAND (wiki minor-character infoboxes) via the Snowfall Oasis minigame, reachable from the event start (Stage I-5 unlock; Part I open at the Dec 7 maintenance end) — event-start convention for event NPCs |

## Result

50/50 **reviewed**, **8 ids corrected across 6 rows** (c212_02,
c170_02, c271_01 — the monthly-MP premium pattern again, one per
announcing update; mbg001 — the BUCKET_03 carry-over item resolved:
the Alteisen boss is a post-launch Co-Op model first appearing in the
2022-11-18 Co-Op, not an Oct 2023 addition; c967–c969/c970 — one-day
alignment to the NEVERLAND event start). Everything else is directly
documented by an official update post (the archive also covers the
launch posts, which settled the mbg001 question), the wiki
character/event pages for the two Oct updates missing from the
archive, the MP-season file + nikke.gg client data, or the
RESEARCH.md/viewer-log chains re-verified this pass.

Notable resolutions: the **BUCKET_03 open item (a) on mbg001 is
closed**; the launch dev note's "rolled out sequentially" line is
now the documented reason Co-Op bosses pre-date their first
table-listed Co-Op by an unposted hotfix; **c811_02** resolved via
the YoRHa Pass sale window (Sept 8, with A2); **9S** identified as
the OuteR:Automata story minor character; **Mica: Snow Buddy**
confirmed at its Dec 14 gacha start (pre-staged Dec 7).

**Pattern for later buckets (reinforced):** for the Oct 2023 window
(no official posts in the archive), the wiki releaseDate + event-page
startDate + viewer-log staging batch + nikke.gg obtain-source chain
was sufficient on its own.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 8 date corrections (c212_02, c170_02,
      c271_01, mbg001, c967, c968, c969, c970)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered (40 in BUCKET_15)
