# BUCKET_10 — entries 451–500 (`smol_mpriv` … `c513_03`, 2024-02-05 → 2026-07-02)

Status: **done — awaiting review** · Reviewed: —

## Sources used this pass

- Wiki (live fetches this pass, `research2/b10_*.json`): character pages
  with `releaseDate` — Anchor: Innocent Maid (6 february 2025), Asuka
  Shikinami Langley: WILLE (20 february 2025), Rei Ayanami (Tentative
  Name) (27 february 2025), Trina (13 march 2025), Bready (27 march
  2025), Crust (10 april 2025), Mihara: Bonding Chain (**1 may 2025** —
  not 2025-04-24), Little Mermaid (24 april 2025), Mori (24 april 2025),
  Arcana (15 may 2025), K (29 may 2025); NPC page — Eyeri (debut =
  Chapter 36: Betrayal); Nora page (debut = **Blank Ticket**, "the
  focus character of the events Blank Ticket and Terminus Ticket");
  event pages — New Flavor (startDate March 27th, 2025; "===21-Day Login
  Event - Maid in Bloom=== … The costume 'Maid in Spring' for Ade is
  attainable during this event", "===April Mission Pass=== … the premium
  track offers the costume 'Sweet Chef' for Tia"), Unbreakable Sphere
  (startDate April 24th, 2025 → May 15th, 2025; the 2.5th-anniversary
  event: "===2.5th Anniversary Pass=== … premium track offers 'Beautiful
  You' for Grave", "===2.5th Anniversary Costume Gachas: Abyss Flower and
  Pain Eater=== * Abyss Flower (Little Mermaid) - End of maintenance to
  5:00 May 15th * **Pain Eater (Mihara: Bonding Chain) - 5:00 May 1st to
  5:00 May 22nd**", the minigame is "Bubble March"), Arcane Archive
  (startDate May 15th, 2025), Wave to You (startDate **July 2nd, 2026** —
  the 2026 event that carries the ISLAND BREAKER minigame; "===Costume
  Gacha: Shell Princess=== * End of maintenance to 4:59 July 23rd … A
  Costume Gacha for Little Mermaid"), Blank Ticket (startDate
  **November 20th, 2025** → December 4th, 2025; the 65th story event,
  Soline: Frost Ticket + Nora — the wiki "Blank Ticket" is the 2025-11-20
  event, **not** the 2025-05-29 update), Little Mermaid page trivia
  ("first character with two separate Costume Gacha ('Abyss Flower' and
  'Shell Princess')").
- Module:NikkeCostume/data (`research2/b07y_datamod.json`): the EVA2
  block — school uniforms all "EMERGENCY MISSION challenge" (wave 1),
  "Final Battle: {Asuka,Mari}" = "QUEST MISSION challenge" (wave 1),
  "Ocean's Lament" / "Mystery Muse" / "Soul Connect" = "Passion CaNon -
  {Asuka,Mari,Rei} Pass" (wave 2), "Miss Lookalike from Village-3" =
  "QUEST MISSION challenge" (wave 2); Biscuit "Spring Puppy — Mission
  Pass Season 29", Tia "Sweet Chef — Mission Pass Season 30", Cinderella
  "Beautiful Me — Mission Pass Season 31", Helm "Post-Shower Moment —
  Costume Gacha", Ade "Maid In Spring — Maid in Bloom login reward",
  Grave "Beautiful You — 2.5 Anniversary Pass", Little Mermaid "Abyss
  Flower — Costume Gacha" / "Shell Princess — Costume Gacha", Blanc "No.
  77 Batter — Base Ball Pass", Noir "Baseball Cheerleader — Home In!
  login reward", Mihara: Bonding Chain "Pain Eater — Costume Gacha".
- MP-season file `mp_costumes.json`: S29 Biscuit (Spring Puppy)
  2025-03-01, S30 Tia (Sweet Chef) 2025-04-01, S31 Cinderella (Beautiful
  Me) 2025-05-01.
- The wiki **Event list page 2025 table** (cached
  `research2/b08_eventlist.json`, parsed this pass): Out of Uniform
  2025-01-01, Wisdom Spring 2025-01-16, Romantic Valentine 2025-01-30,
  **Second Quest 2025-02-20**, For Rest 2025-03-13, New Flavor
  2025-03-27, Fool Burst Day 2025-04-01, True Flavor 2025-04-10,
  Unbreakable Sphere 2025-04-24, Arcane Archive 2025-05-15, **Lord, for
  Justice 2025-05-29**, Memories Teller 2025-06-12, …, Blank Ticket
  2025-11-20, Terminus Ticket 2025-12-04, Ark Guardian 2025-12-30.
- `research/ev_dates.json`: second quest 2025-02-20, for rest
  2025-03-13, new flavor 2025-03-27, fool burst day 2025-04-01, true
  flavor 2025-04-10, unbreakable sphere 2025-04-24, arcane archive
  2025-05-15, bready 2025-03-27, arcana 2025-05-15, "pick up 72 mihara
  bonding chain = 2025-05-01", "costume gacha mihara bonding chain (pain
  eater) = 2025-05-01".
- Viewer update log `research2/updateLog.json`: 2025-02-21 "Added Helm
  and Biscuit Skins"; 2025-03-08 "Renamed Grave. Added Avista & Eyeri";
  2025-03-15 "Added Trina & For Rest"; 2025-03-28 "Added Bready, Crust,
  Ade & Tia Skins. Added New Flavor scene"; 2025-04-05 "Added … mustang
  asset. Added Mecha Shifty"; 2025-04-12 "Added true flavor"; 2025-05-02
  "Updated OverSpec Mihara and added her skin. Added Cinderella's skin.
  Updated Little Mermaid and added her skin. Added Jin Mori. … Added Ziz"
  + "Added Unbreakable Sphere album"; 2025-05-18 "Added Arcana and
  Arcane Archive scene"; 2025-06-01 "Live2d: K blanc noir moran lord for
  justice" (the 2025-05-29 batch); 2025-06-02 "Added liter chinese
  skin"; 2026-02-14/15 "Added 5 NPCs … 'NPC: TBA'" / "Updated the names
  for **Nora**, …" (late pickup, Lie Cause Recoil batch).
- Prior-pass files: RESEARCH.md (chapter table — "35–36 | Conversation,
  Betrayal | Second Quest **2025-02-20**", "37–38 | Struggle, Gluttony |
  Unbreakable Sphere 2025-04-24"; c9xx rows — "c9002 Nora = Blank
  Ticket 2025-05-29" (the event label there is a misnomer — see the c9002 row in BUCKET_11),
  "c082_80 Liter (CN) 2025-05-29 — Nikke-db 2025-06-02 'liter chinese
  skin' ⇒ global 2025-05-29 update"; CN rows — "c902_01 Mustang (CN)
  2025-04-01 … Nikke-db 2025-04-05", "story0401_3 … shipped in the
  global client with the 2025-04-01 update (Nikke-db log 2025-04-21)"),
  BUCKET_09 (c501_01 = MP S28 2025-02-01, c016_02 = Poll III reward
  2025-04-19).

## Table
| # | id | name | date | evidence | verdict |
|---|----|------|------|----------|---------|
| 1 | smol_mpriv | Smol Maid Privaty | 2024-02-05 | **not** a Jan 30 item: update log **2024-02-07**: "Added **Smol Maid Privaty** and Smol Ade from the **Perfect Maid Minigame**" — shipped with the 2024-02-05 update (same entry as the smol_ade row, BUCKET_09) | **corrected** (2025-01-30 → 2024-02-05) |
| 2 | piratecafe | Pirate Cafe | 2025-01-30 | the minigame of the Romantic Valentine update — the wiki "Romantic Valentine" page (live) lists "Pirate Cafe" in its soundtrack/event section; update log 2025-02-21: "Added Smol Mast Pirate + Anchor + Sin, **Pirate Cafe**, Romantic Valentine, Sweet Johnny" (the 2025-01-30 client batch) | confirmed |
| 3 | smol_emilia | Smol Emilia | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch) | confirmed |
| 4 | smol_liter | Smol Liter | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch) | confirmed |
| 5 | smol_mary | Smol Mary | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch) | confirmed |
| 6 | smol_mast | Smol Mast | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch; distinct from the separately-named `smol_mast_pirate` row (below) — the log's "Smol Mast Pirate" is the pirate model, the plain Smol Mast has no earlier log entry) | confirmed |
| 7 | smol_mast_pirate | Smol Mast Pirate | 2025-01-30 | update log 2025-02-21 names it explicitly: "Added **Smol Mast Pirate** + Anchor + Sin, Pirate Cafe, Romantic Valentine, Sweet Johnny" (the 2025-01-30 client) | confirmed |
| 8 | smol_pepper | Smol Pepper | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch; no earlier log entry names a Smol Pepper) | confirmed |
| 9 | smol_ram | Smol Ram | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch; no earlier log entry names a Smol Ram) | confirmed |
| 10 | smol_rapi | Smol Rapi | 2025-01-30 | the smol_anchor row (BUCKET_09; same minigame batch; no earlier log entry names a Smol Rapi) | confirmed |
| 11 | smol_rem | Smol Rem | 2025-01-30 | the Romantic Valentine / Pirate Cafe update's Smol batch (update log 2025-02-21 "Added Smol Mast Pirate + Anchor + Sin, Pirate Cafe, Romantic Valentine, Sweet Johnny" is the 2025-01-30 client; no earlier log entry names a Smol Rem) | confirmed |
| 12 | smol_sin_pirate | Smol Sin Pirate | 2025-01-30 | same batch — the log's "Sin" (the Pirate Cafe minigame's pirate Sin) | confirmed |
| 13 | smol_yan | Smol Yan | 2025-01-30 | same batch; no earlier log entry names a Smol Yan | confirmed |
| 14 | c355 | Anchor: Innocent Maid | 2025-02-06 | wiki "Anchor: Innocent Maid" page (live): `releaseDate = 6 february 2025` (the New Year 2025 follow-up SSR) | confirmed |
| 15 | c352_02 | Helm Post-Shower Moment | 2025-02-20 | module: Helm "Post-Shower Moment — Costume Gacha" (the gacha of the 2025-02-20 Second Quest update); update log 2025-02-21: "Added **Helm** and Biscuit Skins" (the 2025-02-20 client) | confirmed |
| 16 | c440 | Eyeri | 2025-02-20 | wiki "Eyeri" NPC page (live): "debut = **Chapter 36: Betrayal**" (Overseer Squad member); RESEARCH.md chapter table: "35–36 \| Conversation, Betrayal \| Second Quest **2025-02-20**" (update log 2025-03-08 "Added Avista & Eyeri" — late pickup of the 2025-02-20 client) | confirmed |
| 17 | c830_01 | Asuka Asuka's School Uniform | 2025-02-20 | module: Asuka "Asuka's School Uniform — **EMERGENCY MISSION challenge**" (the wave-1 challenge of the Second Quest update, 2025-02-20) | confirmed |
| 18 | c831_01 | Rei Rei's School Uniform | 2025-02-20 | module: Rei "Rei's School Uniform — EMERGENCY MISSION challenge" (same wave-1 challenge) | confirmed |
| 19 | c832_01 | Mari Mari's School Uniform | 2025-02-20 | module: Mari "Mari's School Uniform — EMERGENCY MISSION challenge" (same wave-1 challenge) | confirmed |
| 20 | c832_03 | Mari Final Battle: Mari | 2025-02-20 | module: Mari "Final Battle: Mari — **QUEST MISSION challenge**" (wave 1, 2025-02-20) | confirmed |
| 21 | c835 | Asuka: WILLE | 2025-02-20 | wiki "Asuka Shikinami Langley: WILLE" page (live): `releaseDate = 20 february 2025` (EVA2 wave-1 SSR) | confirmed |
| 22 | c835_01 | Asuka: WILLE Final Battle: Asuka | 2025-02-20 | module: "Final Battle: Asuka — QUEST MISSION challenge" (wave 1, 2025-02-20) | confirmed |
| 23 | secondquest1 | Second Quest | 2025-02-20 | the story cutscene models of the Second Quest event — wiki Event list page 2025 table: "Second Quest \| 20 february 2020…" (2025-02-20); `ev_dates.json`: second quest = 2025-02-20; the event shipped chapters 35–36 (update log 2025-03-08 "Added Second Quest. Added story chapter 35-36" — late pickup) | confirmed |
| 24 | secondquest2 | Second Quest | 2025-02-20 | as the secondquest1 row | confirmed |
| 25 | c832_04 | Mari Mystery Muse | 2025-02-27 | **not** a Feb 20 item: module: Mari "Mystery Muse — **Passion CaNon - Mari Pass**" — the wave-2 (Rei (Tentative Name), 2025-02-27) event pass, not the wave-1 event | **corrected** (2025-02-20 → 2025-02-27) |
| 26 | c834 | Rei (Tentative Name) | 2025-02-27 | wiki "Rei Ayanami (Tentative Name)" page (live): `releaseDate = 27 february 2025` (EVA2 wave-2 SSR — the Passion CaNon wave) | confirmed |
| 27 | c834_01 | Rei (Tentative Name) Miss Lookalike from Village-3 | 2025-02-27 | module: "Miss Lookalike from Village-3 — QUEST MISSION challenge" (wave 2, 2025-02-27) | confirmed |
| 28 | c834_02 | Rei (Tentative Name) Soul Connect | 2025-02-27 | module: "Soul Connect — **Passion CaNon - Rei Pass**" (wave 2, 2025-02-27) | confirmed |
| 29 | c835_02 | Asuka: WILLE Ocean's Lament | 2025-02-27 | **not** a Feb 20 item: module: "Ocean's Lament — **Passion CaNon - Asuka Pass**" — the wave-2 (2025-02-27) event pass | **corrected** (2025-02-20 → 2025-02-27) |
| 30 | c381_01 | Biscuit Spring Puppy | 2025-03-01 | **not** a Feb 20 item: module: Biscuit "Spring Puppy — **Mission Pass Season 29**"; `mp_costumes.json` S29 = Biscuit (Spring Puppy), start **2025-03-01** (the March MP — the model itself shipped with the 2025-02-20 client per the log, but the premium opened with the season) | **corrected** (2025-02-20 → 2025-03-01) |
| 31 | c412 | Trina | 2025-03-13 | wiki "Trina" page (live): `releaseDate = 13 march 2025` (the For Rest character); update log 2025-03-15: "Added Trina & For Rest" | confirmed |
| 32 | forrest | For Rest | 2025-03-13 | `ev_dates.json`: for rest = 2025-03-13; wiki Event list page 2025 table: "For Rest \| 13 march 2025" | confirmed |
| 33 | c310_01 | Ade Maid In Spring | 2025-03-27 | module: Ade "Maid In Spring — **Maid in Bloom login reward**"; wiki "New Flavor" page (live): "===21-Day Login Event - Maid in Bloom=== … The costume 'Maid in Spring' for Ade is attainable during this event" (the 2025-03-27 update's login event); update log 2025-03-28 "Added … Ade & Tia Skins" | confirmed |
| 34 | c520 | Bready | 2025-03-27 | wiki "Bready" page (live): `releaseDate = 27 march 2025` (the New Flavor character); `ev_dates.json`: bready = 2025-03-27; update log 2025-03-28 "Added Bready …" | confirmed |
| 35 | newflavor | New Flavor | 2025-03-27 | wiki "New Flavor" event page (live): startDate March 27th, 2025; `ev_dates.json`: new flavor = 2025-03-27; update log 2025-03-28 "Added New Flavor scene" | confirmed |
| 36 | c451_02 | Tia Sweet Chef | 2025-04-01 | **not** a Mar 27 item: module: Tia "Sweet Chef — **Mission Pass Season 30**"; `mp_costumes.json` S30 = Tia (Sweet Chef), start **2025-04-01**; the New Flavor page documents it: "===April Mission Pass=== The Mission Pass will be refreshed on the first day of April. The premium track offers the costume 'Sweet Chef' for Tia" | **corrected** (2025-03-27 → 2025-04-01) |
| 37 | c902_01 | Mustang (CN) | 2025-04-01 | RESEARCH.md CN row: "c902_01 Mustang (CN) — **2025-04-01** — CN-exclusive Mustang skin; Nikke-db 2025-04-05 'chinese exclusive … mustang asset' ⇒ in the global client with the 2025-04-01 update" (Fool Burst Day) | confirmed (previous pass) |
| 38 | c993 | Mecha Shifty | 2025-04-01 | update log 2025-04-05: "Added **Mecha Shifty**" (the 2025-04-01 Fool Burst Day client — 4-day lag, the standard viewer lag for a global update); the recorded date matches | confirmed |
| 39 | story0401_3 | Story 04-02 (CN) | 2025-04-01 | RESEARCH.md CN row: the Chinese version of chapter 4's scene 02 — "shipped in the global client with the **2025-04-01** update (Nikke-db log 2025-04-21: 'Added the Mustang Chinese story scene from chapter 4')" | confirmed (previous pass) |
| 40 | c521 | Crust | 2025-04-10 | wiki "Crust" page (live): `releaseDate = 10 april 2025` (the True Flavor character); update log 2025-04-12 "Added true flavor" | confirmed |
| 41 | trueflavor | True Flavor | 2025-04-10 | `ev_dates.json`: true flavor = 2025-04-10; wiki Event list page 2025 table: "True Flavor \| 10 april 2025" | confirmed |
| 42 | c513 | Little Mermaid | 2025-04-24 | wiki "Little Mermaid" page (live): `releaseDate = 24 april 2025` (the Unbreakable Sphere main character — "the event centers around Little Mermaid") | confirmed |
| 43 | c513_01 | Little Mermaid Abyss Flower | 2025-04-24 | wiki "Unbreakable Sphere" page (live): "Abyss Flower (Little Mermaid) - **End of maintenance** to 5:00 May 15th (UTC+9)" — the gacha opened with the 2025-04-24 update; module: "Abyss Flower — Costume Gacha" | confirmed |
| 44 | c514_01 | Grave Beautiful You | 2025-04-24 | module: Grave "Beautiful You — **2.5 Anniversary Pass**"; wiki "Unbreakable Sphere" page (live): "===2.5th Anniversary Pass=== An event-exclusive Mission Pass. The Premium Track offers the costume 'Beautiful You' for Grave" (the 2025-04-24 2.5th-anniversary event) | confirmed |
| 45 | c561 | Ziz | 2025-04-24 | a 2.5th-anniversary character of the Unbreakable Sphere update — update log 2025-05-02 "Added Ziz" (the 2025-04-24 client; no earlier entry, the character page carries no releaseDate) | confirmed |
| 46 | c590 | Mori | 2025-04-24 | wiki "Mori" page (live): `releaseDate = 24 april 2025`; wiki "Unbreakable Sphere" page: the 2.5th-anniversary login box offers "a copy of Mori, Kilo, or Rei" (update log 2025-05-02 "Added Jin Mori") | confirmed |
| 47 | c162 | Mihara: Bonding Chain | 2025-05-01 | **not** a Apr 24 item: wiki "Mihara: Bonding Chain" page (live): `releaseDate = **1 may 2025**`; `ev_dates.json`: "pick up 72 mihara bonding chain = 2025-05-01" — the 2.5th-anniversary content spanned two updates (the event + Abyss Flower gacha on 04-24, Mihara's recruitment on 05-01); the recorded value was the event's date | **corrected** (2025-04-24 → 2025-05-01) |
| 48 | c162_01 | Mihara: Bonding Chain Pain Eater | 2025-05-01 | wiki "Unbreakable Sphere" page (live): "Pain Eater (Mihara: Bonding Chain) - **5:00 May 1st** to 5:00 May 22nd (UTC+9)" (the gacha opened with the 2025-05-01 update, not the 04-24 one); `ev_dates.json`: "costume gacha mihara bonding chain (pain eater) = 2025-05-01"; update log 2025-05-02 "Updated OverSpec Mihara and added her skin" | **corrected** (2025-04-24 → 2025-05-01) |
| 49 | c511_02 | Cinderella Beautiful Me | 2025-05-01 | **not** a Apr 24 item: module: Cinderella "Beautiful Me — **Mission Pass Season 31**"; `mp_costumes.json` S31 = Cinderella (Beautiful Me), start **2025-05-01** (the May MP announced with the 04-24 Unbreakable Sphere update) | **corrected** (2025-04-24 → 2025-05-01) |
| 50 | c513_03 | Little Mermaid Shell Princess | 2026-07-02 | **not** an Apr 24 item — module: "Shell Princess — Costume Gacha", and the Unbreakable Sphere page's 2.5th-anniversary gacha list is explicitly "Abyss Flower and Pain Eater" only; the wiki "Wave to You" event page (live, startDate July 2nd, 2026): "===**Costume Gacha: Shell Princess**=== * End of maintenance to 4:59 July 23rd … A Costume Gacha for Little Mermaid" — the second (separate) Little Mermaid gacha ran with the 2026 Wave to You event (whose ISLAND BREAKER minigame plays the "Shell Princess" track); the recorded value was the character's debut date | **corrected** (2025-04-24 → 2026-07-02) |
## Corrections

| # | id | Recorded date | Corrected date | Why |
|---|----|---------------|----------------|-----|
| 1 | c381_01 | 2025-02-20 | 2025-03-01 | the **March** MP premium (module S29; `mp_costumes.json` S29 = Biscuit (Spring Puppy)) — the recorded value was the Second Quest announcing update (the model shipped in that client, the premium opened with the season) |
| 2 | c451_02 | 2025-03-27 | 2025-04-01 | the **April** MP premium (module S30; `mp_costumes.json` S30 = Tia (Sweet Chef); the New Flavor page's "April Mission Pass" section) |
| 3 | c511_02 | 2025-04-24 | 2025-05-01 | the **May** MP premium (module S31; `mp_costumes.json` S31 = Cinderella (Beautiful Me)) — the recorded value was the Unbreakable Sphere announcing update |
| 4 | c162 | 2025-04-24 | 2025-05-01 | wiki releaseDate **1 may 2025** + pick-up page 2025-05-01 — the 2.5th-anniversary content spanned the 04-24 event and the 05-01 recruitment update |
| 5 | c162_01 | 2025-04-24 | 2025-05-01 | the Pain Eater gacha window is "**5:00 May 1st** to 5:00 May 22nd" (Unbreakable Sphere page) + the gacha page date 2025-05-01 |
| 6 | c835_02 | 2025-02-20 | 2025-02-27 | the **Passion CaNon - Asuka Pass** premium — the EVA2 **wave-2** (Rei (Tentative Name)) event pass, not the wave-1 (Second Quest) event |
| 7 | c832_04 | 2025-02-20 | 2025-02-27 | the **Passion CaNon - Mari Pass** premium — same wave-2 pass family |
| 8 | c9002 | 2025-05-29 | 2025-11-20 | Nora's debut is the **Blank Ticket** event (wiki: "debut = Blank Ticket", event 20 november 2025) — the recorded value came from a mislabeled c9xx row that called the 2025-05-29 update "Blank Ticket" (it is Lord, for Justice) |
| 9 | c513_03 | 2025-04-24 | 2026-07-02 | the dedicated **Costume Gacha: Shell Princess** ran with the **Wave to You** event (2026-07-02, "End of maintenance to 4:59 July 23rd") — the second of the Little Mermaid's two separate gachas; the recorded value was the character's debut date (base-debt inheritance) |

## Result

50/50 **reviewed**, **9 ids corrected** — the second-largest correction
count (behind BUCKET_09). Breakdown: 3 monthly MP premiums (rows 1–3 —
the pattern at eighteen instances, now spanning S15–S43), 2
**event-window corrections on the 2.5th-anniversary block** (rows 4–5:
the 2.5th anniversary spanned two updates — the Unbreakable Sphere event
on 04-24 and the Mihara: Bonding Chain recruitment + Pain Eater gacha on
05-01 — so the event date had bled into the recruitment rows), 2
**collab wave corrections** (rows 6–7: the "Passion CaNon" wave-2 passes
belong to the 2025-02-27 Rei wave, not the 2025-02-20 wave-1 event — the
EVA2 collab's two waves each carried their own passes), 1 **event-name
mislabel correction** (row 8: Nora's debut is the 2025-11-20 Blank
Ticket event; the 2025-05-29 update is Lord, for Justice — the wiki
"Blank Ticket" page is the November 2025 event), and 1 **base-debt
inheritance into 2026** (row 9: Shell Princess' gacha is the 2026 Wave
to You event — fourteen months after the character's debut).
Everything else is documented by wiki releaseDates / event pages fetched
live this pass, the module obtain table, `mp_costumes.json`, the wiki
Event list page's 2025 table (parsed this pass — it resolved the
2025-02-20 = Second Quest and 2025-05-29 = Lord, for Justice update
names), the viewer update log, or prior-pass rows (c501_01 and c016_02
from BUCKET_09; the c902_01/story0401_3/c082_80 CN rows from the
previous pass).

**Pattern notes (new this pass):** (1) **anniversary content can span
two updates** — the 2.5th anniversary's event/gacha/premium landed on
2025-04-24 (US) while its third SSR (Mihara: Bonding Chain) and her gacha
landed on 2025-05-01; the event page's "Version Updates" section lists
both gachas' windows, which is how the split shows up. (2) **event-name
collisions are real**: "Blank Ticket" (2025-11-20, Soline/Nora) vs the
2025-05-29 update (Lord, for Justice) — the c9xx pass had conflated
them; the wiki event page + Event list table settle the identity. (3)
**costume gachas are per-costume, not per-character**: the Little Mermaid
has two separate gachas (Abyss Flower 2025-04-24, Shell Princess
2026-07-02) — a character's debut gacha says nothing about its later
costume gachas.


**Partition restoration (post-pass):** the eight rows verified here
that belong to BUCKET_11's planned set (unbreakablesphere, c581,
arcanearchive, c041, c082_80, c270_02, c271_02, c9002) — their
full-evidence rows now sit in BUCKET_11's table; the two borrowed
copies (c016_02, c501_01) were dropped (BUCKET_09 owns them); the ten
BUCKET_10 rows verified in BUCKET_09 (piratecafe,
smol_emilia/liter/mary/mast/mast_pirate/mpriv/pepper/ram/rapi) moved
back from BUCKET_09's table.
## Checks

- [x] every row's date verified against a primary source (or an explicit
      rule with its source named); no value copied without checking
- [x] `models.json` patched: 9 date corrections (c381_01, c451_02,
      c511_02, c162, c162_01, c835_02, c832_04, c9002, c513_03)
- [x] evidence paths point at files actually in `/tmp`
- [x] 50/50 entries covered
