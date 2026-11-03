# BUCKET_05 — entries 201–250 (`c191_01` … `c260_01`, 2023-04-27 → 2024-04-25)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Official INT posts (UTC+9, `research2/nikke_official_news.json` — the
  archive covers this whole window): "Update on April 27" (2023-04-24),
  "Update on May 18" (2023-05-15), "Update on June 1" (2023-05-29),
  "Update on June 15" (2023-06-12), "Update on July 6" (2023-07-03),
  "Update on July 20" (2023-07-17), "Update on August 3" (2023-07-31),
  "Update on August 24" (2023-08-21); May/June Developer's Notes.
- MP-season file: `mp_costumes.json` (S8 Emma 2023-06-01, S9 Frima
  2023-07-01, S10 Yan 2023-08-01 — each row = that season's premium
  costume; season start = first of the month).
- nikke.gg live client data: `research2/gg_costumes_db.json` (costume
  obtain sources: missionpass / eventpass / shop / gacha / event).
- Wiki (live fetches this pass): "Mother Whale"
  (`research2/p_motherwhale.json` — Chapter 21 Stage 21-32 boss, first
  Solo Raid; Co-Op trivia: never featured in a Co-Op), "Indivilia"
  (`research2/p_indivilia.json` — debut **Chapter 24: Banishment**,
  ch 12 as Material H), "Golden Ship" (`research2/p_goldenship.json`,
  startDate 20 july 2023), "First Affection"
  (`research2/p_firstaffection.json`, 2023-08-24 → 08-31; its
  "Version Updates" section lists **no** Mission Pass for that
  update), "Last Kingdom" (cached
  `research2/p_lastkingdom.json` — 33rd story event, 1.5th
  anniversary; "===1.5th Anniversary Pass=== … premium track offers
  the costume 'White Knight' for Snow White"), "Snow White"
  (`research2/p_snowwhite.json`, releaseDate 4 november 2022).
- Prior-pass files: RESEARCH.md (chapter table — ch 21–22 = Over Zone
  2023-04-27, ch 23–24 = Golden Ship 2023-07-20; NPC sweeps —
  c930/c941/c942/c943/c945/c961 = Over Zone, c946/c975 = Nya Nya
  Paradise, c939 = Golden Ship, c263 = Golden Ship; collab/NPC
  "checked and kept" lines), `research2/p_coop.txt` (Co-Op history +
  trivia), `research/costume_ctx.json` + `costume_event_map.json` +
  `costume_records.json` (wiki MP/pass premium gallery, previous
  pass).
- RESEARCH.md: boss-model rule, first-obtainable rule.

## Table

| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | c191_01 | Alice Sweet Home | 2023-04-27 | official "Update on April 27": "2.1 Special Costume: Alice – Sweet Home … can be obtained with the **Wonderland Pass**" (the Over Zone event pass; 6.1 new commodities of this update) — obtainable from the April 27 update | confirmed |
| 2 | c233 | Dorothy | 2023-04-27 | official "Update on April 27": "1.1 SSR Dorothy — Inherit's leader and Eden's angel … Special Recruit: From the end of the April 27, 2023 maintenance" (OVER ZONE event update) | confirmed |
| 3 | c392 | Rei | 2023-04-27 | official "Update on April 27": "1.2 SSR Rei — … Rei of School Circle joins the lineup" (same update) | confirmed |
| 4 | c930 | Beatrice | 2023-04-27 | RESEARCH.md NPC sweep: "c930 Beatrice / c941 Pinne / c942 Commander (GODDESS) / c943 Liliweiss / c961 Oswald, at Over Zone 2023-04-27" (OVER ZONE = April 27 update per the official post) | confirmed |
| 5 | c941 | Pinne | 2023-04-27 | as row 4 | confirmed |
| 6 | c942 | Commander (GODDESS) | 2023-04-27 | as row 4 (the Over Zone story's commander model) | confirmed |
| 7 | c943 | Liliweiss | 2023-04-27 | as row 4 | confirmed |
| 8 | c945 | Katie | 2023-04-27 | RESEARCH.md: "c945 Katie = 2023-04-27 (Chapter 22 commission)"; official post adds Chapters 21 and 22 in this update | confirmed |
| 9 | c961 | Oswald | 2023-04-27 | as row 4 | confirmed |
| 10 | c961_01 | Oswald | 2023-04-27 | as row 4 (variant rig of the same Over Zone model) | confirmed |
| 11 | whitememory1 | White Memory 1 | 2023-04-27 | official "Update on April 27": "3.2 Mini Game: White Memory * From the end of April 27, 2023 maintenance to 4:59:59 May 18, 2023 — Fill up Snow White's search log in the mini game" (event models) | confirmed |
| 12 | whitememory2 | White Memory 2 | 2023-04-27 | as row 11 | confirmed |
| 13 | bba001 | Boss: Mother Whale | 2023-04-27 | wiki "Mother Whale" page (live): "encountered as the titular main antagonist of **Chapter 21**, being the boss of Stage 21-32 and in the first Solo Raid"; official "Update on April 27": "4.1 New Chapters — Added Chapters 21 and 22" (ch 21 = "GIANT WHALE") — the model ships with the update that added the chapter. Not a Co-Op boss (wiki Co-Op trivia: "Mother Whale … are the only Tyrant-class Raptures yet to feature in a Coordinated Operation") | confirmed |
| 14 | story2101 | Story 21-01 | 2023-04-27 | official "Update on April 27": "4.1 New Chapters — Chapter 21: GIANT WHALE flying up in the sky" (RESEARCH.md chapter table: ch 21–22 = Over Zone 2023-04-27) | confirmed |
| 15 | story2201 | Story 22-01 | 2023-04-27 | as row 14 (Chapter 22: INVASION) | confirmed |
| 16 | story2202 | Story 22-02 | 2023-04-27 | as row 14 | confirmed |
| 17 | story2206 | Story 22-06 | 2023-04-27 | as row 14 | confirmed |
| 18 | c200_01 | Rupee Rabbit Deluxe | 2023-05-18 | official "Update on May 18": "2.1 Special Costume: Rupee - Rabbit Deluxe … can be obtained from **Luxury Bunny** along with a new voice, and standing pose" (Coin Rush grand-reopening special gacha item, `gg_costumes_db.json`: gacha, 7000 gems — sale opens with the May 18 update; Bunny X 777 event) | confirmed |
| 19 | c270 | Blanc | 2023-05-18 | official "Update on May 18": "1.1 SSR Blanc — Coin Rush's bunny girl … Special Recruit: From the end of the May 18, 2023 maintenance" | confirmed |
| 20 | 777 | 777 | 2023-05-18 | official "Update on May 18": "3.1 New Story Event: Bunny X 777 * From the end of May 18, 2023 maintenance to 4:59:59 June 1, 2023 — a new event at Coin Rush" (the event's 777 mascot/lobby model; same Coin Rush bunny theme as rows 18–19) | confirmed |
| 21 | c271 | Noir | 2023-05-25 | official "Update on May 18": "1.2 SSR Noir … **Special Recruit duration: From 5:00:00 May 25, 2023** to 4:59:59 June 8, 2023" — the model pre-staged in the May 18 client, first obtainable at the gacha start (first-obtainable rule; same convention as Neon row 30) | confirmed |
| 22 | c090_02 | Emma Office Therapy | 2023-06-01 | the June MP premium (S8): `mp_costumes.json` S8 = Emma (Office Therapy), start 2023-06-01; `gg_costumes_db.json`: "90/Office Therapy — **missionpass**"; RESEARCH.md "c090_02/c282_01 (2023-06-01, Queen's Order)" (wiki maps the June premium to the concurrent Queen's Order event); the June 1 update's bug-fix list ("Emma's Office Therapy costume … shooting motion") confirms it shipped in this client. Not named in any archived post (June MP announcement absent from the archive) | confirmed |
| 23 | c280 | Rosanna | 2023-06-01 | official "Update on June 1": "1.1 SSR Rosanna — the leader of the underworld organization Hedonia … Special Recruit: From the end of the June 1, 2023 maintenance" | confirmed |
| 24 | c282_01 | Sakura Midnight Stealth | 2023-06-01 | official "Update on June 1": "2.1 Permanent Costume: Sakura - Midnight Stealth … Shop opens: After the maintenance on June 1, 2023"; `gg_costumes_db.json`: "282/Midnight Stealth — shop" | confirmed |
| 25 | queensorder | Queen's Order | 2023-06-01 | official "Update on June 1": "3.1 New Story Event: Queen's Order * From the end of June 1, 2023 maintenance to 4:59:59, June 15, 2023" | confirmed |
| 26 | c131_01 | Pepper Ocean Vitamin | 2023-06-15 | official "Update on June 15": "2.1 Special Costume: Pepper - Ocean Vitamin … can be obtained from **BlueWater Pass**" (the BLUEWATER ISLAND event pass; sale opens with the June 15 update) | confirmed |
| 27 | c132 | Mary: Bay Goddess | 2023-06-15 | official "Update on June 15": "1.1 SSR Mary: Bay Goddess — the friendly and mysterious doctor … Limited-Time Recruitment: From the end of the June 15, 2023 maintenance to 4:59:59 July 6, 2023" (variant-character debut) | confirmed |
| 28 | c142_01 | Frima Sea of Sloth | 2023-07-01 | **not** a Blue Water Island costume: `gg_costumes_db.json`: "142/Sea of Sloth — **missionpass**"; `mp_costumes.json` S9 = Frima (Sea of Sloth), start **2023-07-01** → the July monthly MP premium (MP season-start rule). Named in no archived post; the 2023-06-15 value was the staging update (Blue Water Island) | **corrected** (2023-06-15 → 2023-07-01) |
| 29 | bluewaterisland | Blue Water Island | 2023-06-15 | official "Update on June 15": "3.1 New Story Event: BLUEWATER ISLAND * From the end of [June 15] maintenance" (also 1.2 SSR Neon: Blue Ocean, gacha from June 22) | confirmed |
| 30 | c014 | Neon: Blue Ocean | 2023-06-22 | official "Update on June 15": "1.2 SSR Neon: Blue Ocean … **Limited-Time Recruitment duration: From 5:00:00 June 22, 2023** to 4:59:59 July 13, 2023" — pre-staged in the June 15 client, first obtainable at the gacha start (same convention as Noir row 21) | confirmed |
| 31 | c010_03 | Rapi Classic Vacation | 2023-07-06 | official "Update on July 6": "2.2 Special Costume: Rapi – Classic Vacation — can be obtained with 21-Day Login Event" (the event starts with the July 6 update; the model ships with it — rule: the update that first shipped the model) | confirmed |
| 32 | c101_01 | Drake Villain Racer | 2023-07-06 | official "Update on July 6": "2.1 Special Costume: Drake – Villain Racer … Get it from Costume Gacha now!" (gacha sale opens with the July 6 update) | confirmed |
| 33 | c380 | Nero | 2023-07-06 | official "Update on July 6": "1.1 SSR Nero — the cat girl who protects the kittens in the Ark … Special Recruit: From the end of the July 6, 2023 maintenance" | confirmed |
| 34 | c946 | Ruru | 2023-07-06 | RESEARCH.md NPC sweep: "Ruru/Timi, at Nya Nya Paradise 2023-07-06 — Timi is Leona's lion"; official: "3.1 New Event: NYA NYA PARADISE * From the end of July 6, 2023 maintenance to 4:59:59 July 20, 2023" | confirmed |
| 35 | c975 | Timi | 2023-07-06 | as row 34 | confirmed |
| 36 | nyanyaparadise | Nya Nya Paradise | 2023-07-06 | official "Update on July 6": "3.1 New Event: NYA NYA PARADISE" (duration above) | confirmed |
| 37 | c201_01 | Yan Sunrise Market | 2023-08-01 | **not** a Golden Ship/July item: official "Update on July 20": "2.1 Special Costume: Yan – Sunrise Market — can be obtained with the **August Mission Pass**"; `gg_costumes_db.json`: "201/Sunrise Market — **missionpass**"; `mp_costumes.json` S10 = Yan (Sunrise Market), start **2023-08-01** (MP season-start rule). The 2023-07-20 value was the announcing (Golden Ship) update; RESEARCH.md's "Golden Ship MP" note is a misread of "August Mission Pass" | **corrected** (2023-07-20 → 2023-08-01) |
| 38 | c263 | Indivilia | 2023-07-20 | wiki "Indivilia" page (live): infobox `debut = Chapter 24: Banishment` ("she made her debut on Chapter 12 as Material H, but Indivilia made her actual appearance on Chapter 24"); RESEARCH.md chapter table: "23–24 Prison, Banishment — Golden Ship **2023-07-20**" — the model debuts with ch 24, shipped in the Golden Ship update (the Golden Ship event page itself doesn't name her; her later Last Kingdom 2024-04-25 role is a re-appearance) | confirmed |
| 39 | c350 | Mast | 2023-07-20 | official "Update on July 20": "1.1 SSR Mast — the pirate aspirant Nikke who is part of Aegis … Special Recruit: From the end of the July 20, 2023 maintenance" | confirmed |
| 40 | c350_old | Mast_old | 2023-07-20 | as row 39 (the older rig variant of the same debut; RESEARCH.md notes its rig had release_date = null — the character's debut date applies) | confirmed |
| 41 | c939 | Doban | 2023-07-20 | RESEARCH.md NPC sweep: "Doban, at Golden Ship 2023-07-20"; official: "3.1 New Story Event: GOLDEN SHIP * From the end of July 20, 2023 maintenance to 4:59:59 August 3, 2023" | confirmed |
| 42 | goldenship | Golden Ship | 2023-07-20 | official "Update on July 20": "3.1 New Story Event: GOLDEN SHIP" (wiki event page: startDate 20 july 2023) | confirmed |
| 43 | c015 | Anis: Sparkling Summer | 2023-08-03 | official "Update on August 3": "1.1 SSR Anis: Sparkling Summer … Limited-Time Recruitment: From the end of the August 3, 2023 maintenance to 4:59:59, August 24, 2023" (variant-character debut) | confirmed |
| 44 | c082_01 | Liter Guardfish | 2023-08-03 | official "Update on August 3": "2.1 Special Costume: Liter - Guardfish … can be obtained from the **MIGHTY SUMMER PASS**" (the SEA, YOU, AGAIN event pass; `gg_costumes_db.json`: eventpass — sale opens with the August 3 update) | confirmed |
| 45 | c350_01 | Mast A Pirate's Heart | 2023-08-03 | official "Update on August 3": "2.2 Permanent Costume: Mast - A Pirate's Heart * Sale duration: After the end of the August 3, 2023 maintenance * Cash Shop → Costume Shop" | confirmed |
| 46 | c351 | Anchor | 2023-08-03 | official "Update on August 3": "Anchor can be obtained in the new story event, SEA, YOU, AGAIN. * Duration for obtaining: From the end of the August 3, 2023 maintenance to 4:59:59, August 24, 2023" (event-exclusive character, obtainable from the event start) | confirmed |
| 47 | c353 | Helm: Aquamarine | 2023-08-10 | official "Update on August 3": "1.2 SSR Helm: Aquamarine … **Limited-Time Recruitment duration: From 5:00:00 August 10, 2023** to 23:59:59 August 31, 2023" — pre-staged in the August 3 client, first obtainable at the gacha start. This **reverts** the earlier CN-pass correction to 2023-08-03 (RESEARCH.md, which had aligned c353 with c015 on the event infobox startDate): the project convention for pre-staged new characters is the gacha start (Noir 2023-05-25, Neon 2023-06-22 — rows 21/30), and the first-obtainable rule outranks the wiki event-date | **corrected** (2023-08-03 → 2023-08-10) |
| 48 | seayouagain | Sea You Again | 2023-08-03 | official "Update on August 3": "3.1 New Story Event: SEA, YOU, AGAIN * From the end of August 3, 2023 maintenance to 4:59:59 August 24, 2023" | confirmed |
| 49 | c220_01 | Snow White White Knight | 2024-04-25 | **not** an August 2023 costume: wiki "Last Kingdom" page (cached): "===1.5th Anniversary Pass=== An event-exclusive Mission Pass. The premium track offers the costume **'White Knight'** for **Snow White**" (Last Kingdom = 1.5th-anniversary story event, 2024-04-25; the pass refreshed 2024-05-01 with Diesel Midnight Strawberry per the BUCKET_08 note); `gg_costumes_db.json`: "220/White Knight — **eventpass**" (a pass premium, not a shop/MP item). The August 24, 2023 update had no pass at all — the wiki "First Affection" page's Version Updates section lists only Modernia Special / 7-Day Login / Full Burst Day / Union Raid (its "White Knight" squad is a story name, a different thing); the 2023-08-24 value had no source | **corrected** (2023-08-24 → 2024-04-25) |
| 50 | c260_01 | Modernia First Affection | 2023-08-24 | official "Update on August 24": "1.1 Special Costume: Modernia - First Affection … can be obtained from Modernia special" + "2.1 Modernia Special * From the end of the August 24, 2023 maintenance to 4:59:59, September 27, 2023" (popularity-poll winner costume; `gg_costumes_db.json`: "260/First Affection — event"); RESEARCH.md: c260_01 was null in the pre-CN data, set by the CN pass — now independently confirmed | confirmed |

## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c142_01 | 2023-06-15 | 2023-07-01 | the **July** monthly MP premium (nikke.gg "missionpass"; `mp_costumes.json` S9 start 2023-07-01) — the recorded value was the staging update (Blue Water Island) |
| 2 | c201_01 | 2023-07-20 | 2023-08-01 | the **August** monthly MP premium (official July 20 post: "can be obtained with the August Mission Pass"; `mp_costumes.json` S10 start 2023-08-01) — the recorded value was the announcing update; "Golden Ship MP" was a misread |
| 3 | c220_01 | 2023-08-24 | 2024-04-25 | the **1.5th Anniversary Pass** premium of the **Last Kingdom** event (wiki event page, explicit; `gg_costumes_db.json` eventpass) — the 2023-08-24 update contained no pass; the name collision with the "White Knight" squad in the First Affection story explains the misattribution |
| 4 | c353 | 2023-08-03 | 2023-08-10 | first-obtainable = gacha start ("From 5:00:00 August 10, 2023"), per the Noir/Neon convention for pre-staged characters — reverts the earlier CN-pass correction that had aligned c353 to the SEA, YOU, AGAIN event start |

## Result

50/50 **reviewed**, **4 corrected** (c142_01, c201_01 — the
MP-premium misattribution pattern again, both the monthly-MP flavor:
staging/announcing update ≠ obtainable month; c220_01 — wrong event
by 8 months, an anniversary-pass premium misdated to a 2023 costume
update with a name collision; c353 — event-start vs gacha-start,
reverting an earlier correction). Every other row is directly
documented by an official update post (the whole 2023-04-27 →
2023-08-24 window is covered by the archive), the MP-season file +
nikke.gg client data (the two June/July MP premiums whose
announcements are absent from the archive), or the RESEARCH.md
sweeps/chapter table re-verified this pass.

Notable resolutions: **bba001 Mother Whale** identified as the
Chapter 21 Stage 21-32 story boss / first Solo Raid (wiki Rapture
page; it is explicitly *not* a Co-Op boss per the Co-Op page
trivia — so the Co-Op table's absence of it is expected); **c263
Indivilia** chain completed (debut = ch 24 "Banishment" per her
infobox; ch 23–24 shipped with Golden Ship = 2023-07-20 per the
chapter table — the recorded date stands, the old "page date"
rationale was a coincidence); **c50/c260_01 Modernia First
Affection** independently confirmed (official Modernia Special
event). The April 27 post also re-confirms BUCKET_04's c112_01
correction verbatim: "Viper – Toxic Rabbit can be obtained with the
May Mission Pass".

**Pattern for later buckets (reinforced):** MP/anniversary-pass
premiums in `mp_costumes.json` + the nikke.gg client's "Obtained from
a Mission Pass / Event Pass" flag beat the update-post date when they
conflict; an update post announcing "the **Next Month** Mission Pass"
(or an event pass) fixes the premium's month. Watch for name
collisions (a costume sharing a name with a story element of an
earlier event) when a recorded date has no post backing.

## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 4 date corrections (c142_01, c201_01,
      c220_01, c353)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered (40 in BUCKET_15)
