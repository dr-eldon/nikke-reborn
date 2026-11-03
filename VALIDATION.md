# VALIDATION.md — per-entry date validation of `database/models.json`

Companion to RESEARCH.md (the 2026-11-03/04 pass that wrote the `date` field).
RESEARCH.md documents *how* the 740 dates were derived; this file documents
the re-verification: every entry is re-checked against the raw evidence and
corrected where the evidence contradicts the recorded value.

## Unit of work

- `database/models.json` — 740 entries (739 dated, 1 `null` — c985,
  the BUCKET_03 drop), fixed file order.
- A **bucket** is 50 entries, laid out in **ascending order of the current
  `date`** (stable on ties, so same-date entries keep file order) →
  `BUCKET_01.md` … `BUCKET_15.md` (bucket 15 has 40). `models.json` itself
  is not re-sorted; the buckets are the review view.
- Sequential, one bucket per round. The next bucket starts only after the
  previous one is reviewed and greenlit.

## Evidence corpus (fixed — no new fetches unless a source is missing; a
missing source is flagged in the bucket file, not papered over)

Repo:

- `database/characters.json` — `release_date` per base model; primary source
  for base `c###` entries.
- `database/banners.json` — GLOBAL banner history (`start`/`end`, `rerun`).

`/tmp` (fetched 2026-11-03/04; see RESEARCH.md §Sources):

- `wiki_events.json` (408 events, start+end) — **authoritative** event
  dates; overrides `event_dates.json` and `research/ev_dates.json` on
  conflict.
- `mp_costumes.json` — 49 Mission Pass seasons: `season`, `start`, the
  season's premium `char`/`costume`.
- `research/wiki_costume_module.json` — per-costume `series`/`obtain`
  (the costume's acquisition route).
- `research2/updateLog.json` — Nikke-db asset log (189 "Added X" entries);
  a **lower bound** on the ship date (lags a global update by days, CN
  builds by weeks–months).
- `research2/variant_match1.json` — auto-matcher output per variant
  (`ok`/`un`); its `hits` list the event pages where the costume name was
  found.
- `research/pages/*.txt` + `/tmp/*.txt` — cached event/character/chapter
  pages (the announcement texts).
- `research2/gg_costumes_db.json` — nikke.gg costume DB; global vs
  CN-exclusive cross-check.
- `research/stage2.json` — earlier-pass `{id, date, source}`;
  `research2/assembled_final.json` — pre-final-pass assembly
  (`id → [date, source]`). `models.json` differs from it only by the
  2026-11-04 pass's 17 entries (8 CN nulls → ship dates, 9 corrections).
- `research2/cn_entries.json`, `cn_version_history.txt` — CN App Store
  version history (CN player-facing releases).
- `research2/minor_debuts_all.json`, `research/minor_debuts*.json`,
  `research/storymodel_debuts.json` — debut maps for minor characters and
  story models.

The Fandom API (`…/api.php`) is reachable and may be queried when the
cached corpus cannot answer a question (polite rate: ~1 req/s). Used so
far — BUCKET_01 dig, live checks in `/tmp/research2/wiki_deep_six*.json`
(Home page, full-text search, gallery-image histories, character-page
first appearances, Module:NikkeCostume history) and the Miracle Snow
event page (`research2/Miracle_Snow.txt`). Findings: the wiki's
per-costume documentation is a 2023-04-03/04 batch (Brid page section
first in 2023-04-04; gallery images by 2023-05-02; module history starts
2026-05-26) — no per-costume ship dates exist there; event pages carry
reliable windows (Miracle Snow: Dec 8–28, 2022) but often no costume
lists.

External press sources may also be consulted when the corpus cannot
answer (user-supplied so far): **Sakura Index** (sakuraindex.jp) — the
Miracle Snow Winter Update press release
(`research2/sakuraindex_winter.html`, publ. 2022-12-12) and the Feb 1
update press release (`research2/sa_valentine.html`, publ. 2023-02-02)
are the press-level sources of BUCKET_01's corrections; the Brand New
Year (`sa_brandnewyear.html`) and D-Outsiders (`sa_doutsiders.html`)
articles cover the late-Dec/Jan window. The site exposes a WordPress
REST API (`sakuraindex.jp/wp-json/wp/v2/posts?search=…`, title+content
full-text; `after`/`before` date filters are rejected, so paginate) —
explored 2026-11-04: NIKKE coverage starts **2022-12-10 (no launch
articles)**, 58 Nikke posts total (`research2/sa_nikke_posts.json`).
Site-wide full-text search: zero hits for "Bling Bullet"; "Extreme
Fighter" / "Government Grunt" → the Feb 22 / Feb 1 update articles.
Treat dated press announcements of "new characters / new costumes in
version X" as version-window pins (obtainable from the version's
release date), on par with wiki event pages; the site's update press
releases enumerate each update's new costumes (Miracle Snow, Brand New
Year, Maid in Valentine verified; D-Outsiders has none).

**Official site (nikke-en.com)** — the highest-authority source so far.
It is a JS SPA; content is served by the PlayerInfinite GPTS API:
`POST https://na-community.playerinfinite.com/api/gpts.information_feeds_svr.InformationFeedsSvr/GetContentInfoById`
with body `{"content_id":"<38-hex>"}` (anonymous OK; the EN site routes
to the **NA** host — SG host returns "System error"; `SearchInfoFeeds`
returns no hits anonymously; V2 column lists need a login ticket).
Post ids were enumerated via **Wayback Machine CDX** captures of
`newsdetail.html?content_id=…` (earliest capture = existence floor;
ids in `research2/wayback_nikke_ids.json`). Hydrated **108 official
posts, 2022-11-02 → 2024-01-01** →
`research2/nikke_official_news.json` (title, pub time UTC+9, full HTML
content). Official patch notes state "* Shop opens: After the
maintenance on <date>" — the ship date verbatim. They confirm all five
BUCKET_01 corrections (Dec 8 / Feb 1 / Feb 22) plus c210_01, c090_01,
c150_01, c352_01, c022_01; "Bling Bullet" / "New Server Souvenir"
appear in **no** official post (the launch bundle was never announced
by name). More archive can be pulled the same way (CDX range is
extendable; the API accepts any known content_id).

## Rulebook (normative — RESEARCH.md is the single source of truth; do not
re-derive conventions, apply them)

- `date` semantics per model kind: RESEARCH.md §"Semantics per model kind".
- Event/chapter/banner **start** dates (UTC+9); re-runs → first appearance.
- **MP season premium → the season's `start`** (first of the month; S1 =
  launch 2022-11-04). The module's "Mission Pass Season N" and
  `mp_costumes.json` season N are the same numbering (verified: the
  file's premium `char` matches the module's premium for S1/S4/S8/S11/S19/
  S24/S33/S35/S36/S37/S41/S45).
- **A `variant_match1.json` hit confirms a date only when it is an
  announcement** (the event page's cash-shop / login / pass / gacha
  section names the costume as shipping with that event) **or matches the
  MP/banner convention above**. A bare gallery re-list or character-page
  hit is a lower bound, not a date (RESEARCH.md §"Global date corrections"
  documents the false-hit classes; e.g. "Thief of Justice" also matches
  the Go Ninja Thief story gang).
- Cash-shop/login costumes with **no** documented sale date → carrier's
  base date (Halcyon Days rule); a documented announcement wins over the
  rule.
- Collab mid-event gating (banner-week premiums vs event-start gachas):
  RESEARCH.md §"Variant dating rule for mid-event banners".
- CN-exclusive rows: RESEARCH.md §"CN-exclusive models".
- Invariants, checked per bucket: variant date ≥ base date (exceptions:
  c820_02, c830_03, c570_99); no date before 2022-11-04 or after today;
  all values `YYYY-MM-DD`.

## Per-entry procedure

1. Classify by id pattern: base `c###` / variant `c###_##` / minor
   `c9##`+`c9xxx` / `storyXXXX` / Rapture `bba*`+`mbg*` / event CG /
   minigame group / `favorite_c###` / CN-exclusive.
2. Query the defining source for the kind (base → characters.json; variant
   → obtain route → MP file / event table / banners / pages; the rest →
   RESEARCH.md's chapter/event/debut/minigame tables).
3. Cross-checks: `updateLog.json` lower bound; `variant_match1.json` hits
   (per the rule above); first banner of the carrier (≥ base date).
4. Verdict: **confirmed** (evidence agrees with the recorded date) ·
   **corrected** (evidence contradicts it; old → new recorded) ·
   **open** (conflicting or missing evidence; flagged, no silent pick).
5. Corrections are applied to `database/models.json` in place (entry order
   and all other fields untouched) and listed in the bucket file.

## Bucket file format

`BUCKET_<X>.md`: header (range, status), one table row per entry —
`# | id | name | date | evidence (source + citation) | verdict` — then
**Corrections** (old → new, reason) and **Checks** (invariants re-run for
the bucket).

## Cross-bucket notes (findings that predate the bucket they land in)

- **Data-mined sub-models inherit the parent's date (hazard for
  later buckets)** — BUCKET_02's c962–c964 (Product 12 sub-models
  B-0006/C-1002/6000-D) carried the parent Product 12's launch date
  although all three debut in the OuteR:Automata collab
  (**2023-09-01**; wiki Minor characters/Collaboration event infoboxes,
  corrected + RESEARCH.md corrections table). If a later bucket
  contains named sub-models of a mass-produced or collab parent
  (c9xxx "X: Y" names), check the Minor characters pages for an
  individual debut before accepting the parent's date. **Second
  instance (BUCKET_03, 2026-11-04):** c985/c989/c990/c992/c994
  carried the base Yuni/Rapi launch date although the models are
  **distinct from the INTL bases** (user-confirmed) — client Live2D +
  sprite assets absent from nikke.gg INTL data, first seen by the
  Nikke-db viewer in post-2024 client updates. Resolution: the four
  Rapis (c989/c990/c992/c994) belong to the **Rapi: Red Hood**
  release (c016) → **2025-01-01** (user identification; viewer log
  2024-12-27 "Rapi ×4 + Rapi Hood" = the pre-staged batch); c985
  Yuni remains **`null`** (open item). Generalized hazard: any `c9xx`
  row whose name matches an INTL character is *not* automatically a CN
  copy of it — check identity before accepting the inherited date.

- **Launch cohort (BUCKET_01/02/03)** — composition and
  independent verification (2026-11-04; full write-up in
  BUCKET_01.md "Launch-cohort verification"): **63 INTL bases** dated
  2022-11-04 = 54 named NIKKEs + 9 mass-produced units (`c300`–`c308`).
  **Corrected 2026-11-03:** `c472`/`c473` (previously counted as "2 CN
  sister copies") are actually the 2026 fourth-anniversary characters
  **Scarlet: Goddeath** (2026-11-05) and **Rapunzel: Sanctuary**
  (2026-10-29) — the scraper filed them under their base characters;
  excluded from the cohort (BUCKET_02.md rows 23–24). Current
  counts: `models.json` has 117 rows dated 2022-11-04 (63 INTL bases +
  26 INTL story/boss scene models + 28 CN `c9xx`); `characters.json`
  has 73 entries dated 2022-11-04 (71 true launch: 63 INTL + 8 CN; plus
  the 2 misfiled 2026 characters). The official pre-launch
  "Developer's Notes" (nikke-en.com, pub 2022-11-03) states **62
  playable characters at launch** — the INTL cohort (63
  units) matches within ±1: **open item** — identify the residual
  (blog miscount vs. one cohort member whose true date differs) via the
  launch-window capture of the official site (Wayback Machine; IA is
  blocking this IP 2026-11-04 — browser URL in BUCKET_01.md). Boundary
  corroborated: the only other November-2022 base dates are Helm
  (2022-11-10) and Laplace (2022-11-24) = the official "New Character"
  patch-note items; pre-registration rewards (SR Ether c291 / SSR Diesel
  c072) are cohort members. The three sisters (c220–c222) are playable
  combat units (official patch notes document their skills — Rapunzel's
  heal, Snow White's "Seven Dwarves: I" burst, Scarlet's cutscenes), not
  story-only models. Per-name: **41/41 BUCKET_01 bases confirmed on the
  live International wiki** (`releaseDate = 4 November 2022`, fetched
  2026-11-04, `research2/intl_launch41_dates.json`) — note that wiki is
  the `characters.json` upstream (RESEARCH.md §Sources), so it is a
  consistency check, not independent; the main `nikke.fandom.com`
  instance's API was returning empty during this pass.

- **BUCKET_03/04** (late-Dec/Jan 2022–23 entries) — from the Brand New
  Year press release (`research2/sa_brandnewyear.html`, Sakura Index,
  publ. 2022-12-29; update 2022-12-28): "New costumes for the New Year"
  = Helm – Chandelier (New Year event pass → c352_01 = 2022-12-28 ✓),
  Sugar – Hard Boiled (January Mission Pass → 2023-01-12; variant not
  present in models.json — base c040 "D" only; **zero official-site
  mentions of "Hard Boiled"**), Julia – Mild Nocturne ("can be obtained
  in the costume shop" → c150_01 = 2022-12-28 ✓, independently
  corroborates the wiki's "Costume Shop Update" section; also named in
  the official "Update on December 29", pub 2022-12-26, as is
  Chandelier). D-Outsiders (2023-01-12, `sa_doutsiders.html`):
  **no costumes** — consistent with the wiki page. The official archive
  also documents Dolla's "Dark Rose" as the Feb 22, 2023 Mission Pass
  premium (2023-02-22).
- **BUCKET_03** (Dec 2022 entries) — from the Miracle Snow press release
  (`research2/sakuraindex_winter.html`, Sakura Index, publ. 2022-12-12;
  event Dec 8–28, 2022, wiki-corroborated):
  - c210_01 Exia Joy to the Nerds 2022-11-24 → **2022-12-08**: listed as
    one of the "5 new costumes" of the Miracle Snow version ("permanently
    available in the Costume Shop"); the 2022-11-24 (Hightech Toy) value
    appears to be wrong. **Officially confirmed**: nikke-en.com "Update
    on December 8" (pub 2022-12-05) lists "④ Exia – Joy to the Nerds …
    Shop opens: After the maintenance on Dec 8, 2022" (as does the
    official "Update on December 20" re-listing).
  - c090_01 Emma Color me Red 2022-12-08 ✓ confirmed (same article:
    "available for a limited time in the Winter Pass").
  - c203 Rupee: Winter Shopper 2022-12-08 ✓ confirmed (banner Dec 8–28).
  - c121 Anne: Miracle Fairy 2022-12-15 ✓ confirmed (banner Dec 15–28).
  - c193 Neve 2022-12-08 — open question: the press release says her
    (SR) banner ran Dec 15–28 (like Anne's), while characters.json/wiki
    say 2022-12-08 (event start). The article's Neve paragraph also
    contains a copy/paste error ("Anne will be available…"), so weigh
    both; the wiki infobox (Neve page) decides at bucket time.
    **Resolved in BUCKET_03: 2022-12-08 confirmed** — official
    "Update on December 8" names Neve's debut in the Dec 8 update
    ("Available from: End of Dec 8 maintenance to … Dec 28"); the
    press's Dec 15 is the event's second phase (Eternal Memory /
    Anne gacha start).

- **Co-Op boss debut dates (BUCKET_04/06 items, from BUCKET_03's
  Co-Op history table, `research2/p_coop.txt`)** — the wiki Co-Op
  Battle page lists 72 events, oldest **2022-11-18 (Alteisen MK.VI)**:
  (a) `mbg001` "Boss: Alteisen" was dated 2023-10-19 in models.json,
  but the table shows an Alteisen MK.VI Co-Op already on 2022-11-18 —
  **resolved in BUCKET_06: → 2022-11-18.** The director's launch dev
  note (2022-11-03) says Co-Op "will be rolled out sequentially"
  *after* launch (not a launch feature), and the Nov 10 update post —
  the closest documented update before the first Co-Op — lists no
  Co-Op content; the full client dump has exactly one Alteisen boss
  model, so the 2022 Co-Ops used mbg001 and its first appearance is
  the 2022-11-18 Co-Op (the 2023-10-19 value was the 2023-10-20
  "code=water" re-patch); (b) `eba003`
  Gatekeeper Blue/Green/Red (2023-02-22) — the first Gatekeeper Co-Op
  in the table as parsed is 2026-08-28; re-verify the first
  appearance from the full table at bucket time (BUCKET_04).
  **Resolved in BUCKET_04: eba003 trio confirmed 2023-02-22** — the
  official "Version Update on February 22" lists "④ BULLET X
  CHAINSAW Special Coordinated Operation … Collaboration Boss,
  Gatekeeper"; the wiki Co-Op table simply has no 2023 Gatekeeper
  rows (table gap, not counter-evidence). BUCKET_03
  corrections for the same pattern: eba001 Storm Bringer → 2022-12-20
  (first Co-Op 2022-12-23), ebg001 Land Eater → 2022-12-28 (first
  Co-Op 2023-01-06).

- **BUCKET_04** (c022_01 Signal Dramatic Chocolate): the Maid in Valentine
  page (2023-02-01) "February Mission Pass Update" names the costume, the
  Feb 1 update press release (`sa_valentine.html`) lists "Special
  Costume: Signal – Dramatic Chocolate (February Mission Pass, Feb 1–28)",
  and the official nikke-en.com "Update on February 1" (pub 2023-01-30)
  names it as the February MP premium → three-source confirmation of
  2023-02-01 (= MP S4 start).
- **BUCKET_07/08** — two MP-premium corrections identified (event-date →
  MP-refresh-date, per the rulebook):
  - c072_04 Diesel Midnight Strawberry 2024-04-25 → **2024-05-01**: Last
    Kingdom page (2024-04-25) "Mission Pass Update": "refreshed on the
    first day of May … the premium track will offer the costume
    'Midnight Strawberry' for Diesel"; `mp_costumes.json` S19 = Diesel
    (Midnight Strawberry), start 2024-05-01. (The Nikke-db 2024-04-28
    "Added Diesel Midnight Strawberry" is the pre-staged client asset —
    obtainable date is the MP refresh.)
  - c032_01 Miranda Thief of Justice 2024-09-19 → **2024-10-01**: Jinx
    Player page (2024-09-19) "October Mission Pass Update": "refreshed on
    the first day of October … the premium track will offer the costume
    'Thief of Justice' for Miranda"; `mp_costumes.json` S24 = Miranda,
    start 2024-10-01.
  - **Generalized in BUCKET_04 (2026-11-05):** three more instances,
    all the same rule — c112_01 Viper Toxic Rabbit 2023-01-19 →
    **2023-05-01** (S7 premium; nikke.gg client data: "Obtained from
    a Mission Pass"), c202_01 Dolla Dark Rose 2023-02-22 →
    **2023-03-01** (S5), c430_01 Noise Cherry Blossom Stage 2023-03-30
    → **2023-04-01** (S6). Two misattribution flavors: (a) the
    variant inherits the base's gacha start (c112_01 — the wiki
    releaseDate is the inherited value); (b) the premium is dated to
    the *announcing* update, but an update post lists the **next**
    month's MP (the Feb 22 post announces the March MP, the Mar 30
    post the April MP) → premium = first of the following month.
    Check every MP-flagged variant against `mp_costumes.json` + the
    nikke.gg client data.
- **BUCKET_09/10** (c016_01–03) / **BUCKET_13/14** (c017_01/02): open
  question — "skin flavor" vs separate **Costume Gacha** skins. Nikke-db
  viewer added "Red Hood new skins" in the Goddess Fall batch (log
  2025-11-02) although the Red Hood SSR gacha opened 2025-01-01; the Star
  Anis page documents **two** Crown-gacha costumes for Anis: Star —
  "Starlight" and "T.T. Star" (event "Costume Gacha Anis Star
  (Starlight)" starts 2026-04-30, a week after the SSR). If they are
  gacha skins they take the gacha dates, not the parent's.
  **c016_01–03 RESOLVED in BUCKET_09** (module + dedicated gacha pages):
  they are separate gacha/poll/MP skins — Red Flavor gacha 2025-07-17,
  Cherished Red poll reward 2025-04-19, Shining Light MP S43 2026-05-01
  (c017_01/02 still open for BUCKET_13/14).
- **Costumes-page ordering** is not strictly chronological (the Halcyon
  Days block lists Strawberry Flower 2023-10-05 before Black Sunday
  2022-11-04) — do not use listing order as a per-item date bound
  (RESEARCH.md's "roughly chronological" is an overstatement; see
  BUCKET_01 dig).

## Status

| Bucket | Entries | Range (id, current date) | Status | Corrections |
|---|---|---|---|---|
| BUCKET_01 | 1–50 | `c010` … `c210` (2022-11-04) | done — awaiting review | 5 |
| BUCKET_02 | 51–100 | `c212` … `c964` (2022-11-04 → 2026-11-05) | done — corrections applied (c472/c473 re-identified) | 5 |
| BUCKET_03 | 101–150 | `c985` … `c925` (2022-11-04 → 2025-01-01) | done — awaiting review | 4 (+4 set, +1 dropped) |
| BUCKET_04 | 151–200 | `c929` … `ltk` (2023-01-12 → 2024-12-26) | done — awaiting review | 4 |
| BUCKET_05 | 201–250 | `c191_01` … `c260_01` (2023-04-27 → 2024-04-25) | done — awaiting review | 4 |
| BUCKET_06 | 251–300 | `c070_02` … `c082_02` (2023-09-01 → 2023-12-28) | done — awaiting review | 6 |
| BUCKET_07 | 301–350 | `c971` … `c281_01` (2023-12-28 → 2025-06-01) | done — awaiting review | 6 |
| BUCKET_08 | 351–400 | `lastkingdom` … `c403_01` (2024-04-25 → 2025-12-30) | done — awaiting review | 4 |
| BUCKET_09 | 401–450 | `smol_ade` … `c016_03` (2024-02-05 → 2026-05-01) | done — awaiting review | 14 |
| BUCKET_10 | 451–500 | `smol_mpriv` … `c513_03` (2024-02-05 → 2026-07-02) | done — awaiting review | 9 |
| BUCKET_11 | 501–550 | `unbreakablesphere` … `c9002` (2025-04-24 → 2025-11-20) | done — awaiting review | 2 |
| BUCKET_12 | 551–600 | `c093` … `c111_01` (2025-08-07 → 2025-11-20) | done — awaiting review | 10 |
| BUCKET_13 | 601–650 | `blankticket` … `c9026` (2025-11-20 → 2026-03-19) | done — awaiting review | 5 |
| BUCKET_14 | 651–700 | `twoxtwo1` … `c9029` (2026-03-19 → 2026-07-23) | done — awaiting review | 3 |
| BUCKET_15 | 701–740 | `c9030` … `c405` (2026-07-23 → 2026-09-24) | done — awaiting review | 19 |
