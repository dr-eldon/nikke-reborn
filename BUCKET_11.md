# BUCKET_11 — entries 501–550 (`unbreakablesphere` … `c9002`, 2025-04-24 → 2025-11-20)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Wiki (live fetches this pass, `research2/b11_*.json`): character pages
  with `releaseDate` — EVE (12 june 2025), Lily (12 june 2025), Raven
  (**19 june 2025** — the second wave of the Memories Teller collab),
  Sora (3 july 2025), Dorothy: Serendipity (17 july 2025); NPC pages —
  Sky and Cielo (both "debut = **Over the Horizon (event)**", members
  of the Over the Horizon Squad). (The "Adam" page does not exist — c853
  is a side character of the collab, dated by its debut event.)
- Event pages (live fetches this pass):
  - **Memories Teller** (startDate June 12th, 2025 — the Stellar Blade
    collab, 53rd story event): "====New Limited SSR 'Nikkes': [[EVE]]
    and [[Raven]]==== * EVE: End of maintenance to 4:59 July ~~3rd~~
    10th * Raven: 5:00 June 15th to 5:00 July 10th"; "===Costume
    Gachas: Racer's High and Skin Suit=== * Racer's High (Scarlet) -
    **End of maintenance** to 4:59 July 3rd * Skin Suit (EVE) -
    **5:00 June 19th** to 5:00 July ~~3rd~~ 10th"; "===Neurolink Pass===
    * End of maintenance to 5:00 July 3rd … premium track offers the
    costume 'Neurolink Suit' for EVE"; "===Midsummer Pass=== *
    **5:00 June 19th** to 5:00 July 10th … premium track offers the
    costume 'Midsummer Alice' for Raven"; "===Story II=== Part II of the
    story and its stages will be unlocked at **5:00 June 19th**";
    "===Collab Missions - Request List=== … Challenge Missions cleared
    by acquiring at least one copy of each collab SSR grants the
    costumes 'Keyhole Dress' for EVE and 'Planet Diving Suit (6th) V2'
    for Raven" (the gate includes **Raven, obtainable only from
    2025-06-19** — so the challenge rewards are first obtainable on the
    second wave, 06-19).
  - **Over the Horizon** (startDate July 3rd, 2025): "=== **Hidden
    Summer Pass** === A Mission Pass associated with the OuTeR:
    Automata rerun. Purchasing the premium track offers the costume
    'YoRHa Unofficial Waterfront Gear I' for 2B"; "=== 21-Day Login
    Event - **Silent Oasis** === … including the costume 'YoRHa
    Unofficial Waterfront Gear Prototype' for A2"; "=== 1-Day Login
    Event - **Blooming Letter** === Log in to the game any day from the
    end of maintenance to 5:00 July 31st … 10 Standard Recruit Vouchers
    and the costume 'Destined in Blue' for Privaty".
  - **Boom! The Ghost!** (startDate July 17th, 2025): "====Limited SSR
    Nikkes: [[Dorothy: Serendipity]] and [[Elegg: Boom and Shock]]====
    * Dorothy: Serendipity - End of maintenance to 5:00 August 7th *
    **Elegg: Boom and Shock - 5:00 July 24th** to 5:00 August 14th";
    "===Survivor Pass=== … premium track includes the costume 'Sunblaze'
    for Tove"; "===Favorite Item Update=== After maintenance, Favorite
    Items will be available for **Poli, Julia, Bay, and Tove**".
- Module:NikkeCostume/data (`research2/b07y_datamod.json`): Centi
  "Ocean Repair — **Mission Pass Season 33**", Julia "Summer Romance —
  **Mission Pass Season 34**", Scarlet "Racer's High — Costume Gacha",
  EVE "Keyhole Dress — Request List Mission challenge" / "Neurolink
  Suit — Neuro Link Pass" / "Skin Suit — Costume Gacha", Raven
  "Planet Diving Suit (6th) V2 — Request List Mission challenge" /
  "Midsummer Alice — Midsummer Alice Pass", 2B "YoRHa Unofficial
  Waterfront Gear I — Hidden Summer Pass", A2 "YoRHa Unofficial
  Waterfront Gear Prototype — Silent Oasis login reward", Privaty
  "Destined in Blue — Blooming Letter bundle", Tove "Sunblaze —
  Survivor Pass", Elegg: Boom and Shock (a distinct SSR, obtain
  "Recruitment").
- MP-season file `/tmp/mp_costumes.json`: **S33 = Centi (Ocean Repair),
  start 2025-07-01**; **S34 = Julia (Summer Romance), start 2025-08-01**.
- `research/ev_dates.json`: memories teller 2025-06-12, over the
  horizon 2025-07-03, boom! the ghost! 2025-07-17.
- Viewer update log `research2/updateLog.json`: 2025-06-01 "K blanc
  noir moran lord for justice"; 2025-06-14 "Updated the name of
  Privaty (CN) to Privaty Destined in Blue. Added Centi & Scarlet skins.
  Added Eve, Raven, Lily, Adam, Com and the respective skins" (the
  2025-06-12 client — the Raven/Com models were staged there ahead of
  the 06-19 wave); 2025-06-28 "Added Hermin. Added both memories teller
  event scenes."; 2025-06-29 "Added Dorothy and Modernia skins exclusive
  to Chinese server"; 2025-07-05 "Added Sora, Sky, Cielo, 2b'skin
  a2'skin. Added Over the Horizon scene"; 2025-07-17 "Added Tove and
  rapipi skins, added summer elegg and dorothy. **Added the 8 ghosts
  from summer event**"; 2025-07-25 "Added the 4 new favorites with
  merged animation" (the 07-17 client, late pickup) + the layer-editor
  fix entry that names "Elegg Boom and Shock"; 2025-07-31 "Added Boom
  the Ghost event scene."
- Prior-pass files: RESEARCH.md (c9xx rows — "c931_01 Com — 2023-04-27 ⇒
  **2025-06-12** (Stellar Blade collab model (Collection-Robot variant);
  Nikke-db 2025-06-14 added it with Eve/Raven/Lily/Adam)", "c998 Hermin
  also debuted with Memories Teller", "c9000/c9001 Ghost family = Boom!
  The Ghost! **2025-07-17**"; CN rows — "c233_80 Dorothy (CN) 宴桃源
  **2025-06-20** — CN 4.0.1 notes … Nikke-db 2025-06-29 = the CN 4.0.1
  client 9 days later", "c260_80 Modernia (CN) **2025-06-20** — same
  Nikke-db 2025-06-29 entry ⇒ same CN 4.0.1 client"), the wiki Event
  list page 2025 table parsed in BUCKET_10 (Memories Teller 2025-06-12,
  Over the Horizon 2025-07-03, Boom! The Ghost! 2025-07-17), and
  BUCKET_10 (rows 1–7 and 50 of this bucket).

## Table
| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | unbreakablesphere | Unbreakable Sphere | 2025-04-24 | wiki "Unbreakable Sphere" event page (live): startDate April 24th, 2025 (the 54th story event, the 2.5th anniversary); `ev_dates.json`: unbreakable sphere = 2025-04-24; update log 2025-05-02 "Added Unbreakable Sphere album" | confirmed |
| 2 | arcanearchive | Arcane Archive | 2025-05-15 | wiki "Arcane Archive" event page (live): startDate May 15th, 2025; `ev_dates.json`: arcane archive = 2025-05-15; update log 2025-05-18 "Added Arcana and Arcane Archive scene" | confirmed |
| 3 | c581 | Arcana | 2025-05-15 | wiki "Arcana" page (live): `releaseDate = 15 may 2025` (the Arcane Archive character); `ev_dates.json`: arcana = 2025-05-15 | confirmed |
| 4 | c041 | K | 2025-05-29 | wiki "K" page (live): `releaseDate = 29 may 2025` (the Lord, for Justice character — wiki Event list page 2025 table: "Lord, for Justice \| 29 may 2025"; update log 2025-06-01 "K blanc noir moran lord for justice") | confirmed |
| 5 | c082_80 | Liter (CN) | 2025-05-29 | RESEARCH.md CN row: "c082_80 Liter (CN) — **2025-05-29** — Nikke-db 2025-06-02 'liter chinese skin' ⇒ global 2025-05-29 update (the row's event label 'Blank Ticket' is a misnomer — that update's event is Lord, for Justice; the date stands)"; update log 2025-06-02 "Added liter chinese skin" | confirmed (previous pass) |
| 6 | c270_02 | Blanc No. 77 Batter | 2025-05-29 | module: Blanc "No. 77 Batter — **Base Ball Pass**" (the event-exclusive pass of the 2025-05-29 Lord, for Justice update — the baseball-themed event) | confirmed |
| 7 | c271_02 | Noir Baseball Cheerleader | 2025-05-29 | module: Noir "Baseball Cheerleader — **Home In! login reward**" (the 2025-05-29 update's login event) | confirmed |
| 8 | lordforjustice | Lord For Justice | 2025-05-29 | the story cutscene models of the Lord, for Justice event — wiki Event list page 2025 table: "Lord, for Justice \| 29 may 2025"; update log 2025-06-01 "K blanc noir moran lord for justice" | confirmed |
| 9 | c222_01 | Scarlet Racer's High | 2025-06-12 | module: Scarlet "Racer's High — Costume Gacha"; wiki "Memories Teller" page (live): "===Costume Gachas: Racer's High and Skin Suit=== * Racer's High (Scarlet) - **End of maintenance** to 4:59 July 3rd (UTC+9)" — the gacha opened with the 2025-06-12 update; update log 2025-06-14 "Added Centi & Scarlet skins" (the 06-12 client) | confirmed |
| 10 | c850 | EVE | 2025-06-12 | wiki "EVE" page (live): `releaseDate = 12 june 2025` ("a playable SSR otherworlder from Stellar Blade" — the Memories Teller collab); the event page: "EVE: End of maintenance to 4:59 July 10th" (the gacha opened with the 06-12 update); update log 2025-06-14 "Added Eve …" | confirmed |
| 11 | c850_02 | EVE Neurolink Suit | 2025-06-12 | module: EVE "Neurolink Suit — Neuro Link Pass"; wiki "Memories Teller" page (live): "===Neurolink Pass=== * **End of maintenance** to 5:00 July 3rd … premium track offers the costume 'Neurolink Suit' for EVE" (the 06-12 update's event pass) | confirmed |
| 12 | c852 | Lily | 2025-06-12 | wiki "Lily" page (live): `releaseDate = 12 june 2025` (the collab SR — "Clearing Stages II-12N and II-15H will grant a copy of Lily"); update log 2025-06-14 "Added … Lily …" | confirmed |
| 13 | c853 | Adam | 2025-06-12 | a side character of the Memories Teller (Stellar Blade) collab — no wiki page exists (live lookup: page doesn't exist); debut event Memories Teller = 2025-06-12 (event page startDate); update log 2025-06-14 "Added … Adam …" (the 06-12 client) | confirmed |
| 14 | c931_01 | Com | 2025-06-12 | RESEARCH.md c9xx row (previous pass, correction already applied): "c931_01 Com — 2023-04-27 ⇒ **2025-06-12** — Stellar Blade collab model (Collection-Robot variant); Nikke-db 2025-06-14 added it with Eve/Raven/Lily/Adam (Memories Teller 2025-06-12)"; update log 2025-06-14 "Added … Com …" | confirmed (previous pass) |
| 15 | c998 | Hermin | 2025-06-12 | RESEARCH.md c9xx note (previous pass): "c998 Hermin also debuted with Memories Teller" (2025-06-12); update log 2025-06-28 "Added Hermin" (late pickup of the 06-12 client) | confirmed (previous pass) |
| 16 | memoriesteller_1 | Memories Teller 1 | 2025-06-12 | the story cutscene models of the Memories Teller event — event page (live): startDate June 12th, 2025; `ev_dates.json`: memories teller = 2025-06-12; update log 2025-06-28 "Added both memories teller event scenes" | confirmed |
| 17 | memoriesteller_2 | Memories Teller 2 | 2025-06-12 | as the memoriesteller_1 row | confirmed |
| 18 | c850_01 | EVE Keyhole Dress | 2025-06-19 | module: EVE "Keyhole Dress — **Request List Mission challenge**"; wiki "Memories Teller" page (live): the Request List challenge missions "cleared by acquiring at least one copy of **each collab SSR** grants the costumes 'Keyhole Dress' for EVE and 'Planet Diving Suit (6th) V2' for Raven" — the gate requires Raven, obtainable only from the **2025-06-19** second wave (event page: "Raven: 5:00 June … to 5:00 July 10th", wiki Raven releaseDate 19 june 2025, "Story II … unlocked at 5:00 June 19th"); the model was staged in the 06-12 client (update log 2025-06-14 "the respective skins") | confirmed |
| 19 | c850_03 | EVE Skin Suit | 2025-06-19 | module: EVE "Skin Suit — Costume Gacha"; wiki "Memories Teller" page (live): "Skin Suit (EVE) - **5:00 June 19th** to 5:00 July ~~3rd~~ 10th (UTC+9)" — the gacha opened with the 06-19 second wave | confirmed |
| 20 | c851 | Raven | 2025-06-19 | wiki "Raven" page (live): `releaseDate = **19 june 2025**` (the Memories Teller collab's second wave — the event page lists the Raven gacha and the 06-19 "Story II" unlock); update log 2025-06-14 "Added … Raven …" = the model staged in the 06-12 client, obtainable from 06-19 | confirmed |
| 21 | c851_01 | Raven Planet Diving Suit (6th) V2 | 2025-06-19 | module: Raven "Planet Diving Suit (6th) V2 — Request List Mission challenge"; the same Request List gate as the c850_01 row ("acquiring at least one copy of each collab SSR" incl. Raven ⇒ first obtainable 2025-06-19) | confirmed |
| 22 | c851_02 | Raven Midsummer Alice | 2025-06-19 | module: Raven "Midsummer Alice — Midsummer Alice Pass"; wiki "Memories Teller" page (live): "===Midsummer Pass=== * **5:00 June 19th** to 5:00 July 10th … premium track offers the costume 'Midsummer Alice' for Raven" | confirmed |
| 23 | c233_80 | Dorothy (CN) | 2025-06-20 | RESEARCH.md CN row (previous pass): "c233_80 Dorothy (CN) 宴桃源 — **2025-06-20** — CN 4.0.1 notes: '桃乐丝全新时装【宴桃源】正式登场' (CN-exclusive cheongsam, with the 记忆与遗忘/Over-Zone package); Nikke-db 2025-06-29 = the CN 4.0.1 client 9 days later (no global update in that window)"; update log 2025-06-29 "Added Dorothy and Modernia skins exclusive to Chinese server" | confirmed (previous pass) |
| 24 | c260_80 | Modernia (CN) | 2025-06-20 | RESEARCH.md CN row (previous pass): "c260_80 Modernia (CN) — **2025-06-20** — same Nikke-db 2025-06-29 entry ⇒ same CN 4.0.1 client; caveat: the CN notes announced it to players only in 18.2.1 (2026-05-19) — the asset shipped decades earlier in the client" | confirmed (previous pass) |
| 25 | c080_02 | Centi Ocean Repair | 2025-07-01 | **not** a Jun 12 item — module: Centi "Ocean Repair — **Mission Pass Season 33**"; `/tmp/mp_costumes.json` S33 = Centi (Ocean Repair), start **2025-07-01** (the July MP — the model shipped with the 2025-06-12 Memories Teller client per the update log 2025-06-14 "Added Centi & Scarlet skins", but the premium opened with the season, the standard MP pattern) | **corrected** (2025-06-12 → 2025-07-01) |
| 26 | c170_03 | Privaty Destined in Blue | 2025-07-03 | module: Privaty "Destined in Blue — **Blooming Letter bundle**"; wiki "Over the Horizon" page (live): "===1-Day Login Event - **Blooming Letter**=== Log in to the game any day from **the end of maintenance** to 5:00 July 31st … the costume 'Destined in Blue' for Privaty" (the 2025-07-03 update's login event). The update log 2025-06-14 "Updated the name of Privaty (CN) to Privaty Destined in Blue" is the CN-exclusive model staged in the 06-12 client and renamed (the global obtainable is the 07-03 login reward) | confirmed |
| 27 | c530 | Sky | 2025-07-03 | wiki "Sky" NPC page (live): "debut = **Over the Horizon (event)**" (member of the Over the Horizon Squad); the event = 2025-07-03 (event page live; Event list table); update log 2025-07-05 "Added Sora, Sky, Cielo …" | confirmed |
| 28 | c531 | Cielo | 2025-07-03 | wiki "Cielo" NPC page (live): "debut = **Over the Horizon (event)**" (same squad); as the c530 row | confirmed |
| 29 | c532 | Sora | 2025-07-03 | wiki "Sora" page (live): `releaseDate = 3 july 2025` (the Over the Horizon character); update log 2025-07-05 "Added Sora …" | confirmed |
| 30 | c810_03 | 2B YoRHa Unofficial Waterfront Gear I | 2025-07-03 | module: 2B "YoRHa Unofficial Waterfront Gear I — **Hidden Summer Pass**"; wiki "Over the Horizon" page (live): "===Hidden Summer Pass=== A Mission Pass associated with the OuTeR: Automata rerun. Purchasing the premium track offers the costume … for 2B" (the 07-03 update's rerun pass); update log 2025-07-05 "2b'skin" | confirmed |
| 31 | c811_03 | A2 YoRHa Unofficial Waterfront Gear Prototype | 2025-07-03 | module: A2 "YoRHa Unofficial Waterfront Gear Prototype — **Silent Oasis login reward**"; wiki "Over the Horizon" page (live): "===21-Day Login Event - Silent Oasis=== … including the costume … for A2" (the 07-03 update's login event); update log 2025-07-05 "a2'skin" | confirmed |
| 32 | overthehorizon | Over the Horizon | 2025-07-03 | wiki "Over the Horizon (event)" page (live): startDate July 3rd, 2025; `ev_dates.json`: over the horizon = 2025-07-03; update log 2025-07-05 "Added Over the Horizon scene" | confirmed |
| 33 | boomtheghost | Boom the Ghost | 2025-07-17 | the story cutscene models of the Boom! The Ghost! event — event page (live): startDate July 17th, 2025; `ev_dates.json`: boom! the ghost! = 2025-07-17; update log 2025-07-31 "Added Boom the Ghost event scene" | confirmed |
| 34 | c192_02 | Tove Sunblaze | 2025-07-17 | module: Tove "Sunblaze — **Survivor Pass**"; wiki "Boom! The Ghost!" page (live): "===Survivor Pass=== … premium track includes the costume 'Sunblaze' for Tove" (the 07-17 event's pass); update log 2025-07-17 "Added Tove and rapipi skins" | confirmed |
| 35 | c234 | Dorothy: Serendipity | 2025-07-17 | wiki "Dorothy: Serendipity" page (live): `releaseDate = 17 july 2025`; the Boom! The Ghost! page: "Dorothy: Serendipity - **End of maintenance** to 5:00 August 7th" (the gacha opened with the 07-17 update); update log 2025-07-17 "added … dorothy" | confirmed |
| 36 | c9000 | Ghost - Alfred | 2025-07-17 | RESEARCH.md c9xx row: "c9000/c9001 Ghost family = **Boom! The Ghost! 2025-07-17**"; update log 2025-07-17 "Added the 8 ghosts from summer event" (the 07-17 client) | confirmed (previous pass) |
| 37 | c9000_01 | Ghost - Neaty | 2025-07-17 | as the c9000 row (the same Ghost squad of the Boom! The Ghost! event) | confirmed (previous pass) |
| 38 | c9000_02 | Ghost - Sizzly | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 39 | c9000_03 | Ghost - Fixy | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 40 | c9000_05 | Ghost - Detaily | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 41 | c9000_06 | Ghost - Sellsy | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 42 | c9000_07 | Ghost | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 43 | c9001 | Ghost - Pinne | 2025-07-17 | as the c9000 row | confirmed (previous pass) |
| 44 | favorite_c030 | Favorite: Poli | 2025-07-17 | wiki "Boom! The Ghost!" page (live): "===Favorite Item Update=== After maintenance, Favorite Items will be available for **Poli**, Julia, Bay, and Tove" (the 07-17 update's "after maintenance"); update log 2025-07-25 "Added the 4 new favorites with merged animation" (the 07-17 client, late pickup) | confirmed |
| 45 | favorite_c150 | Favorite: Julia | 2025-07-17 | as the favorite_c030 row (same Favorite Item update) | confirmed |
| 46 | favorite_c192 | Favorite: Tove | 2025-07-17 | as the favorite_c030 row | confirmed |
| 47 | favorite_c550 | Favorite: Bay | 2025-07-17 | as the favorite_c030 row | confirmed |
| 48 | c502 | Elegg: Boom and Shock | 2025-07-24 | a distinct SSR (module: data["Elegg: Boom and Shock"], obtain "Recruitment"); wiki "Boom! The Ghost!" page (live): "Elegg: Boom and Shock - **5:00 July 24th** to 5:00 August 14th (UTC+9)" — the gacha opened with the 2025-07-24 update (the week after the 07-17 event update); update log 2025-07-25 names "Elegg Boom and Shock" in the layer-editor fix | confirmed |
| 49 | c150_02 | Julia Summer Romance | 2025-08-01 | **not** a Jul 17 item — module: Julia "Summer Romance — **Mission Pass Season 34**"; `/tmp/mp_costumes.json` S34 = Julia (Summer Romance), start **2025-08-01** (the August MP — the model shipped with the 2025-07-17 Boom! The Ghost! client, the premium opens with the season) | **corrected** (2025-07-17 → 2025-08-01) |
| 50 | c9002 | Nora | 2025-11-20 | **not** a May 29 item: wiki "Nora" NPC page (live): "**debut = [[Blank Ticket]]** … the focus character of the events Blank Ticket and Terminus Ticket"; the wiki "Blank Ticket" event (live): startDate **November 20th, 2025** (→ December 4th, 2025; the 65th story event, Soline: Frost Ticket + Nora); wiki Event list page 2025 table: "Blank Ticket \| 20 november 2025". The recorded 2025-05-29 came from the RESEARCH.md c9xx row's mislabel — that row called the 2025-05-29 update "Blank Ticket", but that update's event is **Lord, for Justice** (wiki Event list page; the old woman NPC in it never became the named character Nora). The viewer picked the model up late (2026-02-14, as "NPC: TBA", named 2026-02-15 — the Lie Cause Recoil batch) | **corrected** (2025-05-29 → 2025-11-20) |
## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c080_02 | 2025-06-12 | 2025-07-01 | the **July** monthly MP premium (module S33; `/tmp/mp_costumes.json` S33 = Centi (Ocean Repair), start 2025-07-01) — the recorded value was the Memories Teller update that shipped the model (the standard MP pattern: model in the client, premium opens with the season) |
| 2 | c150_02 | 2025-07-17 | 2025-08-01 | the **August** monthly MP premium (module S34; `/tmp/mp_costumes.json` S34 = Julia (Summer Romance), start 2025-08-01) — the recorded value was the Boom! The Ghost! update that shipped the model |

## Result

50/50 **reviewed**, **2 ids corrected** (both monthly MP premiums — the
season-start rule — c080_02, c150_02). The rest split: 8 rows (rows
1–7 and 50) hold the full-evidence rows verified in BUCKET_10 — moved
from BUCKET_10's table in the partition restoration; those ids belong
to this bucket's planned set (BUCKET_10's table documented them when
its slice was re-extracted); 9 rows rest on
previous-pass RESEARCH.md rows (Com/Hermin CN-era corrections, the
Ghost family, the two CN 4.0.1 skins); 33 rows are new this pass — the
**Memories Teller collab block** (EVE/Lily/Adam 06-12, the Raven second
wave 06-19, the Racer's High gacha, the Neurolink/Midsummer passes, the
Request List challenge gate) is the bucket's core, documented by the
event page's Version Updates section, which cleanly separates the
06-12 wave (EVE gacha end-of-maintenance, Racer's High gacha, Neurolink
Pass) from the 06-19 wave (Raven gacha, Skin Suit gacha, Midsummer
Pass, Story II unlock) — the two-wave structure is what pins the
challenge-costume dates (c850_01, c851_01): the Request List rewards require
"at least one copy of each collab SSR", and Raven is only obtainable
from 06-19. The **Over the Horizon block** (Sky/Cielo NPCs, Sora, the
2B/A2 OuTeR-rerun pass + login costume, the Blooming Letter login
reward) and the **Boom! The Ghost! block** (Dorothy: Serendipity, the
Elegg: Boom and Shock 07-24 gacha, Tove Sunblaze, the 4 new Favorites,
the Ghost squad) round it out.

**Pattern notes (new this pass):** (1) **collab events can ship in two
waves a week apart** — Memories Teller's Story II + Raven + the
second-wave gacha/pass opened at 5:00 June 19th, one week after the
event start; costume models are staged in the first client (the viewer
picked them up 06-14) but are first obtainable on the wave date.
(2) **the MP premium pattern now has 20 confirmed instances** (S15–S43
minus the gaps, plus S33/S34 here) — every "Mission Pass Season N"
module obtain maps to `mp_costumes.json` season start. (3) **challenge
missions can gate on future characters** — a costume reward is dated to
the moment its acquisition condition is satisfiable, not the event
start.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 2 date corrections (c080_02 → 2025-07-01,
      c150_02 → 2025-08-01)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered
