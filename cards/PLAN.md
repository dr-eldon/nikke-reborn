# NIKKE REBORN — Card Pack Plan

*Status: settled · drafted 2025-10-21 · re-based on the wiki's event archive 2026-11-05 — the banner-history packs 2–10 are replaced by six event-named sets (50–60 NIKKE entries each, set 1 extended through Sea You Again on theme plus one summer add-on), every other model of a set's window riding in as extras; **Base** is unchanged and built*

**Base** (pack 1, `cards/Base.toml`) carries the launch models and is already shipped — baselines in `tests/baselines/Base/`, the byte-protocol check is `uv run test Base c010`. Everything below releases after it.

## How a set is cut

- **Cut-offs are wiki events.** Each set ends at the start date of an event from the International fandom wiki's Event page (Event Archiving) — the name and dates in `database/events.json` (87 events, 84 distinct start dates, 2022-11-10 *No Caller ID* → 2026-10-29 *MARIA-n*; fetched 2026-11-05). A set is named for its cut-off event; the set's marquee NIKKEs are dated on the cut-off day, so the name matches the content.
- **Windows.** Set k covers `(previous cut-off, cut-off]` on `database/models.json`'s `date` (all 740 models are dated, through 2026-11-05). Set 1 opens after the launch day (2022-11-04) — Base carries the launch models.
- **NIKKE entries.** A NIKKE entry is a model whose base id matches `c\d{3}` with a number under 900 — the story-character range (c9xx), the Ghost series (c9000+) and the CN-exclusive ids (c8xxx, four digits) are excluded; sub-flavors count under their base id (c082_80 *Liter (CN)*, c233_80 *Dorothy (CN)*, c260_80 *Modernia (CN)*). **Sets carry 50–60 NIKKE entries** — the band is what fixes the cut-offs — with one thematic exception: set 1 extends through *Sea You Again* (2023-08-03), the second summer-island event after *Blue Water Island* (the two share a location; the expansion is named for it), so set 1 carries 73 NIKKE entries in the band (72 in the roster — the window's 72 plus *Helm: Aquamarine* (c353, 2023-08-10), summer-themed and released shortly after *Sea You Again*, as a single-model add-on; Mast_old is curated out) and set 2 is the residual window (42). As of 2026-11-05: 358 NIKKE entries post-launch → six sets; a seventh band-constrained set is infeasible (no chain of in-band windows reaches 350 of the 358, so the tail after six sets is always ≥ 17).
- **Extras.** Every other model dated in a window joins the set: story characters (c9xx), Ghosts (c9000+), event CGs and event models (event art, story-scene CGs, event props, the `777` model), chibis (Smol / Favorite), and the CN-exclusive NIKKEs (c8xxx).
- **Curation** — Base's exclusions extended, applied to rosters (not to the band counts): no bosses (Base: the 7 launch bosses; set 1 drops the remaining 8); no Faceless crowd NPCs (Base: c911/c912/c916–c924; set 5 drops the series' continuation c947–c952); no `*_old` legacy sibling models (Base: Rapi_old c010_01; set 1 drops Shifty_old c907_01 and Mast_old c350_old — Mast_old counts in set 1's band, so the roster carries 72 NIKKE against the band's 73); story scenes print the no-filter variant where both exist (no such pair falls in a new window).
- **Waves are never split.** Simultaneous release waves sit whole in one set — the pirate crew on set 1's cut-off day (2023-08-03), the NERV trios (sets 3/4), the Rapi winter wave (set 4), EVE/Raven (set 5), the RE trio (set 5), the Kuroko's pair (set 6) — or whole in the tail: the Persona/Kuroko's wave (Queen, Yukiko, Aigis, all 12 `ce009` smols, the Teddie/Morgana ghosts) and the Guilty/Sin twins.
- **The next set.** The pending tail becomes the next set once it accumulates 50 NIKKE entries; its cut-off is the first event start date that lands the window in the band. It holds 19 NIKKE entries today — the latest archived event (*MARIA-n*, 2026-10-29) would carry only 18 — so the next set waits for further releases.

## The sets

| # | Set (cut-off event) | Cut-off | NIKKE (band) | Extras | Models | Marquee |
|---|---|---|---|---|---|---|
| 1 | **Blue Water Island** | 2023-08-03 | 73¹ | 45 | 117 | Mary: Bay Goddess, the pirate crew |
| 2 | **Kill the Lord** | 2024-03-07 | 42 | 47 | 89 | D: Killer Wife |
| 3 | **Phantom Thief vs Detective** | 2024-10-03 | 55 | 23 | 78 | the NERV trio + Quency: Escape Queen |
| 4 | **Lord, for Justice** | 2025-05-29 | 54 | 41 | 95 | K |
| 5 | **Blank Ticket** | 2025-11-20 | 58 | 31 | 89 | Soline: Frost Ticket |
| 6 | **Project Matis** | 2026-07-23 | 57 | 58 | 115 | Laplace: Ultimate Hero |
| — | *pending tail* | after 2026-07-23 | 19 | 17 | 36 | the Kuroko's/Persona wave, the MARIA-n pair |

¹ 72 NIKKE in the window (2022-11-04, 2023-08-03] plus *Helm: Aquamarine* (c353, 2023-08-10) as a single-model summer add-on; Mast_old (c350_old) is in the band but curated out — the roster carries 72 NIKKE.

The six sets + tail carry 619 models; the 14 post-launch models curated out (8 bosses, 4 Faceless, 2 `*_old`) print in no set; with Base's 87 cards and the 20 launch models curated out of Base, that is the 740-model catalog.

## Rosters

Roster order for `cards/<set>.toml`: NIKKEs in release order (date, then id), then the non-CG extras in release order, the event CGs (event art + story scenes) closing the set — the Base precedent.

### 1 · Blue Water Island — (2022-11-04, 2023-08-03] + Helm: Aquamarine (c353, 2023-08-10) — 72 NIKKE, 45 extras = 117 models

| NIKKE | ID | Released |
|---|---|---|
| Helm | c352 | 2022-11-10 |
| Laplace | c100 | 2022-11-24 |
| Maxwell Mechanic White | c102_01 | 2022-12-01 |
| Poli Sweet Holic | c030_01 | 2022-12-08 |
| Brid Model Worker | c070_01 | 2022-12-08 |
| Emma Color me Red | c090_01 | 2022-12-08 |
| Maiden Covert Nurse | c181_01 | 2022-12-08 |
| Neve | c193 | 2022-12-08 |
| Rupee: Winter Shopper | c203 | 2022-12-08 |
| Exia Joy to the Nerds | c210_01 | 2022-12-08 |
| Anne: Miracle Fairy | c121 | 2022-12-15 |
| Julia Mild Nocturne | c150_01 | 2022-12-29 |
| Sugar Hard-Boiled | c140_01 | 2023-01-01 |
| Modernia | c260 | 2023-01-01 |
| Helm Chandelier | c352_01 | 2023-01-01 |
| Jackal | c111 | 2023-01-12 |
| Guilty | c400 | 2023-01-12 |
| Sin | c401 | 2023-01-12 |
| Quency | c402 | 2023-01-12 |
| Viper | c112 | 2023-01-19 |
| Signal Dramatic Chocolate | c022_01 | 2023-02-01 |
| Privaty Government Grunt | c170_01 | 2023-02-01 |
| Cocoa | c311 | 2023-02-01 |
| Soda | c312 | 2023-02-01 |
| Milk Extreme Fighter | c141_01 | 2023-02-22 |
| Makima | c800 | 2023-02-22 |
| Makima Coat Off | c800_01 | 2023-02-22 |
| Power | c801 | 2023-02-22 |
| Himeno | c802 | 2023-02-22 |
| Denji | c803 | 2023-02-22 |
| Denji Chainsaw Man | c803_01 | 2023-02-22 |
| Aki Hayakawa | c804 | 2023-02-22 |
| Dolla Dark Rose | c202_01 | 2023-03-01 |
| Centi Supreme Holiday | c080_01 | 2023-03-15 |
| Biscuit | c381 | 2023-03-15 |
| Yuni Pretty in Pink | c160_01 | 2023-03-30 |
| Novel Penguin Holmes | c212_01 | 2023-03-30 |
| Nihilister | c261 | 2023-03-30 |
| Sakura | c282 | 2023-03-30 |
| Sakura | c836 | 2023-03-30 |
| Noise Cherry Blossom Stage | c430_01 | 2023-04-01 |
| D | c040 | 2023-04-13 |
| Alice Sweet Home | c191_01 | 2023-04-27 |
| Dorothy | c233 | 2023-04-27 |
| Rei | c392 | 2023-04-27 |
| Mass Produced Blue | c251 | 2023-04-29 |
| Mass Produced Orange | c252 | 2023-04-29 |
| Mass Produced Green | c253 | 2023-04-29 |
| Mass Produced Purple | c254 | 2023-04-29 |
| Mass Produced White | c255 | 2023-04-29 |
| Viper Toxic Rabbit | c112_01 | 2023-05-01 |
| Rupee Rabbit Deluxe | c200_01 | 2023-05-18 |
| Blanc | c270 | 2023-05-18 |
| Noir | c271 | 2023-05-25 |
| Emma Office Therapy | c090_02 | 2023-06-01 |
| Rosanna | c280 | 2023-06-01 |
| Sakura Midnight Stealth | c282_01 | 2023-06-01 |
| Pepper Ocean Vitamin | c131_01 | 2023-06-15 |
| Mary: Bay Goddess | c132 | 2023-06-15 |
| Neon: Blue Ocean | c014 | 2023-06-22 |
| Frima Sea of Sloth | c142_01 | 2023-07-01 |
| Rapi Classic Vacation | c010_03 | 2023-07-06 |
| Drake Villain Racer | c101_01 | 2023-07-06 |
| Nero | c380 | 2023-07-06 |
| Indivilia | c263 | 2023-07-20 |
| Mast | c350 | 2023-07-20 |
| Yan Sunrise Market | c201_01 | 2023-08-01 |
| Anis: Sparkling Summer | c015 | 2023-08-03 |
| Liter Guardfish | c082_01 | 2023-08-03 |
| Mast A Pirate's Heart | c350_01 | 2023-08-03 |
| Anchor | c351 | 2023-08-03 |
| Helm: Aquamarine | c353 | 2023-08-10 |

**Story characters (18):** Papillon (c908, 2022-11-24); Angelina (c934, 2022-12-08); Johan (c925, 2023-01-12); Cecil (c929, 2023-01-12); Joseph (c935, 2023-01-12); Hologram (c910, 2023-02-01); Sweet Johnny (c910_01, 2023-02-01); Bolt (c933, 2023-03-15); Max (c936, 2023-03-15); Booboo (c937, 2023-03-15); Andersen Soaked (c903_01, 2023-04-01); Shifty (c907, 2023-04-01); Beatrice (c930, 2023-04-27); Doban (c939, 2023-04-27); Pinne (c941, 2023-04-27); Katie (c945, 2023-04-27); Ruru (c946, 2023-07-06); — Shifty_old (c907_01) is curated out (`*_old`).

**Ghosts (1):** Deipara (c9006, 2023-01-12).

**Event CGs and event models (27):** No Caller ID (nocallerid, 2022-11-10 — the first post-launch event; it printed in no former pack); High Tech Toy (hightechtoy, 2022-11-24); Miracle Snow (miraclesnow, 2022-12-08); Brand New Year (brandnewyear, 2022-12-29); D Outsider (doutsider, 2023-01-12); Story 14-01 (story1401, 2023-01-12); Story 14-03 (story1403, 2023-01-12); Story 14-05 (story1405, 2023-01-12); Story 15-01 (story1501, 2023-01-12); Story 19-01 (story1902, 2023-01-12); Story 20-01 (story2002, 2023-01-12); Maid in Valentine (maidinvalentine, 2023-02-01); Bow Wow Paradise (bowwowparadise, 2023-03-15); Cherry Blossom (cherryblossom, 2023-03-30); License to Kill (ltk, 2023-04-13); Story 21-01 (story2101, 2023-04-27); Story 22-01 (story2201, 2023-04-27); Story 22-02 (story2202, 2023-04-27); Story 22-06 (story2206, 2023-04-27); White Memory 1 (whitememory1, 2023-04-27); White Memory 2 (whitememory2, 2023-04-27); 777 (777, 2023-05-18 — the Bunny X 777 event's NIKKE model, a non-`c` id so it rides as an extra); Queen's Order (queensorder, 2023-06-01); Blue Water Island (bluewaterisland, 2023-06-15); Nya Nya Paradise (nyanyaparadise, 2023-07-06); Golden Ship (goldenship, 2023-07-20); Sea You Again (seayouagain, 2023-08-03).

*Curated out (8 bosses, 1 `*_old` sibling): Boss: Alteisen (mbg001), Boss: Storm Bringer (eba001), Boss: Land Eater (ebg001), Boss: Nihilister (mba002), Boss: Gatekeeper Blue/Green/Red (eba003, eba003_green, eba003_hsta), Boss: Mother Whale (bba001), Mast_old (c350_old, 2023-07-20 — the `*_old` legacy sibling of Mast c350; it counts in the band, so the roster carries 72 against the band's 73).*

### 2 · Kill the Lord — (2023-08-03, 2024-03-07] — 42 NIKKE, 47 extras = 89 models

| NIKKE | ID | Released |
|---|---|---|
| Modernia First Affection | c260_01 | 2023-08-24 |
| Brid Black Moon | c070_02 | 2023-09-01 |
| 2B | c810 | 2023-09-01 |
| 2B Metamorphic Damage | c810_01 | 2023-09-01 |
| 2B YoRHa Uniform 1 | c810_02 | 2023-09-01 |
| Pascal | c812 | 2023-09-01 |
| 9S | c813 | 2023-09-01 |
| A2 | c811 | 2023-09-08 |
| A2 Metamorphic Damage | c811_01 | 2023-09-08 |
| A2 YoRHa Uniform Prototype | c811_02 | 2023-09-08 |
| Marciana | c321 | 2023-09-21 |
| Novel Detective Nurse | c212_02 | 2023-10-01 |
| Diesel Strawberry Flower | c072_02 | 2023-10-05 |
| Naga | c450 | 2023-10-05 |
| Tia | c451 | 2023-10-12 |
| Quiry | c033 | 2023-10-19 |
| Privaty Banquet Princess | c170_02 | 2023-11-01 |
| Snow White: Innocent Days | c224 | 2023-11-02 |
| Harran Banquet Witch | c230_01 | 2023-11-02 |
| Dorothy Nostalgia | c233_01 | 2023-11-02 |
| Red Hood | c470 | 2023-11-02 |
| Mass Produced Red | c250 | 2023-11-16 |
| Tove | c192 | 2023-11-23 |
| Noir Black Rabbit | c271_01 | 2023-12-01 |
| Ludmilla: Winter Owner | c194 | 2023-12-07 |
| Blanc White Rabbit | c270_01 | 2023-12-07 |
| Mica: Snow Buddy | c062 | 2023-12-14 |
| Liter Cute Sunflower | c082_02 | 2024-01-01 |
| Guillotine Dark Tracer | c180_01 | 2024-01-01 |
| Scarlet: Black Shadow | c225 | 2024-01-01 |
| Noise Classic Diva | c430_02 | 2024-01-01 |
| Leona | c382 | 2024-01-11 |
| Moran | c281 | 2024-01-25 |
| Sugar Wild Backyard | c140_02 | 2024-02-01 |
| Drake Maid For Villain | c101_02 | 2024-02-05 |
| Privaty: Unkind Maid | c313 | 2024-02-05 |
| Ade | c310 | 2024-02-15 |
| Liveryn | c480 | 2024-02-22 |
| Hammering | c490 | 2024-02-22 |
| Elegg | c500 | 2024-02-22 |
| Exia Gamer | c210_02 | 2024-03-01 |
| D: Killer Wife | c043 | 2024-03-07 |

**Story characters (18):** Product 12: B-0006 (c962, 2023-09-01); Product 12: C-1002 (c963, 2023-09-01); Product 12: 6000-D (c964, 2023-09-01); Commander (GODDESS) (c942, 2023-11-02); Liliweiss (c943, 2023-11-02); Freesia (c960, 2023-11-02); Oswald (c961, 2023-11-02); Oswald (c961_01, 2023-11-02); Ghost - Lumi (c967, 2023-12-07); Ghost - Lua (c968, 2023-12-07); Ghost - Lena (c969, 2023-12-07); Lumi (c970, 2023-12-07); Rose (c971, 2023-12-28); Mass Produced Melee (c974, 2023-12-28); Mass Produced Melee 2 (c974_01, 2024-01-06); Timi (c975, 2024-01-11); Raptillion (c915, 2024-02-22); T.Rony (c976, 2024-02-22).

**Chibis (Smol / Favorite) (12):** Smol Anchor (smol_anchor, 2023-09-03); Smol Bolt (smol_bolt, 2023-09-03); Smol Frima (smol_frima, 2023-09-03); Smol Helm (smol_helm, 2023-09-03); Smol Liter (smol_liter, 2023-09-03); Smol Mary (smol_mary, 2023-09-03); Smol Mast (smol_mast, 2023-09-03); Smol Pepper (smol_pepper, 2023-09-03); Smol Rapi (smol_rapi, 2023-09-03); Smol Yan (smol_yan, 2023-09-03); Smol Ade (smol_ade, 2024-02-05); Smol Maid Privaty (smol_mpriv, 2024-02-05).

**Event CGs and event models (17):** Outer Automata (outerautomata, 2023-09-01); School Of Lock (schooloflock, 2023-09-21); Dazzling Cupid: Naga (dazzlingcupid_naga, 2023-10-05); Dazzling Cupid: Tia (dazzlingcupid_tia, 2023-10-05); ACPU FREEZE (acpufreeze, 2023-10-19); RED ASH 1 (redash1, 2023-11-02); RED ASH 2 (redash2, 2023-11-02); Story 25-01 (story2501, 2023-11-02); Story 26-02 (story2602, 2023-11-02); Alone Survivor (alonesurvivor, 2023-11-23); Neverland (neverland, 2023-12-07); New Year New Sword (newyearnewsword, 2023-12-28); Lion Heart (lionheart, 2024-01-11); Dirty Backyard (dirtybackyard, 2024-01-25); Perfect Maid (perfectmaid, 2024-02-05); BOOM's DAY (boomsday, 2024-02-22); Kill The Lord (killthelord, 2024-03-07).

### 3 · Phantom Thief vs Detective — (2024-03-07, 2024-10-03] — 55 NIKKE, 23 extras = 78 models

| NIKKE | ID | Released |
|---|---|---|
| Rem Pure Blossom | c820_02 | 2024-03-21 |
| Emilia | c821 | 2024-03-21 |
| Emilia Clumsy Maid | c821_01 | 2024-03-21 |
| Emilia Spring Breeze | c821_02 | 2024-03-21 |
| Ram | c822 | 2024-03-21 |
| Rem | c820 | 2024-03-28 |
| Rem Handy Maid | c820_01 | 2024-03-28 |
| Poli Cheer Up Police | c030_02 | 2024-04-01 |
| Rosanna Ms. Dangerous | c280_01 | 2024-04-01 |
| Bay | c550 | 2024-04-11 |
| Snow White White Knight | c220_01 | 2024-04-25 |
| Modernia Second Affection | c260_02 | 2024-04-25 |
| Crown | c330 | 2024-04-25 |
| Kilo | c361 | 2024-04-25 |
| Fragile | c481 | 2024-04-25 |
| Drilley | c491 | 2024-04-25 |
| Diesel Midnight Strawberry | c072_04 | 2024-05-01 |
| Crown Naked King | c330_01 | 2024-05-02 |
| Trony | c501 | 2024-05-16 |
| Ark Ranger Black | c570_99 | 2024-05-16 |
| Mary Medical Rabbit | c130_01 | 2024-05-30 |
| Soda: Twinkling Bunny | c314 | 2024-05-30 |
| Folkwang Moist Rabbit | c242_01 | 2024-06-01 |
| Alice: Wonderland Bunny | c195 | 2024-06-06 |
| Clay | c551 | 2024-06-20 |
| Maiden Under The Sun | c181_02 | 2024-07-01 |
| Viper Shine of Love | c112_02 | 2024-07-04 |
| Sakura: Bloom in Summer | c284 | 2024-07-04 |
| Mast Mast the Diver | c350_02 | 2024-07-04 |
| Anchor Anchor the Diver | c351_01 | 2024-07-04 |
| Guilty Wave of Disbelief | c400_01 | 2024-07-04 |
| Rosanna: Chic Ocean | c283 | 2024-07-11 |
| Ein | c391 | 2024-07-25 |
| Tia Lovely Date | c451_01 | 2024-07-25 |
| Behemoth | c560 | 2024-07-25 |
| Naga Elegant Date | c450_01 | 2024-08-01 |
| Marciana School Days | c321_01 | 2024-08-08 |
| Zwei | c390 | 2024-08-08 |
| Asuka | c830 | 2024-08-22 |
| Asuka Asuka's School Uniform | c830_01 | 2024-08-22 |
| Asuka Cynical Street | c830_02 | 2024-08-22 |
| Asuka Test Plugsuit | c830_03 | 2024-08-22 |
| Misato | c833 | 2024-08-22 |
| Rei | c831 | 2024-08-29 |
| Rei Rei's School Uniform | c831_01 | 2024-08-29 |
| Rei Peaceful Vacation | c831_02 | 2024-08-29 |
| Leona Zoo Keeper | c382_01 | 2024-09-01 |
| Mari | c832 | 2024-09-05 |
| Mari Mari's School Uniform | c832_01 | 2024-09-05 |
| Mari Leisure Travel | c832_02 | 2024-09-05 |
| Rouge | c272 | 2024-09-19 |
| Red Hood Nonsense Red | c470_01 | 2024-09-19 |
| Miranda Thief of Justice | c032_01 | 2024-10-01 |
| Tove Baseball Fan | c192_01 | 2024-10-03 |
| Quency: Escape Queen | c403 | 2024-10-03 |

**Story characters (2):** Syuen (c901, 2024-04-01); Kilo (c977, 2024-04-25).

**Chibis (Smol / Favorite) (8):** Smol Emilia (smol_emilia, 2024-03-21); Smol Ram (smol_ram, 2024-03-21); Smol Rem (smol_rem, 2024-03-21); Favorite: Diesel (favorite_c072, 2024-05-30); Favorite: Laplace (favorite_c100, 2024-05-30); Favorite: Frima (favorite_c142, 2024-05-30); Favorite: Exia (favorite_c210, 2024-05-30); Favorite: Viper (favorite_c112, 2024-07-04).

**Event CGs and event models (13):** Re: Cipe For You (recipeforyou, 2024-03-21); One More Time (onemoretime, 2024-04-11); Last Kingdom (lastkingdom, 2024-04-25); D.ARK HERO (darkhero, 2024-05-16); Golden Coin Rush (goldencoinrush, 2024-05-30); Claymore (claymore, 2024-06-20); Aegis the Diver (aegisthediver, 2024-07-04); Beauty Full Shot (beautyfullshot, 2024-07-04); Juvenile Days (juveniledays, 2024-07-25); Colorless (colorless, 2024-08-08); Evangelion (evangelion, 2024-08-22); Jinx Player (jinxplayer, 2024-09-19 — the second event of the double-date 2024-09-19); Phantom Thief (phantomthief, 2024-10-03).

### 4 · Lord, for Justice — (2024-10-03, 2025-05-29] — 54 NIKKE, 41 extras = 95 models

| NIKKE | ID | Released |
|---|---|---|
| Phantom | c580 | 2024-10-10 |
| Rumani | c240 | 2024-10-17 |
| Scarlet: Black Shadow Longing Flower | c225_01 | 2024-10-31 |
| Rapunzel: Pure Grace | c226 | 2024-10-31 |
| Isabel Honeymoon Party | c231_01 | 2024-10-31 |
| Cinderella | c511 | 2024-10-31 |
| Leviathan | c562 | 2024-10-31 |
| D: Killer Wife Secret Party Cleaner | c043_01 | 2024-11-01 |
| Grave | c510 | 2024-11-07 |
| Cinderella Glass Princess | c511_01 | 2024-11-07 |
| Grave | c514 | 2024-11-07 |
| Flora | c411 | 2024-11-21 |
| Volume Beat the Gun | c431_01 | 2024-12-01 |
| Vesti Ark Mage | c091_01 | 2024-12-05 |
| Maiden: Ice Rose | c183 | 2024-12-05 |
| Guillotine: Winter Slayer | c182 | 2024-12-12 |
| Ein Handmade Festa | c391_01 | 2024-12-26 |
| Naga Last Girlhood | c450_02 | 2024-12-26 |
| Rapi: Red Hood | c016 | 2025-01-01 |
| Zwei First Festa | c390_01 | 2025-01-01 |
| Mana | c290 | 2025-01-16 |
| Mast: Romantic Maid | c354 | 2025-01-30 |
| Sin Backstreet Dream | c401_01 | 2025-01-30 |
| Trony Sweet Step | c501_01 | 2025-02-01 |
| Anchor: Innocent Maid | c355 | 2025-02-06 |
| Helm Post-Shower Moment | c352_02 | 2025-02-20 |
| Eyeri | c440 | 2025-02-20 |
| Asuka: WILLE | c835 | 2025-02-20 |
| Asuka: WILLE Ocean's Lament | c835_02 | 2025-02-20 |
| Mari Final Battle: Mari | c832_03 | 2025-02-27 |
| Mari Mystery Muse | c832_04 | 2025-02-27 |
| Rei (Tentative Name) | c834 | 2025-02-27 |
| Rei (Tentative Name) Miss Lookalike from Village-3 | c834_01 | 2025-02-27 |
| Rei (Tentative Name) Soul Connect | c834_02 | 2025-02-27 |
| Asuka: WILLE Final Battle: Asuka | c835_01 | 2025-02-27 |
| Biscuit Spring Puppy | c381_01 | 2025-03-01 |
| Trina | c412 | 2025-03-13 |
| Ade Maid In Spring | c310_01 | 2025-03-27 |
| Bready | c520 | 2025-03-27 |
| Tia Sweet Chef | c451_02 | 2025-04-01 |
| Crust | c521 | 2025-04-10 |
| Little Mermaid | c513 | 2025-04-24 |
| Little Mermaid Abyss Flower | c513_01 | 2025-04-24 |
| Grave Beautiful You | c514_01 | 2025-04-24 |
| Ziz | c561 | 2025-04-24 |
| Mori | c590 | 2025-04-24 |
| Mihara: Bonding Chain | c162 | 2025-05-01 |
| Mihara: Bonding Chain Pain Eater | c162_01 | 2025-05-01 |
| Cinderella Beautiful Me | c511_02 | 2025-05-01 |
| Arcana | c581 | 2025-05-15 |
| K | c041 | 2025-05-29 |
| Liter (CN) | c082_80 | 2025-05-29 |
| Blanc No. 77 Batter | c270_02 | 2025-05-29 |
| Noir Baseball Cheerleader | c271_02 | 2025-05-29 |

**Story characters (16):** Nadia (c983, 2024-10-17); Yuni (c985, 2024-10-27); Abe (c979, 2024-10-31); Hansel (c980, 2024-10-31); Gretel (c981, 2024-10-31); Red Shoes (c982, 2024-10-31); Rapi (c989, 2024-10-31); Chloe - Village Guardian (c988, 2024-12-05); Rapi (c990, 2024-12-26); D.E.E.P. (c991, 2024-12-26); Rapi (c992, 2024-12-26); Rapi (c994, 2024-12-26); Jien (c973, 2025-01-16); Mustang (CN) (c902_01, 2025-04-01); Mecha Shifty (c993, 2025-04-01 — a NIKKE with a story-range id, so it rides as an extra); Leviathan (c996, 2025-04-10).

**Ghosts (1):** Jien (c9032, 2025-01-16).

**Chibis (Smol / Favorite) (7):** Favorite: Miranda (favorite_c032, 2025-01-16); Favorite: Drake (favorite_c101, 2025-01-16); Favorite: Milk (favorite_c141, 2025-01-16); Favorite: Helm (favorite_c352, 2025-01-16); Smol Anchor Pirate (smol_anchor_pirate, 2025-01-30); Smol Mast Pirate (smol_mast_pirate, 2025-01-30); Smol Sin Pirate (smol_sin_pirate, 2025-01-30).

**Event CGs and event models (17):** Life Again (lifeagain, 2024-10-17); Old Tales (oldtales, 2024-10-31); Secret Garden (secretgarden, 2024-11-21); Ice Dragon Saga (icedragonsaga, 2024-12-05); Footstep Walk Run (footstepwalkrun, 2024-12-26); Wisdom Spring (wisdomspring, 2025-01-16); Pirate Cafe (piratecafe, 2025-01-30); Romantic Valentine (romanticvalentine, 2025-01-30); Second Quest (secondquest1, 2025-02-20); Second Quest (secondquest2, 2025-02-20); For Rest (forrest, 2025-03-13); New Flavor (newflavor, 2025-03-27); Story 04-02 (CN) (story0401_3, 2025-04-01); True Flavor (trueflavor, 2025-04-10); Unbreakable Sphere (unbreakablesphere, 2025-04-24); Arcane Archive (arcanearchive, 2025-05-15); Lord For Justice (lordforjustice, 2025-05-29).

### 5 · Blank Ticket — (2025-05-29, 2025-11-20] — 58 NIKKE, 31 extras = 89 models

| NIKKE | ID | Released |
|---|---|---|
| Moran Off-Duty Queen | c281_01 | 2025-06-01 |
| Scarlet Racer's High | c222_01 | 2025-06-12 |
| EVE | c850 | 2025-06-12 |
| EVE Neurolink Suit | c850_02 | 2025-06-12 |
| Lily | c852 | 2025-06-12 |
| Adam | c853 | 2025-06-12 |
| EVE Keyhole Dress | c850_01 | 2025-06-19 |
| EVE Skin Suit | c850_03 | 2025-06-19 |
| Raven | c851 | 2025-06-19 |
| Raven Planet Diving Suit (6th) V2 | c851_01 | 2025-06-19 |
| Raven Midsummer Alice | c851_02 | 2025-06-19 |
| Dorothy (CN) | c233_80 | 2025-06-20 |
| Modernia (CN) | c260_80 | 2025-06-20 |
| Centi Ocean Repair | c080_02 | 2025-07-01 |
| Privaty Destined in Blue | c170_03 | 2025-07-03 |
| Sky | c530 | 2025-07-03 |
| Cielo | c531 | 2025-07-03 |
| Sora | c532 | 2025-07-03 |
| 2B YoRHa Unofficial Waterfront Gear I | c810_03 | 2025-07-03 |
| A2 YoRHa Unofficial Waterfront Gear Prototype | c811_03 | 2025-07-03 |
| Rapi: Red Hood Red Flavor | c016_01 | 2025-07-17 |
| Tove Sunblaze | c192_02 | 2025-07-17 |
| Dorothy: Serendipity | c234 | 2025-07-17 |
| Elegg: Boom and Shock | c502 | 2025-07-24 |
| Julia Summer Romance | c150_02 | 2025-08-01 |
| Emma: Tactical Upgrade | c093 | 2025-08-07 |
| Eunhwa: Tactical Upgrade Day Off | c095_01 | 2025-08-07 |
| Pinocchio | c227 | 2025-08-07 |
| Eternity | c370 | 2025-08-07 |
| Endless | c371 | 2025-08-07 |
| Eunhwa: Tactical Upgrade | c095 | 2025-08-14 |
| Vesti: Tactical Upgrade | c094 | 2025-08-21 |
| Exia Hacker Rabbit | c210_03 | 2025-09-01 |
| Rouge Unlucky Rabbit | c272_01 | 2025-09-04 |
| Ade: Agent Bunny | c315 | 2025-09-04 |
| Bay Radiant Rabbit | c550_01 | 2025-09-04 |
| Milk: Blooming Bunny | c143 | 2025-09-11 |
| D: Killer Wife Secret Police | c043_02 | 2025-09-24 |
| Ada | c840 | 2025-09-24 |
| Ada Separate Ways | c840_01 | 2025-09-24 |
| Ada Dress | c840_02 | 2025-09-24 |
| Claire | c842 | 2025-09-24 |
| K Undercover | c041_01 | 2025-10-01 |
| Jill | c841 | 2025-10-02 |
| Jill Classic | c841_01 | 2025-10-02 |
| Jill Battle Suit | c841_02 | 2025-10-02 |
| Rapi: Red Hood Cherished Red | c016_02 | 2025-10-16 |
| Delta: Ninja Thief | c023 | 2025-10-16 |
| Nayuta | c223 | 2025-10-30 |
| Crown Glorious Flower | c330_02 | 2025-10-30 |
| Chime | c331 | 2025-10-30 |
| Red Hood Retro Days | c470_02 | 2025-10-30 |
| Logey | c482 | 2025-10-30 |
| Bahamut | c563 | 2025-10-30 |
| Little Mermaid Beautiful Bubble | c513_02 | 2025-11-01 |
| Nayuta Wu Wei | c223_01 | 2025-11-06 |
| Liberalio | c262 | 2025-11-06 |
| Soline: Frost Ticket | c074 | 2025-11-20 |

**Story characters (4):** Com (c931_01, 2025-06-12); Hermin (c998, 2025-06-12); Rose - Mirror (c971_01, 2025-10-30); Only One (c997, 2025-10-30).

**Ghosts (14):** Ghost - Alfred (c9000, 2025-07-17); Ghost - Neaty (c9000_01, 2025-07-17); Ghost - Sizzly (c9000_02, 2025-07-17); Ghost - Fixy (c9000_03, 2025-07-17); Ghost - Detaily (c9000_05, 2025-07-17); Ghost - Sellsy (c9000_06, 2025-07-17); Ghost (c9000_07, 2025-07-17); Ghost - Pinne (c9001, 2025-07-17); Mrs. Miss (c9003, 2025-08-07); Rapture (c9005, 2025-08-07); Rapture (c9005_01, 2025-08-07); Nayuta (c9008, 2025-08-07); Nihilister (c9009, 2025-10-30); Nora (c9002, 2025-11-20).

**Chibis (Smol / Favorite) (4):** Favorite: Poli (favorite_c030, 2025-07-17); Favorite: Julia (favorite_c150, 2025-07-17); Favorite: Tove (favorite_c192, 2025-07-17); Favorite: Bay (favorite_c550, 2025-07-17).

**Event CGs and event models (9):** Memories Teller 1 (memoriesteller_1, 2025-06-12); Memories Teller 2 (memoriesteller_2, 2025-06-12); Over the Horizon (overthehorizon, 2025-07-03); Boom the Ghost (boomtheghost, 2025-07-17); Absolute (absolute, 2025-08-07); Coins In Rush (coinsinrush, 2025-09-04); Reborn Evil (rebornevil, 2025-09-24); Go! Ninja Thief (goninjathief, 2025-10-16); Blank Ticket (blankticket, 2025-11-20).

*Curated out (4 Faceless crowd NPCs): Faceless NPC 10 (c947), Faceless NPC 11 (c948), Faceless NPC 12 (c951), Faceless NPC 13 (c952) — all 2025-08-07.*

### 6 · Project Matis — (2025-11-20, 2026-07-23] — 57 NIKKE, 58 extras = 115 models

| NIKKE | ID | Released |
|---|---|---|
| Jackal Class Troublemaker | c111_01 | 2025-12-01 |
| Diesel: Winter Sweets | c075 | 2025-12-04 |
| Blanc Fortune Express | c270_03 | 2025-12-04 |
| Bready Frosty Bite | c520_01 | 2025-12-04 |
| Brid: Silent Track | c073 | 2025-12-11 |
| Quency: Escape Queen Masquerade Swan | c403_01 | 2025-12-30 |
| Emma: Tactical Upgrade Secret Therapy | c093_01 | 2026-01-01 |
| Alice Märchen Dream | c191_02 | 2026-01-01 |
| Snow White: Heavy Arms | c471 | 2026-01-01 |
| Label | c582 | 2026-01-15 |
| Velvet | c316 | 2026-01-29 |
| Velvet Sensual Rabbit | c316_01 | 2026-02-01 |
| Mast: Romantic Maid Tea Service | c354_01 | 2026-02-12 |
| Chisato | c860 | 2026-02-12 |
| Chisato DA Training Wear (First) | c860_01 | 2026-02-12 |
| Chisato Red Spark Guitar | c860_02 | 2026-02-12 |
| Kurumi | c862 | 2026-02-12 |
| Takina | c861 | 2026-02-19 |
| Takina DA Training Wear (Second) | c861_01 | 2026-02-19 |
| Takina Blue Pulse Bass | c861_02 | 2026-02-19 |
| Zwei Spring Stroll | c390_02 | 2026-03-01 |
| E.H. | c113 | 2026-03-05 |
| Vesti: Tactical Upgrade Pure Beginner | c094_01 | 2026-03-19 |
| Viper Punky Street | c112_03 | 2026-03-19 |
| Privaty Sharp Lesson | c170_04 | 2026-03-19 |
| Arcana: Fortune Mate | c583 | 2026-03-19 |
| Sora Spring Flight | c532_01 | 2026-04-01 |
| Mekami Shifty | c610 | 2026-04-01 |
| Clay Cheer Up Training | c551_01 | 2026-04-02 |
| Snow Crane | c620 | 2026-04-09 |
| Anis: Star | c017 | 2026-04-23 |
| Dorothy Luna Light | c233_02 | 2026-04-23 |
| Liberalio Dreaming Lake | c262_01 | 2026-04-23 |
| Avistar | c441 | 2026-04-23 |
| Anis: Star Starlight | c017_01 | 2026-04-30 |
| Anis: Star T.T. STAR | c017_02 | 2026-04-30 |
| Neon: Vision Eye | c018 | 2026-04-30 |
| Rapi: Red Hood Shining Light | c016_03 | 2026-05-01 |
| Mint | c600 | 2026-05-14 |
| Mint Fresh Mint | c600_01 | 2026-05-14 |
| Mint | c600_02 | 2026-05-14 |
| Prika | c601 | 2026-05-28 |
| Prika Cool Paprika | c601_01 | 2026-05-28 |
| Prika | c601_02 | 2026-05-28 |
| Trina Natural White | c412_01 | 2026-06-01 |
| E.H. Junkyard Vanguard | c113_01 | 2026-06-11 |
| Moran King of Flowers | c281_02 | 2026-06-11 |
| Ark Ranger Black | c570 | 2026-06-11 |
| Ark Ranger Red | c571 | 2026-06-11 |
| Ark Ranger Blue | c572 | 2026-06-11 |
| Naga Ring Ensemble | c450_03 | 2026-07-01 |
| Tia Sea Lizzie | c451_03 | 2026-07-02 |
| Little Mermaid Shell Princess | c513_03 | 2026-07-02 |
| Cinderella: Crystal Wave | c515 | 2026-07-02 |
| Marciana: Marine Study | c322 | 2026-07-09 |
| Laplace: Ultimate Hero | c103 | 2026-07-23 |
| Laplace: Ultimate Hero Prototype Hero | c103_01 | 2026-07-23 |

**Story characters (1):** E.H. (c940, 2026-03-05 — the story-side model; the NIKKE is c113, on the table above).

**Ghosts (25):** Mass Produced Heretic (c9014, 2025-12-30); Central Government Platoon Leader (c9015, 2025-12-30); V.T.C. Priestess (c9016, 2025-12-30); Jane (c9010, 2026-02-12); Rain (c9011, 2026-02-12); Altruia (c9017, 2026-02-12); Princess (c9018, 2026-02-12); Stall III (c9019, 2026-02-12); Amy (c9026, 2026-03-19); Freesia (c9020, 2026-04-09); Freesia (c9020_01, 2026-04-09); Hanson (c9023, 2026-04-09); Anis (c9021, 2026-04-23); Anis (c9021_01, 2026-04-23); Mustang (c9022, 2026-04-23); Yoyo (c9024, 2026-04-23); Egovista (c9025, 2026-04-23); Hope (c9028, 2026-06-11); Penguin (c9034, 2026-07-02); Penguin (c9035, 2026-07-02); Penguin (c9036, 2026-07-02); Penguin (c9037, 2026-07-02); Laplace (c9029, 2026-07-23); Enme (c9030, 2026-07-23); Syuen (c9031, 2026-07-23).

**Chibis (Smol / Favorite) (6):** Smol Anis TTS (smol_anis, 2026-04-23); Smol Mint TTS (smol_mint, 2026-04-23); Smol Prika TTS (smol_prika, 2026-04-23); Smol Marciana TTS (smol_marciana, 2026-07-23); Smol Naga TTS (smol_naga, 2026-07-23); Smol Tia TTS (smol_tia, 2026-07-23).

**CN-exclusive NIKKEs (3):** Ying Ning (婴宁) (CN) (c8004, 2025-11-25); Hua Pi (画皮) (CN) (c8005, 2025-11-25); Ying Ning (婴宁) (CN) (c8006, 2025-11-25) — the four-digit ids miss the NIKKE pattern, so they ride as extras.

**Event CGs and event models (23):** AZX Service Time 1–9 (azxservicetime_1 … azxservicetime_9, 2025-12-04); Terminus Ticket (terminusticket, 2025-12-04); Ark Guardian (arkguardian, 2025-12-30); Sin Editor (sineditor, 2026-01-15); Fatal Maid (fatalmaid, 2026-01-29); Lie Cause Recoil (liecauserecoil, 2026-02-12); Enter Heaven (enterheaven, 2026-03-05); 2x2 LOVE 1 (twoxtwo1, 2026-03-19); 2x2 LOVE 2 (twoxtwo2, 2026-03-19); Good World (goodworld, 2026-04-09); Star Anis (staranis, 2026-04-23); B Side Idol (bsideidol, 2026-05-14); Bitter Spice (bitterspice, 2026-05-28); Ark Ranger (arkranger, 2026-06-11); Project Matis (projectmatis, 2026-07-23).

## The pending tail (the next set)

Models after 2026-07-23 — 19 NIKKE entries, 17 extras = 36 models. The next set cuts from here (rule above); it opens at Maxwell: Ordinary Mechanic (2026-07-30).

| NIKKE | ID | Released |
|---|---|---|
| Maxwell: Ordinary Mechanic | c105 | 2026-07-30 |
| Maxwell: Ordinary Mechanic Chief Researcher | c105_01 | 2026-08-01 |
| Phantom Saint Thief | c580_01 | 2026-08-13 |
| Queen (Makoto) | c870 | 2026-08-13 |
| Queen (Makoto) Shujin Academy Student Council President | c870_01 | 2026-08-13 |
| Queen (Makoto) Queen's Pajamas (Ver. NIKKE Collabo) | c870_02 | 2026-08-13 |
| Aigis | c872 | 2026-08-13 |
| Yukiko | c871 | 2026-08-20 |
| Yukiko Inn Kimono | c871_01 | 2026-08-20 |
| Yukiko Winter Roomwear (Ver. NIKKE Collabo) | c871_02 | 2026-08-20 |
| Flora Fairy Rabbit | c411_01 | 2026-09-01 |
| Drake: Great Villain | c104 | 2026-09-03 |
| Sugar Killer Rabbit | c140_03 | 2026-09-17 |
| Mana Drunken Rabbit | c290_01 | 2026-09-17 |
| Guilty: Mighty Bunny | c404 | 2026-09-17 |
| Sin: Swift Bunny | c405 | 2026-09-24 |
| Crust Treat Chef | c521_01 | 2026-10-01 |
| Rapunzel: Sanctuary | c473 | 2026-10-29 |
| Scarlet: Goddeath | c472 | 2026-11-05 |

**Ghosts (3):** Teddie (c9038, 2026-08-13); Morgana (c9039, 2026-08-13); Morgana (c9040, 2026-08-13).

**CG (12):** the `ce009` kit — Smol Queen (Makoto) (ce009_char_01), Smol Yukiko (ce009_char_02), Smol Aigis (ce009_char_03), Smol Ade (ce009_enemy_ade), Smol Delta (ce009_enemy_delta), Smol Miranda (ce009_enemy_miranda), Smol Phantom (ce009_enemy_phantom), Smol Poli (ce009_enemy_poli), Smol Quency (ce009_enemy_quency), Smol Johanna (ce009_skill_01), Smol Amaterasu (ce009_skill_02), Smol Athena (ce009_skill_03) — all dated 2026-08-13, so the whole collab art kit lands with the wave.

**Event CGs and event models (2):** Great Villain Union (greatvillainunion, 2026-09-03); Coin Rush Showdown (coinrushshowdown, 2026-09-17).

## Why this line (the design space)

263 feasible lines exist — every combination of per-set cut-offs whose six windows all land in the 50–60 band. The per-set options and their coupling; a cell's number is the NIKKE entries the cut-off carries after the named previous cut-off:

| Set | Cut-off event (date) | NIKKE entries — after |
|---|---|---|
| 1 | Bunny X 777 (2023-05-18) | 53 |
| 1 | Queen's Order (2023-06-01) | 57 |
| 1 | Blue Water Island (2023-06-15) | 59 |
| 1 | Sea You Again (2023-08-03) | 72 — the thematic extension, out of band — set 1's actual cut |
| 2 | Perfect Maid (2024-02-05) | 56 / 52 / 50 after Bunny X 777 / Queen's Order / Blue Water Island |
| 2 | Booms Day (2024-02-22) | 60 / 56 / 54 after Bunny X 777 / Queen's Order / Blue Water Island |
| 2 | Kill the Lord (2024-03-07) | 58 / 56 after Queen's Order / Blue Water Island |
| 3 | Nonsense Red + Jinx Player (2024-09-19) | 58 / 54 / 52 after Perfect Maid / Booms Day / Kill the Lord |
| 3 | Phantom Thief vs Detective (2024-10-03) | 57 / 55 after Booms Day / Kill the Lord |
| 3 | Life Again (2024-10-17) | 59 / 57 after Booms Day / Kill the Lord |
| 4 | Arcane Archive (2025-05-15) | 53 / 50 after Nonsense Red / Phantom Thief |
| 4 | Lord, for Justice (2025-05-29) | 57 / 54 / 52 after Nonsense Red / Phantom Thief / Life Again |
| 4 | Memories Teller (2025-06-12) | 60 / 58 after Phantom Thief / Life Again |
| 5 | Yes, My Commander (2025-10-16) | 52 after Arcane Archive |
| 5 | Goddess Fall (2025-10-30) | 58 / 54 after Arcane Archive / Lord, for Justice |
| 5 | Blank Ticket (2025-11-20) | 58 / 52 after Lord, for Justice / Memories Teller |
| 5 | Terminus Ticket (2025-12-04) | 56 after Memories Teller |
| 5 | Ark Guardian (2025-12-30) | 58 after Memories Teller |
| 6 | B-Side Idol (2026-05-14) | 51 after Yes, My Commander — tail 35 |
| 6 | Bitter Spice (2026-05-28) | 54 after Yes, My Commander — tail 32 |
| 6 | Ark Ranger (2026-06-11) | 60 / 54 / 50 after Yes, My Commander / Goddess Fall / Blank Ticket — tail 26 |
| 6 | Wave to You (2026-07-02) | 58 / 54 / 50 after Goddess Fall / Blank Ticket / Terminus Ticket — tail 22 |
| 6 | Project Matis (2026-07-23) | 57 / 53 / 51 after Blank Ticket / Terminus Ticket / Ark Guardian — tail 19 |
| 6 | Persona on Frontline (2026-08-12) | 59 / 55 / 53 after Blank Ticket / Terminus Ticket / Ark Guardian — tail 17 |

The settled line — **Blue Water Island → Kill the Lord → Phantom Thief vs Detective → Lord, for Justice → Blank Ticket → Project Matis** — is picked because:

- it is the tightest spread of the 263 lines (59 / 56 / 55 / 54 / 58 / 57 — every window inside 54–59);
- every cut-off event's marquee NIKKE is dated on the cut-off day, so each set's name matches its content;
- it sidesteps the 2024-09-19 double-event date (Nonsense Red and Jinx Player start the same day — a set cut there has no single name);
- set 1 then extends to **Sea You Again** (2023-08-03) on theme: *Blue Water Island* and *Sea You Again* are both summer-island events and share a location, so the two are released together under the *Blue Water Island* name. Set 1 carries 73 NIKKE entries in the band — the window's 72 plus *Helm: Aquamarine* (c353, 2023-08-10), a summer-themed model released shortly after the cut-off, added as a single-model add-on (72 in the roster — Mast_old is curated out) — and 45 extras = 117 models; set 2 becomes the residual window (2023-08-03, 2024-03-07] minus that add-on — 42 NIKKE entries, 47 extras = 89 models. No in-band cut exists in that residual window (the 15 event start-dates in it would carry at most 43), so *Kill the Lord* stands as the named cut-off with its marquee NIKKE (D: Killer Wife) dated on the day.

Caveats on the other options: **Memories Teller** (2025-06-12) as set 4 splits EVE/Raven across the set boundary (EVE is dated on the cut-off, Raven 2025-06-19 lands in the next window); **Persona on Frontline** (2026-08-12) as set 6 would name the set after a collab whose models are dated after the event start (Queen/Aigis 2026-08-13, Yukiko 2026-08-20 — they fall in the tail either way).

Roster size across the 263 lines (models per set, curation applied — the settled line deviates at sets 1–2 by the thematic extension and the single-model add-on, at 117 and 89):

| Set | min | median | max |
|---|---|---|---|
| 1 | 92 | 97 | 100 |
| 2 | 96 | 106 | 111 |
| 3 | 74 | 81 | 85 |
| 4 | 90 | 99 | 105 |
| 5 | 79 | 88 | 102 |
| 6 | 88 | 104 | 117 |

## Sources

- Cut-offs: <https://nikke-goddess-of-victory-international.fandom.com/wiki/Event#Event_Archiving> — fetched 2026-11-05; the parsed (name, start-date) pairs are kept in `database/events.json` (87 events).
- Roster and dates: `database/models.json` — the viewer's full client dump (740 models, all dated, through 2026-11-05; presence means the model is in the current catalog).
- Card titles and NIKKE rarities: `database/characters.json` (313 entries) — every NIKKE base id in this plan has a record (verified 2026-11-05); extras without one fall back to the model's name.
- `database/banners.json` (165 banners, fetched 2025-10-21) is no longer a cut-off source — the event archive replaced the banner history for boundaries — and is kept for banner names and portraits.

## Naming and files

- `cards/BlueWaterIsland.toml`, `cards/KillTheLord.toml`, `cards/PhantomThief.toml`, `cards/LordForJustice.toml`, `cards/BlankTicket.toml`, `cards/ProjectMatis.toml` — the event-art model ids in CamelCase (the `cards/Base` single-word convention).
- Roster order inside `cards`: per the Rosters section (NIKKEs in release order, then the non-CG extras, the event CGs closing the set).
- `rarities`, `pack`, `logo` and `background` are per-set at build time; Base's values are the defaults to start from.

## Build status

- All six sets and the tail: every model is in the current catalog and every NIKKE base id in `characters.json` — renderable today.
- The dated client dump settles the old plan's "unreleased" flags: Denji (c803, 2023-02-22) and Aki Hayakawa (c804, 2023-02-22) in set 1, 9S (c813, 2023-09-01) in set 2, Adam (c853, 2025-06-12) in set 5, Rapunzel: Pure Grace (c226, 2024-10-31) in set 4. *Endless* (c371, 2025-08-07, set 5) — a story NPC (deceased) in the old plan's reserve — is a dated model and prints as a NIKKE entry.
- The old commons reserve is fully absorbed by the windows: Himeno, Neve, Rei, Nihilister → 1; Kilo → 3; Mecha Shifty → 4 (story-range id — extra); Lily, Chime, Endless, Claire → 5; Kurumi, Avistar → 6; Aigis → tail; Syuen → 3 (story-range id — extra); Shifty → 1 (story-range id — extra); Rapunzel: Pure Grace → 4. The four with no model (liqueur c053, Acre c081, Bibli c320, Pin c342) are absent from the catalog and print in no set.
- Open for the build — extras' presentation treatment goes beyond Base's precedent (story characters: static + idle only, their absent in-game rarity treated as R; Ghosts: same treatment — flagged; event CGs: a single full-art presentation at the set's highest, fixed SSR; chibis and the CN-exclusive Ying Ning/Hua Pi: treatment TBD).
- *Sakura* (c836, 2023-03-30, set 1): the 2026-10-24 audit leaves its identity unverified (name collision with c282); it prints as the dated model does.

## Data notes

- The MARIA-n pair are new fairy-tale-line characters beside the launch ones — Rapunzel: Sanctuary (c473) beside Rapunzel (c221), Scarlet: Goddeath (c472) beside Scarlet (c222), the third being Snow White: Heavy Arms (c471, set 6) beside Snow White (c220); `characters.json` carries c472/c473 under the bare names *Scarlet*/*Rapunzel* (manufacturer PILGRIM, SSR), so the cards title that way.
- Two *Grave* models (c510 and c514) are both dated 2024-11-07 (set 4), and the placeholder *Ark Ranger Black* (c570_99) is dated 2024-05-16 (set 3) ahead of the real model (c570, 2026-06-11, set 6) — they print as the dated models do.
- *Marian* (c013): the catalog name carries a leading underscore (`_Marian`); `characters.json` and the rosters use the clean name, as throughout.
- Card titles come from `characters.json` and the subtitle (the skin) from the model's name; the roster tables above show the `characters.json` name for base ids and the model's name for sub-flavors.

## Changelog

- 2026-11-05: cut-offs re-based from the banner history to the wiki's **Event archive** (Event page, Event Archiving — fetched 2026-11-05, 87 events / 84 distinct start dates, 2022-11-10 → 2026-10-29; the parsed pairs are now `database/events.json`). The nine banner-history packs (Devil Hunter … Pumpkin Witch, 20–30 NIKKEs with New/Re-appears/Base-forms/Reserve/Collab slots and the commons reserve) are superseded by **six event-named sets**, each sized at **50–60 NIKKE entries** — a NIKKE entry being a `c\d{3}` base id under 900 (the c9xx story range, the c9000+ Ghost series and the four-digit CN-exclusive c8xxx ids excluded; `*_80` CN sub-flavors count under their base id) — with **every other model dated in a set's window riding in as extras** (story characters, Ghosts, event CGs and event models, Smol/Favorite chibis, CN-exclusive NIKKEs). Base is unchanged and already built. The band admits 263 lines of six sets; the seventh is infeasible (no in-band chain reaches 350 of the 358 post-launch NIKKE entries). Settled line: **Blue Water Island** (2023-06-15, 59), **Kill the Lord** (2024-03-07, 56), **Phantom Thief vs Detective** (2024-10-03, 55), **Lord, for Justice** (2025-05-29, 54), **Blank Ticket** (2025-11-20, 58), **Project Matis** (2026-07-23, 57) — the tightest spread (all windows inside 54–59), each set named for its cut-off event whose marquee NIKKE is dated on the cut-off day, the 2024-09-19 double-event date (Nonsense Red + Jinx Player) avoided, simultaneous waves (the NERV trios, the Rapi winter, EVE/Raven, the RE trio, the Kuroko's pair, the Guilty/Sin twins, the Persona/Kuroko's wave) never split. Base's curation precedents extend to the new sets: no bosses (set 1 drops the 8 remaining launch-era boss models), no Faceless crowd NPCs (set 5 drops c947–c952), no `*_old` legacy siblings (set 1 drops Shifty_old c907_01, set 2 drops Mast_old c350_old — set 2's roster is 55 against the band's 56), the no-filter story-scene rule (no applicable pair in any new window). The pending tail (19 NIKKE + 17 extras = 36 models, from Maxwell: Ordinary Mechanic 2026-07-30) becomes the next set once it reaches 50 NIKKE entries — the latest archived event (*MARIA-n*, 2026-10-29) would carry only 18, so the set waits for further releases. CN treatment: `c082_80`/`c233_80`/`c260_80` count as NIKKE entries; the CN-exclusive c8004–c8006 (Ying Ning ×2, Hua Pi, 2025-11-25) and `c902_01` Mustang (CN) ride as extras. The dated client dump (740 models, through 2026-11-05) supersedes the old plan's release flags: Denji c803 and Aki Hayakawa c804 (2023-02-22) in set 1, 9S c813 (2023-09-01) in set 2, Adam c853 (2025-06-12) in set 5, Rapunzel: Pure Grace c226 (2024-10-31) in set 4, Endless c371 (2025-08-07) in set 5; the commons reserve is fully absorbed by the windows (the four no-model members — liqueur, Acre, Bibli, Pin — print in no set). Full per-set rosters recorded below (619 models across the six sets + tail; 14 post-launch models curated out of everything). Set 1 then extends to *Sea You Again* (2023-08-03) — *Blue Water Island* and *Sea You Again* are both summer-island events sharing a location, so the two are released together under the *Blue Water Island* name (the shared location): set 1 carries 72 NIKKE entries in the band (71 in the roster — Mast_old c350_old's curation moves with the window) and 45 extras = 116 models; set 2 becomes the residual window (2023-08-03, 2024-03-07] — 43 NIKKE entries (no in-band cut exists in it — the 15 event start-dates would carry at most 43), 47 extras = 90 models, *Kill the Lord* standing as the named cut-off. *Helm: Aquamarine* (c353, 2023-08-10) — summer-themed, released shortly after *Sea You Again*, and the only model dated before the next event (First Affection, 2023-08-24) — then joins set 1 as a single-model add-on: set 1 carries 73 NIKKE entries in the band (the window's 72 + the add-on; 72 in the roster), 45 extras = 117 models; set 2's residual is 42 NIKKE entries, 47 extras = 89 models.
- 2026-11-03: the three base packs merge into the single first expansion **Base** (100 models) — the 63 launch NIKKEs (ELYSION 19, TETRA 22, MISSILIS 16 + PILGRIM 6 — the manufacturer lines kept as roster blocks, Rapi leading as 0001) plus the 37 other models `database/models.json` dates 2022-11-04: the 4 launch sub-flavors (c010_01, c010_02, c011_01, c072_01), the 20 story characters/NPCs (c900 Ingrid … c932 Bolt Junior) and the 13 story-scene CGs (story0001 … story1303, the launch chapters 00/02/04/07/12/13); the 7 boss models dated 2022-11-04 (bbg001–003, ebg002, mbg002, mbg004 + mbg004_appearance) are excluded — no bosses. `models.json`'s dates are final (740/740 dated, the null-`date` wording retracted) and now define the launch roster (107 models); the stale † legends drop. New roster slot **Launch model** (summary-table column + Base's blocks); the story characters print static + idle only (their absent in-game rarity treated as R) and the story scenes as event illustration CGs (single full-art presentation, fixed SSR). Ten packs now; packs 4–12 renumber 2–10 (cross-references updated), the summary total 259 → 296 (+ 37 launch models), and "One 63-NIKKE launch pack" moves from the alternatives (rejected 2026-10-22) into the plan, 21/21/21 marked superseded. Consolidation pending: `cards/ELYSION.toml` + `cards/TETRA/` + `cards/MISSILIS/` → `cards/Base.toml` (the 26 drafted cards renumber, the ELYSION baselines re-record as `tests/baselines/Base/`, and the byte-protocol check becomes `uv run test Base c010`). Same-day curation trim: *Rapi_old* (c010_01) and the 11 Faceless crowd NPCs (c911, c912, c916–c924) are dropped — launch models 37 → 25, Base 100 → 88, total 296 → 284, and the two sub-flavor cards renumber again (0064 *Rapi White Promise*, 0066 *Diesel Black Sunday*). The story scenes then print the no-filter variants where they exist — the 2 filtered duplicates (story0001, story0002) are dropped: launch models 25 → 23, Base 88 → 86, total 284 → 282. `cards/Base.toml` is created (its values from `cards/ELYSION.toml`, its `cards` the 86 launch models in roster order); the consolidation's remainder — the drafted cards' renumber, the baselines' re-record — stays pending. `cards/Base.toml`'s `cards` are then ordered by id across the set — Rapi (c010) sorts first and keeps 0001, the story-scene CGs (the only events) close it — so the drafted cards' numbers move again: 0013 *Brid*, 0040 *Alice*, 0066 *Aria*, 0005 *Anis*, 0011 *Belorta*, 0036 *Admi*, 0002 *Rapi White Promise*, 0016 *Diesel Black Sunday* (0001 *Rapi* unchanged). `cards/ELYSION.toml` is then removed — ELYSION ceases to exist as an expansion (Base is the only toml under `cards/`), the `nocallerid` example card prints in no expansion, and the baselines re-record the same day as `tests/baselines/Base/` (`test Base c010 --new-baseline`; the forced re-render matches byte-for-byte, so the byte-protocol check is `uv run test Base c010` — the AGENTS.md line updated); the leftovers are then removed — the orphaned `tests/baselines/ELYSION/` baselines, the empty old-set stem dirs (`cards/ELYSION/`, `cards/TETRA/`, `cards/MISSILIS/`) and the `output/ELYSION*` artifacts — the 26 drafts re-drafting under their Base numbers on the next generate.
- 2026-10-24: the ELYSION base pack stands at 19 — the *Bibli* (c320) reserve top-up is dropped, base packs carry launch-day NIKKEs only (purity beats the 20 lower bound); *Bibli* returns to the commons reserve (16 → 17), reserve top-ups 7 → 6, total roster 259 → 258. Release-status audit via the viewer (`../nikke-viewer`), corrected: the current model catalog is `database/src/utils/json/l2d.json` (740 models, full client dump) — `assets/js/json/l2d.json` (267), used for an interim flip, is stale, and its 5 extra named models (liqueur, Acre, Bibli, Siren, Pin) are absent from the current catalog; that interim "stale flag → released" flip is therefore retracted except for Kilo (dated 04/25/2024 in the Release dates list). The ‡ mark now covers 10 reserve members — 4 with no current model (liqueur, Acre, Bibli, Pin) and 6 with client models but no release trace (Endless, Avistar, Lily, Kurumi, Aigis, Mecha Shifty) — plus both pack picks (Siren c340 → pack 5, Claire c842 → pack 10), keep-or-replace pending; *Bibli* is unreleased (data-mined) after all — the pack 1 exclusion stands on both grounds (unreleased and not launch-day). Siren c340 (pack 5 pick) resolved the same day: it is the data-mined pre-release alias of *Little Mermaid* (c513, released 2025-04-24, pack 12 roster) — the pick duplicates a roster NIKKE, so it is replaced (recommend Himeno c802, the only dated released reserve member before the pack's 2023 window); c340 itself has no model in the current catalog. Claire c842 (pack 10 pick) resolved the same day: likely released — a Resident Evil collab character of the Outbreak period (the trio with Ada c840 and Jill c841); its absence from the banner tracker and Release dates list is source incompleteness, not non-release; the pick stands. The International fandom wiki (verified 2026-10-24) then resolved the rest: all five remaining ‡ reserve members are released with dates (Mecha Shifty 04/01/2025, Lily 06/12/2025, Kurumi 02/12/2026, Avistar 04/23/2026, Aigis 08/13/2026) — the reserve's ‡ set is now just the 4 no-model names (liqueur, Acre, Bibli, Pin, confirmed page-less); *Endless* (c371) is removed from the reserve — a story NPC (deceased), not a playable NIKKE (17 → 16); *Siren* confirmed as *Little Mermaid*'s in-story nickname rather than a pre-release alias. *Endless* (c371) is restored to the reserve (16 → 17) — NPCs are card-able. The five stale `characters.json` entries (Siren c340 and the four no-model ‡ names) are dropped from the file (206 → 201). *Himeno* (c802) is confirmed a Chainsaw Man/Devil Hunter collab NIKKE (wiki: same 02/22/2023 wave as Makima c800 and Power c801) — drawn to the Genesis pack instead of Abyss filler (Reserve 2 → 3; pack 20 → 21; top-ups 6 → 7; total 258 → 259), leaving the commons reserve (17 → 16); the pack 5 replacement recommendation becomes *Shifty* (c907, ELYSION R, 04/01/2023). A `Collab` grouping is added (new summary-table column + per-pack line, footnote ⁴): collab NIKKES released in-window with no banner in the tracker are classified as Collab rather than Reserve — *Himeno* moves from Genesis's Reserve to its Collab line (Genesis 3 → 2 Reserve, 1 Collab) and *Claire* (c842, Resident Evil — the only other ABNORMAL among the drawn top-ups) from Outbreak's Reserve to its Collab line (Outbreak 1 → 0 Reserve, 1 Collab); totals unchanged (Reserve 7 → 5, Collab 2, 259). The commons reserve table is reformatted to one member per row (cosmetic). `database/characters.json` is completed and re-sourced (201 → 311): every base c-id of the current catalog (310) plus *Belorta: Pumpkin Witch* (c063, which postdates the snapshot) — 222 playable NIKKEs / 40 story characters / 49 no-wiki models — with a new `release_date` field (wiki-verified ISO dates, null otherwise). The wiki cross-check corrects 16 existing entries: c190 *Lucilla* → *Ludmilla*, c262 *Liberelli* → *Liberalio*, c321 *Marchana* → *Marciana*, c310 *Aid* → *Ade*, c041 *Agent K* → *K*, the underscored names (_Marian/_Rouge/_Moran/_Chime) cleaned, and the collabs by full name (*Ada Wong*, *Jill Valentine*, *Claire Redfield*, *Asuka Shikinami Langley*, *Mari Makinami Illustrious*, *Chisato Nishikigi*, *Takina Inoue*). Consequences: base *Ludmilla* (c190) is confirmed in the current catalog — the TETRA launch placeholder is filled with c190, the pack-12 ‡ marks on the Kuroko's pair drop (wiki-dates 08/13 + 08/20/2026, one day later than the roster's 08/12 + 08/19), and *Ludmilla* leaves the commons reserve (15 — she is on the TETRA roster; the pool split is now 39 launch + 7 drawn). Four data-mined collab models are newly identified as unreleased (client model, no wiki page): Denji (c803), Aki Hayakawa (c804), 9S (c813), Adam (c853). Follow-up audit of the no-page entries: *Rei Ayanami (Tentative Name)* (c834) is confirmed as the second collab Rei (wiki: Abnormal, NERV, SSR, 2025-02-27) and is already on the Red Hood roster (New, 2025-02-27, from the banner tracker — the roster was right; no change needed); *Asuka: WILLE* (c835) gets its file `release_date` 2025-02-20 from the banner roster (its wiki page is a redirect); c836 *Sakura* had borrowed c282's *Sakura* NIKKE data via a name collision and is nulled (identity unverified — collab-range model with no page, banner, or roster reference). The *Release dates* section (127 entries, MM/DD/YYYY, ending at *Ein* 07/25/2024) is removed — fully superseded by `database/characters.json`'s `release_date`: every listed name and date is present in the file except *Nero* (c380), where the list's 06/06/2023 (June) conflicts with the wiki's 6 July 2023 — the file keeps the wiki date. References now point at the file. The *Genesis* pack is renamed **Devil Hunter**: its name was a position artifact (the "first" slot belongs to the base packs since the 2026-10-22 restructure) and collided with pack 7's *Neon Genesis*; the new name follows the headline-content convention with the pack's marquee content — the Chainsaw Man/Devil Hunter collab wave (Makima c800, Power c801, 2023-02-21; Himeno c802, 2023-02-22) — on the same footing as *Neon Genesis* and *Outbreak*. `cards/Genesis/` → `cards/DevilHunter/`; the gitignored `output/` artifacts regenerate on the next build.
- 2026-10-22: launch roster (the 63 base NIKKEs, per the new Release dates section) split into three base packs before all the others — ELYSION (20, the set's face Rapi leading as 0001), TETRA (22, incl. Ludmilla †), MISSILIS (16 MISSILIS + 6 PILGRIM) — grouped by manufacturer (ELYSION first as the face-card line, then by launch-line size), ordered SSR → SR → R (ties by NIKKE id; Rapi leads ELYSION as 0001) instead of alphabetical; the 22 launch NIKKEs previously printed as base forms in the other packs move to the base packs; 7 reserve top-ups (ELYSION ×1, Genesis ×2, Abyss ×3, Outbreak ×1) hold those packs at 20; commons reserve 61 → 16; 12-pack structure with every pack inside 20–30.
- 2025-10-21: plan drafted from the banner history (165 banners) and the 206-skin viewer database; 9-pack structure settled at 20–30 NIKKEs per pack.
