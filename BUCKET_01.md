# BUCKET_01 — entries 1–50 (`c010` … `c210`, 2022-11-04 → 2022-11-04)

Status: **done — awaiting review** · Reviewed: —

## Cohort evidence (applies to the 41 base rows)

- `database/characters.json` — all 41 rows carry `release_date` = **2022-11-04**
  (primary source; verified against wiki infoboxes 2026-10-24 per
  RESEARCH.md §Sources). Cohort composition (2026-11-04, see the
  verification section below): the launch cohort is **63 INTL bases** —
  54 named NIKKEs, 9 mass-produced units (`c300`–`c308`);
  `models.json` holds 117 launch-dated rows in total (63 INTL bases +
  26 INTL story/boss scene models + 28 CN-exclusive `c9xx`),
  `characters.json` 71 true launch entries (63 INTL + 8 CN).
  *(Corrected 2026-11-03: the two "CN copies of the sisters"
  (`c472`/`c473`) counted here are actually the 2026
  fourth-anniversary characters Scarlet: Goddeath / Rapunzel:
  Sanctuary — see BUCKET_02.md rows 23–24; they never belonged to the
  launch cohort.)* This bucket carries the first 41 in file order
  (`c010` … `c210`); the other 22 INTL launch bases
  (`c212`, `c220`–`c242`, `c291`, `c300`–`c308`, `c430`–`c432`)
  land in BUCKET_02.
- **Independent verification (2026-11-04; `nikke_official_news.json`)** —
  the official launch posts confirm both the date and the cohort size
  without reference to the wiki: "Official Launch FAQ" (pub 2022-11-02):
  "The game will be released globally on November 4th, 2022";
  "Developer's Notes" (pub 2022-11-03, the director's pre-launch note):
  "10 new characters have been added, making for a total of **62 playable
  characters at launch**"; "Official Launch Guide" (pub 2022-11-04):
  "is officially launched now!". The INTL cohort (63 units: 54 named +
  9 mass-produced) matches 62 within ±1; the pre-registration rewards
  named in the FAQ/Guide ("SR character Ether *1, SSR character Diesel
  *1") are both in the cohort (`c291`, `c072`); and the only other
  November-2022 base dates in the file are Helm (2022-11-10) and Laplace
  (2022-11-24) — exactly the "New Character" items of the official Nov 10
  / Nov 24 patch notes → the cohort boundary is corroborated on all
  corroborated on all sides. Per-name: the live International wiki
  (the `characters.json` upstream — consistency check, not independent)
  confirms 41/41 at 2026-11-04
  (`research2/intl_launch41_dates.json`); the independent
  launch-window capture of the official site is still pending (IA
  blocking this IP; captures from 2022-11-04..10 exist — open
  `http://web.archive.org/web/20221104142542/https://nikke-en.com/` in
  a browser; see the verification section below).
- `database/banners.json` — the first rows of the GLOBAL banner history are
  launch-character rate-ups: Helm **2022-11-10** → 11-23 and Laplace
  **2022-11-24** → 12-07 (the first two weeks after launch; the Hightech Toy
  update 2022-11-24 added chapters 17–18 per RESEARCH.md's chapter table).
- `updateLog.json` starts 2023-10-01 — no lower-bound entries predate the
  launch assets.

| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c010 | Rapi | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 2 | c011 | Neon | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 3 | c012 | Anis | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 4 | c013 | Marian | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 5 | c020 | Delta | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 6 | c022 | Signal | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 7 | c030 | Poli | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 8 | c032 | Miranda | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 9 | c060 | Belorta | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 10 | c061 | Mica | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 11 | c070 | Brid | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 12 | c071 | Soline | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 13 | c072 | Diesel | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 14 | c080 | Centi | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 15 | c082 | Liter | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 16 | c090 | Emma | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 17 | c091 | Vesti | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 18 | c092 | Eunhwa | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 19 | c101 | Drake | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 20 | c102 | Maxwell | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 21 | c110 | Crow | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 22 | c120 | N102 | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 23 | c130 | Mary | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 24 | c131 | Pepper | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 25 | c140 | Sugar | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 26 | c141 | Milk | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 27 | c142 | Frima | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 28 | c150 | Julia | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 29 | c160 | Yuni | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 30 | c161 | Mihara | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 31 | c170 | Privaty | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 32 | c171 | Yulha | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 33 | c172 | Admi | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 34 | c180 | Guillotine | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 35 | c181 | Maiden | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 36 | c190 | Ludmilla | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 37 | c191 | Alice | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 38 | c200 | Rupee | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 39 | c201 | Yan | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 40 | c202 | Dolla | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 41 | c210 | Exia | 2022-11-04 | `characters.json` `release_date` (launch cohort — see note) | confirmed |
| 42 | c010_01 | Rapi_old | 2022-11-04 | old rig of c010; asset `l2d/c010_01` present in the GLOBAL client tree (`nikkedb_tree.txt`, 14 files); old rigs follow the parent model (RESEARCH.md, cf. c350_old) | confirmed |
| 43 | c010_02 | Rapi White Promise | 2022-11-04 | costume module: obtain **Closed Beta gift** (series White Promise); nikke.gg: "Obtained from the CBT Special Costume"; asset `l2d/c010_02` in the GLOBAL tree; RESEARCH.md: the CBT gift shipped in the launch client | confirmed |
| 44 | c011_01 | Neon Bling Bullet | 2022-11-04 | module: **Halcyon Days \| Cash Shop bundle**; nikke.gg: $1.00 package (Costumes-page trivia: the only bundle costume that is not $19.99); **Recruit page shop catalog** (`recruit.txt` §Shop Packages): "Bling Bullet Package — **New Server Souvenir** — $1.00 (100k Credit + Neon Bling Bullet)", listed just before the Sunrise Pass (New Year 2023) row → launch/new-server-window product; full-text search: no event page announces it; **official site archive (108 posts, 2022-11-02 → 2024-01-01): zero mentions of "Bling Bullet"/"New Server Souvenir"** and the launch posts (Official Launch Guide 2022-11-04 / FAQ 2022-11-02) carry no shop/bundle section (dig, points 8–9); **Sakura Index**: no article on the site mentions it, and it is absent from every documented update costume list 2022-12-08 → 2023-02-22 → launch window holds; asset in GLOBAL tree | confirmed |
| 45 | c030_01 | Poli Sweet Holic | 2022-12-08 | **Official pre-announcement** (nikke-en.com "Update on December 8", pub 2022-12-05): "2.2 Permanent Costumes: ① Poli – Sweet Holic ② Brid – Model Worker ③ Maiden – Covert Nurse ④ Exia – Joy to the Nerds * Shop opens: After the maintenance on Dec 8, 2022 * How to obtain: Cash Shop → Costume Shop"; corroborated by the Sakura Index Miracle Snow press (2022-12-12) and the wiki Miracle Snow window (dig, points 7–9) | **corrected** (2022-11-04 → 2022-12-08) |
| 46 | c070_01 | Brid Model Worker | 2022-12-08 | same official pre-announcement ("Update on December 8", pub 2022-12-05): "② Brid – Model Worker … Shop opens: After the maintenance on Dec 8, 2022 … Cash Shop → Costume Shop"; corroborated by the Sakura Index Miracle Snow press; the 2023-04-04 wiki section addition is documentation, not ship | **corrected** (2022-11-04 → 2022-12-08) |
| 47 | c072_01 | Diesel Black Sunday | 2022-11-04 | module: **Halcyon Days \| Mission Pass Season 1**; `mp_costumes.json` S1 = Diesel (Black Sunday), start **2022-11-04** (the monthly MP launched with the game); matcher hit Unbreakable_Sphere 2025-04-24 = documented false hit (costume-gallery re-list — RESEARCH.md final pass corrected this entry) | confirmed |
| 48 | c141_01 | Milk Extreme Fighter | 2023-02-22 | **Official patch notes** (nikke-en.com "Version Update on February 22", pub 2023-02-22; user-supplied URL): "2.1 Permanent Costumes: Milk – Extreme Fighter * Shop opens: After the maintenance on February 22, 2023. From the end of the February 22 maintenance to 4:59:59, March 2, Extreme Fighter is on sale! * How to obtain: Cash Shop → Costume Shop"; pre-announced in "Update on February 22, 2023" (pub 2023-02-20); the 2023-09-01 "Optimization" hit is a battle-pose bug fix; earlier corpus evidence (no announcement; wiki batch-documented) consistent — the sale post-dated launch (dig, points 8–9) | **corrected** (2022-11-04 → 2023-02-22) |
| 49 | c170_01 | Privaty Government Grunt | 2023-02-01 | **Official pre-announcement** (nikke-en.com "Update on February 1", pub 2023-01-30): "2.2 Permanent Costume: Privaty – Government Grunt * Shop opens: After the maintenance on February 1, 2023 * How to obtain: Cash Shop → Costume Shop" (Maid in Valentine update) — not launch; corroborated by the Sakura Index Feb 1 press (2023-02-02, the only site-wide hit for the name); RESEARCH.md: the INT cash-shop costume — **not** the CN-exclusive "Destined in Blue" | **corrected** (2022-11-04 → 2023-02-01) |
| 50 | c181_01 | Maiden Covert Nurse | 2022-12-08 | same official pre-announcement ("Update on December 8", pub 2022-12-05): "③ Maiden – Covert Nurse … Shop opens: After the maintenance on Dec 8, 2022 … Cash Shop → Costume Shop" (also re-listed in "Update on December 20", pub 2022-12-19); corroborated by the Sakura Index Miracle Snow press (dig, points 7–9) | **corrected** (2022-11-04 → 2022-12-08) |

## Dig: the six Halcyon-Days cash-shop costumes (rows 44–50)

These six are the only entries in the file dated **by rule rather than by
announcement**; the corpus was mined for a pin on each:

1. **Full-text search** (earlier pass, `research/costume_search.json`):
   each name occurs only on its character/gallery/Costumes pages and in
   story pages where the words are prose (e.g. "Model Worker" in Elysion
   text, "Government Grunt" describing troops). **No event page, shop
   section, or pass page names any of them as a product** — except Bling
   Bullet's Recruit-page shop entry (row 44).
2. **Per-update documentation pattern**: cash-shop costume sales *are*
   documented per update — the first such section is **Brand New Year**
   (2022-12-28) "Costume Shop Update" (Julia "Mild Nocturne" only).
   Hightech Toy (2022-11-24) and D-Outsiders (2023-01-12) carry no costume
   section at all; no other cached update page names the six → they are
   not tied to any documented update.
3. **Character-page revision history**
   (`research2/costume_firstrev_check.json`,
   `costume_charpage_firstrev.json`): the names are absent from the first
   revision of all six character pages (Neon 2021-11-27 and Privaty
   2021-12-05 are CBT-era stubs; Poli 2022-11-29, Brid 2022-12-01, Maiden
   2022-12-12, Milk 2022-12-26); wiki documentation landed in the
   2023-04-03/04 batch → no pin from revisions.
4. **Costumes-page ordering** (`research2/p_Costumes.txt`, Halcyon Days
   block, lines 44–71): the six sit inside the block, but the block is
   **not** chronological (Strawberry Flower 2023-10-05 is listed before
   Black Sunday 2022-11-04) → ordering yields no per-item bound.
5. **nikke.gg** (`gg_costumes_db.json`): all six are permanent $19.99
   "Costume Shop" products (Bling Bullet the $1.00 package); the DB
   carries no dates.
6. **Live wiki query** (2026-11-04, Fandom API — beyond the cached
   corpus; raw results in `/tmp/research2/wiki_deep_six*.json`):
   - **Home page**: a `{{MainPage}}` portal template — no costume
     content.
   - **Full-text search** (API): the same page set as point 1; no
     additional page names any of the six as a product.
   - **Costume gallery image histories**: truncated. Five of the six
     file pages show their oldest surviving revision as a
     **2023-05-02** category edit (pre-dating the 2023-10-05 /
     2024-08-22 gallery renames); Brid's shows only the 2024-08-22
     rename. Original upload revisions and the pre-rename titles are
     not preserved → images were in the wiki by ~2023-05-02 (the
     2023-04-03/04 documentation batch), no earlier bound.
   - **Character-page history**: the Brid page's "Model Worker" section
     first appears in a **2023-04-04** revision — the batch, not a
     release. The other five character pages carry the costume names
     **nowhere in their wikitext** (module-only data).
   - **Module:NikkeCostume**: page history starts **2026-05-26**
     (recreated; 50 revisions) — no pre-2026 data history.

7. **Sakura Index press release** (user-supplied 2026-11-04;
   `research2/sakuraindex_winter.html`, "Nikke: Goddess of Victory
   Winter Update", published 2022-12-12, wire copy dated Dec 8, 2022):
   the **Miracle Snow** Winter Update (Dec 8–28, 2022 — window matches
   the wiki Miracle Snow page infobox `startDate = December 8, 2022` and
   `wiki_events.json`) "introduces 3 new characters, 5 new costumes, PvP
   gameplay" (PvP/Arena launched with it). Characters: Rupee: Winter
   Shopper (banner Dec 8–28 → c203 = 2022-12-08 ✓), Anne: Miracle Fairy
   (Dec 15–28 → c121 = 2022-12-15 ✓), Neve (SR, banner Dec 15–28 → c193
   carried, see VALIDATION.md cross-bucket notes). Costumes — "**5 new
   costumes**": Emma – Color me Red ("available for a limited time in the
   Winter Pass" → c090_01 = 2022-12-08 ✓), **Poli – Sweet Holic**,
   **Brid – Model Worker**, **Maiden – Covert Nurse**, Exia – Joy to the
   Nerds — "the other four costumes will be **permanently available in
   the Costume Shop**" from this version. The three other Halcyon-Days
   cash-shop costumes (Bling Bullet, Extreme Fighter, Government Grunt)
   are **not** on the list.
8. **Sakura Index site-wide exploration** (2026-11-04; WordPress REST
   API; raw files `sa_*.html`, `sa_nikke_posts.json`): the site's NIKKE
   coverage begins **2022-12-10** — it has no launch (November 2022)
   articles. Site-wide full-text search (verified working via content
   hits): **zero** articles mention "Bling Bullet" or "Extreme
   Fighter"; "Government Grunt" appears in exactly one article — the
   February 1 update press release (publ. 2023-02-02,
   `sa_valentine.html`): "…2 new costumes available for Signal and
   Privaty: Special Costume: Signal – Dramatic Chocolate (February
   Mission Pass, Feb 1–28); **Permanent Costume: Privaty – Government
   Grunt — Available in the Costume Shop**". The site documents each
   update's costumes; the complete launch-era record: Miracle Snow
   (2022-12-08): the five above; Brand New Year (2022-12-28, article
   2022-12-29 `sa_brandnewyear.html`): Helm – Chandelier (New Year event
   pass), Sugar – Hard Boiled (January Mission Pass), Julia – Mild
   Nocturne ("can be obtained in the costume shop" — independently
   corroborates the wiki's "Costume Shop Update" section); D-Outsiders
   (2023-01-12, `sa_doutsiders.html`): **no costumes**; Maid in
   Valentine (2023-02-01): Dramatic Chocolate + Government Grunt.
9. **Official site (nikke-en.com) news archive** (2026-11-04; user
   supplied the Extreme Fighter URL): the site is a JS SPA; the content
   API is PlayerInfinite GPTS —
   `POST https://na-community.playerinfinite.com/api/gpts.information_feeds_svr.InformationFeedsSvr/GetContentInfoById`
   with body `{"content_id":"<38-hex>"}` (works anonymously; `gameid`
   must be the string "29080" if sent; the `SearchInfoFeeds` endpoint
   returns no results anonymously). Post ids were recovered from
   **Wayback Machine CDX** snapshots of `newsdetail.html?content_id=…`
   (earliest capture = existence floor) → **108 official posts
   hydrated, 2022-11-02 → 2024-01-01** (`research2/nikke_official_news.json`;
   ids in `research2/wayback_nikke_ids.json`). Findings:
   - **"Update on December 8"** (pub 2022-12-05): "2.2 Permanent
     Costumes: ① Poli – Sweet Holic ② Brid – Model Worker ③ Maiden –
     Covert Nurse ④ Exia – Joy to the Nerds * Shop opens: After the
     maintenance on Dec 8, 2022 * How to obtain: Cash Shop → Costume
     Shop" (+ "2.1 Special Costume: Emma – Color me Red … Winter Pass",
     + "3. New Gameplay: Arena PVP — Arena is now open") →
     **official confirmation of rows 45, 46, 50** (and c210_01 /
     c090_01).
   - **"Update on February 1"** (pub 2023-01-30): "2.2 Permanent
     Costume: Privaty – Government Grunt * Shop opens: After the
     maintenance on February 1, 2023" → **official confirmation of
     row 49**.
   - **"Version Update on February 22"** (pub 2023-02-22, the
     user-supplied post; pre-announced 2023-02-20): "2.1 Permanent
     Costumes: Milk – Extreme Fighter * Shop opens: After the
     maintenance on February 22, 2023. From the end of the February 22
     maintenance to 4:59:59, March 2, Extreme Fighter is on sale!" →
     **row 48 corrected to 2023-02-22**. (Its 2023-09-01 archive hit is
     a battle-pose illustration fix.)
   - **"Update on December 29"** (pub 2022-12-26): names Mild Nocturne
     and Chandelier → corroborates c150_01 / c352_01.
   - **"Bling Bullet" / "New Server Souvenir": zero mentions across all
     108 posts**; the Official Launch Guide (2022-11-04) and Launch FAQ
     (2022-11-02) have no shop/bundle section → the launch bundle was
     never officially announced by name; the wiki's "New Server
     Souvenir" catalog entry remains its only product-window source.

**Conclusion:** the wiki (live and cached) contains no per-costume ship
date for any of the six — its documentation pattern (batch
2023-04-03/04, images by 2023-05-02, module recreated 2026-05-26) is why
they were rule-dated — but the official patch notes and press releases
supply the version-window evidence: **Sweet Holic, Model Worker and
Covert Nurse shipped with the 2022-12-08 version; Government Grunt with
the 2023-02-01 update; Extreme Fighter with the 2023-02-22 update
(rows 45, 46, 50, 49, 48 — corrected)**; **Bling Bullet shipped at
launch** (2022-11-04 — the Halcyon-Days rule and the earliest
defensible ship date, pinned to the new-server window by the "New
Server Souvenir" shop-catalog entry and negative-confirmed by absence
from every official and press costume list 2022-12-08 → 2023-02-22).

## Launch-cohort verification (the 41 base rows), 2026-11-04

Question: are the 41 base rows really the 2022-11-04 launch NIKKEs, with
evidence beyond `characters.json`?

- **The date itself — official, triple-sourced** (`nikke_official_news.json`):
  Launch FAQ (pub 2022-11-02, pre-launch) "released globally on November
  4th, 2022"; Developer's Notes (pub 2022-11-03, signed by director
  Yoo Hyung Suk, pre-launch) "The official release of the game is just
  around the corner"; Launch Guide (pub 2022-11-04) "is officially
  launched now!".
- **The roster size — official, pre-launch**: Developer's Notes: "In
  light of the voting results, 10 new characters have been added, making
  for a total of **62 playable characters at launch**." Cohort in the
  file: 63 launch-dated INTL bases = 54 named + 9 mass-produced
  (`c300`–`c308`: Soldier EG/FA/OW, Product 08/12/23, iDoll
  Flower/Ocean/Sun). *(Corrected 2026-11-03: the "+ 2 CN sister copies
  (`c472`/`c473`)" previously listed here are the 2026 fourth-
  anniversary characters Scarlet: Goddeath / Rapunzel: Sanctuary, not
  launch-cohort members — BUCKET_02.md rows 23–24.)* The official count
  matches within ±1 (mass-produced units are
  playable in-combat; the residual is either a blog miscount or a single
  off-by-one date within the cohort — logged as an open item, see
  VALIDATION.md).
- **The cohort boundary — official patch notes**: the only other
  November-2022 base dates are **Helm 2022-11-10** and **Laplace
  2022-11-24**, matching the "New Character" items of "Notice on Server
  Update on November 10" (pub 2022-11-09: "New Character SSR NIKKE Helm,
  the Unsullied Captain, will be available in Special Recruit!") and
  "Update on November 24" (pub 2022-11-21: "New Character Hero of the
  Ark — SSR Nikke Laplace will join Special Recruit"). No later
  character carries a launch date, and no launch character is dated to
  those two updates; `banners.json`'s first GLOBAL banners (Helm
  11-10→11-23, Laplace 11-24→12-07) agree.
- **Named anchors — official**: pre-registration rewards "SR character
  Ether *1, SSR character Diesel *1" (FAQ + Guide) → `c291`/`c072`, both
  in the cohort (Diesel is row 14 here; Ether spills to BUCKET_02/03).
- **Per-name — live International wiki (2026-11-04)**: all 41 character
  infoboxes on `nikke-goddess-of-victory-international.fandom.com`
  (the upstream of `characters.json` per RESEARCH.md §Sources) carry
  `releaseDate = 4 November 2022` / `4 nov 2022` — 41/41, zero
  deviations, zero fetch failures
  (`research2/intl_launch41_dates.json`); nothing changed since the
  2026-10-24 pass. (The wiki's `action=raw` endpoint is
  Cloudflare-challenged; the MediaWiki `api.php` parse endpoint is not.)
- **Per-name — truly independent, pending**: the decisive source is the
  launch-window capture of the official site (its CHARACTER strip
  server-renders the roster names; captures exist at 2022-11-04 14:25
  UTC, 11-05, 11-07, 11-09 pre-Helm, 11-10 post-Helm, and 2022-10-21
  CBT-era). The Internet Archive is currently blocking this IP (bot
  flag); open in a browser:
  `http://web.archive.org/web/20221104142542/https://nikke-en.com/`.
  Interim position: the cohort evidence above (size ±1, boundary,
  anchors, 41/41 wiki infoboxes) plus the official pre-launch count is
  the verification record.

## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c030_01 | 2022-11-04 | 2022-12-08 | Sakura Index press release (publ. 2022-12-12): the Miracle Snow version (Dec 8–28, 2022) introduces "5 new costumes" — "Poli – Sweet Holic … permanently available in the Costume Shop"; event window corroborated by the wiki Miracle Snow page (startDate December 8, 2022) and `wiki_events.json` |
| 2 | c070_01 | 2022-11-04 | 2022-12-08 | same article: "Brid – Model Worker" is one of the five new Miracle Snow costumes, Costume Shop from the Dec 8 version |
| 3 | c181_01 | 2022-11-04 | 2022-12-08 | same article: "Maiden – Covert Nurse" is one of the five new Miracle Snow costumes, Costume Shop from the Dec 8 version |
| 4 | c170_01 | 2022-11-04 | 2023-02-01 | Official pre-announcement (nikke-en.com "Update on February 1", pub 2023-01-30): "Permanent Costume: Privaty – Government Grunt * Shop opens: After the maintenance on February 1, 2023"; corroborated by the Sakura Index Feb 1 press (the only site-wide mention of the name) |
| 5 | c141_01 | 2022-11-04 | 2023-02-22 | Official patch notes (nikke-en.com "Version Update on February 22", pub 2023-02-22; user-supplied URL): "Permanent Costumes: Milk – Extreme Fighter * Shop opens: After the maintenance on February 22, 2023 … Extreme Fighter is on sale!" (on sale until 4:59:59, March 2) |

## Result

50/50 **verified**, **5 corrected** (c030_01, c070_01, c181_01 →
2022-12-08; c170_01 → 2023-02-01; c141_01 → 2023-02-22 — official
patch notes / pre-announcements, corroborated by Sakura Index press
releases). The remaining 45 are consistent: every base carries
`release_date` 2022-11-04 in `characters.json`, and the launch-dated
non-bases resolve to the launch client (old rig, CBT gift, MP Season 1
premium, or the Halcyon-Days rule — row 44 now negative-confirmed by
the full official + press costume record 2022-12-08 → 2023-02-22).
Row 44 rests on the earliest-defensible-date rule rather than an
individual announcement — see the dig; Bling Bullet is additionally
pinned to the launch window by the Recruit page's "New Server Souvenir"
entry.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 5 date corrections (c030_01, c070_01,
      c181_01, c170_01, c141_01)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered (40 in BUCKET_15)
