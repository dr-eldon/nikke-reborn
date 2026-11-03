# RESEARCH.md — `date` field for `database/models.json`

Goal: give every entry of `database/models.json` (740 models — the viewer's
full client dump: playable NIKKEs, their skins/variants, event CGs, story
cutscenes, Rapture bosses, minor characters, collab models, minigame models)
a `date` field (`YYYY-MM-DD`) — the date the model first shipped in the
client it released in. Every one of the 740 entries is dated; the eight
CN-exclusive rows (never released to International players) are dated to
the CN client update that shipped them — or to the global client update,
where Shift Up shipped the CN asset there first — and are documented
under **CN-exclusive models**.

Semantics per model kind:

| Kind | `date` means |
|---|---|
| base character `c###` | its recruitment release date (`characters.json`) |
| variant `c###_##` | the date that costume/skin flavor first became obtainable (gacha first appearance, mission pass, event, cash shop, or the parent skin's date for same-skin flavors); CN-exclusive variants: the update that first shipped the model in the client it released in (see **CN-exclusive models**) |
| event CG (`bluewaterisland`, `777`, …) | the start date of the event that shipped the CG |
| story cutscene (`storyXXXX`) | the release date of the story chapter it belongs to (chapter = first two digits; scene = last two) |
| Rapture boss (`bba001`, `mbg001`, …) | the date the chapter/event that introduced the Rapture released |
| minor character (`c9##`) | the date of the chapter/event/side story of its debut |
| minigame model (`smol_*`, `azxservicetime_*`, `piratecafe`, `ce009_*`) | the date the minigame shipped |
| collection model (`favorite_c###`) | the date the Favorite-Items feature content shipped |

Variant dating rule for mid-event banners: when a character's banner opens
mid-event (multi-week collabs), the variant dates align with the gating
mechanic, not the event start:

- costume **gacha** (open from event start, e.g. 2B's `YoRHa Uniform 1`,
  Asuka's `Test Plugsuit`, Rem's collab gacha) → **event start**;
- **mission-pass premiums** and **challenge missions** → the date their
  gate opens: the carrier's banner date when the pass/challenge is scoped
  to that banner week (YoRHa Pass ran 9/8–9/28 with A2's banner; the
  Memories Teller challenge "own each collab SSR" required both EVE and
  Raven, so both gated costumes date to Raven's 2025-06-19 banner), the
  banner week for per-banner MP premiums (Evangelion waves), or the
  carrier's earlier banner date when the challenge says "by recruiting X"
  (c820_01 Handy Maid = Rem's 2024-03-28 banner, gacha opened 2024-03-21).

This keeps variant ≥ base except where a costume gacha provably opened at
event start before the carrier's banner (c830_03, c820_02) or the variant
is an older rig than the current one (c570_99).

Popularity-Poll winner costumes (`obtain = "20NN Popularity Poll rewards"`):
the poll page date (voting start) is **not** the costume date — resolve each
edition individually: 2023 (Poll I) shipped the winner costume via a
dedicated commemorative quest event ("First Affection", 2023-08-24); 2024
(Poll II) "awarded" a costume already gacha-released pre-poll (Nonsense Red,
2023-11-01); 2025 (Poll III) was a free all-servers distribution dated to the
results livestream (2025-04-19, no dedicated costume page). Voting runs
~April 8–14 each year (commemorating the anniversary); results are revealed
at the anniversary livestream.

## Sources

Local (already in the repo):

- `database/characters.json` — 311 base-model entries, all carry `release_date` (ISO; verified against wiki infoboxes 2026-10-24 per `cards/PLAN.md`).
- `database/banners.json` — GLOBAL banner history (lootandwaifus, fetched 2025-10-21): per-banner `start`/`end`, `nikke` = viewer id without the `c` prefix, `rerun` flag. First appearance = earliest `start` per `nikke`.
- `cards/PLAN.md` — pack plan; key facts: the model dump is a full client dump (presence ≠ release); Endless (c371) is a deceased story NPC, not a playable NIKKE. (Its "Denji/Aki/9S/Adam unreleased" and the 2024-06-02 favorite date are wrong — see Findings.)

Wiki (`nikke-goddess-of-victory-international.fandom.com`, API + cached pages in
`/tmp` from an earlier pass):

- Events page (cached `/tmp/event_page.txt`, parsed `/tmp/wiki_events.json`,
  **408 events with start/end UTC+9 — authoritative** for event dates) and
  `/tmp/event_dates.json` (239), `/tmp/research/ev_dates.json` (348
  normalized-title → date; superseded by `/tmp/wiki_events.json` where they
  conflict).
- Costumes page (cached `/tmp/research2/p_Costumes.txt`; also
  `/tmp/costumes_page.txt`) — every costume grouped by **series** (the
  listing order within a series is roughly chronological — used to bracket
  the undated Halcyon Days cash-shop costumes before `Coat Off` 2023-02-22).
- Module:NikkeCostume data (cached `/tmp/nikkcostume_data.txt`, parsed
  `/tmp/research/wiki_costume_module.json`, 212 characters; live re-fetch
  of the full data module at `/tmp/research2/b07y_datamod.json` —
  `Module:NikkeCostume/data`, all costumes) — per-costume `obtain` strings
  (vocabulary: `Mission Pass Season N` — numbering verified 1:1 against
  `mp_costumes.json`, `Cash Shop`, specific pass names, login-event names,
  `Closed Beta gift`, `Recruitment`, …). Settles any variant whose
  nikke.gg flag is a bare "missionpass".
- Mission pass seasons (cached `/tmp/mp_costumes.json`, 49 seasons with start
  dates). Season start = first of the month; season 35 = 2025-09-01, 37 =
  2025-11-01, 41 = 2026-03-01, 45 = 2026-07-01 (verified in-file).
- Gacha first appearances (cached `/tmp/research/gacha_dates.json`, 42 rows — some gachas appear twice: first run + re-run; first appearance = earliest `start`).
- Chapter list: `Template:Navbox Story Chapters` (51 main chapters 00–50 + 6 side stories + 1 commission) — fetched to `/tmp/research2/navbox_story_chapters.txt`.
- Chapter pages (cached `/tmp/ch_*.txt`) and their *Character Appearances* tables (debut markers).
- Minor characters pages (cached `/tmp/research/p_Minor_characters_*.txt`,
  `/tmp/research2/minor_*.txt`) → parsed debut maps
  `/tmp/research/minor_debuts.json` (239), `minor_debuts2.json` (116),
  `/tmp/research2/minor_debuts_all.json` (105 name → debut line).
- Rapture page + class tables (cached `/tmp/rapture.txt`, `/tmp/tpl_Rapture*Table.txt`, per-Rapture pages `/tmp/rapture_*.txt`, `/tmp/research/rapt_*.txt`).
- Event pages (cached `/tmp/research/pages/*.txt`) — `Favorite Item`
  sections, `Mission Pass` sections, `Costume Gacha` sections, story text
  (cast verification).
- Soundtrack pages disambiguate minigame CGs (e.g. `AZX: Service Time` → "title song for the AZX: Service Time Minigame", `source = Terminus Ticket`).
- Event list page (cached `/tmp/research2/b08_eventlist.json`) — yearly
  tables of story events with start/end dates; a compact cross-check
  for event dates. **Gotcha:** rowspan rows share an event slot
  (e.g. "Nonsense Red"/"Jinx Player" both start 19 september 2024), so
  naive "logo → next date" parsing misattributes; read the raw rows.

Nikke-db site (github.com/Nikke-db):

- `updateLog.json` (Nikke-db/nikke-db-vue `src/utils/json/updateLog.json`,
  mirror `/tmp/research2/updateLog.json`, 189 entries) — the site's asset
  additions: "Added X" on date D ⇒ model X was in the client by D (entries
  usually land within days of the update). Used as a lower-bound cross-check
  and to identify CN-exclusive assets ("chinese exclusive …", "… exclusive
  to Chinese server").
- Full asset tree fetched to `/tmp/research2/nikkedb_tree.txt`.

Apple App Store (CN):

- `apps.apple.com/cn/app/id6467825646` (《胜利女神：新的希望》) — the page
  is server-rendered and carries the full 版本历史 (version history): 23
  entries, 1.2.6 (2025-01-23) → 22.1.1 (2026-09-29), each with its content
  list (events, characters, costumes, chapters, minigames). Saved to
  `/tmp/research2/cn_version_history.txt` / `cn_entries.json`. Authoritative
  for CN player-facing releases (CN App Store releaseDate = launch
  2025-05-21). Pre-launch beta builds (1.2.6–2.9.1, 2025-01-23 → 05-15)
  carry only placeholder descriptions.
- Dead ends: Fandom has no CN ship dates; nikke.qq.com news is behind an
  opaque gateway; Baidu/Baike/Bing block or return junk; gamekee.com is a
  pure SPA. nikke.gg (DotGG) has a working global costume DB
  (`/tmp/research2/gg_costumes_db.json`, 408 rows, no dates) — useful only
  to cross-check which costumes are global vs CN-exclusive (e.g. it proves
  Privaty "Destined in Blue" is the INT c170_03, not the CN skin).

Character-page revision history (Fandom API): for the undated
cash-shop/login costumes, the first revision of the character page containing
the costume name ≈ its release date (the wiki documents new costumes shortly
after they ship). Character pages are rolling (created 2021–2022, updated
continuously), unlike the batch-created chapter pages.

Earlier pass (kept as-is, used as a starting point):

- `/tmp/research/stage2.json` — 740 rows `{id, name, date, source}`; 293 dated (characters.json 310, skin flavors 12, ~50 event CGs, Memories Teller ×2), 447 open.
- `/tmp/research/variants.json` (194 `c###_##` → char/costume names), `named_page_map.json` (69 model id → wiki page), `resolved_titles.json` (175), `chapter_numbers.json` (32 chapter names → numbers), `storymodel_debuts.json` (38 model → debut chapter), `costume_event_map.json` (17), `costume_records.json` (98), `page_dates.json` (77), `event_dates_full.json` (94), `version_updates.json` (9), `fetch_events.py` (the fetcher; API works).
- `/tmp/research2/variant_match1.json` — 127/179 variant dates auto-resolved from event-page costume announcements.

## Working method

- Dates are the event/chapter/banner **start** dates (UTC+9, as the wiki lists them).
- For re-run gachas/banners the first-appearance date is used (models shipped once).
- Chapter dates: where no update record exists, the chapter page's first
  wiki revision is used as the proxy (pages are created on release) — marked
  `(wiki first rev)` in the tables below.
- Everything is kept in `/tmp/research2/` (assembly scripts + fetched data);
  the final step writes `date` into `database/models.json`.
- Model IDs are **not** in ship order (e.g. c9032 Jien shipped 2025-01-16,
  c9029–c9031 shipped 2026-07-23) — never infer dates from ID proximity.

## Findings

### Chapter release dates (main story)

Each campaign update (event start) adds chapters; the chapter dates below come
from the `===Campaign Update===` section of the event pages (cached in
`/tmp/research/pages/`, parsed in `/tmp/research2/event_chapters.json`).
Launch shipped chapters 00–16 (Hightech Toy added 17–18 two weeks later, and
D-Outsiders added 19–20, so everything below 17 shipped at launch).

| Chapters | Name(s) | Update (event start) |
|---|---|---|
| 00–16 | Fall … Brand | launch **2022-11-04** |
| 17–18 | Purpose, Hero | Hightech Toy **2022-11-24** |
| 14–15 *(CGs only)* | Journey, Luck | D-Outsiders **2023-01-12** ("CGs added to Chapters 14 and 15") |
| 19–20 | Eden, Flame Dragon | D-Outsiders **2023-01-12** |
| 21–22 | Giant Whale, Invasion | Over Zone **2023-04-27** ("and associated story cutscenes") |
| 23–24 | Prison, Banishment | Golden Ship **2023-07-20** |
| 25–26 | Tracking, Return | Red Ash **2023-11-02** |
| 27–28 | Exploration, The Unknown | BOOM's Day **2024-02-22** |
| 29–30 | Rescue, Treasure | Last Kingdom **2024-04-25** |
| 31–32 | Mabeast, Advance | Juvenile Days **2024-07-25** |
| 33–34 | Clash, Inheritance | Old Tales **2024-10-31** |
| 35–36 | Conversation, Betrayal | Second Quest **2025-02-20** |
| 37–38 | Struggle, Gluttony | Unbreakable Sphere **2025-04-24** |
| 39–40 | Gene, Choice | ABSOLUTE **2025-08-07** |
| 41–42 | Birth, Only One | Goddess Fall **2025-10-30** |
| 43–44 | Key, Path | Lie cause Recoil **2026-02-12** |
| 45–46 | The Price of Sin, Rebirth | Star Anis **2026-04-23** |
| 47–48 | Outbreak, Reborn | Persona on Frontline **2026-08-12** |
| 49–50 | Final Battle, Ascension | MARIA-n **2026-10-29** |

Caveat: the wiki chapter pages' first revisions are *batch page creations*
(e.g. all of ch 00–05 on 2023-07-19), not release dates — do not use them.

### Side story release dates

From each side chapter page ("released with the X update"):

| Side chapter | Update | Date |
|---|---|---|
| Second Affection | One More Time | 2024-04-11 |
| Wordless | Life Again | 2024-10-17 |
| Mudfish | True Flavor | 2025-04-10 |
| Eden Spear | Go! Ninja Thief! | 2025-10-16 |
| Pretty Star | Good World | 2026-04-09 |
| Gingerbread House | Little Witch Trick | 2026-10-08 |

### Story cutscene models (`storyXXXX`)

`story{CC}{SS}` = main-story chapter CC, cutscene SS (the model names agree:
`story1902` is "Story 19-01", `story2002` is "Story 20-01"). Date = the
chapter's release (table above). `story0401_3` "Story 04-02 (CN)" is the
Chinese version of chapter 4's scene 02 — **CN-exclusive**; shipped in the
global client with the 2025-04-01 update (Nikke-db log 2025-04-21: "Added
the Mustang Chinese story scene from chapter 4") → **2025-04-01**, see
**CN-exclusive models**.

### Event CG models

- The client's CG slugs match event names (`bluewaterisland`, `redash1/2`,
  `twoxtwo1/2`, …). The Nikke-db site (github.com/Nikke-db/Nikke-db.github.io,
  full asset tree fetched to `/tmp/research2/nikkedb_tree.txt`) confirms the
  ambiguous ones:
  - `777` → `l2d/777/EventScene_BunnyX777_01.png`, gallery
    `EventTitle_BunnyX777_01.png` → **Bunny X 777** (2023-05-18). "777" is
    Rouge's Tetra squad, not a character.
  - `whitememory1/2` → "White Memory" is the **Over Zone** minigame/CG
    (Over Zone/White Memory/Story Dialogue on the wiki) → **2023-04-27**.
  - `aegisthediver` → "Aegis the Diver" is the minigame of the **Beauty Full
    Shot** event (wiki Events-page mini-game table; the "Aegis the Diver"
    article is missing) → **2024-07-04**.
  - `evangelion` → scene files `EventScene_ce004_*` = collab event #4 = the
    first Evangelion collab (You Can (Not) Evade) → **2024-08-21** (event
    start; Nikke-db log "evangelion patch" added 2024-08-21; Asuka's banner
    opened 2024-08-22). The 2nd wave was "Second Quest" (2025-02-20), the
    5th collab event.
  - `dazzlingcupid_tia/naga` → **Dazzling Cupid** 2023-10-05.
  - `twoxtwo1/2` → **2x2 Love** 2026-03-19.
- The mini-game table on the wiki Events page (cached `/tmp/event_page.txt`)
  maps minigames to events: Pirate Cafe → Romantic Valentine, AZX Service
  Time → Terminus Ticket, Aegis the Diver → Beauty Full Shot, White Memory →
  Over Zone, etc.

### Minigame / collab model groups

- `smol_*` (except the six "TTS" ones) + `piratecafe` → the **Pirate Cafe**
  minigame, part of the **Romantic Valentine** event → **2025-01-30**.
- `smol_anis`, `smol_mint`, `smol_prika` (chibi TTS models) → **Star Anis**
  update **2026-04-23** (Nikke-db log: "Chibi Anis, Prika and Mint TTS" added
  2026-04-25).
- `smol_naga`, `smol_tia`, `smol_marciana` (chibi TTS) → **Project Matis**
  update **2026-07-23** (Nikke-db log: "TTS naga/tia/marciana" added
  2026-07-27).
- `azxservicetime_1..9` → **Terminus Ticket** **2025-12-04** (soundtrack page:
  "title song for the AZX: Service Time Minigame", source = Terminus Ticket;
  event runs 2025-12-04 → 12-30).
- `ce009_*` (12 smol models: Persona collab cast + smol enemies + skill
  chibis) → **Persona on Frontline** **2026-08-12** (collab event #9;
  Nikke-db log added them 2026-09-27 after the event).
- The collab events are numbered `ce00N`: ce001 = BULLET X CHAINSAW
  (2023-02-22), ce004 = Evangelion I / You Can (Not) Evade (2024-08-21),
  ce005 = EVANGELION: Second Quest (2025-02-20), ce009 = Persona on
  Frontline (2026-08-12).

### Favorite-Item groups (`favorite_c###`, 13 models)

From the `Favorite Item` sections of the event pages:

| Nikkes | Update | Date |
|---|---|---|
| Laplace, Exia, Frima, Diesel | Golden Coin Rush — "Collection Item System Implementation": "For the initial release, Laplace, Exia, Frima, and Diesel will have Favorite Items" | **2024-05-30** |
| Viper | Beauty Full Shot | **2024-07-04** |
| Helm, Miranda, Drake, Milk | Wisdom Spring | **2025-01-16** |
| Poli, Julia, Bay, Tove | Boom! The Ghost! ("1000 days of Nikke" login event) | **2025-07-17** |

Corrections to earlier notes: Golden Coin Rush is **2024-05-30** (not
2023-12-08 — that date was the NEVERLAND update; the 2024-06-02 in
PLAN.md is wrong too), Wisdom Spring is **2025-01-16** (not 2024-05-16),
and the Poli/Julia/Bay/Tove favorites shipped with **Boom! The Ghost!**
2025-07-17 (Nikke-db log: "Added the 4 new favorites with merged animation"
2025-07-25), not 2025-09-04.

### Costume (variant) dates resolved this pass

Mission-pass season premiums (date = season start, first of the month):

| Model | Costume | Source | Date |
|---|---|---|---|
| c210_03 Exia | Hacker Rabbit | Mission Pass Season 35 (ABSOLUTE: "refreshed on the first day of September") | **2025-09-01** |
| c513_02 Little Mermaid | Beautiful Bubble | Mission Pass Season 37 | **2025-11-01** |
| c390_02 Zwei | Spring Stroll | Mission Pass Season 41 | **2026-03-01** |
| c450_03 Naga | Ring Ensemble | Mission Pass Season 45 | **2026-07-01** |

Event passes / challenges / one-off gachas:

| Model | Costume | Source | Date |
|---|---|---|---|
| c330_02 Crown | Glorious Flower | Glorious Flower Pass, Goddess Fall | **2025-10-30** |
| c113_01 E.H. | Junkyard Vanguard | Junkyard Pass, Ark Ranger | **2026-06-11** |
| c800_01 Makima | Coat Off | BULLET X CHAINSAW mission challenge | **2023-02-22** |
| c830_03 Asuka | Test Plugsuit | Collab Costume Gacha, You Can (Not) Evade (rerun in Second Quest) | **2024-08-21** |
| c010_02 Rapi | White Promise | "Closed Beta gift" (White Promise series) — shipped in the launch client | **2022-11-04** |
| c030_02 Poli | Cheer Up Police | "Cheer Up Spring! (2024) login reward"; Nikke-db added it 2024-04-06 → 2024-04-01 update (Liar's End) | **2024-04-01** |

Collab costume waves (see rule at top for mid-event banners):

- **Evangelion I** (You Can (Not) Evade, 2024-08-21). Per-character MP
  ("Pilot in Summer Pass") premiums, active during each rate-up week:
  c830_02 Cynical Street **2024-08-22** (Asuka), c831_02 Peaceful Vacation
  **2024-08-29** (Rei), c832_02 Leisure Travel **2024-09-05** (Mari).
- **Evangelion II** (Second Quest, 2025-02-20). Challenge-mission rewards:
  the School Uniform costumes of the wave-1 SSRs (c830_01, c831_01,
  c832_01), "Final Battle: Mari" (c832_03); Passion Canon Pass premiums:
  "Soul Connect" (c834_02), "Mystery Muse" (c832_04) → **2025-02-20**.
  c834_01 "Miss Lookalike from Village-3" also a challenge reward, but its
  carrier (c834 Rei (Tentative Name), banner 2025-02-27) dates both to
  **2025-02-27**. (c836 Sakura is *not* part of this collab — see below.)
- **Resident Evil** (Reborn Evil, 2025-09-24): c840_01 Separate Ways +
  c840_02 Dress (Ada, week 1, "premium track offers the costume 'Dress' for
  Ada Wong") → **2025-09-24**; c841_01 Classic + c841_02 Battle Suit (Jill,
  week 2 banner 2025-10-02) → **2025-10-02**.
- **Lycoris Recoil** (Lie cause Recoil, 2026-02-12): c860_01 + c860_02
  (Chisato, First Lycoris Pass, banner 2026-02-12) → **2026-02-12**; c861_01
  + c861_02 (Takina, Second Lycoris Pass from 2026-02-19, banner 2026-02-19)
  → **2026-02-19**.
- **Persona 3** (Persona on Frontline, 2026-08-12): c870_01 Student Council
  President (challenge) + c870_02 Queen's Pajamas Ver. NIKKE Collabo (Thief
  Queen Pass premium) → **2026-08-13** (Queen banner); c871_01 Amagi Inn
  Kimono (challenge) + c871_02 Winter Roomwear Ver. NIKKE Collabo (Snow
  Flakes Pass premium) → **2026-08-20** (Yukiko banner).

Gating corrections found on final review (the auto-matcher's event-start
dates were wrong for pass/challenge-gated costumes):

| Model | Costume | Gate | Date |
|---|---|---|---|
| c811_01 A2 | Metamorphic Damage | challenge "own A2" (banner 2023-09-08) | **2023-09-08** |
| c811_02 A2 | YoRHa Uniform Prototype | YoRHa Pass ran 9/8–9/28 (A2's banner week) | **2023-09-08** |
| c810_03 2B | YoRHa Unofficial Waterfront Gear I | costume gacha first offered in the OuteR rerun at Over the Horizon | **2025-07-03** |
| c811_03 A2 | YoRHa Unofficial Waterfront Gear Prototype | same rerun (Silent Oasis login bonus) | **2025-07-03** |
| c850_01 EVE | Keyhole Dress | challenge "own each collab SSR" (Raven banner 2025-06-19) | **2025-06-19** |
| c850_03 EVE | Skin Suit | costume gacha ran 6/19–7/10 | **2025-06-19** |
| c851_01 Raven | Planet Diving Suit (6th) V2 | challenge "own each collab SSR" | **2025-06-19** |
| c851_02 Raven | Midsummer Alice | Midsummer Pass ran 6/19–7/10 | **2025-06-19** |

Notes: the Waterfront Gear costumes appear nowhere in the original 2023
event page (its Costumes Update lists only the four originals + Brid) —
they are rerun-exclusive variants, first offered 2025-07-03. c850_02
(EVE Neurolink Suit, Neurolink Pass from event start) keeps **2025-06-12**.
Discrepancy: the wiki lists Raven's banner as 6/15, but `banners.json`
(2025-06-19) and `characters.json` agree on **2025-06-19**, which also
matches the Midsummer Pass and Solo Raid start dates on the wiki page —
the repo date was kept.

The last 7 undated variants, resolved:

- c903_01 **Andersen Soaked** → **2023-04-01** (Full Fool Day — the
  protagonist's shirtless/wet model; Andersen is the protagonist, debut
  ch 1 = 2022-11-04; gallery: "Andersen (Shirtless) FB.png | Full Fool
  Day").
- c011_01 Bling Bullet, c030_01 Sweet Holic, c070_01 Model Worker, c141_01
  Extreme Fighter, c170_01 Government Grunt, c181_01 Covert Nurse → the
  first 13 "Halcyon Days" cash-shop costumes (all before `Coat Off`
  2023-02-22 per the Costumes-page ordering), all `obtain` = Cash Shop. No
  in-game sale date is documented anywhere (wiki text and images were all
  batch-documented 2023-04-03/04; the KR wiki is not on Fandom). Dated to
  the carrier's base release date — all six carriers (Neon, Poli, Brid,
  Milk, Privaty, Maiden) debuted at launch **2022-11-04**, the earliest
  defensible ship date (an asset cannot ship before its character;
  consistent with the documented cases c010_02 White Promise = 2022-11-04
  and c800_01 Coat Off = the carrier's 2023-02-22 debut). Note: c170_01 is
  **not** the CN-exclusive Privaty skin — that one is "Destined in Blue"
  (renamed in the Nikke-db log 2025-06-14); Government Grunt is an INT
  cash-shop costume.

### Collab / data-mined characters — correction to PLAN.md

`cards/PLAN.md` (2026-10-24) calls Denji (c803), Aki Hayakawa (c804), 9S
(c813), Adam (c853) "unreleased" because they have no NIKKE *character*
wiki page. That is not quite right: all four have wiki pages under
**Minor characters/Collaboration event** (fetched to
`/tmp/research2/p_Minor_characters_Collab.txt`) with documented in-game
debut events:

| Model | Debut (wiki) | Date |
|---|---|---|
| c803 Denji, c804 Aki Hayakawa (+c803_01) | BULLET X CHAINSAW (Chainsaw Man collab, #1) | 2023-02-22 |
| c813 9S | OuteR:Automata (NieR:Automata collab) | 2023-09-01 |
| c853 Adam (Stellar Blade) | Memories Teller | 2025-06-12 |
| c9038 Teddie, c9039/c9040 Morgana | Persona on Frontline | 2026-08-12 |
| c9006 Deipara | Reborn Evil (story; Nikke-db added "Deipara" 2025-09-28) | 2025-09-24 |
| c9010 Jane, c9011 Rain | Lie cause Recoil | 2026-02-12 |

So these models *did* ship (as story/cutscene models) — dates come from the
debut event, not `null`. (c998 Hermin also debuted with Memories Teller.)

**c836 Sakura correction:** an earlier note dated c836 to Second Quest
(2025-02-20), mistaking the WILLE medical-chief *minor NPC* of that event
for this model. c836 is **Sakura (T.T. Star SSR)** — a playable NIKKE
(wiki page created 2023-03-27; her "Sakura" gacha ran 2023-03-30 → 04-13;
infobox: T.T. Star, Supporter, Ichigenkin) → **2023-03-30**. The
WILLE nurse is an unnamed minor character, not a model.

### Minor-character / NPC corrections this pass

From `minor_debuts_all.json` debut lines + event-page story casts + Nikke-db
log:

| Model | Debut | Date |
|---|---|---|
| c9032 Jien | Wisdom Spring story (M.M.R. scientist; Nikke-db "Added Jien" 2025-01-16). **Not** Project Matis (2026-07-23 reuses the model) | **2025-01-16** |
| c9005 / c9005_01 Rapture | ABSOLUTE story "brand-new Rapture species"; Nikke-db "Raptures from the Absolute event" (2025-08-10) | **2025-08-07** |
| c9014 Mass Produced Heretic | Lie cause Recoil (Nikke-db 2026-02-14 "5 NPCs from collab and story"; named 2026-02-15) | **2026-02-12** |
| c974 Mass Produced Melee, c974_01 Mass Produced Melee 2 | New Year, New Sword (Nikke-db 2023-12-29 / 2024-01-06) | **2023-12-28** |
| c971 Rose | New Year, New Sword story (mass-produced squad; Nikke-db added "Rose" with the NYNS assets 2023-12-29) — earlier note said 2023-12-08, wrong | **2023-12-28** |
| c9021 Anis, c9022 Mustang, c9024 Yoyo, c9025 Egovista | Star Anis story (all in the cast; Nikke-db added Anis 2026-04-12, Yoyo/Egovista 2026-04-25) | **2026-04-23** |
| c9023 Hanson | ch 28 commission "Go to the Coordinates sent by Handsome Commander" (BOOM's Day update) | **2024-02-22** |
| c9026 Amy | 2x2 Love story | **2026-03-19** |
| c113 E.H. (base) | Enter Heaven (characters.json 2026-03-05; Nikke-db "Added E.H. and Rain" 2026-03-08). "Added to the Standard pools" at 2x2 Love (2026-03-19) is the gacha, not the model ship | **2026-03-05** |
| c903 Andersen | the **protagonist** (Deputy Chief; infobox debut: Chapter 1; va JP Tomokazu Sugita) | **2022-11-04** |
| c903_01 Andersen Soaked | Full Fool Day (gallery: "Andersen (Shirtless) FB.png \| Full Fool Day") | **2023-04-01** |
| c9034–c9037 Penguin (×4) | Wave to You (Nikke-db "the new 4 penguins" added 2026-07-04) | **2026-07-02** |

### Base characters resolved this pass (undated in `characters.json`)

19 playable bases + the c350_old rig had `release_date = null` in
`characters.json` (the 2026-10-24 verification pass skipped them). Dated
from the chapter/event that shipped them (page-creation dates corroborate
the update; the Nikke-db viewer log's "Added X" batches lag 1–16 days, so
page/event dates are used, not the log):

| Model | Character | Ship (update) |
|---|---|---|
| c227 | Pinocchio | ABSOLUTE **2025-08-07** (page 2025-08-06) |
| c250–c255 | Mass Produced ×6 | Red Ash **2023-11-02** (viewer batch 2023-11-16) |
| c263 | Indivilia | Golden Ship **2023-07-20** (debut ch 24 "Banishment" per her infobox; ch 23–24 shipped with Golden Ship — re-verified BUCKET_05) |
| c350_old | Mast (old rig) | with Mast **2023-07-20** |
| c370, c371 | Eternity, Endless | ABSOLUTE **2025-08-07** (pages 2025-08-08; viewer 2025-08-10) |
| c440 | Eyeri | Second Quest **2025-02-20** (page 2025-02-20; viewer 2025-03-08) |
| c480, c490 | Liveryn, Hammering | BOOM's Day **2024-02-22** (pages 2024-02-22; viewer 2024-03-01) |
| c481, c491 | Fragile, Drilley | Last Kingdom **2024-04-25** (pages 2024-04-24) |
| c482 | Logey | Goddess Fall **2025-10-30** (page 2025-11-07; viewer 2025-11-02) |
| c530, c531 | Sky, Cielo | Over the Horizon **2025-07-03** (page 2025-07-03) |
| c560 | Behemoth | Juvenile Days **2024-07-25** (page 2024-07-26) |
| c561 | Ziz | Unbreakable Sphere **2025-04-24** (page 2025-04-25) |
| c562 | Leviathan | Old Tales **2024-10-31** (page 2024-10-26; viewer 2025-04-12 lags) |
| c563 | Bahamut | Goddess Fall **2025-10-30** (page 2025-10-26; viewer 2025-11-02) |
| c571, c572 | Ark Ranger Red, Ark Ranger Blue | Ark Ranger **2026-06-11** |
| c915 | Raptillion | BOOM's Day **2024-02-22** (viewer batch 2024-03-01) |
| c853 | Adam (Stellar Blade NPC) | Memories Teller **2025-06-12** (viewer 2025-06-14) |
| c910 | Hologram | Maid in Valentine **2023-02-01** — the projector rig shipped with the Sweet Johnny manager hologram (event story: "a hologram appears and introduces itself as … Sweet Johnny"); reused in the 2025 Pirate Cafe minigame |

Also corrected: **c836 Sakura = 2023-03-30** (see above), **c945 Katie =
2023-04-27** (ch 22 commission), **c911/c912 Faceless Man/Woman =
2022-11-04** (launch crowd assets).

### Minor characters (c9xx / c9xxx) resolved this pass

All 63 undated three-digit `c9##` models and 44 four-digit `c9xxx` models
dated from debut evidence: chapter pages (ch 00–16 NPCs + Faceless 1–13 =
launch **2022-11-04**; Ingrid ch 2, Mustang ch 4, Andersen ch 1, Enikk ch
4, Rian ch 14 (her own page says Chapter 14: Journey), Burningum ch 14, Einkk Simulation Room, Collection Robot
ch 10), event pages (Papillon/Johan/Cecil/Joseph in D-Outsiders ch 19 =
**2023-01-12**; Beatrice/Pinne/Commander (GODDESS)/Liliweiss/Oswald in
Over Zone **2023-04-27**; Bolt/Bolt Junior/Max/Booboo in Bow-Wow Paradise
**2023-03-15**; Doban in Golden Ship **2023-07-20**; Ruru/Timi in Nya Nya
Paradise **2023-07-06** — Timi is Leona's lion; the four Ghost Lumi/Lua/
Lena + Lumi in NEVERLAND **2023-12-08**; Rose + Mass Produced Melee in
New Year, New Sword **2023-12-28**; Abe/Hansel/Gretel/Red Shoes in Old
Tales second series **2024-10-31**; Nadia in Life Again **2024-10-17**;
Chloe in Ice Dragon Saga **2024-12-05**), the Minor characters wiki tabs,
and Nikke-db log entries. Four-digit story NPCs follow their chapter/event
(c9000/c9001 Ghost family = Boom! The Ghost! **2025-07-17**; c9003/c9005/
c9008/c9005_01 = ABSOLUTE **2025-08-07**; c9002 Nora = Blank Ticket
**2025-11-20** (BUCKET_10 correction — her debut event is the 2025-11-20
Blank Ticket; the 2025-05-29 update is Lord, for Justice); c9006 Deipara = Reborn Evil **2025-09-24**; c9009
Nihilister = Liberation II **2023-03-30**; c9010–c9019 = Lie cause Recoil
**2026-02-12** — incl. c9015/c9016, whose names arrived in the 2026-02-15
updateLog rename, confirming the 2026-02-12 ship; c9020/c9020_01 Freesia
= Good World **2026-04-09**; c9021/c9024/c9025/c9022 = Star Anis
**2026-04-23**; c9023 Hanson = ch 28 commission **2024-02-22**; c9026 Amy
= 2x2 Love **2026-03-19**; c9028 Hope = Ark Ranger **2026-06-11**;
c9029–c9031 Laplace/Enme/Syuen = Project Matis **2026-07-23**; c9032 Jien
= Wisdom Spring **2025-01-16**; c9034–c9037 penguins = Wave to You
**2026-07-02**; c9038–c9040 Teddie/Morgana = Persona **2026-08-12**).
Duplicate rigs take the model they duplicate (c960 Freesia = c9020,
c973 Jien = c9032, c996 Leviathan = c562). **c570_99 Ark Ranger Black =
2024-05-16** (the "Black Ark Ranger" rig added in the 2024-05-16 update;
the current c570 rig shipped 2026-06-11 with the Ark Ranger event — an
older variant than its base, the only ID-scheme exception alongside
c820_02/c830_03).

### Event-date corrections (wiki_events.json wins)

- Wisdom Spring = **2025-01-16** (page infobox; earlier 2024-05-16 was wrong).
- Fool Burst Day = **2025-04-01**; 2026-04-01 is **Fool Metal Panic**. The
  April Fools' series: Full Fool Day 2023-04-01, Liar's End 2024-04-01,
  Fool Burst Day 2025-04-01, Fool Metal Panic 2026-04-01.
- Golden Coin Rush = **2024-05-30** (a Grand Event; the 2023-12-08 update
  was NEVERLAND).
- Terminus Ticket = **2025-12-04** → 12-30 (start date used).
- You Can (Not) Evade = **2024-08-21**; Enter Heaven = **2026-03-05**;
  2x2 Love = **2026-03-19**; Great Villain Union = **2026-09-03**.

### CN-exclusive models

The eight CN-exclusive rows — present in the client dump (Shift Up ships CN
assets in the global client) but never released to International players —
are **dated, not `null`**: `date` = the update that first shipped the model
in the client it released in. The CN App Store page's full version history
(see Sources) pins the CN player-facing releases; the Nikke-db "chinese
exclusive" log entries pin the client ships (the log lags a global update
by days, but lags CN client builds by weeks to months — the maintainer
extracts CN builds only sporadically).

| Model | `date` | Evidence |
|---|---|---|
| c902_01 Mustang (CN) | **2025-04-01** | CN-exclusive Mustang skin; Nikke-db 2025-04-05 "chinese exclusive … mustang asset" ⇒ in the global client with the 2025-04-01 update (Fool Burst Day; no global update in between); released to CN players at the CN launch 2025-05-21 (App Store 2.11.1) |
| story0401_3 Story 04-02 (CN) | **2025-04-01** | CN chapter-4 scene 02; Nikke-db 2025-04-21 — no global update between 2025-04-01 and 2025-04-24, so the 2025-04-01 client |
| c082_80 Liter (CN) | **2025-05-29** | Nikke-db 2025-06-02 "liter chinese skin" ⇒ global 2025-05-29 update (Lord, for Justice, 4-day log lag); never listed in any CN App Store notes (unannounced minor content) |
| c233_80 Dorothy (CN) 宴桃源 | **2025-06-20** | CN 4.0.1 notes: "桃乐丝全新时装【宴桃源】正式登场" (CN-exclusive cheongsam, with the 记忆与遗忘/Over-Zone package); Nikke-db 2025-06-29 = the CN 4.0.1 client 9 days later (no global update in that window) |
| c260_80 Modernia (CN) | **2025-06-20** | same Nikke-db 2025-06-29 entry ⇒ same CN 4.0.1 client; caveat: the CN notes announced it to players only in 18.2.1 (**2026-05-19**, 牡丹【休假女王】, with Modernia's CN debut) — the asset shipped dormant in the client for 11 months |
| c8004, c8006 Ying Ning (CN) | **2025-10-28** | CN 9.4.1 notes (半周年/RED ASH update): SSR NIKKE 「婴宁」 added to special recruit; the Nikke-db 2026-01-17 entry is the *global* client copy (~3-month log lag) |
| c8005 Hua Pi (CN) | **2025-10-28** | CN 9.4.1 notes: SSR NIKKE 「画皮」 (the two models share the update) |

CN context: the CN server (《胜利女神：新的希望》, Tencent) launched
**2025-05-21** (App Store 2.11.1; beta builds 1.2.6–2.9.1 ran
2025-01-23 → 05-15). CN updates bundle global events 1–2.5 years late
(Over Zone → 4.0.1 2025-06-20; Red Ash → 9.4.1 2025-10-28; A.C.P.U.
Freeze → 18.2.1 2026-05-19), so the CN App Store content lists date CN
player-facing releases, not the client ships — the dates above follow the
client ship, per the file's semantics.

No other `null`s remain: the data-mined models without any NIKKE character
page (Denji/Aki/9S/Adam and all other c9xx/c9xxx models) all have a
documented debut (see **Collab / data-mined characters**).

### Global date corrections (CN pass, 2026-11-04)

While dating the CN-exclusive models, the auto-matcher's output
(`/tmp/research2/variant_match1.json`) was re-verified against the event
pages + Nikke-db log. The matcher takes the earliest hit date; a
character-page revision, a re-run page, or an event-page costume gallery
(some event pages re-list old costumes — e.g. Unbreakable Sphere lists
Alice Sweet Home, Liter Cute Sunflower, Diesel Black Sunday, Sugar
Hard-Boiled) sometimes beat the true release page. Nine entries
corrected:

| Model | Was | Now | Evidence |
|---|---|---|---|
| c233_01 Dorothy Nostalgia | 2023-04-27 | **2023-11-02** | Red Ash page: "1st Anniversary Costume Gacha: Dorothy - Nostalgia" (ran to 2023-11-23); Nikke-db 2023-11-05 (RED ASH batch); the 2023-04-27 hit was the Dorothy character page |
| c270_01 Blanc White Rabbit | 2023-05-18 | **2023-12-07** | NEVERLAND page: "Bunny Lucky Pass" (event-exclusive, "separate from the monthly version") premium "White Rabbit" for Blanc → event date; Nikke-db 2023-12-09 (Neverland batch); the 2023-05-18 hits were Bunny X 777 |
| c350_01 Mast A Pirate's Heart | 2023-07-20 | **2023-08-03** | SEA, YOU, AGAIN page (startDate 2023-08-03): "A Mast costume … permanently added to the Cash Shop"; matches c015 Anis: Sparkling Summer (same event); the 2023-07-20 hit was the Mast page (her Golden Ship debut) |
| c352_01 Helm Chandelier | 2022-11-10 | **2022-12-28** | Brand New Year page: Sunrise Pass premium "Chandelier" for Helm (event pass → event date, per the event-pass rule) |
| c353 Helm: Aquamarine | 2023-08-10 → (CN pass) 2023-08-03 → **2023-08-10** | the CN pass had aligned c353 with c015 on the SEA, YOU, AGAIN event infobox startDate (2023-08-03); **reverted in BUCKET_05** — official "Update on August 3": "Limited-Time Recruitment duration: From 5:00:00 **August 10**, 2023"; first-obtainable = gacha start, the project convention for pre-staged new characters (Noir 2023-05-25, Neon 2023-06-22) |
| c931_01 Com | 2023-04-27 | **2025-06-12** | Stellar Blade collab model (Collection-Robot variant); Nikke-db 2025-06-14 added it with Eve/Raven/Lily/Adam (Memories Teller 2025-06-12, cf. c853 Adam); the 2023-04-27 hits were Over Zone |
| c162 Mihara: Bonding Chain | 2025-05-01 | **2025-04-24** | Unbreakable Sphere debut (bonus-Nikke bullet — not an MP-season premium; that event's May MP premium is Cinderella's "Beautiful Me"); Nikke-db 2025-05-02 (US batch, "added her skin"); aligned with c513/c513_01 (same event) |
| c162_01 Mihara: Bonding Chain Pain Eater | 2025-05-01 | **2025-04-24** | same debut |
| c072_01 Diesel Black Sunday | 2025-04-24 | **2022-11-04** | **launch costume** — wiki Module:NikkeCostume: series "Halcyon Days", obtain "Mission Pass Season 1"; the MP season file's Season 1 is exactly Diesel (Black Sunday) with start **2022-11-04** (the monthly MP launched with the game; only later seasons refresh on the first of the month); nikke.gg confirms a missionpass obtain; the 2025-04-24 hits were the Unbreakable Sphere costume gallery (a re-list of old costumes) |
| c962 Product 12: B-0006 | 2022-11-04 | **2023-09-01** | OuteR:Automata debut — wiki Minor characters/Collaboration event infobox `debut = [[OuteR:Automata]]` (cached + live 2026-11-04); NieR collab 2023-09-01 (`ev_dates.json`, `event_dates_full.json`); the 2022-11-04 value was the parent Product 12's launch date |
| c963 Product 12: C-1002 | 2022-11-04 | **2023-09-01** | same (all three Product-12 sub-models debut in the same collab event) |
| c964 Product 12: 6000-D | 2022-11-04 | **2023-09-01** | same (6000-D = the event's main antagonist, "Taciturn Product 12") |
| c472 Scarlet: Goddeath | 2022-11-04 | **2026-11-05** | not a CN copy — the 4th-anniversary new SSR character **Scarlet: Goddeath** (wiki `releaseDate = 5 november 2026`, "4th Anniversary version"; nikke.gg live client bundle maps model 472 to it; user-confirmed gacha opening 2026-11-05). The scraper filed it under base Scarlet with her 2022 launch date (characters.json entry mislabeled likewise) |
| c473 Rapunzel: Sanctuary | 2022-11-04 | **2026-10-29** | not a CN copy — the 4th-anniversary new SSR character **Rapunzel: Sanctuary** (wiki `releaseDate = 29 october 2026`; nikke.gg live bundle maps model 473 to it; user-confirmed release 2026-10-29) |
| c989, c990, c992, c994 (Rapi ×4) | 2022-11-04 | **2025-01-01** | the "CN client copy of Rapi" reading was a name-match inference — the user confirmed these are **distinct models** belonging to the **Rapi: Red Hood** release (c016 "Rapi: Red Hood" + c016_01–03, all 2025-01-01, the New-Year SSR gacha). Viewer log "Decembre 27th 2024 :: added Rapi, Rapi, Rapi, Rapi Hood, Ein, Zwei, Naga" = the pre-staged client batch for that update (viewer additions can precede the obtainable date; the "Naga" entry matches c450_02 2024-12-26) |
| c985 (Yuni) | 2022-11-04 | **`null` (dropped, 2026-11-04)** | the "CN client copy of Yuni" reading was a name-match inference — the user confirmed the model is **distinct from INTL c160 Yuni**. Client Live2D + sprite asset (`l2d/c985/…`), absent from nikke.gg's INTL data; the Nikke-db viewer first picked a Yuni Live2D up on 2024-10-27 ("N Corp Groẞhammer Yuni"), so the 2022 value is wrong, but no source maps the id to a specific model/update → date dropped (BUCKET_03 open item; resolution path: same as the Rapi batch) |
| c112_01 Viper Toxic Rabbit | 2023-01-19 | **2023-05-01** | the variant is the **May 2023 Mission Pass premium**, not a launch costume: nikke.gg live client data `gg_costumes_db.json` "112/Toxic Rabbit — Obtained from a Mission Pass"; `mp_costumes.json` S7 = Viper (Toxic Rabbit), start 2023-05-01 (MP season-start rule); the 2023-01-19 value was the base Viper's gacha start (wiki releaseDate) inherited by the variant |
| c202_01 Dolla Dark Rose | 2023-02-22 | **2023-03-01** | the **March** MP premium (official "Update on February 22, 2023": "5.2 March Mission Pass, Sale 00:00:00 March 1 → 23:59:59 March 31 … Win Dolla's special costume Dark Rose"; `mp_costumes.json` S5 start 2023-03-01) — the 2023-02-22 value was the announcing update's date |
| c430_01 Noise Cherry Blossom Stage | 2023-03-30 | **2023-04-01** | the **April** MP premium (official "Update on March 30": "can be obtained with April Mission Pass", sale Apr 1–30; `mp_costumes.json` S6 start 2023-04-01) — same misattribution pattern |
| c991 D.E.E.P. | 2023-04-13 | **2024-12-26** | the model debuts in the **Footstep, Walk, Run** event (wiki `startDate = December 26th, 2024`, "the last event of 2024" — Rapi's past with mentor Red Hood, where the guardian D.E.E.P. appears; `minor_debuts.json`: "D.E.E.P." → "Footstep, Walk, Run"; viewer 2025-01-02 added its Live2D; c991 present in the live INTL client bundle). The 2023-04-13 value had no source — the LICENSE TO KILL event (the actual 2023-04-13 event) never mentions D.E.E.P. |
| c212_02 Novel Detective Nurse | 2023-09-21 | **2023-10-01** | the **October** MP premium (official "Update on September 21": "can be obtained from an **October Mission Pass**"; `mp_costumes.json` S12 = Novel (Detective Nurse), start 2023-10-01; `gg_costumes_db.json`: missionpass) — the 2023-09-21 value was the announcing update |
| c170_02 Privaty Banquet Princess | 2023-10-19 | **2023-11-01** | the **November** MP premium (`mp_costumes.json` S13 = Privaty (Banquet Princess), start 2023-11-01; `gg_costumes_db.json`: missionpass) — the announcing Oct 19 post is absent from the official archive; the viewer's Oct 19 batch shows it staged in that update |
| c271_01 Noir Black Rabbit | 2023-11-23 | **2023-12-01** | the **December** MP premium (official "Update on November 23": "can be obtained from the **December Mission Pass**"; `mp_costumes.json` S14 = Noir (Black Rabbit), start 2023-12-01) |
| mbg001 Boss: Alteisen | 2023-10-19 | **2022-11-18** | Co-Op is a **post-launch** feature — the director's launch dev note (2022-11-03): "coordinated operations … will be rolled out **sequentially**" after the initial release, and the Nov 10 update post (closest documented update before the first Co-Op) lists no Co-Op content; the first documented Alteisen Co-Op ran **2022-11-18** (oldest row of the wiki Co-Op table) and the full client dump contains exactly one Alteisen boss model (the 2022 Co-Ops used mbg001); the 2023-10-19 value was the client re-patch for the 2023-10-20 "Alteisen MK.VI\|code=water" Co-Op (resolves the BUCKET_03 carry-over item) |
| c967–c969 Ghost Lumi/Lua/Lena, c970 Lumi | 2023-12-08 | **2023-12-07** | the ghost models debut in the **NEVERLAND** event (wiki Minor characters/Event infoboxes: `debut = [[NEVERLAND]]`; `minor_debuts.json`: Lumi/Lena → NEVERLAND) via its **Snowfall Oasis** minigame — "Unlocked after clearing Stage I-5", with Part I stages open from the Dec 7 maintenance end → reachable from the event start; event-NPC convention = event start (cf. c939 Doban, c945 Katie); the 2023-12-08 value had no identifiable source |
| c140_02 Sugar Wild Backyard | 2024-01-25 | **2024-02-01** | the **February** MP premium — wiki `Module:NikkeCostume/data`: Sugar "Wild Backyard — Mission Pass Season 16"; `mp_costumes.json` S16 start 2024-02-01; the Dirty Backyard page documents the "February Mission Pass Update" (the recorded value was the announcing update) |
| c210_02 Exia Gamer | 2024-02-22 | **2024-03-01** | the **March** MP premium (module: Exia "Gamer — Mission Pass Season 17"; `mp_costumes.json` S17) |
| c280_01 Rosanna Ms. Dangerous | 2024-03-21 | **2024-04-01** | the **April** MP premium (module: Rosanna "Ms. Dangerous — Mission Pass Season 18"; `mp_costumes.json` S18) — the recorded value was the Re:CIPE FOR YOU announcing update |
| c072_04 Diesel Midnight Strawberry | 2024-04-25 | **2024-05-01** | the **May** MP premium (module: Diesel "Midnight Strawberry — Mission Pass Season 19"; `mp_costumes.json` S19) — the recorded value was the Last Kingdom announcing update |
| c281_01 Moran Off-Duty Queen | 2024-01-25 | **2025-06-01** | the **June 2025** MP premium (module: Moran "Off-Duty Queen — Mission Pass Season 32"; `mp_costumes.json` S32 = "Moran (Off-Duty Queen)", start 2025-06-01) — the variant had inherited the base character's 2024 debut date |
| c043_01 D: Killer Wife Secret Party Cleaner | 2024-03-07 | **2024-11-01** | the **November 2024** MP premium (module: "Secret Party Cleaner — Mission Pass Season 25"; `mp_costumes.json` S25 = "D: Killer Wife (Secret Party Cleaner)", start 2024-11-01) — the variant had inherited the character's KILL THE LORD debut date |
| c181_02 Maiden Under the Sun | 2024-06-20 | **2024-07-01** | the **July** MP premium (module: Maiden "Under the Sun — Mission Pass Season 21"; `mp_costumes.json` S21) — the recorded value was the announcing (Clay, More!) update |
| c450_01 Naga Elegant Date | 2024-07-25 | **2024-08-01** | the **August** MP premium (module: Naga "Elegant Date — Mission Pass Season 22"; `mp_costumes.json` S22) — the recorded value was the Juvenile Days announcing update |
| c032_01 Miranda Thief of Justice | 2024-09-19 | **2024-10-01** | the **October** MP premium (module: Miranda "Thief of Justice — Mission Pass Season 24"; `mp_costumes.json` S24) — the recorded value was the Jinx Player announcing update |
| c403_01 Quency: Escape Queen Masquerade Swan | 2024-10-03 | **2025-12-30** | the **Ark Guardian "New Year Pass"** premium — module: "Masquerade Swan — 2026 New Year Pass"; the Ark Guardian event page (30 december 2025 → 20 january 2026) documents the pass: "The premium track offers the costume 'Masquerade Swan' for Quency: Escape Queen" — the variant had inherited the character's Phantom Thief debut date |
| c431_01 Volume Beat the Gun | 2024-11-21 | **2024-12-01** | the **December** MP premium (module: Volume "Beat the Gun — Mission Pass Season 26"; `mp_costumes.json` S26) — the recorded value was the Secret Garden announcing update |
| c390_01 Zwei First Festa | 2024-12-26 | **2025-01-01** | the **January** MP premium (module: Zwei "First Festa — Mission Pass Season 27"; `mp_costumes.json` S27) — the recorded value was the Footstep Walk Run announcing update |
| c391_01 Ein Handmade Festa | 2024-12-26 | **2025-01-01** | the **2025 New Year Pass** premium (module) — the event pass of the 2025-01-01 update |
| c501_01 Trony Sweet Step | 2025-01-30 | **2025-02-01** | the **February** MP premium (module: Trony "Sweet Step — Mission Pass Season 28"; `mp_costumes.json` S28) — the recorded value was the Romantic Valentine announcing update |
| c354_01 Mast: Romantic Maid Tea Service | 2025-01-30 | **2026-02-12** | the dedicated **Costume Gacha** page for the Tea Service costume (`ev_dates.json`: "costume gacha mast romantic maid (tea service) = 2026-02-12", the Lie Cause Recoil update) — the variant had inherited the character's Romantic Valentine debut date |
| c016_01 Rapi: Red Hood Red Flavor | 2025-01-01 | **2025-07-17** | the dedicated **Costume Gacha** page for Red Flavor (`ev_dates.json`: "costume gacha rapi red hood (red flavor) = 2025-07-17", the Boom! The Ghost! update) — Rapi: Red Hood's three launch-era variants are all later-obtained (gacha 2025-07, poll reward 2025-04, MP S43 2026-05) |
| c016_02 Rapi: Red Hood Cherished Red | 2025-01-01 | **2025-04-19** | the **2025 Popularity Poll winner costume** (module: "Cherished Red — 2025 Popularity Poll rewards"; Poll III voting 8→14 April 2025, top 1 = Rapi: Red Hood, costume "distributed across all servers for free", results revealed at the 2.5th-anniversary livestream on 2025-04-19). No dedicated costume page exists — the date is the documented announcement/distribution date (flagged for re-check) |
| c016_03 Rapi: Red Hood Shining Light | 2025-01-01 | **2026-05-01** | the **May 2026** MP premium (module: "Shining Light — Mission Pass Season 43"; `mp_costumes.json` S43) |
| smol_ade | 2025-01-30 | **2024-02-05** | the model first shipped with the **Perfect Maid** minigame (viewer update log 2024-02-07: "Added Smol Maid Privaty and Smol Ade from the Perfect Maid Minigame"); the 2025-01-30 value was the later Pirate Cafe batch it reappears in |
| smol_mpriv | 2025-01-30 | **2024-02-05** | same 2024-02-07 log entry names "Smol Maid Privaty" from the Perfect Maid Minigame (resolved in BUCKET_09 after the row slid into that bucket's range) |
| c180_01 Guillotine Dark Tracer | 2023-12-28 | **2024-01-01** | the **January** MP premium (module: Guillotine "Dark Tracer — Mission Pass Season 15"; `mp_costumes.json` S15) — the recorded value was the New Year, New Sword announcing update (BUCKET_09 gap row) |
| c430_02 Noise Classic Diva | 2023-12-28 | **2024-01-01** | its Costume Gacha opened at **New Year's midnight** — wiki "New Year, New Sword" page: "Costume Gacha - Noise: Classic Diva … Duration: Midnight, January 1st to 5:00 January 18th (UTC+9)" (BUCKET_09 gap row) |
| c225_01 Scarlet: Black Shadow Longing Flower | 2024-01-01 | **2024-10-31** | the dedicated **Costume Gacha** page for Longing Flower (`ev_dates.json`: "costume gacha scarlet black shadow (longing flower) = 2024-10-31", the Old Tales update) — the variant had inherited the character's New Year debut date (BUCKET_09 gap row) |
| c382_01 Leona Zoo Keeper | 2024-01-11 | **2024-09-01** | the **September** MP premium (module: Leona "Zoo Keeper — Mission Pass Season 23"; `mp_costumes.json` S23) — the recorded value was the character's debut (BUCKET_09 gap row) |
| c142_01 Frima Sea of Sloth | 2023-06-15 | **2023-07-01** | the **July** monthly MP premium (nikke.gg client data: "Obtained from a Mission Pass"; `mp_costumes.json` S9 = Frima (Sea of Sloth), start 2023-07-01) — the 2023-06-15 value was the staging update (Blue Water Island); the June/July MP announcements are absent from the official archive |
| c201_01 Yan Sunrise Market | 2023-07-20 | **2023-08-01** | the **August** monthly MP premium — official "Update on July 20": "Yan – Sunrise Market can be obtained with the **August Mission Pass**"; `mp_costumes.json` S10 = Yan, start 2023-08-01. The recorded value was the announcing (Golden Ship) update; the old "Golden Ship MP" note was a misread of "August Mission Pass" |
| c220_01 Snow White White Knight | 2023-08-24 | **2024-04-25** | the **1.5th Anniversary Pass** premium of the **Last Kingdom** event (wiki Last Kingdom page: "An event-exclusive Mission Pass. The premium track offers the costume 'White Knight' for Snow White"; Last Kingdom = 2024-04-25 1.5th-anniversary story event; nikke.gg: eventpass). The 2023-08-24 update contained no pass (wiki First Affection page: only Modernia Special / 7-Day Login / Full Burst Day / Union Raid) — the misattribution stems from the "White Knight" squad that appears in the First Affection story (a different thing) |

Checked and kept as-is (the same re-verification): the four monthly
MP-season premiums follow the documented season-start convention (c210_03
2025-09-01 S35/ABSOLUTE, c513_02 2025-11-01 S37/Goddess Fall, c390_02
2026-03-01 S41/Lie cause Recoil — wiki name "Sweet Stroll", c450_03
2026-07-01 S45), plus c041_01 K Undercover 2025-10-01 (S40, Reborn Evil
MP). Also verified against their event pages: c030_02 (2024-04-01,
Liar's End login — Nikke-db 2024-04-06), c070_02 (2023-09-01,
OuteR:Automata — the NieR collab is 2023, not 2025), c090_02/c282_01
(2023-06-01, Queen's Order), c810/c810_01/c810_02 (2023-09-01,
OuteR:Automata), c112 (2023-01-19 — official gacha start + wiki
releaseDate; c112_01 Toxic Rabbit is **not** a launch costume, see
the corrections table), c910/c910_01 (2023-02-01, Maid in
Valentine — the 2025-02-21 Nikke-db "Sweet Johnny" entry is the Pirate
Cafe reuse), c022_01 (2023-02-01, February MP premium, S4).

### BUCKET_10 corrections (from BUCKET_10.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c381_01 Biscuit Spring Puppy | 2025-02-20 | **2025-03-01** | the **March** monthly MP premium — module:NikkeCostume/data: Biscuit "Spring Puppy — **Mission Pass Season 29**"; `mp_costumes.json` S29 = Biscuit (Spring Puppy), start 2025-03-01. The 2025-02-20 (Second Quest) client shipped the model but the premium opened with the season |
| c451_02 Tia Sweet Chef | 2025-03-27 | **2025-04-01** | the **April** monthly MP premium — module: Tia "Sweet Chef — **Mission Pass Season 30**"; `mp_costumes.json` S30 = Tia (Sweet Chef), start 2025-04-01; the New Flavor page documents it: "===April Mission Pass=== The Mission Pass will be refreshed on the first day of April. The premium track offers the costume 'Sweet Chef' for Tia" |
| c511_02 Cinderella Beautiful Me | 2025-04-24 | **2025-05-01** | the **May** monthly MP premium — module: Cinderella "Beautiful Me — **Mission Pass Season 31**"; `mp_costumes.json` S31 = Cinderella (Beautiful Me), start 2025-05-01 — announced with the 04-24 Unbreakable Sphere update, opened with the season |
| c162 Mihara: Bonding Chain | 2025-04-24 | **2025-05-01** | wiki "Mihara: Bonding Chain" page: `releaseDate = 1 may 2025`; ev_dates "pick up 72 mihara bonding chain = 2025-05-01". The 2.5th-anniversary content spanned **two** updates: the Unbreakable Sphere event + Abyss Flower gacha on 04-24, and the Mihara: Bonding Chain recruitment on 05-01 |
| c162_01 Mihara: Bonding Chain Pain Eater | 2025-04-24 | **2025-05-01** | wiki "Unbreakable Sphere" page: "Pain Eater (Mihara: Bonding Chain) - **5:00 May 1st** to 5:00 May 22nd (UTC+9)" (the gacha opened with the 05-01 update); ev_dates "costume gacha mihara bonding chain (pain eater) = 2025-05-01"; update log 2025-05-02 "Updated OverSpec Mihara and added her skin" |
| c835_02 Asuka: WILLE Ocean's Lament | 2025-02-20 | **2025-02-27** | module: Asuka "Ocean's Lament — **Passion CaNon - Asuka Pass**" — the EVA2 **wave-2** (Rei (Tentative Name)) event pass, not the wave-1 Second Quest event (2025-02-20). The wave-2 banner date: wiki "Rei Ayanami (Tentative Name)" releaseDate 27 february 2025; the sibling pass c834_02 Soul Connect was already 2025-02-27 |
| c832_04 Mari Mystery Muse | 2025-02-20 | **2025-02-27** | module: Mari "Mystery Muse — **Passion CaNon - Mari Pass**" — same wave-2 pass family (2025-02-27) |
| c9002 Nora | 2025-05-29 | **2025-11-20** | wiki "Nora" NPC page: "**debut = [[Blank Ticket]]** … the focus character of the events Blank Ticket and Terminus Ticket"; the wiki Blank Ticket event: startDate November 20th, 2025 (→ December 4th; the 65th story event, Soline: Frost Ticket + Nora); wiki Event list page 2025 table: "Blank Ticket \| 20 november 2025". The 2025-05-29 value came from this file's earlier mislabel — the row above called the 2025-05-29 update "Blank Ticket" (that label also appears in the c082_80 row), but that update's event is **Lord, for Justice** (wiki Event list page 2025 table; the viewer's 2025-06-01 entry "K blanc noir moran lord for justice"). The viewer picked the model up late (2026-02-14 as "NPC: TBA", named 2026-02-15 — the Lie Cause Recoil batch) |
| c513_03 Little Mermaid Shell Princess | 2025-04-24 | **2026-07-02** | the dedicated **Costume Gacha: Shell Princess** ran with the **Wave to You** event — wiki "Wave to You" page: startDate July 2nd, 2026, "===Costume Gacha: Shell Princess=== * End of maintenance to 4:59 July 23rd (UTC+9) … A Costume Gacha for Little Mermaid"; the Unbreakable Sphere page's 2.5th-anniversary gacha list is explicitly "Abyss Flower and Pain Eater" **only**; the Little Mermaid page: "first character with two separate Costume Gacha ('Abyss Flower' and 'Shell Princess')". The recorded value was the character's debut date (base-debt inheritance). (The wiki's standalone "Shell Princess" page is the ISLAND BREAKER minigame's soundtrack from the WAVE TO YOU album — consistent with the 2026 event) |

Checked and kept as-is (same pass, 41 rows): the Pirate Cafe smol batch
(smol_rem, smol_sin_pirate, smol_yan @ 2025-01-30 — update log
2025-02-21), c501_01 (2025-02-01, BUCKET_09) and c016_02 (2025-04-19,
BUCKET_09), c355/c835/c412/c520/c521/c513/c590/c581/c041 (wiki
releaseDates, fetched live), the EVA2 wave-1 challenge costumes
(c830_01/c831_01/c832_01 school uniforms = "EMERGENCY MISSION
challenge", c832_03/c835_01 Final Battle = "QUEST MISSION challenge" —
module, wave 1 = the Second Quest update 2025-02-20, per the Event
list page 2025 table), c834 + c834_01 + c834_02 (wave 2, 2025-02-27),
secondquest1/2 (the Second Quest story models, 2025-02-20), c440 Eyeri
(Overseer NPC, debut = Chapter 36: Betrayal = Second Quest 2025-02-20,
per the chapter table in this file), c352_02 (the 2025-02-20 update's
Costume Gacha; update log 2025-02-21 "Added Helm and Biscuit Skins"),
c310_01 (the New Flavor 2025-03-27 login event "Maid in Bloom"),
c902_01 + story0401_3 (the 2025-04-01 CN rows above), c993 Mecha
Shifty (update log 2025-04-05), c513_01 Abyss Flower (the 2025-04-24
gacha, "End of maintenance to 5:00 May 15th"), c514_01 (the "2.5
Anniversary Pass" premium), c561 Ziz (the 2.5th-anniversary character;
update log 2025-05-02 "Added Ziz"), unbreakablesphere / newflavor /
trueflavor / forrest / arcanearchive (event pages + Event list table),
c082_80 (the 2025-05-29 CN row above), c270_02 + c271_02 (the
2025-05-29 Lord, for Justice pass/login).

### BUCKET_11 corrections (from BUCKET_11.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c080_02 Centi Ocean Repair | 2025-06-12 | **2025-07-01** | the **July** monthly MP premium — module:NikkeCostume/data: Centi "Ocean Repair — **Mission Pass Season 33**"; `/tmp/mp_costumes.json` S33 = Centi (Ocean Repair), start 2025-07-01. The 2025-06-12 (Memories Teller) client shipped the model (update log 2025-06-14 "Added Centi & Scarlet skins") but the premium opened with the season |
| c150_02 Julia Summer Romance | 2025-07-17 | **2025-08-01** | the **August** monthly MP premium — module: Julia "Summer Romance — **Mission Pass Season 34**"; `/tmp/mp_costumes.json` S34 = Julia (Summer Romance), start 2025-08-01. The 2025-07-17 (Boom! The Ghost!) client shipped the model but the premium opens with the season |

Checked and kept as-is (same pass, 48 rows): rows 1–8 re-verified in
BUCKET_10 (this bucket's head overlapped B10's tail), plus: lordforjustice
/ memoriesteller_1+2 / overthehorizon / boomtheghost (the story
cutscene models of their events — wiki Event list page 2025 table +
event pages + update log), the Memories Teller collab block — c850/c852
(wiki releaseDate 12 june 2025), c853 (no wiki page; debut event
2025-06-12), c850_02 (the Neurolink Pass, "End of maintenance to 5:00
July 3rd"), c222_01 (the Racer's High gacha, "End of maintenance to
4:59 July 3rd"), the 06-19 second wave — c851 (wiki releaseDate
**19 june 2025**), c850_03 (the Skin Suit gacha, "5:00 June 19th"),
c851_02 (the Midsummer Pass, "5:00 June 19th"), c850_01 + c851_01
(Request List challenge rewards gated on "each collab SSR" incl.
Raven ⇒ first obtainable 2025-06-19; event page: "Story II … unlocked
at 5:00 June 19th"), c931_01 + c998 (previous-pass c9xx rows), c233_80
+ c260_80 (previous-pass CN 4.0.1 rows, 2025-06-20), the Over the
Horizon block — c530/c531 (NPC pages: debut = Over the Horizon), c532
(releaseDate 3 july 2025), c810_03 (the Hidden Summer Pass, the OuTeR
rerun pass), c811_03 (the Silent Oasis 21-day login reward), c170_03
(the Blooming Letter 1-day login reward of the 07-03 update; the
update log's 06-14 "rename Privaty (CN)" is the CN model staged in the
06-12 client), the Boom! The Ghost! block — c234 (releaseDate 17 july
2025 + the gacha "End of maintenance to 5:00 August 7th"), c192_02
(the Survivor Pass premium), c9000/c9000_01/02/03/05/06/07 + c9001
(previous-pass row: Ghost family = Boom! The Ghost! 2025-07-17; update
log 2025-07-17 "the 8 ghosts"), favorite_c030/c150/c192/c550 (the event
page's "Favorite Item Update — Poli, Julia, Bay, and Tove"; update log
2025-07-25 "the 4 new favorites"), c502 (the Elegg: Boom and Shock
gacha "5:00 July 24th to 5:00 August 14th").

### BUCKET_12 corrections (from BUCKET_12.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c093_01 Emma: TU Secret Therapy | 2025-08-07 | **2026-01-01** | the **January** monthly MP premium (S39) — module: Emma: TU "Secret Therapy — **Mission Pass Season 39**"; `mp_costumes.json` S39 start 2026-01-01 |
| c094_01 Vesti: TU Pure Beginner | 2025-08-21 | **2026-03-19** | the **2x2 Love** (2026-03-19) event-exclusive "Pure Beginner Pass" premium — wiki 2x2 Love page + module "Pure Beginner — Pure Beginner Pass" |
| c130_01 Mary Medical Rabbit | 2025-09-04 | **2024-05-30** | the **2024** Golden Coin Rush (startDate 2024-05-30) "Doctor Bunny Pass" premium — the 2025 Coins in Rush is a rerun whose story never features Mary's bunny |
| c242_01 Folkwang Moist Rabbit | 2025-09-04 | **2024-06-01** | the **June 2024** monthly MP (S20) premium — Golden Coin Rush 2024 page: "updated on the first day of June … Moist Bunny for Folkwang" |
| c223_01 Nayuta Wu Wei | 2025-10-30 | **2025-11-06** | the dedicated **Costume Gacha: Wu Wei** "5:00 November 6th to 5:00 November 27th" (Goddess Fall page) — a week after the Nayuta banner |
| c8004 Ying Ning (CN) | 2025-10-28 | **2025-11-25** | CN version history: **11.0.1** (2025/11/25, half-anniversary RED ASH / Faceless Ghost) adds 婴宁 to special recruit — the 9.4.1 (2025/10/28) entry is the Stellar Blade MEMORIES TELLER collab (伊芙/渡鸦/百合) |
| c8005 Hua Pi (CN) | 2025-10-28 | **2025-11-25** | same CN 11.0.1 update adds 画皮 (see c8004) |
| c8006 Ying Ning (CN) | 2025-10-28 | **2025-11-25** | same CN 11.0.1 update, second 婴宁 model (see c8004) |
| c262_01 Liberalio Dreaming Lake | 2025-11-06 | **2026-04-23** | the **Star Anis** 3.5th-anniversary event (startDate 2026-04-23) "Dreaming Lake" costume gacha — "End of maintenance to 5:00 May 14th" |
| c111_01 Jackal Class Troublemaker | 2025-11-20 | **2025-12-01** | the **December** monthly MP premium (S38) — Blank Ticket page: "refreshed on the first day of December … Class Troublemaker for Jackal"; `mp_costumes.json` S38 start 2025-12-01 |

Checked and kept as-is (same pass, 40 rows): the ABSOLUTE block —
c093/c095/c094 (the three TU banners: wiki releaseDates 7/14/21 august
2025 + the ABSOLUTE page banner lines 583–585), c095_01 (the 21-day
login "Not Tactical" final reward, gated on the 08-14 banner start —
retroactive login), c227/c370/c371/c9003/c9005/c9005_01/c9008 (the
story/NPC models of the Nikke-db 2025-08-10/08-16 ABSOLUTE client
batches), c210_03 (the September MP S35 — wiki "Hacker Bunny" =
client "Hacker Rabbit"), the Coins in Rush 2025 block — c272_01 (the
Rouge Unlucky Rabbit costume gacha), c315 (banner "End of
maintenance to 23:59, September 23rd"), c550_01 (the Cheer Bunny Pass
premium), c143 (banner "5:00, September 11th" + wiki releaseDate),
coinsinrush (startDate 2025-09-04), the Reborn Evil block — c840 (Ada
banner "End of maintenance to 23:59 October 21st") + c840_01
(Separate Ways challenge reward) + c840_02 (the Dress event MP), c842
(Claire free SR login bonus), c9006 (the Deipara story NPC; update log
2025-09-28), c041_01 (K Undercover, the October MP S36), c841/c841_01/
c841_02 (the Jill banner "5:00 October 2nd" — the collab's second
wave — + the Classic challenge costume + the Battle Suit event MP),
the Go! Ninja Thief / Goddess Fall block — c023/goninjathief
(startDate 2025-10-16), c223 (banner "End of maintenance to 5:00
November 20th"), c330_02 (the Glorious Flower Pass premium), c331
(Chime, the 14-day login reward), c482/c563 (the Logey/Bahamut story
NPCs; update log 2025-11-02), c971_01 (Rose - Mirror, the GF story
revival), c997 (campaign chapters 41–42), c513_02 (the November MP
S37), c262 (banner "5:00 November 6th"), the Blank Ticket block — c074
(Soline: Frost Ticket, releaseDate 20 november 2025).

### BUCKET_13 corrections (from BUCKET_13.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c102_01 Maxwell Mechanic White | 2025-12-30 | **2022-12-01** | module: Maxwell "Mechanic White — **Mission Pass Season 2**"; `mp_costumes.json` S2 = Maxwell, start 2022-12-01 — the Ark Guardian (2025-12-30) listing is a costume-only **Cash Shop rerun**, not the first obtainable |
| c191_02 Alice Märchen Dream | 2025-12-30 | **2026-01-01** | the Ark Guardian "Costume Gacha: Alice - Märchen Dream" runs "**00:00, January 1st** to 5:00, January 22nd (UTC+9) … available at the start of 2026" — New Year's midnight |
| c316_01 Velvet Sensual Rabbit | 2026-01-29 | **2026-02-01** | the **February** monthly MP premium (S40) — module: Velvet "Sensual Rabbit — **Mission Pass Season 40**"; `mp_costumes.json` S40 start 2026-02-01 |
| c532_01 Sora Spring Flight | 2026-03-19 | **2026-04-01** | the **April** monthly MP premium (S42) — module: Sora "Spring Flight — **Mission Pass Season 42**"; `mp_costumes.json` S42 start 2026-04-01 |
| c551_01 Clay Cheer Up Training | 2026-03-19 | **2026-04-02** | the 2x2 Love "21-Day Login Event - Cheer Up Spring!" window runs "**5:00, April 2nd** to 4:59, April 30th" (final reward, retroactive login) — a week after the event start |

Checked and kept as-is (same pass, 45 rows): the Terminus Ticket
block — blankticket (`startDate = November 20th, 2025`, the
preceding event, verified in the B12 pass), terminusticket
(`startDate = December 4, 2025`), c075 (banner
"End of maintenance to 5:00 December 25th"), c270_03 (the Fortune
Express Blanc gacha, "End of maintenance to 5:00 December 30th"),
c520_01 (the Frosty Bite Pass premium), azxservicetime_1..9 (the
event's AZX Service Time minigame CGs), c073 (the second banner wave
"5:00 December 11th to 23:59 December 31st" + wiki releaseDate 11
december 2025), the Ark Guardian / New Year block — arkguardian
(startDate 2025-12-30, "the New Year event of 2026"), c471 (Snow
White: Heavy Arms releaseDate 1 january 2026), the winter character
block — c582 (Label releaseDate 15 january 2026 + the Sin Editor
banner), sineditor (startDate 2026-01-15), c316 (Velvet releaseDate
29 january 2026 + the Fatal Maid banner), fatalmaid (startDate
2026-01-29), the Lycoris Recoil collab block — c860 (Chisato banner
"End of maintenance to 4:59 March 12th"), c860_01 (the Shooting
Evaluation challenge, live from 02-12), c860_02 (First Lycoris Pass
premium), c862 (Kurumi, the free SR), c9010/c9011 (the Jane/Rain
story twins; Minor characters page "debut = Lie cause Recoil"),
c9014–c9019 (the CPC/platoon/priestess/Altruia Solo-Raid/client
models of the LCR batch; Nikke-db 2026-03-08), liecauserecoil
(startDate 2026-02-12), c861/c861_01/c861_02 (the Takina wave-2
banner 02-19 + challenge + Second Lycoris Pass), the spring block —
c390_02 (S41, start 2026-03-01), c113/c940 (E.H. banner "End of
maintenance to 4:59, March 19th"; Nikke-db 2026-03-08), enterheaven
(startDate 2026-03-05), c112_03 (Punky Street Pass / NIKKE x RAZER;
Nikke-db 2026-03-21 "Privaty + Viper + … skins"), c170_04 (the Sharp
Lesson gacha "End of maintenance to 4:59, April 9th"), c583 (the
Arcana banner), c9026 (the 2x2 Love story's transfer student Amy).

### BUCKET_14 corrections (from BUCKET_14.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c017_01 Anis: Star Starlight | 2026-04-23 | **2026-04-30** | Starlight is the **Twinkle Star** costume gacha's Tier 1 prize and that gacha runs "**5:00 April 30th** to 5:00 May 21st" (Star Anis version updates) — the gacha opens a week after the event start |
| c017_02 Anis: Star T.T. STAR | 2026-04-23 | **2026-04-30** | the same Twinkle Star gacha — T.T. Star is its Tier 2 prize (T.T. Star is also the trio's band name in the event story) |
| c412_01 Trina Natural White | 2026-05-28 | **2026-06-01** | the **June** monthly MP premium (S44) — the Bitter Spice page states the pass "will be refreshed on **the first day of June**"; module: Trina "Natural White — **Mission Pass Season 44**" |

Checked and kept as-is (same pass, 47 rows): the 2x2 Love CG pair
(twoxtwo1/2 — Nikke-db 2026-04-05 "2x2 LOVE CGs"), the April Fool's /
Good World block — c610 (Mekami Shifty, the Fool Metal Panic April
Fool's 2026 quest — "temporarily playable during the quest event"),
c620 (Snow Crane banner "End of maintenance to 23:59, April 22nd" +
releaseDate 9 april 2026), c960/c9020/c9020_01 (the three Freesia
rigs of the Pretty Star side story shipped with Good World — the
story's girl Pretty is named Freesia per the wiki "Pretty" page
`realname = Freesia`), goodworld (startDate 2026-04-09), the Star
Anis 3.5th-anniversary block — c017 (Anis: Star banner "End of
maintenance to 5:00 May 14th"), c233_02 (the event-exclusive Luna
Light Pass, page line 1472), c441 (Avistar, the free SSR "for logging
into the game during Star Anis"), c9021/c9021_01 (the base-Anis story
rigs), c9022 (Mustang, the Tetra executive), c9024 (Yoyo, the rival
idol), c9025 (Egovista, the Solo Raid boss), staranis (startDate
2026-04-23), smol_anis/smol_mint/smol_prika (the chibi/TTS trio of
the Star Anis client batch — the Mint/Prika models ship a month ahead
of the idols' own debuts), the spring character block — c018 (Neon:
Vision Eye's 04-30 second banner wave "5:00 April 30th to 5:00 May
21st" on the Star Anis page + releaseDate 30 april 2026), c600 (Mint
banner, B-Side Idol startDate 2026-05-14), c600_01 (the event-exclusive
Fresh Mint Pass), c600_02 (the "Concert Mint" performance rig —
Nikke-db 2026-04-25; the event story is Mint's concert at Arkrian
Hall), bsideidol (startDate 2026-05-14), c601 (Prika banner, Bitter
Spice startDate 2026-05-28), c601_01 (the event-exclusive Cool
Paprika Pass), c601_02 (the "Concert Prika" performance rig),
bitterspice (startDate 2026-05-28), the Ark Ranger block — c113_01
(the event-exclusive Junkyard Pass), c281_02 (the King of Flowers
gacha "available after maintenance"), c570 (Ark Ranger Black, the
New SSR banner + releaseDate 11 june 2026; re-debut — she first
appeared in D.ark Hero), c571/c572 (the Red/Blue squad members — NPC
pages + Nikke-db 2026-06-14), c9028 (Hope, the story twin named after
A New Hope), arkranger (startDate 2026-06-11), and the summer block —
c450_03 (S45 premium, mp S45 = Naga 2026-07-01), c451_03 (the
event-exclusive Sea Lizzie Pass, Wave to You line 614), c515
(Cinderella: Crystal Wave banner "End of maintenance to 5:00 July
23rd" + releaseDate 2 july 2026), c9034–c9037 (the four Penguin
Squad members of the Wave to You story; Nikke-db 2026-07-04 "the new
4 penguins"), c322 (Marciana: Marine Study's 07-09 second banner wave
"5:00 July 9th to 5:00 July 30th" + releaseDate 9 july 2026), c103
(Laplace: Ultimate Hero banner, Project Matis startDate 2026-07-23 +
releaseDate 23 july 2026), c103_01 (the event-exclusive Prototype
Pass), c9029 (the Project Matis client NPC; Nikke-db 2026-07-27
"the syuen/jian/laplace npcs").

### BUCKET_15 corrections (from BUCKET_15.md)

| Model | Recorded date | Corrected date | Evidence |
|---|---|---|---|
| c105_01 Maxwell: Ordinary Mechanic Chief Researcher | 2026-07-30 | **2026-08-01** | the **August** monthly MP premium (S46) — the Project Matis page: "refreshed on **the first day of August** … 'Chief Researcher' for Maxwell: Ordinary Mechanic"; module "Mission Pass Season 46" |
| c411_01 Flora Fairy Rabbit | 2026-08-12 | **2026-09-01** | the **September** monthly MP premium (S47) — the Persona on Frontline page: "refreshed on **the first day of September** … 'Fairy Rabbit' for Flora" (not Persona event content) |
| c521_01 Crust Treat Chef | 2026-09-17 | **2026-10-01** | the **October** monthly MP premium (S48) — the Coin Rush Showdown page: "refreshed on **the first day of October** … 'Treat Chef' for Crust" |
| c580_01 + c9038/c9039/c9040 + ce009_char_01–03 / enemy_ade/delta/miranda/phantom/poli/quency / skill_01–03 (16 rows) | 2026-08-12 | **2026-08-13** | the Persona on Frontline event **starts August 13th, 2026** — infobox (`startTime = End of maintenance (7:00)`), every "End of maintenance to 5:00 September 10th" banner, the Queen/Aigis releaseDates (13 August 2026) and the Nikke-db 2026-08-13 client batch all agree; the recorded 08-12 is a stale pre-announcement value |

Checked and kept as-is (same pass, 21 rows): the Project Matis tail —
c9030 (Enme, Syuen's father in the story), c9031 (Syuen, the CEO;
Nikke-db 2026-07-27 "syuen/jian/laplace npcs"), projectmatis
(startDate 2026-07-23), smol_marciana/smol_naga/smol_tia (the event's
TTS trio — Nikke-db 2026-07-27 "add TTS naga/tia/marciana"), c105
(Maxwell: Ordinary Mechanic's second banner wave "5:00 July 30th to
5:00 August 20th"), the Persona on Frontline confirmed rows — c870
(Queen (Makoto) releaseDate 13 august 2026 + "End of maintenance to
5:00 September 10th" banner), c870_01 (the S.E.E.S. Mission
challenge, from 08-13), c870_02 (the Thief Queen Pass, "End of
maintenance to 5:00 September 10th"), c872 (Aigis, the free SR
granted by the "Phantom Thieves' Calling Card" daily login; releaseDate
13 august 2026), c871 (Yukiko's second banner wave "5:00 August 20th";
releaseDate 20 august 2026), c871_01 (the S.E.E.S. challenge costume
gated by Yukiko's 08-20 open — same character-gate rule as B13's
c861_01), c871_02 (the Snow Flakes Pass, "5:00 August 20th to 5:00
September 10th"), the Great Villain Union block — c104 (Drake: Great
Villain releaseDate 3 september 2026 + "End of maintenance to 5:00
September 17th" banner), greatvillainunion (startDate 2026-09-03),
and the Coin Rush Showdown block — c140_03 (the Sugar Killer Rabbit
gacha, "End of maintenance to 5:00 October 8th"), c290_01 (the
Let's Drink Pass, same window), c404 (Guilty: Mighty Bunny releaseDate
17 september 2026 + banner), coinrushshowdown (startDate 2026-09-17,
a same-day event), c405 (Sin: Swift Bunny's second banner wave "5:00
September 24th to 5:00 October 15th"; releaseDate 24 september 2026).

## Event date table

`/tmp/research/ev_dates.json` (348 normalized names → start date, the wiki
Events page incl. pickups & mission passes) is the working event-date
source; `/tmp/wiki_events.json` (408 rows with start+end) **overrides it
where they conflict** (see corrections above). Event start dates are UTC+9.
Re-run gachas carry two rows in `/tmp/research/gacha_dates.json`; the first
appearance (earliest `start`) is the model's date.

## Status: complete (2026-11-04)

`date` written into `database/models.json` for all 740 entries (assembly:
`/tmp/research2/assemble_final.py`, deterministic output
`/tmp/research2/assembled_final.json`; the 2026-11-04 CN pass replaced the
eight CN-exclusive `null`s with ship dates and applied nine global
corrections (incl. c072_01 Diesel Black Sunday → 2022-11-04, the
Mission Pass Season 1 launch premium — see **CN-exclusive models** and
**Global date corrections**): **739 dated, 1 `null`** (c985 dropped
2026-11-04; c989–c994 set to 2025-01-01 — see the table rows above).
Verification:

- every model id covered exactly once (base → flavor → event-CG →
  minigame → auto-matched variants → manual variants → story → boss →
  favorite → c9xxx → one-offs; first match wins, asserted);
- every variant date ≥ its base date, except the three documented
  exceptions (c820_02, c830_03 collab-gacha-before-banner; c570_99 older
  rig) — re-checked after the 2026-11-04 corrections;
- no date before the 2022-11-04 launch or after today; all non-null
  values `YYYY-MM-DD` (the c985 null excepted — identity
  unestablished, date dropped).

`uvx ruff check src/` + `uvx ruff format --check src/` are clean (the
change touches only `database/models.json`).
