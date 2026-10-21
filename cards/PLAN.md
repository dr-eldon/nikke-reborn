# NIKKE REBORN — Card Pack Plan

*Status: planning · drafted 2025-10-21 · the `cards/Alpha` set is a dev prototype (see data notes)*

Nine card packs (expansions) covering every NIKKE banner release from Nov 2022 to Oct 2026, in release order. Each pack carries **20–30 NIKKEs**; each NIKKE in a pack gets the three card variants — static, idle animated, and a skill-cut full art where the NIKKE has a cut-in (all roster NIKKEs are SR/SSR and do).

## How a pack is built

| Roster slot | What it is | Source |
|---|---|---|
| **New** | the pack's featured NIKKEs — every banner first appearance in the pack's window, in release order | banner history |
| **Re-appears** | NIKKEs whose (older) banner the game re-ran concurrently with the pack's banners — the "previous packs re-appear" rule | banner re-runs |
| **Base forms** | a featured skin's base model, where it exists in the viewer database (e.g. base *Rapi* beside *Rapi: Red Hood*) | viewer database |

- Packs are grouped by release season; seasons are merged until the roster lands at 20–30 NIKKEs. Concurrent banners are never split across packs (2B/A2, the NERV trios).
- Nothing is double-counted inside a pack (a NIKKE listed as a re-appearance is not also listed as a base form); the same NIKKE may appear in several packs — re-appears and base forms are often re-lists of a pack's own predecessors (base *Helm* in Abyss re-lists Genesis' Helm; *Dorothy* in Outbreak re-lists Genesis' Dorothy).
- Pack slots are filled per the pack rarity config (mostly common): the **commons reserve** (below) supplies repeat-print filler, while the pack's new NIKKEs anchor the top tiers and re-appears/base forms print mid-rarity.

## Sources

- Banner history: <https://lootandwaifus.com/nikke-banner-history/> (GLOBAL server list — 165 banners: 120 first appearances + 45 re-runs, Nov 2022 – Oct 2026). Fetched 2025-10-21; raw parse kept in `database/banners.json`. Portrait paths resolve to the viewer model ids (`mi_c405_00` → `c405`); four legacy-portrait banners were resolved against the database (c103, c105, c322, c515).
- Renderable roster: `database/characters.json` — 206 NIKKE skins `nikke-viewer` can render (`c`-prefixed ids, as used by card JSON `id` fields).
- Cross-check: <https://nikke.gg/characters/> (client-rendered; its latest-48 roster confirmed the same id scheme).

## Packs

| # | Pack | Window¹ | New | Re-appears | Base forms | Total |
|---|------|--------|-----|-----------|------------|-------|
| 1 | **Genesis** | 2022-11-10 – 2023-05-31 | 19 | 0 | 1 | **20** |
| 2 | **Abyss** | 2023-06-14 – 2023-11-22 | 14 | 2 | 4 | **20** |
| 3 | **Molten** | 2023-12-06 – 2024-05-30 | 15 | 3 | 5 | **23** |
| 4 | **Neon Genesis** | 2024-06-06 – 2024-11-21 | 16 | 6 | 4 | **26** |
| 5 | **Red Hood** | 2024-12-05 – 2025-05-29 | 15 | 6 | 6 | **27** |
| 6 | **Tactical** | 2025-06-12 – 2025-08-21 | 8 | 10 | 5 | **23** |
| 7 | **Outbreak** | 2025-09-04 – 2025-11-20 | 8 | 11 | 3 | **22** |
| 8 | **Blizzard** | 2025-12-04 – 2026-05-28 | 14 | 5 | 6 | **25** |
| 9 | **Pumpkin Witch** | 2026-06-11 – 2026-10-08 | 11 | 11 | 8 | **30** |
| — | — | — | **120** | 54² | 42² | — |

¹ from the first to the last *new* NIKKE released in the pack (banner end-dates overlap between neighbours).
² roster slots, not distinct NIKKEs — several re-list NIKKEs featured in earlier packs.

### 1 · Genesis — Nov 2022 – May 2023 (20 NIKKEs)

**New (19)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Helm | c352 | 2022-11-10 |
| Laplace | c100 | 2022-11-24 |
| Rupee: Winter Shopper | c203 | 2022-12-08 |
| Anne: Miracle Fairy | c121 | 2022-12-15 |
| Modernia | c260 | 2022-12-31 |
| Jackal | c111 | 2023-01-11 |
| Viper | c112 | 2023-01-11 |
| Cocoa | c311 | 2023-01-31 |
| Soda | c312 | 2023-01-31 |
| Makima | c800 | 2023-02-21 |
| Power | c801 | 2023-02-21 |
| Biscuit | c381 | 2023-03-14 |
| Sakura | c282 | 2023-03-29 |
| Alice | c191 | 2023-04-12 |
| D | c040 | 2023-04-12 |
| Dorothy | c233 | 2023-04-26 |
| Blanc | c270 | 2023-05-17 |
| Noir | c271 | 2023-05-24 |
| Rosanna | c280 | 2023-05-31 |

**Re-appears (0)**: —

**Base forms (1)**: Rupee (c200)

### 2 · Abyss — Jun 2023 – Nov 2023 (20 NIKKEs)

**New (14)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Mary: Bay Goddess | c132 | 2023-06-14 |
| Neon: Blue Ocean | c014 | 2023-06-21 |
| Nero | c380 | 2023-07-05 |
| Mast | c350 | 2023-07-19 |
| Anis: Sparkling Summer | c015 | 2023-08-02 |
| Helm: Aquamarine | c353 | 2023-08-09 |
| 2B | c810 | 2023-08-31 |
| A2 | c811 | 2023-09-07 |
| Marchana | c321 | 2023-09-20 |
| Naga | c450 | 2023-10-04 |
| Tia | c451 | 2023-10-11 |
| Quiry | c033 | 2023-10-18 |
| Red Hood | c470 | 2023-11-01 |
| Tove | c192 | 2023-11-22 |

**Re-appears (2)**: Anne: Miracle Fairy (c121), Rupee: Winter Shopper (c203)

**Base forms (4)**: Neon (c011), Anis (c012), Mary (c130), Helm (c352)

### 3 · Molten — Dec 2023 – May 2024 (23 NIKKEs)

**New (15)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ludmilla: Winter Owner | c194 | 2023-12-06 |
| Mica: Snow Buddy | c062 | 2023-12-13 |
| Scarlet: Black Shadow | c225 | 2023-12-31 |
| Leona | c382 | 2024-01-11 |
| Moran | c281 | 2024-01-25 |
| Privaty: Unkind Maid | c313 | 2024-02-05 |
| Aid | c310 | 2024-02-15 |
| Elegg | c500 | 2024-02-22 |
| D: Killer Wife | c043 | 2024-03-07 |
| Emilia | c821 | 2024-03-21 |
| Rem | c820 | 2024-03-27 |
| Bay | c550 | 2024-04-11 |
| Crown | c330 | 2024-04-25 |
| Trony | c501 | 2024-05-16 |
| Soda: Twinkling Bunny | c314 | 2024-05-30 |

**Re-appears (3)**: Anne: Miracle Fairy (c121), Rupee: Winter Shopper (c203), Modernia (c260)

**Base forms (5)**: D (c040), Mica (c061), Privaty (c170), Scarlet (c222), Soda (c312)

### 4 · Neon Genesis — Jun 2024 – Nov 2024 (26 NIKKEs)

**New (16)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Alice: Wonderland Bunny | c195 | 2024-06-06 |
| Clay | c551 | 2024-06-20 |
| Sakura: Bloom in Summer | c284 | 2024-07-04 |
| Rosanna: Chic Ocean | c283 | 2024-07-11 |
| Ein | c391 | 2024-07-25 |
| Zwei | c390 | 2024-08-08 |
| Asuka | c830 | 2024-08-21 |
| Rei Ayanami | c831 | 2024-08-29 |
| Mari | c832 | 2024-09-05 |
| Rouge | c272 | 2024-09-19 |
| Quency: Escape Queen | c403 | 2024-10-03 |
| Phantom | c580 | 2024-10-10 |
| Rumani | c240 | 2024-10-17 |
| Cinderella | c511 | 2024-10-31 |
| Grave | c514 | 2024-11-07 |
| Flora | c411 | 2024-11-21 |

**Re-appears (6)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Mica: Snow Buddy (c062), Mary: Bay Goddess (c132), Ludmilla: Winter Owner (c194), Helm: Aquamarine (c353)

**Base forms (4)**: Alice (c191), Rosanna (c280), Sakura (c282), Quency (c402)

### 5 · Red Hood — Dec 2024 – May 2025 (27 NIKKEs)

**New (15)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Maiden: Ice Rose | c183 | 2024-12-05 |
| Guillotine: Winter Slayer | c182 | 2024-12-12 |
| Rapi: Red Hood | c016 | 2025-01-01 |
| Mana | c290 | 2025-01-16 |
| Mast: Romantic Maid | c354 | 2025-01-30 |
| Anchor: Innocent Maid | c355 | 2025-02-06 |
| Asuka: WILLE | c835 | 2025-02-20 |
| Rei Ayanami (Tentative Name) | c834 | 2025-02-27 |
| Trina | c412 | 2025-03-13 |
| Bready | c520 | 2025-03-27 |
| Crust | c521 | 2025-04-10 |
| Little Mermaid | c513 | 2025-04-24 |
| Mihara: Bonding Chain | c162 | 2025-05-01 |
| Arcana | c581 | 2025-05-15 |
| Agent K | c041 | 2025-05-29 |

**Re-appears (6)**: Mica: Snow Buddy (c062), Ludmilla: Winter Owner (c194), Scarlet: Black Shadow (c225), Asuka (c830), Rei Ayanami (c831), Mari (c832)

**Base forms (6)**: Rapi (c010), Mihara (c161), Guillotine (c180), Maiden (c181), Mast (c350), Anchor (c351)

### 6 · Tactical — Jun 2025 – Aug 2025 (23 NIKKEs)

**New (8)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| EVE | c850 | 2025-06-12 |
| Raven | c851 | 2025-06-19 |
| Sora | c532 | 2025-07-03 |
| Dorothy: Serendipity | c234 | 2025-07-17 |
| Elegg: Boom and Shock | c502 | 2025-07-24 |
| Emma: Tactical Upgrade | c093 | 2025-08-07 |
| Eunhwa: Tactical Upgrade | c095 | 2025-08-14 |
| Vesti: Tactical Upgrade | c094 | 2025-08-21 |

**Re-appears (10)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Anne: Miracle Fairy (c121), Mary: Bay Goddess (c132), Rupee: Winter Shopper (c203), Rosanna: Chic Ocean (c283), Sakura: Bloom in Summer (c284), Helm: Aquamarine (c353), 2B (c810), A2 (c811)

**Base forms (5)**: Emma (c090), Vesti (c091), Eunhwa (c092), Dorothy (c233), Elegg (c500)

### 7 · Outbreak — Sep 2025 – Nov 2025 (22 NIKKEs)

**New (8)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ade: Agent Bunny | c315 | 2025-09-04 |
| Milk: Blooming Bunny | c143 | 2025-09-11 |
| Ada | c840 | 2025-09-24 |
| Jill | c841 | 2025-10-02 |
| Delta: Ninja Thief | c023 | 2025-10-16 |
| Nayuta | c223 | 2025-10-30 |
| Liberelli | c262 | 2025-11-06 |
| Soline: Frost Ticket | c074 | 2025-11-20 |

**Re-appears (11)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Anne: Miracle Fairy (c121), Mary: Bay Goddess (c132), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), Rupee: Winter Shopper (c203), Dorothy (c233), Modernia (c260), Helm: Aquamarine (c353), Red Hood (c470)

**Base forms (3)**: Delta (c020), Soline (c071), Milk (c141)

### 8 · Blizzard — Dec 2025 – May 2026 (25 NIKKEs)

**New (14)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Diesel: Winter Sweets | c075 | 2025-12-04 |
| Brid: Silent Track | c073 | 2025-12-10 |
| Snow White: Heavy Arms | c471 | 2025-12-31 |
| Label | c582 | 2026-01-14 |
| Velvet | c316 | 2026-01-29 |
| Chisato | c860 | 2026-02-11 |
| Takina | c861 | 2026-02-18 |
| E.H. | c113 | 2026-03-05 |
| Arcana: Fortune Mate | c583 | 2026-03-19 |
| Snow Crane | c620 | 2026-04-09 |
| Anis: Star | c017 | 2026-04-22 |
| Neon: Vision Eye | c018 | 2026-04-29 |
| Mint | c600 | 2026-05-14 |
| Prika | c601 | 2026-05-28 |

**Re-appears (5)**: Rapi: Red Hood (c016), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), EVE (c850), Raven (c851)

**Base forms (6)**: Neon (c011), Anis (c012), Brid (c070), Diesel (c072), Snow White (c220), Arcana (c581)

### 9 · Pumpkin Witch — Jun 2026 – Oct 2026 (30 NIKKEs)

**New (11)** — in release order:

| NIKKE | ID | Released |
|---|---|---|
| Ark Ranger Black | c570 | 2026-06-11 |
| Cinderella: Crystal Wave | c515 | 2026-07-02 |
| Marciana: Marine Study | c322 | 2026-07-08 |
| Laplace: Ultimate Hero | c103 | 2026-07-23 |
| Maxwell: Ordinary Mechanic | c105 | 2026-07-29 |
| Queen (Makoto Nijima) † | c870 | 2026-08-12 |
| Yukiko † | c871 | 2026-08-19 |
| Drake: Great Villain | c104 | 2026-09-03 |
| Guilty: Mighty Bunny | c404 | 2026-09-17 |
| Sin: Swift Bunny | c405 | 2026-09-23 |
| Belorta: Pumpkin Witch | c063 | 2026-10-08 |

**Re-appears (11)**: Neon: Blue Ocean (c014), Anis: Sparkling Summer (c015), Mica: Snow Buddy (c062), Anne: Miracle Fairy (c121), Guillotine: Winter Slayer (c182), Maiden: Ice Rose (c183), Ludmilla: Winter Owner (c194), Rupee: Winter Shopper (c203), Dorothy: Serendipity (c234), Sakura: Bloom in Summer (c284), Helm: Aquamarine (c353)

**Base forms (8)**: Belorta (c060), Laplace (c100), Drake (c101), Maxwell (c102), Marchana (c321), Guilty (c400), Sin (c401), Cinderella (c511)

† not in the viewer database yet — see build status.

## Naming

- Series: **NIKKE REBORN**; the nine packs are its expansions, shipped as `cards/Genesis`, `cards/Abyss`, `cards/Molten`, `cards/NeonGenesis`, `cards/RedHood`, `cards/Tactical`, `cards/Outbreak`, `cards/Blizzard`, `cards/PumpkinWitch` (matching the existing `cards/Alpha` single-word convention).
- Each pack name is its headline content:

| Pack | Name | Why |
|---|---|---|
| 1 | Genesis | the global-launch wave (Alice, D, Dorothy, Blanc, Noir …) — the game's launch chapter |
| 2 | Abyss | the ocean-skin summer (Mary: Bay Goddess, Neon: Blue Ocean, Anis: Sparkling Summer, Helm: Aquamarine) |
| 3 | Molten | the v2.0-era window: Scarlet, the first winter limiteds, D: Killer Wife, Emilia/Rem |
| 4 | Neon Genesis | the NERV collab trio (Asuka, Rei Ayanami, Mari) + Ein/Zwei |
| 5 | Red Hood | Rapi: Red Hood's winter, plus the second NERV wave (Asuka: WILLE, Rei Ayanami (TN)) |
| 6 | Tactical | the Emma/Eunhwa/Vesti: Tactical Upgrade wave with EVE, Raven, Sora |
| 7 | Outbreak | the Resident Evil collab (Ada, Jill) and the bunny duo (Ade, Milk) |
| 8 | Blizzard | the Dec 2025–Jan 2026 winter wave (Diesel: Winter Sweets, Brid: Silent Track, Snow White: Heavy Arms) |
| 9 | Pumpkin Witch | Belorta's Halloween banner, the bunny twins (Guilty, Sin) and the Kuroko's collab |

## Build status

- Packs 1–8: every NIKKE is in `database/characters.json` — renderable today.
- Pack 9: needs two viewer models before it can render — `Queen (Makoto Nijima)` (c870) and `Yukiko` (c871) (Kuroko's Basketball collab, Aug 2026). All 28 other NIKKEs in the pack are ready.
- The global-launch standard banners (Ryu, Meryl, Bittercandy …) are absent from both the banner tracker and the viewer database, so no pack covers them; if wanted, that is a 10th "launch" pack pending viewer models.

## Commons reserve

61 NIKKEs from the viewer database are in no pack roster. They are the staple fillers for the packs' common slots (and the raw material for a future "Classics" reissue pack). R-ranks have no skill cut-in, so they would carry static + idle only.

| ID | NIKKE | Rarity | | ID | NIKKE | Rarity |
|---|---|---|---|---|---|---|
| c013 | Marian | SR | c261 | Nihilister | SSR |
| c022 | Signal | SSR | c291 | Ether | SR |
| c030 | Poli | SSR | c300 | Soldier EG | R |
| c032 | Miranda | SSR | c301 | Soldier FA | R |
| c053 | liqueur | R | c302 | Product 08 | R |
| c080 | Centi | SSR | c303 | Product 12 | R |
| c081 | Acre | R | c304 | iDoll Flower | R |
| c082 | Liter | SSR | c305 | iDoll Ocean | R |
| c110 | Crow | SSR | c306 | Soldier OW | R |
| c120 | N102 | SR | c307 | Product 23 | R |
| c131 | Pepper | SSR | c308 | iDoll Sun | R |
| c140 | Sugar | SSR | c320 | Bibli | SSR |
| c142 | Frima | SSR | c331 | Chime | SSR |
| c150 | Julia | SSR | c340 | Siren | SSR |
| c160 | Yuni | SSR | c342 | Pin | SSR |
| c171 | Yulha | SSR | c361 | Kilo | SSR |
| c172 | Admi | SSR | c371 | Endless | SSR |
| c190 | Lucilla | SSR | c392 | Rei | SSR |
| c193 | Neve | SR | c430 | Noise | SSR |
| c201 | Yan | SSR | c431 | Volume | SSR |
| c202 | Dolla | SSR | c432 | Aria | SSR |
| c210 | Exia | SSR | c441 | Avistar | SSR |
| c212 | Novel | SSR | c802 | Himeno | SR |
| c221 | Rapunzel | SSR | c842 | Claire | SR |
| c224 | Snow White: Innocent Days | SSR | c852 | Lily | SR |
| c226 | Rapunzel: Pure Grace | SSR | c862 | Kurumi | SR |
| c230 | Harran | SSR | c872 | Aigis | SR |
| c231 | Isabel | SSR | c901 | Syuen | R |
| c232 | Noah | SSR | c907 | Shifty | R |
| c241 | Epinel | SSR | c993 | Mecha Shifty | R |
| c242 | Folkwang | SSR | | | |

## Data notes

- Packs 1–2 begin with the KR-launch era (Nov 2022 – Mar 2023); the tracker's history is the true release order across servers.
- Spelling quirks from the source data: the database spells c321 *Marchana* (officially Marciana) and c310 *Aid* (officially Ade); the banner titles read *K* (database: Agent K) and *Liberalio* (database: Liberelli). Pack rosters use the database names (the renderable ones); banner names are preserved in `database/banners.json`.
- Pack 9's re-appearances: the concurrent re-run window nominally carries 14 NIKKEs; three (Mary: Bay Goddess c132, Rosanna: Chic Ocean c283, Elegg: Boom and Shock c502) are trimmed to keep the roster at 30. Drop the trim if 20–30 is a soft bound (roster 33).
- `cards/Alpha` is the dev prototype (Rapi + Neon, including sub-flavor viewer ids like `c010_02` White Promise and `c016_01` Red Hood Red Flavor that sit outside the top-level database). Its NIKKEs are covered by packs 2, 5 and 8 (Neon c011, Rapi c010 / Rapi: Red Hood c016); sub-flavors are a future per-card option, not part of this plan.

## Alternatives considered

- **8 packs**: merge 6 (Tactical) + 7 (Outbreak) — 16 new + 15 distinct re-appears + 7 base = 38, trimmed to 30 by dropping 8 re-appears.
- **10 packs**: split 4 (Neon Genesis) at the NERV collab — Jun–Aug 2024 (8 new + 4 re + 3 base = 15, topped up from the reserve to 20) and Sep–Nov 2024 (the NERV trio, Rouge, Quency: Escape Queen, Phantom, Rumani, Cinderella, Grave, Flora: 8 new + 2 re + 1 base = 11, topped up to 20).

## Changelog

- 2025-10-21: plan drafted from the banner history (165 banners) and the 206-skin viewer database; 9-pack structure settled at 20–30 NIKKEs per pack.
