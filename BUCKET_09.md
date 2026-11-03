# BUCKET_09 — entries 401–450 (`smol_ade` … `c016_03`, 2024-02-05 → 2026-05-01)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Wiki (live fetches this pass, `research2/b09_*.json`): character pages
  with `releaseDate` — Grave (7 november 2024), Flora (21 november
  2024), Mana (16 january 2025), Rapi: Red Hood (1 january 2025); event
  pages — Ice Dragon Saga (startDate December 5th, 2024; "===Ark Mage
  Pass=== An event-exclusive Mission Pass … premium track offers the
  costume 'Ark Mage' for Vesti"), Romantic Valentine (startDate January
  30th, 2025 → February 19th, 2025; "===Backstreet Maid Pass=== …
  premium track offers the costume 'Backstreet Dream' for Sin"; the
  soundtrack section lists the "Pirate Cafe" minigame), First Affection
  (a **quest event**, 24–31 august 2023, "made to commemorate Modernia
  winning the Popularity Poll I" — the precedent for how poll rewards
  land), Doki Doki NIKKE Global Popularity Poll III (voting April 8 →
  14, 2025; "The Top 1 Nikke with the most votes will be rewarded with a
  special costume that will be distributed for free"; results revealed
  at the 2.5th-anniversary livestream, 19:30 April 19th; top 1 =
  Rapi: Red Hood, 1,398,772 votes).
- Official poll page `nikke-en.com/events/nikkevote2025/`
  (`research2/b09_official_poll.html`): "The Nikke that tops the poll
  will receive a specially designed costume that will be distributed
  across all servers for free" (event April 8–14, 2025).
- MP-season file `mp_costumes.json`: S26 Volume (Beat the Gun)
  2024-12-01, S27 Zwei (First Festa) 2025-01-01, S28 Trony (Sweet Step)
  2025-02-01, S43 Rapi: Red Hood (Shining Light) 2026-05-01.
- `research2/b07y_datamod.json` (Module:NikkeCostume/data) — obtain per
  costume, incl. the whole Rapi: Red Hood block (Red Flavor — Costume
  Gacha; Cherished Red — 2025 Popularity Poll rewards; Shining Light —
  Mission Pass Season 43), Zwei "First Festa — Mission Pass Season 27",
  Ein "Handmade Festa — **2025 New Year Pass**", Naga "Last Girlhood —
  Costume Gacha", Sin "Backstreet Dream — Backstreet Maid Pass",
  Mast: Romantic Maid "Tea Service — Costume Gacha", Vesti "Ark Mage —
  Ark Mage Pass", Volume "Beat the Gun — Mission Pass Season 26",
  Trony "Sweet Step — Mission Pass Season 28".
- nikke.gg live client data `research2/gg_costumes_db.json` (390/1 &
  390/2 missionpass, 391/1 eventpass, 431/1 missionpass, 450/2 gacha,
  501/1 missionpass, 354/1 gacha).
- Viewer update log `research2/updateLog.json`: 2024-02-07 "Added Smol
  Maid Privaty and Smol Ade **from the Perfect Maid Minigame**";
  2025-02-21 "Added Smol Mast Pirate + Anchor + Sin, **Pirate Cafe**,
  Romantic Valentine, Sweet Johnny" (the 2025-01-30 client batch);
  2024-04-28 "Updated Unknown name to **Grave**" (the Last Kingdom NPC
  later gacha-released).
- Prior-pass files: RESEARCH.md (NPC sweep — c996 Leviathan = c562
  2024-10-31, c988 Chloe Ice Dragon Saga 2024-12-05, c991 D.E.E.P.
  2024-12-26, c9032 Jien Wisdom Spring 2025-01-16 + "c973 Jien =
  c9032"; Favorite-Item table — Helm/Miranda/Drake/Milk, Wisdom Spring,
  2025-01-16; the c989–c994 Rapi ×4 = 2025-01-01 correction),
  `research/ev_dates.json` (secret garden 2024-11-21, grave 2024-11-07,
  ice dragon saga 2024-12-05, footstep walk run 2024-12-26,
  wisdom spring 2025-01-16, romantic valentine 2025-01-30, pick-up
  pages 60/61/62/64, "costume gacha mast romantic maid (tea service) =
  2026-02-12", "costume gacha rapi red hood (red flavor) = 2025-07-17",
  poll I/II/III/IV page dates), `research2/b08_eventlist.json` (2024/2025
  event tables). The official post archive ends 2023-12-25.

## Table
| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | smol_ade | Smol Ade | 2024-02-05 | **not** a Jan 30 item: update log **2024-02-07**: "Added Smol Maid Privaty and **Smol Ade** from the **Perfect Maid Minigame**" — the model first shipped with the 2024-02-05 Perfect Maid update (it reappears in the 2025 Pirate Cafe minigame, but its debut is the 2024 one) | **corrected** (2025-01-30 → 2024-02-05) |
| 2 | c983 | Nadia | 2024-10-17 | RESEARCH.md: "Nadia in Life Again **2024-10-17**" (the event's minor character; `ev_dates.json`: life again = 2024-10-17) | confirmed |
| 3 | lifeagain | Life Again | 2024-10-17 | `ev_dates.json`: life again = 2024-10-17; wiki Event list page: "Life Again \| 17 october 2024" | confirmed |
| 4 | c226 | Rapunzel: Pure Grace | 2024-10-31 | the Old Tales variant character — module has "Rapunzel: Pure Grace" as its own character entry (rarity SSR); the Old Tales story (wiki page, live) features "A [[Rapunzel: Pure Grace\|priestess]] checked her for injuries" (the 2nd-generation Grimm's models) | confirmed |
| 5 | c231_01 | Isabel Honeymoon Party | 2024-10-31 | the **2nd Anniversary Pass** premium — wiki "Old Tales (event)" page (live): "===2nd Anniversary Pass=== An event-exclusive Mission Pass separate from the standard version. The premium track offers the costume 'Honeymoon Party' for Isabel" (the 2nd anniversary was celebrated with the Old Tales event, startDate October 31st, 2024; module: Isabel "Honeymoon Party — 2nd Anniversary Pass") | confirmed |
| 6 | c511 | Cinderella | 2024-10-31 | wiki "Cinderella" page (live): `releaseDate = 31 october 2024` (the Old Tales main character, "the 2nd-generation Grimm's") | confirmed |
| 7 | c511_01 | Cinderella Glass Princess | 2024-10-31 | module: Cinderella "Glass Princess — Costume Gacha" (the Old Tales update's gacha, 2024-10-31) | confirmed |
| 8 | c562 | Leviathan | 2024-10-31 | RESEARCH.md NPC sweep: "c562 Leviathan — Old Tales **2024-10-31** (page 2024-10-26; viewer 2025-04-12 lags)" | confirmed |
| 9 | c979 | Abe | 2024-10-31 | RESEARCH.md: "Abe/Hansel/Gretel/Red Shoes in Old Tales second series **2024-10-31**"; the Old Tales story (live) features Abe ("the woman who woke her") | confirmed |
| 10 | c980 | Hansel | 2024-10-31 | as the c979 row (the Old Tales story features Hansel and Gretel) | confirmed |
| 11 | c981 | Gretel | 2024-10-31 | verified in BUCKET_08 (RESEARCH.md's Old Tales row: "Abe/Hansel/Gretel/Red Shoes in Old Tales second series **2024-10-31**"); slid into this bucket's range by the smol_ade/smol_mpriv corrections — the c982 sibling sits alongside it in this table (verified in BUCKET_08) | confirmed (BUCKET_08) |
| 12 | c982 | Red Shoes | 2024-10-31 | verified in BUCKET_08 (RESEARCH.md's Old Tales row names all four second-series minors: "Abe/Hansel/Gretel/Red Shoes … **2024-10-31**"); it slid into this bucket's sorted range when the smol_ade correction shifted the rows | confirmed (BUCKET_08) |
| 13 | c996 | Leviathan | 2024-10-31 | RESEARCH.md rule: "c996 Leviathan = c562" (same Old Tales boss rig) — c562 dated 2024-10-31 (Old Tales, BUCKET_08) | confirmed |
| 14 | oldtales | Old Tales | 2024-10-31 | wiki "Old Tales (event)" page (fetched BUCKET_08): startDate October 31st, 2024; `ev_dates.json`: old tales = 2024-10-31 | confirmed |
| 15 | c510 | Grave | 2024-11-07 | wiki "Grave" page (live): `releaseDate = 7 november 2024` (her gacha release); she is the Last Kingdom NPC the viewer had carried as "Unknown" (update log 2024-04-28: "Updated Unknown name to Grave"); the Rapi: Red Hood page trivia confirms "Grave's case, with her NPC sprite remaining as a narrative-relevant depiction in-game" — story model since 2024-04-25, playable from 2024-11-07 | confirmed |
| 16 | c514 | Grave | 2024-11-07 | second Grave model of the same release (duplicate-rig pattern); the character's only release is 2024-11-07 (the c510 row) | confirmed |
| 17 | c411 | Flora | 2024-11-21 | wiki "Flora" page (live): `releaseDate = 21 november 2024` (the Secret Garden character) | confirmed |
| 18 | secretgarden | Secret Garden | 2024-11-21 | `ev_dates.json`: secret garden = 2024-11-21; wiki Event list page: "Secret Garden \| 21 november 2024" | confirmed |
| 19 | c431_01 | Volume Beat the Gun | 2024-12-01 | **not** a Nov 21 item: module: Volume "Beat the Gun — **Mission Pass Season 26**"; `mp_costumes.json` S26 = Volume (Beat the Gun), start **2024-12-01** (the December MP announced with the Nov 21 Secret Garden update); `gg_costumes_db.json`: missionpass | **corrected** (2024-11-21 → 2024-12-01) |
| 20 | c091_01 | Vesti Ark Mage | 2024-12-05 | wiki "Ice Dragon Saga" page (live, startDate December 5th, 2024): "===Ark Mage Pass=== An event-exclusive Mission Pass … premium track offers the costume 'Ark Mage' for [[Vesti]]"; module: Vesti "Ark Mage — Ark Mage Pass" | confirmed |
| 21 | c183 | Maiden: Ice Rose | 2024-12-05 | the Ice Dragon Saga variant character — module has "Maiden: Ice Rose" as its own character entry; `ev_dates.json`: "pick up 60 maiden ice rose = 2024-12-05" (her pick-up page) | confirmed |
| 22 | c988 | Chloe - Village Guardian | 2024-12-05 | RESEARCH.md NPC sweep: "Chloe in Ice Dragon Saga **2024-12-05**" (the event's minor character; the Ice Dragon Saga story, live, features "Now Chloe, her one and only friend, is hurt") | confirmed |
| 23 | icedragonsaga | Ice Dragon Saga | 2024-12-05 | wiki "Ice Dragon Saga" event page (live): startDate December 5th, 2024; `ev_dates.json`: ice dragon saga = 2024-12-05 | confirmed |
| 24 | c182 | Guillotine: Winter Slayer | 2024-12-12 | the Dec 12 variant character — module has "Guillotine: Winter Slayer" as its own character entry; `ev_dates.json`: "pick up 61 guillotine winter slayer = 2024-12-12" | confirmed |
| 25 | c450_02 | Naga Last Girlhood | 2024-12-26 | module: Naga "Last Girlhood — Costume Gacha" (the gacha of the Dec 26 Footstep Walk Run update); `gg_costumes_db.json`: gacha (Costume Gacha) | confirmed |
| 26 | footstepwalkrun | Footstep Walk Run | 2024-12-26 | wiki Event list page: "Footstep, Walk, Run \| 26 december 2024"; `ev_dates.json`: footstep, walk, run = 2024-12-26 | confirmed |
| 27 | c016 | Rapi: Red Hood | 2025-01-01 | wiki "Rapi: Red Hood" page (live): `releaseDate = 1 january 2025` (the New Year SSR); `ev_dates.json`: "pick up 62 rapi red hood = 2025-01-01" | confirmed |
| 28 | c390_01 | Zwei First Festa | 2025-01-01 | **not** a Dec 26 item: module: Zwei "First Festa — **Mission Pass Season 27**"; `mp_costumes.json` S27 = Zwei (First Festa), start **2025-01-01** (the January MP announced with the Dec 26 Footstep Walk Run update); `gg_costumes_db.json`: missionpass | **corrected** (2024-12-26 → 2025-01-01) |
| 29 | c391_01 | Ein Handmade Festa | 2025-01-01 | **not** a Dec 26 item: module: Ein "Handmade Festa — **2025 New Year Pass**" (the event pass of the 2025-01-01 New Year update — the same pass family as the Ark Guardian "New Year Pass" of the c403_01 row in BUCKET_08); `gg_costumes_db.json`: eventpass | **corrected** (2024-12-26 → 2025-01-01) |
| 30 | c290 | Mana | 2025-01-16 | wiki "Mana" page (live): `releaseDate = 16 january 2025` (the Wisdom Spring character); `ev_dates.json`: mana = 2025-01-16 | confirmed |
| 31 | c9032 | Jien | 2025-01-16 | RESEARCH.md: "c9032 Jien = Wisdom Spring **2025-01-16**" | confirmed (previous pass) |
| 32 | c973 | Jien | 2025-01-16 | RESEARCH.md rule: "c973 Jien = c9032" (duplicate rig) | confirmed (previous pass) |
| 33 | favorite_c032 | Favorite: Miranda | 2025-01-16 | RESEARCH.md Favorite-Item table: "Helm, Miranda, Drake, Milk — Wisdom Spring — **2025-01-16**" | confirmed (previous pass) |
| 34 | favorite_c101 | Favorite: Drake | 2025-01-16 | as the favorite_c032 row | confirmed (previous pass) |
| 35 | favorite_c141 | Favorite: Milk | 2025-01-16 | as the favorite_c032 row | confirmed (previous pass) |
| 36 | favorite_c352 | Favorite: Helm | 2025-01-16 | as the favorite_c032 row | confirmed (previous pass) |
| 37 | wisdomspring | Wisdom Spring | 2025-01-16 | `ev_dates.json`: wisdom spring = 2025-01-16; wiki Event list page: "Wisdom Spring \| 16 january 2025" | confirmed |
| 38 | c354 | Mast: Romantic Maid | 2025-01-30 | the Romantic Valentine variant character — module has "Mast: Romantic Maid" as its own character entry (the second character redesigned after becoming playable, per the character page); `ev_dates.json`: "pick up 64 mast romantic maid = 2025-01-30" | confirmed |
| 39 | c401_01 | Sin Backstreet Dream | 2025-01-30 | wiki "Romantic Valentine" event page (live, startDate January 30th, 2025): "===Backstreet Maid Pass=== An event-exclusive Mission Pass … premium track offers the costume 'Backstreet Dream' for [[Sin]]"; module: Sin "Backstreet Dream — Backstreet Maid Pass" | confirmed |
| 40 | romanticvalentine | Romantic Valentine | 2025-01-30 | wiki "Romantic Valentine" event page (live): startDate January 30th, 2025; `ev_dates.json`: romantic valentine = 2025-01-30 | confirmed |
| 41 | smol_anchor | Smol Anchor | 2025-01-30 | the Pirate Cafe minigame's Smol cast, shipped with the Romantic Valentine update — update log 2025-02-21: "Added Smol Mast Pirate + **Anchor** + Sin, Pirate Cafe, Romantic Valentine" (the 2025-01-30 client) | confirmed |
| 42 | smol_anchor_pirate | Smol Anchor Pirate | 2025-01-30 | as the smol_anchor row (same minigame batch) | confirmed |
| 43 | smol_bolt | Smol Bolt | 2025-01-30 | as the smol_anchor row (same minigame batch) | confirmed |
| 44 | smol_frima | Smol Frima | 2025-01-30 | as the smol_anchor row (same minigame batch) | confirmed |
| 45 | smol_helm | Smol Helm | 2025-01-30 | as the smol_anchor row (same minigame batch) | confirmed |
| 46 | c501_01 | Trony Sweet Step | 2025-02-01 | **not** a Jan 30 item: module: Trony "Sweet Step — **Mission Pass Season 28**"; `mp_costumes.json` S28 = Trony (Sweet Step), start **2025-02-01** (the February MP announced with the Jan 30 Romantic Valentine update); `gg_costumes_db.json`: missionpass | **corrected** (2025-01-30 → 2025-02-01) |
| 47 | c016_02 | Rapi: Red Hood Cherished Red | 2025-04-19 | **not** a Jan 1 item: module: "Cherished Red — **2025 Popularity Poll rewards**"; wiki "Doki Doki NIKKE Global Popularity Poll III" (live): voting April 8 → 14, 2025, top 1 = Rapi: Red Hood, "The Top 1 Nikke … will be rewarded with a special costume that will be distributed for free", "All results will be revealed during the 2.5th Anniversary live stream, set to broadcast at 19:30, April 19th" — official page: "distributed across all servers for free". No dedicated costume page/gacha exists, so the date is the documented announcement/distribution date | **corrected** (2025-01-01 → 2025-04-19) |
| 48 | c016_01 | Rapi: Red Hood Red Flavor | 2025-07-17 | **not** a Jan 1 item: module: "Red Flavor — Costume Gacha"; `ev_dates.json`: the dedicated gacha page "costume gacha rapi red hood (red flavor) = **2025-07-17**" (the Boom! The Ghost! update) — the variant had inherited the character's New Year debut date | **corrected** (2025-01-01 → 2025-07-17) |
| 49 | c354_01 | Mast: Romantic Maid Tea Service | 2026-02-12 | **not** a Jan 30 item: module: "Tea Service — Costume Gacha"; `ev_dates.json`: the dedicated gacha page "costume gacha mast romantic maid (tea service) = **2026-02-12**" (the Lie Cause Recoil update) — the variant had inherited the character's Romantic Valentine debut date | **corrected** (2025-01-30 → 2026-02-12) |
| 50 | c016_03 | Rapi: Red Hood Shining Light | 2026-05-01 | **not** a Jan 1 item: module: "Shining Light — **Mission Pass Season 43**"; `mp_costumes.json` S43 = Rapi: Red Hood (Shining Light), start **2026-05-01** | **corrected** (2025-01-01 → 2026-05-01) |
## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c431_01 | 2024-11-21 | 2024-12-01 | the **December** MP premium (module S26; `mp_costumes.json` S26 = Volume (Beat the Gun)) — the recorded value was the Secret Garden announcing update |
| 2 | c390_01 | 2024-12-26 | 2025-01-01 | the **January** MP premium (module S27; `mp_costumes.json` S27 = Zwei (First Festa)) |
| 3 | c391_01 | 2024-12-26 | 2025-01-01 | the **2025 New Year Pass** premium (module) — the event pass of the 2025-01-01 update, announced with the Dec 26 Footstep Walk Run update |
| 4 | c501_01 | 2025-01-30 | 2025-02-01 | the **February** MP premium (module S28; `mp_costumes.json` S28 = Trony (Sweet Step)) |
| 5 | c354_01 | 2025-01-30 | 2026-02-12 | the dedicated **Costume Gacha** page for the Tea Service costume ran on 2026-02-12 (the Lie Cause Recoil update) — the variant had inherited the Mast: Romantic Maid debut date |
| 6 | c016_01 | 2025-01-01 | 2025-07-17 | the dedicated **Costume Gacha** page for Red Flavor ran on 2025-07-17 (the Boom! The Ghost! update) — same base-debt pattern |
| 7 | c016_02 | 2025-01-01 | 2025-04-19 | the **2025 Popularity Poll winner costume** (Poll III, top 1 = Rapi: Red Hood) — "distributed across all servers for free", results revealed at the 2.5th-anniversary livestream on 2025-04-19 (no dedicated costume page; the date is the documented announcement/distribution date) |
| 8 | c016_03 | 2025-01-01 | 2026-05-01 | the **May 2026** MP premium (module S43; `mp_costumes.json` S43 = Rapi: Red Hood (Shining Light)) |
| 9 | smol_ade | 2025-01-30 | 2024-02-05 | the model first shipped with the **Perfect Maid** minigame (update log 2024-02-07: "Added Smol Maid Privaty and Smol Ade from the Perfect Maid Minigame") — the 2025-01-30 value was the later Pirate Cafe batch it reappears in |
| 10 | smol_mpriv | 2025-01-30 | 2024-02-05 | as row 9 — the log's same 2024-02-07 entry names "Smol Maid Privaty" from the Perfect Maid Minigame (the model slid into this bucket's range only after the row 9 correction shifted the rows) |
| 11 | c180_01 | 2023-12-28 | 2024-01-01 | the **January** MP premium (module S15; `mp_costumes.json` S15 = Guillotine (Dark Tracer)) — the recorded value was the NYNS announcing update |
| 12 | c430_02 | 2023-12-28 | 2024-01-01 | its Costume Gacha opened at **New Year's midnight** (NYNS page: "Midnight, January 1st to 5:00 January 18th") — the recorded value was the event start |
| 13 | c225_01 | 2024-01-01 | 2024-10-31 | the dedicated **Costume Gacha** page for Longing Flower ran on 2024-10-31 (the Old Tales update) — the variant had inherited the character's debut date |
| 14 | c382_01 | 2024-01-11 | 2024-09-01 | the **September** MP premium (module S23; `mp_costumes.json` S23 = Leona (Zoo Keeper)) — the recorded value was the character's debut |

## Result

50/50 **rows covered** (this bucket's planned set — see the
partition-restoration note below), **14 ids corrected** — the largest
correction count so far (14 rows in the Corrections table; rows 11–14
are the four gap-row ids that now sit in BUCKET_07's table, corrected
in this pass and listed here). Breakdown: 6 monthly
MP premiums / NY-pass premiums (Corrections rows 1–4, 11 and 14 — the
pattern at fifteen instances), 3 **base-debt inheritances on the Rapi:
Red Hood block** (Corrections rows 6–8: all three of the character's
launch-era costume variants were later-obtained — a 2025 gacha, the
2025 poll reward, and the May 2026 MP — so the block's 2025-01-01 date
applied only to the character and its ×4 rigs), 4 gacha corrections for
other variants (Corrections rows 5–6, 12–13, incl. the New Year's
midnight gacha of row 12), and 2 **earlier-debut corrections**
(Corrections rows 9 and 10: Smol Ade and Smol Maid Privaty are from the
2024 Perfect Maid minigame — the Smol models the viewer log explicitly
dates before the 2025 batch). Everything else is documented by wiki
releaseDates / event pages fetched live this pass (Grave, Flora, Mana,
Rapi: Red Hood; Ice Dragon Saga's Ark Mage Pass; Romantic Valentine's
Backstreet Maid Pass + the Pirate Cafe minigame), the Poll III page +
official poll site (the c016_02 row), the module obtain table, `mp_costumes.json`,
or prior-pass RESEARCH.md rows (c996/c988/c991/c9032/c973/favorites/
Rapi ×4).

**Pattern notes (new this pass):** (1) the **Popularity Poll** reward
date is not the poll's page date — the 2023 winner costume landed via a
dedicated commemorative *quest event* ("First Affection", 2023-08-24),
the 2024 one was a pre-poll gacha (Nonsense Red, 2023-11-01), and the
2025 one is a free distribution dated to the results livestream
(2025-04-19); each poll must be resolved individually. (2) **Smol models
ship with minigames** — the viewer log is the arbiter of which minigame
batch a given Smol belongs to. (3) A character's **launch-era costume
variants are not necessarily launch-era** — Rapi: Red Hood's three
variants span 2025-04 → 2026-05.

**One judgment call to flag for review:** c016_02 uses the
2025-04-19 livestream date because no wiki costume page or gacha page
exists for Cherished Red; if a later distribution date surfaces (e.g. a
2025-04-29 update tie-in), that row should be re-checked.

**Partition restoration (post-pass):** the ten rows of this table that
belong to BUCKET_10's planned set (piratecafe,
smol_emilia/liter/mary/mast/mast_pirate/mpriv/pepper/ram/rapi) now sit
in BUCKET_10's table — verified here, moved in the restoration; the
nine BUCKET_09 rows verified in BUCKET_08 (c226, c231_01, c511,
c511_01, c562, c979, c980, c983, lifeagain) moved back from
BUCKET_08's table; the six borrowed copies (c043_01, c989, c990,
c991, c992, c994) were dropped (BUCKET_03/04/07 own them). The former
"Gap rows" side table (10 rows, all BUCKET_07's planned set) was
removed — those rows now sit in BUCKET_07's table.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 14 date corrections (c431_01, c390_01,
      c391_01, c501_01, c354_01, c016_01, c016_02, c016_03, smol_ade,
      smol_mpriv, c180_01, c430_02, c225_01, c382_01)
- [x] evidence paths point at files actually in `/tmp`
- [x] 57/57 rows covered: the 50 extracted at pass start + the seven
      that slid into the range, plus the ten gap rows verified via the
      global coverage check (40 rows in BUCKET_15)
