"""Simulate pack openings for an expansion and write an HTML report.

``simulate <expansion>`` opens 1000 packs of the expansion and writes a
self-contained report to ``output/<Expansion>.html`` with the statistics
for fine-tuning the pack odds and the card prices: how many cards per
rarity were obtained (observed and expected), the average price per
rarity and each rarity's share of the total value, the average packs per
hit (a hit is a card worth more than the ``--hit`` threshold, 100 by
default), the expected value per pack (simulated and theoretical), the
median pack value, the pack value distribution, the per-slot expected
value and the top cards of the set.

The expansion's bundle is rebuilt from ``cards/<expansion>``,
``database/characters.json`` and the current :mod:`nikke_reborn.metadata`
tuning (the same inputs ``generate`` writes to ``output/<expansion>.json``),
so the report always reflects the current ``SlotWeights`` and price
parameters — no ``generate`` run needed, and a stale bundle on disk is
never consulted.

A pack is opened the way the game's pack generation strategies do:

* ``Guaranteed`` — the seven slots of the pack's ``SlotWeights`` tables,
  one rarity per slot drawn by weight, then one card of that rarity;
* ``AllRandomWeighted`` — all seven slots draw their rarity from the
  shared ``NormalWeights`` table;
* ``AllRandom`` — every slot is a uniform random card of the pool.

A card is never repeated within a pack when the pack disallows
duplicates: a slot draws its rarity from its own weight table
renormalized over the rarities that still have an untaken card, and
comes up empty only when none of the rarities in its table can be
drawn any more. A god pack (rolled when the pack enables them) forces
all of its cards to foil (drawn from ``GodWeights`` when the pack
carries some). Every card is priced with the expansion's ``RarityDriven``
formula:

    (floor + step * the card's index in the expansion's rarity list)
    * border base ** the card's border index,

multiplied by the foil multiplier when the card is foil.
"""

from __future__ import annotations

import argparse
import html
import math
import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import nikke_reborn as nr
from nikke_reborn import metadata

#: The border types in the game's ``ECardBorderType`` order (the price
#: formula multiplies by the border base raised to the border's index
#: here).
BORDERS = ["Base", "FirstEdition", "Silver", "Gold", "EX", "FullArt"]

#: A "hit" is a card worth more than this (the default of ``--hit``).
DEFAULT_HIT_THRESHOLD = 100.0

#: The reference price thresholds of the hit table, alongside the active
#: (``--hit``) threshold.
HIT_THRESHOLDS = (500.0, 1000.0, 10000.0, 50000.0)

#: The number of packs opened by default.
DEFAULT_PACKS = 1000

#: The pack value histogram's bucket upper bounds (exclusive; the last
#: bucket runs to infinity).
HIST_BUCKETS = (10.0, 100.0, 1000.0, 10000.0, 100000.0)


@dataclass
class Card:
    """A card of the expansion's pool, with its price."""

    name: str
    rarity: str
    border: str
    foil: bool
    price: float
    sprite: str


@dataclass
class DrawnCard:
    """A card obtained from a pack slot, with the price it paid in."""

    card: Card
    price: float


@dataclass
class Pack:
    """One opened pack: its cards (one per slot, in slot order; ``None``
    for a slot that could not yield a card) and its god-pack flag."""

    cards: list[DrawnCard | None]
    god: bool

    @property
    def value(self) -> float:
        return sum(card.price for card in self.cards if card is not None)


@dataclass
class SimResult:
    """The outcome of one simulation run, with the per-slot aggregates
    (one entry per slot, in slot order)."""

    packs: list[Pack]
    seed: int
    god_packs: int
    empty_slots: int
    per_slot_value: list[float]
    per_slot_hits: list[int]
    per_slot_rarity: list[Counter]


def card_price(expansion: dict, rarity: str, border: str, foil: bool) -> float:
    """The price of a card of *rarity* with *border* under the expansion's
    price strategy: the ``RarityDriven`` formula — (the floor plus the
    step size times the card's index in the expansion's rarity list)
    times the border multiplier base raised to the card's border index,
    multiplied by the foil multiplier when the card is foil."""
    strategy = expansion["CardPriceStrategy"]
    if strategy != "RarityDriven":
        raise nr.GenerationError(
            f"unsupported price strategy {strategy!r} "
            f"(only 'RarityDriven' is simulated)"
        )
    rarity_index = expansion["Rarities"].index(rarity)
    border_index = BORDERS.index(border)
    price = (
        expansion["RarityDrivenFloor"]
        + expansion["RarityDrivenStepSize"] * rarity_index
    ) * expansion["RarityDrivenBorderMultiplierBase"] ** border_index
    if foil:
        price *= expansion["RarityDrivenFoilMultiplier"]
    return price


def _load_expansion(name: str) -> tuple[dict, dict]:
    """The expansion's metadata and its pack item, built from
    ``cards/<name>`` through the current :mod:`nikke_reborn.metadata`
    tuning (what ``generate`` would write to ``output/<name>.json``)."""
    set_dir = nr.CARDS_DIR / name
    if not set_dir.is_dir():
        available = ", ".join(
            sorted(path.name for path in nr.CARDS_DIR.iterdir() if path.is_dir())
        )
        raise nr.GenerationError(f"unknown expansion {name!r} (available: {available})")
    cards = nr._set_cards(set_dir)
    if not cards:
        raise nr.GenerationError(
            f"no card definitions under {set_dir.relative_to(nr.REPO_ROOT)}/"
        )
    return metadata.expansion(name, cards), metadata.pack(name)


def _pool(expansion: dict) -> list[Card]:
    """The expansion's card pool (what a pack slot draws from), with every
    card's price."""
    cards = []
    for entry in expansion["Cards"]:
        cards.append(
            Card(
                name=entry["Name"],
                rarity=entry["Rarity"],
                border=entry["BorderType"],
                foil=entry["IsFoil"],
                sprite=entry["Sprite"],
                price=card_price(expansion, entry["Rarity"], entry["BorderType"], entry["IsFoil"]),
            )
        )
    return cards


def _pools_by_rarity(cards: list[Card]) -> dict[str, list[Card]]:
    pools: dict[str, list[Card]] = {}
    for card in cards:
        pools.setdefault(card.rarity, []).append(card)
    return pools


def _slot_tables(pack: dict) -> list[dict | None]:
    """The per-slot rarity weight tables of the pack's generation
    strategy: the seven ``SlotWeights`` tables for ``Guaranteed``, the
    shared ``NormalWeights`` table for ``AllRandomWeighted``, and ``None``
    (no table: a uniform random card) for ``AllRandom``."""
    strategy = pack["PackGenerationStrategy"]
    if strategy == "Guaranteed":
        return [pack["SlotWeights"][f"Slot{i}"] for i in range(1, 8)]
    if strategy == "AllRandomWeighted":
        return [pack["NormalWeights"]] * 7
    if strategy == "AllRandom":
        return [None] * 7
    raise nr.GenerationError(f"unsupported pack generation strategy {strategy!r}")


def _god_tables(pack: dict, slot_tables: list[dict | None]) -> list[dict | None]:
    """The god pack's per-slot tables: the pack's ``GodWeights`` table for
    every slot when the pack carries some, the slot's own tables
    otherwise."""
    god_weights = pack.get("GodWeights") or {}
    return [god_weights] * 7 if god_weights else slot_tables


def _god_percentage(pack: dict) -> float:
    """The god pack's probability: the pack's ``GodPackPercentage`` when
    the pack enables god packs, 0 otherwise."""
    if pack.get("CanHaveGodPacks") and pack.get("GodPackPercentage", 0.0) > 0:
        return pack["GodPackPercentage"]
    return 0.0


def _available_table(
    table: dict, taken: set[str], pools: dict[str, list[Card]]
) -> dict[str, float]:
    """The draw-able part of *table*: its positive weights restricted to
    the rarities that still have an untaken card in the pool (a rarity
    with no cards, or whose cards are all in *taken*, cannot be
    obtained)."""
    return {
        rarity: weight
        for rarity, weight in table.items()
        if weight > 0 and any(card.sprite not in taken for card in pools.get(rarity, []))
    }


def _slot_probabilities(
    table: dict | None, pools: dict[str, list[Card]]
) -> dict[str, float]:
    """The probability of each rarity in one draw from *table* (a
    ``None`` table is ``AllRandom``: proportional to the pool sizes); the
    probabilities sum to 1, or the table is empty when no rarity can be
    drawn (its pool is empty)."""
    if table is None:
        total = sum(len(cards) for cards in pools.values())
        if total == 0:
            return {}
        return {rarity: len(cards) / total for rarity, cards in pools.items()}
    total = sum(
        weight for rarity, weight in table.items() if weight > 0 and rarity in pools
    )
    if total <= 0:
        return {}
    return {
        rarity: weight / total
        for rarity, weight in table.items()
        if weight > 0 and rarity in pools
    }


def run_simulation(
    expansion: dict,
    pack: dict,
    cards: list[Card],
    n_packs: int,
    seed: int,
    hit_threshold: float = DEFAULT_HIT_THRESHOLD,
) -> SimResult:
    """Open *n_packs* packs of *pack* against the *cards* pool: one rarity
    per slot drawn by the slot's weight table, then a card of that rarity
    (a card is never repeated within a pack when the pack disallows
    duplicates: the slot's table is renormalized over the rarities that
    still have an untaken card, and the slot comes up empty when none of
    them can be drawn any more; a god pack — rolled when the pack enables
    them — draws from its ``GodWeights`` table when the pack carries some
    and forces all of its cards to foil). A slot's hit count covers the
    cards worth more than *hit_threshold*."""
    rng = random.Random(seed)
    pools = _pools_by_rarity(cards)
    slot_tables = _slot_tables(pack)
    god_tables = _god_tables(pack, slot_tables)
    god_chance = _god_percentage(pack)
    no_duplicates = not pack.get("CanHaveDuplicates", False)

    def draw(table: dict | None, taken: set[str]) -> Card | None:
        """One card for a slot, or ``None`` when the slot's table has no
        draw-able rarity left: a rarity of the table's draw-able part
        (its positive weights renormalized over the rarities that still
        have an untaken card), then a random untaken card of it."""
        if table is None:
            options = [
                card
                for card in cards
                if not no_duplicates or card.sprite not in taken
            ]
            return rng.choice(options) if options else None
        available = (
            _available_table(table, taken, pools)
            if no_duplicates
            else {
                rarity: weight
                for rarity, weight in table.items()
                if weight > 0 and rarity in pools
            }
        )
        if not available:
            return None
        rarity = rng.choices(list(available), weights=list(available.values()))[0]
        if no_duplicates:
            options = [card for card in pools[rarity] if card.sprite not in taken]
        else:
            options = pools[rarity]
        return rng.choice(options)

    packs: list[Pack] = []
    per_slot_value = [0.0] * 7
    per_slot_hits = [0] * 7
    per_slot_rarity = [Counter() for _ in range(7)]
    god_packs = 0
    empty_slots = 0

    for _ in range(n_packs):
        god = god_chance > 0 and rng.random() < god_chance
        tables = god_tables if god else slot_tables
        drawn: list[DrawnCard | None] = []
        taken: set[str] = set()
        for i, table in enumerate(tables):
            card = draw(table, taken)
            if card is None:
                empty_slots += 1
                drawn.append(None)
                continue
            price = card_price(expansion, card.rarity, card.border, card.foil or god)
            entry = DrawnCard(card=card, price=price)
            taken.add(card.sprite)
            drawn.append(entry)
            per_slot_value[i] += price
            per_slot_rarity[i][card.rarity] += 1
            if price > hit_threshold:
                per_slot_hits[i] += 1
        if god:
            god_packs += 1
        packs.append(Pack(cards=drawn, god=god))

    return SimResult(
        packs=packs,
        seed=seed,
        god_packs=god_packs,
        empty_slots=empty_slots,
        per_slot_value=per_slot_value,
        per_slot_hits=per_slot_hits,
        per_slot_rarity=per_slot_rarity,
    )


# --- the statistics ---------------------------------------------------------


def _quantile(sorted_values: list[float], q: float) -> float:
    """The q-quantile (inclusive linear interpolation) of *sorted_values*."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    fraction = position - low
    return sorted_values[low] * (1 - fraction) + sorted_values[high] * fraction


def _pool_means(pools: dict[str, list[Card]]) -> dict[str, float]:
    """The average price of each rarity's pool (what a draw of that
    rarity is worth on average)."""
    return {
        rarity: sum(card.price for card in cards) / len(cards)
        for rarity, cards in pools.items()
    }


def _god_pool_means(
    expansion: dict, pools: dict[str, list[Card]]
) -> dict[str, float]:
    """The average price of each rarity's pool when every card is foil
    (the god pack's price in place)."""
    return {
        rarity: sum(
            card_price(expansion, card.rarity, card.border, True) for card in cards
        )
        / len(cards)
        for rarity, cards in pools.items()
    }


def _slot_expected(
    table: dict | None, pools: dict[str, list[Card]], means: dict[str, float]
) -> float:
    """The expected value of one draw from *table* (the rarity's
    probability times the pool's average price, summed over the
    rarities)."""
    return sum(
        probability * means[rarity]
        for rarity, probability in _slot_probabilities(table, pools).items()
    )


def _theoretical_ev_per_pack(
    expansion: dict, pack: dict, pools: dict[str, list[Card]]
) -> float:
    """The expected value of one pack straight from the weights: for each
    slot, the rarity's probability times the pool's average price (the
    god blend in place — the foil price for a god pack's cards)."""
    slot_tables = _slot_tables(pack)
    god_tables = _god_tables(pack, slot_tables)
    god_chance = _god_percentage(pack)
    normal = _pool_means(pools)
    foil = _god_pool_means(expansion, pools)
    return sum(
        _slot_expected(table, pools, normal) * (1.0 - god_chance)
        + _slot_expected(god, pools, foil) * god_chance
        for table, god in zip(slot_tables, god_tables)
    )


def _expected_per_rarity(
    expansion: dict, pack: dict, pools: dict[str, list[Card]], n_packs: int
) -> dict[str, float]:
    """The expected number of cards of each rarity over *n_packs* packs:
    for each slot, the rarity's probability in the slot's table (the god
    blend in place), times the number of packs."""
    slot_tables = _slot_tables(pack)
    god_tables = _god_tables(pack, slot_tables)
    god_chance = _god_percentage(pack)

    per_rarity: dict[str, float] = {}
    for table, god in zip(slot_tables, god_tables):
        for rarity, probability in _slot_probabilities(table, pools).items():
            per_rarity[rarity] = per_rarity.get(rarity, 0.0) + probability * (
                1.0 - god_chance
            )
        for rarity, probability in _slot_probabilities(god, pools).items():
            per_rarity[rarity] = per_rarity.get(rarity, 0.0) + probability * god_chance

    return {rarity: count * n_packs for rarity, count in per_rarity.items()}


def _probability_pack_contains(
    expansion: dict, pack: dict, pools: dict[str, list[Card]], predicate
) -> float:
    """The probability one pack contains a card matching *predicate*
    (a card): 1 minus the product over the slots of the slot not drawing
    such a card (the god blend in place — a god pack's cards are all
    foil, so the predicate is applied to the foil price for them)."""
    slot_tables = _slot_tables(pack)
    god_tables = _god_tables(pack, slot_tables)
    god_chance = _god_percentage(pack)

    fraction = {
        rarity: sum(1 for card in cards if predicate(card)) / len(cards)
        for rarity, cards in pools.items()
    }
    god_fraction = {
        rarity: (
            sum(
                1
                for card in cards
                if predicate(_god_twin(expansion, card))
            )
            / len(cards)
        )
        for rarity, cards in pools.items()
    }

    no_hit = 1.0
    for table, god in zip(slot_tables, god_tables):
        normal = _slot_probabilities(table, pools)
        god_prob = _slot_probabilities(god, pools)
        per_pack = (
            sum(probability * fraction[r] for r, probability in normal.items())
            * (1.0 - god_chance)
            + sum(probability * god_fraction[r] for r, probability in god_prob.items())
            * god_chance
        )
        no_hit *= 1.0 - per_pack
    return 1.0 - no_hit


def _god_twin(expansion: dict, card: Card) -> Card:
    """*card* priced as a god pack prices it: the foil price in place."""
    return Card(
        name=card.name,
        rarity=card.rarity,
        border=card.border,
        foil=True,
        price=card_price(expansion, card.rarity, card.border, True),
        sprite=card.sprite,
    )


def _hit_indices(packs: list[Pack], threshold: float) -> list[int]:
    """The 1-based indices of the packs holding a card worth more than
    *threshold*."""
    return [
        i
        for i, pack in enumerate(packs, start=1)
        if any(
            drawn is not None and drawn.price > threshold for drawn in pack.cards
        )
    ]


def compute_statistics(
    expansion: dict,
    pack: dict,
    cards: list[Card],
    result: SimResult,
    hit_threshold: float = DEFAULT_HIT_THRESHOLD,
) -> dict:
    """The report's statistics from one simulation run: the per-rarity
    rows (observed and expected counts, the pool's average and top price,
    the value share, the packs until first obtained), the per-slot rows
    (observed and expected value per pack, the hits, the top rarity),
    the pack value distribution, the hit tables (the *hit_threshold*
    alongside the :data:`HIT_THRESHOLDS` references) and the top cards."""
    pools = _pools_by_rarity(cards)
    n_packs = len(result.packs)
    values = [pack.value for pack in result.packs]
    sorted_values = sorted(values)
    total_value = sum(values)
    total_cards = sum(
        sum(counter.values()) for counter in result.per_slot_rarity
    )

    rarity_counts: Counter[str] = Counter()
    rarity_value: dict[str, float] = {}
    rarity_first_pack: dict[str, int] = {}
    for i, opened in enumerate(result.packs, start=1):
        for drawn in opened.cards:
            if drawn is None:
                continue
            rarity_counts[drawn.card.rarity] += 1
            rarity_value[drawn.card.rarity] = (
                rarity_value.get(drawn.card.rarity, 0.0) + drawn.price
            )
            rarity_first_pack.setdefault(drawn.card.rarity, i)

    expected = _expected_per_rarity(expansion, pack, pools, n_packs)

    rarity_rows = []
    for rarity in expansion["Rarities"]:
        if rarity not in pools:
            continue
        cards_of_rarity = pools[rarity]
        count = rarity_counts.get(rarity, 0)
        first = rarity_first_pack.get(rarity)
        rarity_rows.append(
            {
                "rarity": rarity,
                "pool": len(cards_of_rarity),
                "count": count,
                "expected": expected.get(rarity, 0.0),
                "observed_share": count / total_cards if total_cards else 0.0,
                "bottom_price": min(c.price for c in cards_of_rarity),
                "average_price": sum(c.price for c in cards_of_rarity)
                / len(cards_of_rarity),
                "max_price": max(c.price for c in cards_of_rarity),
                "total_value": rarity_value.get(rarity, 0.0),
                "value_share": (
                    rarity_value.get(rarity, 0.0) / total_value if total_value else 0.0
                ),
                "first_pack": first,
                "expected_first_pack": _expected_first_pack(expansion, pack, pools, rarity),
            }
        )

    slot_tables = _slot_tables(pack)
    slot_rows = []
    for i, table in enumerate(slot_tables):
        probabilities = _slot_probabilities(table, pools)
        top_rarity, top_probability = (
            max(probabilities.items(), key=lambda item: item[1])
            if probabilities
            else (None, 0.0)
        )
        slot_rows.append(
            {
                "slot": i + 1,
                "observed_value": result.per_slot_value[i] / n_packs,
                "expected_value": _slot_expected(table, pools, _pool_means(pools)),
                "hits": result.per_slot_hits[i],
                "top_rarity": top_rarity,
                "top_probability": top_probability,
            }
        )

    threshold_rows = []
    for threshold in sorted({hit_threshold, *HIT_THRESHOLDS}):
        indices = _hit_indices(result.packs, threshold)
        probability = _probability_pack_contains(
            expansion, pack, pools, lambda card, t=threshold: card.price > t
        )
        gaps = [b - a for a, b in zip(indices, indices[1:])]
        threshold_rows.append(
            {
                "threshold": threshold,
                "probability": probability,
                "expected_packs": None if probability <= 0 else 1.0 / probability,
                "count": len(indices),
                "first": indices[0] if indices else None,
                "mean_gap": statistics.fmean(gaps) if len(gaps) > 1 else None,
            }
        )

    top_cards = []
    for card in sorted(cards, key=lambda c: c.price, reverse=True)[:10]:
        per_pack = expected.get(card.rarity, 0.0) / n_packs / len(pools[card.rarity])
        top_cards.append(
            {
                "name": card.name,
                "rarity": card.rarity,
                "border": card.border,
                "foil": card.foil,
                "price": card.price,
                "expected_packs": None if per_pack <= 0 else 1.0 / per_pack,
            }
        )

    histogram = []
    bounds = [0.0] + list(HIST_BUCKETS) + [math.inf]
    for low, high in zip(bounds[:-1], bounds[1:]):
        count = sum(1 for value in values if low <= value < high)
        histogram.append(
            {
                "low": low,
                "high": high,
                "count": count,
                "share": count / n_packs if n_packs else 0.0,
            }
        )

    hit_indices = _hit_indices(result.packs, hit_threshold)
    hit_gaps = [b - a for a, b in zip(hit_indices, hit_indices[1:])]
    hit_probability = _probability_pack_contains(
        expansion, pack, pools, lambda card: card.price > hit_threshold
    )

    return {
        "n_packs": n_packs,
        "total_cards": total_cards,
        "total_value": total_value,
        "simulated_ev": statistics.fmean(values) if values else 0.0,
        "theoretical_ev": _theoretical_ev_per_pack(expansion, pack, pools),
        "median": statistics.median(sorted_values) if sorted_values else 0.0,
        "minimum": sorted_values[0] if sorted_values else 0.0,
        "maximum": sorted_values[-1] if sorted_values else 0.0,
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "quantiles": {
            label: _quantile(sorted_values, q)
            for label, q in (
                ("p25", 0.25),
                ("p75", 0.75),
                ("p90", 0.90),
                ("p95", 0.95),
                ("p99", 0.99),
            )
        },
        "hit_count": len(hit_indices),
        "hit_share": len(hit_indices) / n_packs if n_packs else 0.0,
        "hit_first": hit_indices[0] if hit_indices else None,
        "hit_mean_gap": statistics.fmean(hit_gaps) if len(hit_gaps) > 1 else None,
        "hit_probability": hit_probability,
        "hit_expected_packs": (
            1.0 / hit_probability if hit_probability > 0 else None
        ),
        "rarity_rows": rarity_rows,
        "slot_rows": slot_rows,
        "threshold_rows": threshold_rows,
        "top_cards": top_cards,
        "histogram": histogram,
        "god_packs": result.god_packs,
        "empty_slots": result.empty_slots,
    }


def _expected_first_pack(
    expansion: dict, pack: dict, pools: dict[str, list[Card]], rarity: str
) -> float | None:
    """The expected number of packs until *rarity* is obtained at least
    once: 1 / the probability the rarity appears in a pack. ``None`` when
    the rarity cannot be obtained (no positive weight leads to it)."""
    probability = _probability_pack_contains(
        expansion, pack, pools, lambda card: card.rarity == rarity
    )
    return None if probability <= 0 else 1.0 / probability


# --- the report -------------------------------------------------------------


def _money(value: float) -> str:
    if value >= 10000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _pct(probability: float) -> str:
    if probability <= 0:
        return "0%"
    percent = probability * 100
    if percent < 0.1:
        return f"{percent:.3f}%"
    if percent < 1:
        return f"{percent:.2f}%"
    return f"{percent:.1f}%"


def _packs(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 1000:
        return f"{value:,.1f}"
    return f"{value:,.0f}"


def _bar(label: str, count: int, share: float, maximum: float) -> str:
    width = max(0.5, share / maximum * 100) if maximum > 0 else 0.5
    return (
        f'<div class="bar-row"><div class="bar-label">{html.escape(label)}</div>'
        f'<div class="bar-track"><div class="bar" style="width: {width:.1f}%"></div></div>'
        f'<div class="bar-count">{count:,} ({_pct(share)})</div></div>'
    )


_STYLE = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #0e1116; color: #dde2ea; font: 15px/1.5 system-ui, "Segoe UI", sans-serif; }
.container { max-width: 1100px; margin: 0 auto; padding: 28px 24px 72px; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: .02em; }
h2 { font-size: 15px; margin: 34px 0 10px; text-transform: uppercase; letter-spacing: .08em; color: #9aa4b8; border-bottom: 1px solid #232a37; padding-bottom: 8px; }
.meta { color: #8b93a7; font-size: 13px; }
.meta code, .formula { background: #1a2130; padding: 1px 6px; border-radius: 4px; color: #c3cbdb; }
.formula { display: block; background: #151a23; border: 1px solid #232a37; border-radius: 10px; padding: 12px 14px; font-family: ui-monospace, Consolas, monospace; font-size: 13px; color: #c3cbdb; overflow-x: auto; margin-top: 12px; white-space: pre; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; margin-top: 16px; }
.stat { background: #151a23; border: 1px solid #232a37; border-radius: 10px; padding: 12px 14px; }
.stat .label { font-size: 11.5px; color: #8b93a7; text-transform: uppercase; letter-spacing: .06em; }
.stat .value { font-size: 21px; font-weight: 650; margin-top: 4px; font-variant-numeric: tabular-nums; }
.stat .sub { font-size: 12px; color: #8b93a7; margin-top: 2px; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
th { text-align: right; color: #9aa4b8; font-weight: 600; padding: 6px 10px; border-bottom: 2px solid #2a3242; white-space: nowrap; }
td { padding: 6px 10px; border-bottom: 1px solid #1d2431; text-align: right; white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
tr:hover td { background: #141a24; }
td.name { font-weight: 600; }
.note { font-size: 12.5px; color: #8b93a7; margin-top: 8px; }
.bar-row { display: flex; align-items: center; gap: 10px; margin: 5px 0; }
.bar-label { width: 140px; text-align: right; font-size: 12.5px; color: #9aa4b8; font-variant-numeric: tabular-nums; }
.bar-track { flex: 1; background: #1a2130; border-radius: 4px; height: 16px; overflow: hidden; }
.bar { height: 100%; background: linear-gradient(90deg, #4f8cff, #8b5cf6); border-radius: 4px 0 0 4px; }
.bar-count { width: 150px; font-size: 12.5px; color: #c3cbdb; font-variant-numeric: tabular-nums; }
footer { margin-top: 40px; padding-top: 14px; border-top: 1px solid #232a37; color: #8b93a7; font-size: 12.5px; }
footer p { margin: 4px 0; }
"""


def render_report(
    name: str,
    expansion: dict,
    pack: dict,
    result: SimResult,
    stats: dict,
    hit_threshold: float = DEFAULT_HIT_THRESHOLD,
) -> str:
    """The self-contained HTML report (no external assets, no scripts)."""
    e = html.escape
    n = stats["n_packs"]
    q = stats["quantiles"]

    price_min = pack["BaseCost"] * pack["MinMarketPricePercent"]
    price_max = pack["BaseCost"] * pack["MaxMarketPricePercent"]
    ev_delta = (
        (stats["simulated_ev"] - stats["theoretical_ev"])
        / stats["theoretical_ev"]
        * 100
        if stats["theoretical_ev"]
        else 0.0
    )

    formula = (
        "price(rarity, border, foil) =\n"
        f"  ({expansion['RarityDrivenFloor']:.2f} + "
        f"{expansion['RarityDrivenStepSize']:.2f} x rarity index in {expansion['Rarities']})\n"
        f"  x {expansion['RarityDrivenBorderMultiplierBase']:.2f} ^ border index "
        f"[{' , '.join(f'{b}={i}' for i, b in enumerate(BORDERS))}]\n"
        f"  x {expansion['RarityDrivenFoilMultiplier']:.2f}   (when the card is foil)"
    )

    summary = f"""
    <div class="cards">
      <div class="stat"><div class="label">Expected value per pack</div>
        <div class="value">{_money(stats['simulated_ev'])}</div>
        <div class="sub">theoretical {_money(stats['theoretical_ev'])} ({ev_delta:+.1f}%)</div></div>
      <div class="stat"><div class="label">Median pack value</div>
        <div class="value">{_money(stats['median'])}</div>
        <div class="sub">of {n:,} packs</div></div>
      <div class="stat"><div class="label">Pack market price</div>
        <div class="value">{_money(price_min)} – {_money(price_max)}</div>
        <div class="sub">BaseCost {pack['BaseCost']:g} x [{pack['MinMarketPricePercent']:g}, {pack['MaxMarketPricePercent']:g}]</div></div>
      <div class="stat"><div class="label">Pack license price</div>
        <div class="value">{_money(pack['LicensePrice'])}</div>
        <div class="sub">one-time unlock</div></div>
      <div class="stat"><div class="label">Hits over {_money(hit_threshold)}</div>
        <div class="value">{stats['hit_count']:,} / {n:,}</div>
        <div class="sub">{_pct(stats['hit_share'])} of the packs</div></div>
      <div class="stat"><div class="label">Packs until first hit</div>
        <div class="value">{stats['hit_first'] if stats['hit_first'] is not None else '—'}</div>
        <div class="sub">expected {_packs(stats['hit_expected_packs'])}</div></div>
      <div class="stat"><div class="label">Average packs per hit</div>
        <div class="value">{_packs(stats['hit_mean_gap'])}</div>
        <div class="sub">expected {_packs(stats['hit_expected_packs'])}</div></div>
      <div class="stat"><div class="label">Total value</div>
        <div class="value">{_money(stats['total_value'])}</div>
        <div class="sub">{stats['total_cards']:,} cards over {n:,} packs</div></div>
    </div>"""

    rarity_rows = "".join(
        f"""<tr>
          <td class="name">{e(row['rarity'])}</td>
          <td>{row['pool']}</td>
          <td>{row['count']:,}</td>
          <td>{row['expected']:,.1f}</td>
          <td>{_pct(row['observed_share'])}</td>
          <td>{_money(row['bottom_price'])}</td>
          <td>{_money(row['average_price'])}</td>
          <td>{_money(row['max_price'])}</td>
          <td>{_money(row['total_value'])}</td>
          <td>{_pct(row['value_share'])}</td>
          <td>{row['first_pack'] if row['first_pack'] is not None else '—'}</td>
          <td>{_packs(row['expected_first_pack'])}</td>
        </tr>"""
        for row in stats["rarity_rows"]
    )

    slot_rows = "".join(
        f"""<tr>
          <td>Slot {row['slot']}</td>
          <td>{_money(row['observed_value'])}</td>
          <td>{_money(row['expected_value'])}</td>
          <td>{row['hits']:,}</td>
          <td class="name">{e(row['top_rarity'] or '—')} ({_pct(row['top_probability'])})</td>
        </tr>"""
        for row in stats["slot_rows"]
    )

    threshold_rows = "".join(
        f"""<tr>
          <td>{_money(row['threshold'])}</td>
          <td>{_pct(row['probability'])}</td>
          <td>{_packs(row['expected_packs'])}</td>
          <td>{row['count']:,} / {n:,}</td>
          <td>{row['first'] if row['first'] is not None else '—'}</td>
          <td>{_packs(row['mean_gap'])}</td>
        </tr>"""
        for row in stats["threshold_rows"]
    )

    top_rows = "".join(
        f"""<tr>
          <td class="name">{e(row['name'])}</td>
          <td>{e(row['rarity'])}</td>
          <td>{e(row['border'])}</td>
          <td>{'yes' if row['foil'] else 'no'}</td>
          <td>{_money(row['price'])}</td>
          <td>{_packs(row['expected_packs'])}</td>
        </tr>"""
        for row in stats["top_cards"]
    )

    histogram_rows = "".join(
        _bar(
            (
                f"< ${row['high']:,.0f}"
                if row["low"] == 0
                else f"${row['low']:,.0f} – "
                + (f"${row['high']:,.0f}" if row["high"] != math.inf else "∞")
            ),
            row["count"],
            row["share"],
            max(r["share"] for r in stats["histogram"]),
        )
        for row in stats["histogram"]
    )

    chips = "".join(
        f"""<div class="stat"><div class="label">{label}</div>
        <div class="value">{_money(value)}</div></div>"""
        for label, value in (
            ("min", stats["minimum"]),
            ("p25", q["p25"]),
            ("median", stats["median"]),
            ("mean", stats["simulated_ev"]),
            ("p75", q["p75"]),
            ("p90", q["p90"]),
            ("p95", q["p95"]),
            ("p99", q["p99"]),
            ("max", stats["maximum"]),
            ("stdev", stats["stdev"]),
        )
    )

    god_note = (
        f"{result.god_packs:,} god pack(s) occurred (all their cards foil)"
        if result.god_packs
        else (
            "god packs are enabled, none occurred"
            if _god_percentage(pack) > 0
            else "god packs are disabled"
        )
    )
    duplicate_note = (
        "no card is repeated within a pack"
        if not pack.get("CanHaveDuplicates", False)
        else "cards may repeat within a pack"
    )
    empty_note = (
        f" {stats['empty_slots']:,} slot(s) could not yield a card."
        if stats["empty_slots"]
        else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pack simulation — {e(name)}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="container">
  <h1>Pack simulation — {e(name)}</h1>
  <div class="meta">
    {n:,} packs of <code>{e(pack['Name'])}</code> &middot; seed {result.seed}
    &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot;
    built from <code>cards/{e(name)}</code> + <code>database/characters.json</code>
    through the current <code>metadata.py</code> tuning
  </div>

  <h2>Price model</h2>
  <div class="meta">
    <code>{e(expansion['CardPriceStrategy'])}</code> strategy,
    {len(expansion['Cards']):,} cards in the pool
  </div>
  <code class="formula">{e(formula)}</code>

  <h2>Summary</h2>
  {summary}

  <h2>Cards per rarity</h2>
  <table>
    <tr><th>Rarity</th><th>Pool</th><th>Obtained</th><th>Expected</th>
        <th>Obs. share</th><th>Bottom price</th><th>Avg price</th>
        <th>Top price</th>
        <th>Total value</th><th>Value share</th><th>First pack</th>
        <th>Exp. packs to first</th></tr>
    {rarity_rows}
  </table>
  <div class="note">Obtained/expected over {n:,} packs ({7 * n:,} slot draws,
  {stats['total_cards']:,} cards). &ldquo;Bottom price&rdquo;/&ldquo;Avg
  price&rdquo;/&ldquo;Top price&rdquo; are the rarity's pool's cheapest,
  average and most expensive cards — what a draw of the rarity is worth at
  the low, average and high end. &ldquo;First pack&rdquo; is the first pack
  (of {n:,}) that produced the rarity; &ldquo;Exp. packs to first&rdquo; its
  expectation.</div>

  <h2>Per-slot value</h2>
  <table>
    <tr><th>Slot</th><th>Value per pack (sim)</th><th>EV per pack (theory)</th>
        <th>Hits &gt; {_money(hit_threshold)}</th><th>Top rarity (share)</th></tr>
    {slot_rows}
  </table>

  <h2>Pack value distribution</h2>
  <div class="cards">{chips}</div>
  {histogram_rows}

  <h2>Hits</h2>
  <table>
    <tr><th>Card worth more than</th><th>P(pack hits)</th><th>Exp. packs per hit</th>
        <th>Packs with hit</th><th>First hit at</th><th>Avg gap (obs)</th></tr>
    {threshold_rows}
  </table>
  <div class="note">A hit is a pack containing at least one card worth more than the
  threshold. &ldquo;Avg gap&rdquo; is the average distance between consecutive hit packs
  (the average packs per hit).</div>

  <h2>Top cards of the set</h2>
  <table>
    <tr><th>Card</th><th>Rarity</th><th>Border</th><th>Foil</th><th>Price</th>
        <th>Exp. packs to first</th></tr>
    {top_rows}
  </table>

  <footer>
    <p>Simulated with <code>simulate {e(name)}</code>
    ({n:,} packs, seed {result.seed}). {e(god_note)}; {duplicate_note}.{empty_note}</p>
    <p>Every card is priced with the expansion's
    <code>{e(expansion['CardPriceStrategy'])}</code> parameters. The theoretical values are
    derived straight from the pack's weight tables under the assumption that every slot
    draws from a fresh pool (duplicates allowed): they match the simulation when a pack
    rarely repeats a card. With a small pool the no-duplicate rule interacts with the
    slot tables — a slot whose table has no rarity left that can be drawn comes up empty
    (the empty-slot count above), and the remaining slots' tables are renormalized over
    the rarities still available, so the simulation can run above or below the
    theoretical values; there the simulation is the number to trust. A report always
    reflects the current <code>metadata.py</code> tuning — a stale
    <code>output/{e(name)}.json</code> is never consulted.</p>
  </footer>
</div>
</body>
</html>
"""


def simulate() -> None:
    """Simulate pack openings for the selected expansion and write the
    HTML report to ``output/<Expansion>.html``."""
    parser = argparse.ArgumentParser(
        prog="simulate",
        description=(
            "Simulate 1000 pack openings of an expansion and write an HTML "
            "report (output/<Expansion>.html) with the statistics for "
            "fine-tuning the pack odds and card prices: cards per rarity, "
            "average price per rarity, average packs per hit (a hit is a "
            "card worth more than the --hit threshold), expected value "
            "per pack, median value, and more."
        ),
    )
    parser.add_argument(
        "expansion",
        help="the expansion to simulate (a directory under cards/)",
    )
    parser.add_argument(
        "--packs",
        type=int,
        default=DEFAULT_PACKS,
        metavar="N",
        help=f"the number of packs to open (default: {DEFAULT_PACKS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="S",
        help="the RNG seed (default: random; the seed is reported in the HTML)",
    )
    parser.add_argument(
        "--hit",
        type=float,
        default=DEFAULT_HIT_THRESHOLD,
        metavar="T",
        help=(
            "the hit price threshold: a hit is a card worth more than this "
            f"(default: {DEFAULT_HIT_THRESHOLD:g})"
        ),
    )
    args = parser.parse_args()

    if args.packs < 1:
        parser.error("--packs must be at least 1")
    if args.hit <= 0:
        parser.error("--hit must be positive")

    name = args.expansion.removeprefix("cards/")
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1 << 31)

    try:
        expansion, pack = _load_expansion(name)
        cards = _pool(expansion)
        result = run_simulation(
            expansion, pack, cards, args.packs, seed, args.hit
        )
        stats = compute_statistics(expansion, pack, cards, result, args.hit)
        report = render_report(name, expansion, pack, result, stats, args.hit)

        nr.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = nr.OUTPUT_DIR / f"{name}.html"
        out_path.write_text(report, encoding="utf-8", newline="\n")

        print(
            f"simulated {args.packs:,} packs of {name} "
            f"(seed {seed}) -> {out_path.relative_to(nr.REPO_ROOT)}"
        )
        print(
            f"  expected value per pack: {_money(stats['simulated_ev'])} "
            f"(theoretical {_money(stats['theoretical_ev'])}); "
            f"median {_money(stats['median'])}"
        )
        first = (
            f"pack {stats['hit_first']}"
            if stats["hit_first"] is not None
            else "none"
        )
        gap = (
            f"{_packs(stats['hit_mean_gap'])} on average"
            if stats["hit_mean_gap"] is not None
            else "n/a (fewer than two hits)"
        )
        print(
            f"  hits over {_money(args.hit)}: {stats['hit_count']:,} of "
            f"{stats['n_packs']:,} packs; first at {first}; {gap} between hits"
        )
    except nr.GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
