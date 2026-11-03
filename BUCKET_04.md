# BUCKET_04 — entries 151–200 (`c929` … `ltk`, 2023-01-12 → 2024-12-26)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Official INT posts (UTC+9, `research2/nikke_official_news.json` — the
  archive covers this whole window): "Update on January 12"
  (2023-01-09), "Update on February 1" (2023-01-30), "Update on
  February 22, 2023" (2023-02-20) + "Version Update on February 22"
  (2023-02-22), "Update on March 15" (2023-03-13/15), "Update on
  March 30" (2023-03-27) + "Update on March 30 [Updated on 7 April]"
  (2023-03-30), "Update on April 13" (2023-04-11/13), "April 2023
  Developer's Note" (2023-04-11).
- MP-season file: `mp_costumes.json` (S4 Signal 2023-02-01, S5 Dolla
  2023-03-01, S6 Noise 2023-04-01, S7 Viper 2023-05-01 — each row =
  that season's premium costume; season start = first of the month).
- Wiki (live fetches this pass): "Shifty" character page
  (`research2/p_shifty.json`, `releaseDate = 1 april 2023`, Full Fool
  Day 2023 April-fools event character; disambiguates Mecha/Mekami
  Shifty as the 2025/2026 April-fools characters), "License to Kill"
  event page (`research2/p_ltk.json`, startDate 2023-04-13),
  "Footstep, Walk, Run" event page (cached
  `research/pages/Footstep_Walk_Run.txt`, startDate 2024-12-26 — D.E.E.P.
  appears in its story), Minor characters pages (cached:
  `p_Minor_characters_*.txt`, `npct_Cecil.txt` — Cecil = Eden
  operator/researcher; Commission tab cross-references Shifty).
- Prior-pass files: RESEARCH.md NPC/minor-character sweeps (c9xx block),
  `minor_debuts.json` (name → debut event), `research2/p_coop.txt`
  (Co-Op history table), `research2/gg_costumes_db.json` +
  `gg_main_fresh.js` (nikke.gg live client data), `research2/updateLog.json`
  (Nikke-db viewer).
- RESEARCH.md: boss-model rule, chapter table (ch 19–20 = D-Outsiders
  2023-01-12; ch 14–15 = CGs only, same update), collab table
  (BULLET X CHAINSAW 2023-02-22).

## Table

| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c929 | Cecil | 2023-01-12 | RESEARCH.md NPC sweep: "Papillon/Johan/Cecil/Joseph in D-Outsiders ch 19 = 2023-01-12"; wiki Cecil page (cached): Eden resident, "operator of Eden, as well as a researcher" — Eden = ch 19 ("A paradise for imperious survivors", official Jan 12 post); `minor_debuts.json` "Joseph": "D-Outsiders" | confirmed |
| 2 | c935 | Joseph | 2023-01-12 | as row 1 (`minor_debuts.json`: debut D-Outsiders; RESEARCH.md sweep) | confirmed |
| 3 | doutsider | D Outsider | 2023-01-12 | official "Update on January 12": "3.1 New Story Event: D-OUTSIDERS * From the end of Jan 12, 2023 maintenance to Jan 25, 2023" | confirmed |
| 4 | mba002 | Boss: Nihilister | 2023-01-12 | official "Update on January 12": "3.4 Coordinated Operation … challenge the Boss Nihilister together" (first Nihilister Co-Op shipped in this update) | confirmed |
| 5 | story1401 | Story 14-01 | 2023-01-12 | official "Update on January 12": "6. New CG in Chapter Stages — Three CGs have been added: Chapter 14: Bait, Chapter 14: Face-To-Face, Chapter 15: Shopaholic"; RESEARCH.md chapter table: "14–15 (CGs only) \| D-Outsiders 2023-01-12" | confirmed |
| 6 | story1403 | Story 14-03 | 2023-01-12 | as row 5 (same ch 14–15 CG batch) | confirmed |
| 7 | story1405 | Story 14-05 | 2023-01-12 | as row 5 (ch 14–15 CG batch; the official list names three CG stages, this stage model ships with the same batch per the chapter table) | confirmed |
| 8 | story1501 | Story 15-01 | 2023-01-12 | as row 5 (Chapter 15: Shopaholic) | confirmed |
| 9 | story1902 | Story 19-01 | 2023-01-12 | official "Update on January 12": "2.1 New Chapters — Added Chapters 19 and 20" (ch 19 = D-Outsiders) | confirmed |
| 10 | story2002 | Story 20-01 | 2023-01-12 | as row 9 (ch 20 = D-Outsiders) | confirmed |
| 11 | c112 | Viper | 2023-01-19 | official "Update on January 12": SSR Viper "Special Recruit duration: From Jan 19, 2023 05:00:00 to Jan 31" (model pre-staged in the Jan 12 client, obtainable from Jan 19 — first-obtainable rule); RESEARCH.md: wiki releaseDate 2023-01-19 | confirmed |
| 12 | c112_01 | Viper Toxic Rabbit | 2023-05-01 | **not** a launch costume: nikke.gg live client data (`gg_costumes_db.json`): "112/Toxic Rabbit — Event — **Obtained from a Mission Pass**"; `mp_costumes.json` S7 = Viper (Toxic Rabbit), start **2023-05-01** → May 2023 MP premium (MP season-start rule); the 2023-01-19 value was the base Viper's gacha start inherited by the variant (RESEARCH.md's "wiki releaseDate" check had read the inherited value) | **corrected** (2023-01-19 → 2023-05-01) |
| 13 | c022_01 | Signal Dramatic Chocolate | 2023-02-01 | official "Update on February 1": "2.1 Special Costume: Signal – Dramatic Chocolate … February Mission Pass" (Feb 1–28); `mp_costumes.json` S4 = Signal, start 2023-02-01; VALIDATION.md three-source note | confirmed |
| 14 | c311 | Cocoa | 2023-02-01 | official "Update on February 1": "1.1 SSR Cocoa — a professional maid and the leader of Maid For You, will join Special Recruit" (from the end of the Feb 1 maintenance) | confirmed |
| 15 | c312 | Soda | 2023-02-01 | official "Update on February 1": "1.2 SSR Soda — the clumsy maid in charge of household chores" (same update) | confirmed |
| 16 | c910 | Hologram | 2023-02-01 | RESEARCH.md: "c910 Hologram — Maid in Valentine 2023-02-01 — the projector rig shipped with the Sweet Johnny manager hologram (event story: 'a hologram appears and introduces itself as … Sweet Johnny'); reused in the 2025 Pirate Cafe minigame"; official Feb 1 post names the Maid in Valentine event (Feb 1 → Feb 15) | confirmed |
| 17 | c910_01 | Sweet Johnny | 2023-02-01 | as row 16 (the hologram manager model of the same event) | confirmed |
| 18 | maidinvalentine | Maid in Valentine | 2023-02-01 | official "Update on February 1": "3.1 New Story Event: Maid in Valentine * From the end of February 1, 2023 maintenance to 4:59:59 February 15, 2023" | confirmed |
| 19 | c202_01 | Dolla Dark Rose | 2023-03-01 | **not** a Feb 22 premium: official "Update on February 22, 2023" lists it under "**5.2 March Mission Pass** * Sale duration: 00:00:00, March 1, 2023 to 23:59:59, March 31, 2023 … Win Dolla's special costume Dark Rose" — the March MP premium (announced in the Feb 22 update, obtainable from the MP start); `mp_costumes.json` S5 = Dolla (Dark Rose), start **2023-03-01** (MP season-start rule); the 2023-02-22 value was the announcing update's date | **corrected** (2023-02-22 → 2023-03-01) |
| 20 | c800 | Makima | 2023-02-22 | official "Version Update on February 22": "1.1 SSR Makima — Public Safety Devil Extermination Special Division 4, will join Limited-Time Recruit" (BULLET X CHAINSAW, Feb 22 → Mar 15) | confirmed |
| 21 | c800_01 | Makima Coat Off | 2023-02-22 | nikke.gg live client data: "800/Coat Off — Event — **Obtained from BULLET X CHAINSAW event missions**" → first obtainable = event start (official event window Feb 22 → Mar 15) | confirmed |
| 22 | c801 | Power | 2023-02-22 | official: "1.2 SSR Power — Blood Fiend … will join Limited-Time Recruit" (same update) | confirmed |
| 23 | c802 | Himeno | 2023-02-22 | official: "1.3 SR Himeno — The Devil Hunter who signed a contract with the Ghost Devil … can be obtained through the Chainsaw Man Event. When to obtain: From the end of the February 22, 2023 maintenance" | confirmed |
| 24 | c803 | Denji | 2023-02-22 | RESEARCH.md collab table: "c803 Denji … BULLET X CHAINSAW (Chainsaw Man collab, #1) \| 2023-02-22" (wiki releaseDate; event-limited character of the officially-dated event Feb 22 → Mar 15) | confirmed |
| 25 | c803_01 | Denji Chainsaw Man | 2023-02-22 | RESEARCH.md: "c803 Denji, c804 Aki Hayakawa (**+c803_01**)" — same collab debut | confirmed |
| 26 | c804 | Aki Hayakawa | 2023-02-22 | as row 24 (RESEARCH.md collab table) | confirmed |
| 27 | eba003 | Boss: Gatekeeper Blue | 2023-02-22 | official "Version Update on February 22": "④ BULLET X CHAINSAW Special Coordinated Operation … challenge **Collaboration Boss, Gatekeeper**, together" — the Gatekeeper Co-Op shipped in the Feb 22 update (first appearance; BUCKET_03 open item resolved). The wiki Co-Op table (p_coop.txt) has no 2023 Gatekeeper row (oldest cached = Aug 2026) — table gap, official post decisive | confirmed |
| 28 | eba003_green | Boss: Gatekeeper Green | 2023-02-22 | as row 27 (the Co-Op table lists the Gatekeeper trio as code variants fire/iron/wind) | confirmed |
| 29 | eba003_hsta | Boss: Gatekeeper Red | 2023-02-22 | as row 27 | confirmed |
| 30 | c080_01 | Centi Supreme Holiday | 2023-03-15 | official "Update on March 15": "2. New Costume — Permanent Costume: Centi - Supreme Holiday * Shop opens: After the maintenance on March 15, 2023" | confirmed |
| 31 | c381 | Biscuit | 2023-03-15 | official "Update on March 15": "1.1 SSR Biscuit — Who let the dogs out? … man's best friend Biscuit is bounding over!" | confirmed |
| 32 | c932 | Bolt Junior | 2023-03-15 | RESEARCH.md NPC sweep: "Bolt/Bolt Junior/Max/Booboo in Bow-Wow Paradise 2023-03-15"; official: BOW-WOW PARADISE event (Mar 15 → Mar 29, "Mass of dogs have escaped from their shelter") | confirmed |
| 33 | c933 | Bolt | 2023-03-15 | as row 32 (the ch 9 "Search for Bolt Jr." commission dogs are earlier/other models; this one debuts with the event per the sweep) | confirmed |
| 34 | c936 | Max | 2023-03-15 | as row 32 (`minor_debuts.json`: "Max": "Bow-Wow Paradise") | confirmed |
| 35 | c937 | Booboo | 2023-03-15 | as row 32 | confirmed |
| 36 | bowwowparadise | Bow Wow Paradise | 2023-03-15 | official "Update on March 15": "3.1 New Story Event: BOW-WOW PARADISE * From the end of March 15, 2023 maintenance to 4:59:59 March 29, 2023" | confirmed |
| 37 | c160_01 | Yuni Pretty in Pink | 2023-03-30 | official "Update on March 30": "2.3 Special Costume: Yuni – Pretty in Pink … 21-Day Login Event" (Mar 30 → Apr 27) — the model ships with the Mar 30 update (rule: the update that first shipped the model; the 21-day login is the reward condition, not the ship date) | confirmed |
| 38 | c212_01 | Novel Penguin Holmes | 2023-03-30 | official "Update on March 30": "2.2 Permanent Costumes: Novel – Penguin Holmes * Shop opens: After the maintenance on March 30, 2023" | confirmed |
| 39 | c261 | Nihilister | 2023-03-30 | official "Update on March 30": "1.2 SSR Nihilister … is from the second batch of Nikkes in the Liberation" + "5.1 Liberation Update * Gameplay begins: After the maintenance on March 30, 2023 … Nihilister added to Liberation!" (Liberation II; obtainable from the gameplay start) | confirmed |
| 40 | c282 | Sakura | 2023-03-30 | official "Update on March 30": "1.1 SSR Sakura — The noble flower born with the Ark's darkness … Class: Supporter, Weapon: Ichigenkin, Manufacturer: Tetra Line" | confirmed |
| 41 | c430_01 | Noise Cherry Blossom Stage | 2023-04-01 | **not** a Mar 30 shop costume: official "Update on March 30": "2.1 Special Costume: Noise – Cherry Blossom Stage … **can be obtained with April Mission Pass**" (April MP sale Apr 1–30) — the April MP premium (MP season-start rule); `mp_costumes.json` S6 = Noise (Cherry Blossom Stage), start **2023-04-01** | **corrected** (2023-03-30 → 2023-04-01) |
| 42 | c836 | Sakura | 2023-03-30 | RESEARCH.md: "c836 is **Sakura (T.T. Star SSR)** — a playable NIKKE (wiki page created 2023-03-27; her 'Sakura' gacha ran 2023-03-30 → 04-13; infobox: T.T. Star, Supporter, Ichigenkin) — same character/debut as row 40 (the second model of the SSR Sakura release) | confirmed |
| 43 | c9009 | Nihilister | 2023-03-30 | RESEARCH.md: "c9009 Nihilister = Liberation II 2023-03-30" (the Liberation II story model; official Liberation II start Mar 30) | confirmed |
| 44 | cherryblossom | Cherry Blossom | 2023-03-30 | official "Update on March 30": "3.1 New Story Event: CHERRY BLOSSOM * From the end of March 30, 2023 maintenance to 4:59:59 April 13, 2023" | confirmed |
| 45 | c903_01 | Andersen Soaked | 2023-04-01 | RESEARCH.md: "c903_01 Andersen Soaked → 2023-04-01 (Full Fool Day — the protagonist's shirtless/wet model; Andersen is the protagonist, debut ch 1 = 2022-11-04; gallery: 'Andersen (Shirtless) FB.png \| Full Fool Day')"; official Mar 30 post: the April 1 "Full Burst Day" weekend block (Apr 1–3) + "April 2023 Developer's Note": "the … April Fool's event" — the April 1, 2023 April-fools content | confirmed |
| 46 | c907 | Shifty | 2023-04-01 | wiki "Shifty" page (live): `releaseDate = 1 april 2023`; "temporarily playable as a joke character during the quest event **Full Fool Day**, made to commemorate April Fool's Day 2023; she can only be played during the respective missions on the field map"; Central Government operator (rarity R supporter). The 2025/2026 "Mecha/Mekami Shifty" viewer-log entries are the later April-fools characters (wiki disambiguation) | confirmed |
| 47 | c907_01 | Shifty_old | 2023-04-01 | as row 46 (the older rig variant of the same event model) | confirmed |
| 48 | c040 | D | 2023-04-13 | official "Update on April 13": "1.1 SSR D … the assassin who moves forward silently with a heavy cross, joins Special Recruit" (Attacker, Storm Eye (SMG), Elysion) | confirmed |
| 49 | c991 | D.E.E.P. | 2024-12-26 | **not** a 2023-04-13 model: `minor_debuts.json` maps "D.E.E.P." → debut **"Footstep, Walk, Run"**; wiki "Footstep, Walk, Run" event page (cached): `startDate = December 26th, 2024`, "the last event of 2024" — Rapi's past with her mentor Red Hood, where **D.E.E.P.** (a guardian who refers to themselves in the plural; "The Profound"; cf. ch Gene/Birth story mentions) appears; viewer log 2025-01-02 "Added D.E.E.P, Footstep Walk Run Live2D & gallery" (post-staged gallery addition); c991 present in the live INTL client bundle (`gg_main_fresh.js`: "c991_00"). The 2023-04-13 value had no source (the LICENSE TO KILL event page never mentions D.E.E.P.) | **corrected** (2023-04-13 → 2024-12-26) |
| 50 | ltk | License to Kill | 2023-04-13 | official "Update on April 13": "3.1 New Story Event: LICENSE TO KILL * From the end of the April 13, 2023 maintenance to 4:59:59 April 27, 2023"; wiki event page (live): startDate 13 apr 2023, "the 10th story event" | confirmed |

## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c112_01 | 2023-01-19 | 2023-05-01 | the variant is the **May 2023 Mission Pass premium** (nikke.gg live client data: "Obtained from a Mission Pass"; `mp_costumes.json` S7 = Viper Toxic Rabbit, start 2023-05-01), not a launch costume; the recorded value was the base Viper's gacha start inherited by the variant |
| 2 | c202_01 | 2023-02-22 | 2023-03-01 | **March** MP premium (official Feb 22 post: "5.2 March Mission Pass … Win Dolla's special costume Dark Rose"; `mp_costumes.json` S5 start 2023-03-01) — the recorded value was the date of the *announcing* update |
| 3 | c430_01 | 2023-03-30 | 2023-04-01 | **April** MP premium (official Mar 30 post: "obtainable with April Mission Pass", sale Apr 1–30; `mp_costumes.json` S6 start 2023-04-01) — same misattribution pattern |
| 4 | c991 | 2023-04-13 | 2024-12-26 | the model debuts in the **Footstep, Walk, Run** event (wiki minor-character debut mapping + event page startDate 2024-12-26 + D.E.E.P. in its story), not in the 2023-04-13 LICENSE TO KILL update (which never mentions D.E.E.P.) |

## Result

50/50 **reviewed**, **4 corrected** (c112_01 → 2023-05-01; c202_01 →
2023-03-01; c430_01 → 2023-04-01 — all three the MP-premium
misattribution pattern; c991 → 2024-12-26 — wrong event entirely).
Every other row is directly documented by an official update post (the
whole window is covered by the official archive, 2023-01-09 →
2023-04-13), the MP-season file, or the RESEARCH.md NPC/collab sweeps
re-verified this pass. Notable resolutions: the **BUCKET_03 open item
on eba003 Gatekeeper is closed** — the official Feb 22 post documents
the "Collaboration Boss, Gatekeeper" Co-Op as part of BULLET X
CHAINSAW (the wiki Co-Op table is missing the 2023 rows, oldest
cached = Aug 2026 — a table gap, not a counter-evidence); **Shifty**
identified via her wiki page (2023 April-fools "Full Fool Day"
joke character, releaseDate 1 April 2023); **D.E.E.P.** identified
via the Footstep, Walk, Run event story.

**Pattern for later buckets (new):** an update post announces the
*next* month's Mission Pass (the Feb 22 post lists the March MP, the
Mar 30 post the April MP) — MP premiums announced in update X belong
to month X+1 and take the first of that month. Any `_01` variant whose
date equals its base's gacha start should be checked against
`mp_costumes.json` + the nikke.gg client data ("Obtained from a
Mission Pass") before accepting the inherited date.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 4 date corrections (c112_01, c202_01,
      c430_01, c991)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered (40 in BUCKET_15)
