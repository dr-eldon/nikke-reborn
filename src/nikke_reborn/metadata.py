import json
import math

from nikke_reborn import expansion as expansion_mod
from nikke_reborn.config import (
    BOX_MESH,
    IMAGES_DIR,
    SHOP_DIR,
)
from nikke_reborn.file import copy
from nikke_reborn.preset import Preset

BUNDLE_NAME = "NIKKE_REBORN"


def write(preset: Preset = Preset.DEFAULT) -> None:
    """Write each expansion's metadata bundle (``<out>/<set>.json``)
    and copy the set's shared assets (foilmask, cardback, box mesh,
    shop images) to ``<out>/<set>/``. An ultra run writes them to the
    ``<set> (Ultra)`` set folder and ``<set> (Ultra).json`` instead, so
    the ultra set folders are self-contained and parallel to the
    default ones; a low run writes them to the ``<set> (Low)`` set
    folder and ``<set> (Low).json`` the same way; a draft run writes
    them to ``draft/`` instead of ``output/`` (the preset's output
    root, :meth:`Preset.set_path`)."""
    for exp in expansion_mod.find_expansions():
        out_set = preset.set_path(exp.name)

        copy(IMAGES_DIR / "Foilmask.png", out_set / "Foilmask.png")
        copy(IMAGES_DIR / "Cardback.png", out_set / "Cardback.png")
        copy(BOX_MESH, out_set / BOX_MESH.name)

        for file in SHOP_DIR.iterdir():
            if not file.is_file():
                continue

            copy(file, out_set / file.name)

        with (out_set.with_name(f"{out_set.name}.json")).open(
            "w", newline="\n", encoding="utf-8"
        ) as file:
            json.dump(
                bundle(
                    exp.name,
                    items=[pack(exp.name, exp.rarities), box(exp.name)],
                    expansions=[expansion(exp.name, cards(exp), exp.rarities)],
                ),
                file,
                indent=2,
            )


def cards(exp: expansion_mod.Expansion) -> list[dict]:
    """The card entries of *exp*'s metadata bundle: every character of
    the expansion, expanded into the presentations the pipeline renders
    (see :func:`nikke_reborn.expansion.presentations_for`), each
    carrying the character's rarity (the base character's when the id
    is suffixed). Shared by :func:`write` and
    :mod:`nikke_reborn.simulation`."""
    cards = []
    for entry in exp.cards:
        info = expansion_mod.resolve_character(entry)
        for presentation in expansion_mod.presentations_for(exp, entry, info):
            cards.append(
                _card(
                    entry.name,
                    presentation.name,
                    entry.rarity,
                    f"{entry.stem}_{presentation.rarity_index:02d}_{presentation.name}",
                )
            )
    return cards


def bundle(name, items=None, expansions=None) -> dict:
    return {
        "Name": f"{BUNDLE_NAME}_{name}",
        "BundleId": f"{BUNDLE_NAME}_{name}",
        "AutoCompressTextures": True,
        "MaxTextureSize": 2048,
        "TextureCompression": "BC7",
        "EnableMipMaps": False,
        "Assemblies": [],
        "Items": items or [],
        "CardExpansions": expansions or [],
        "CustomShops": [
            {
                "PhoneAppId": f"{BUNDLE_NAME}",
                "AppDisplayName": "NIKKE",
                "AppIcon": "Shop_Icon",
                "AppInnerBGImage": "Shop_IBG",
                "AppOuterBGImage": "Shop_OBG",
                "SiteLogo": "Shop_Logo",
                "SiteHeader": "Shop_Banner",
                "SiteBackground": "Shop_Wallpaper",
            }
        ],
    }


def expansion(set, cards, rarities) -> dict:
    """The set's metadata's expansion entry: its cards and its rarities
    (*rarities* — the subset the set's TOML declares, in the order the
    set carries them: the order the set's price ladder indexes, the
    simulation and the sprite sheet follow)."""
    return {
        "Name": f"{set} Set",
        "CardExpansion": f"{BUNDLE_NAME}_{set}",
        "Cards": cards,
        "MenuCategory": "NIKKE",
        "CardbackSprite": "Cardback",
        "FoilMask": "Foilmask",
        "Rarities": list(rarities),
        "HasRandomFoils": False,
        "FoilChance": 0,
        "CardPriceStrategy": "RarityDriven",
        "DefaultBorderMultiplierBase": 3.15,
        "DefaultFoilMultiplier": 10.0,
        "RarityDrivenFloor": 0.03,
        "RarityDrivenStepSize": 0.2,
        "RarityDrivenBorderMultiplierBase": 5.0,
        "RarityDrivenFoilMultiplier": 2.0,
        "PlayCardMaterials": [],  # TODO
    }


def pack(set, rarities) -> dict:
    """The set's pack entry: its slots' rarity weights — the fixed tuning
    projected on the set's *rarities* subset: the slots' tables carry only
    the rarities the set generates, the remaining weights renormalizing,
    so the set's pack rolls only its rarities."""

    allowed = frozenset(rarities)

    def slot(
        profile=0,
        rare=0,
        cover=0,
        aim=0,
        special=0,
        exotic=0,
        goddess=0,
        classified=0,
    ) -> dict:
        weights = {
            "Standard": 100
            - (profile + rare + cover + aim + special + exotic + goddess + classified),
            "Profile": profile,
            "Rare": rare,
            "Cover": cover,
            "Aim": aim,
            "Special": special,
            "Exotic": exotic,
            "Goddess": goddess,
            "Classified": classified,
        }

        return {
            rarity: weight for rarity, weight in weights.items() if rarity in allowed
        }

    common = slot(profile=2, rare=0.5)
    uncommon = slot(
        profile=6,
        rare=2,
        cover=1,
        aim=1,
        special=0.50,
        exotic=0.1,
    )

    rare = slot(
        rare=4,
        cover=3,
        aim=3,
        special=1.5,
        exotic=1,
        goddess=0.2,
        classified=0.1,
    )

    slot_weights = {
        "Slot1": common,
        "Slot2": common,
        "Slot3": common,
        "Slot4": common,
        "Slot5": uncommon,
        "Slot6": uncommon,
        "Slot7": rare,
    }

    return {
        "Name": f"{set} Packs",
        "CardExpansion": f"{BUNDLE_NAME}_{set}",
        "PackType": f"{BUNDLE_NAME}_{set}_CardPack",
        "ItemType": f"{BUNDLE_NAME}_{set}_CardPack_Item",
        "Material": "CardPack_Material",
        "SpriteName": "CardPack_Item",
        "BaseCost": 2,  # TODO
        "SlotWeights": slot_weights,
        "ItemCategory": "TCG",
        "AddItemAsAccessory": False,
        "AddItemAsFigurine": False,
        "AddItemAsBoardGame": False,
        "PhoneAppId": f"{BUNDLE_NAME}",
        "UsesBaseGameMesh": True,
        "MeshToUse": "BasicCardPack",
        "Mesh": "",
        "MaterialList": [],
        "IsBigBox": True,
        "BigBoxHideTillUnlocked": False,
        "LicensePrice": 300,  # TODO
        "LicenseLevelRequirement": 5,  # TODO
        "IgnoreDoubleImage": False,
        "HasSmallBox": True,
        "SmallBoxHideTillUnlocked": False,
        "SmallBoxLicensePrice": 50,  # TODO
        "SmallBoxLicenseLevelRequirement": 1,  # TODO
        "SmallBoxIgnoreDoubleImage": False,
        "IsBulkBox": False,
        "MinMarketPricePercent": 1,
        "MaxMarketPricePercent": 1.20000005,
        "FollowItemPrice": "None",
        "AutoSetBoxPrice": False,
        "IsTallItem": False,
        "InBoxOffsetY": 0,
        "InBoxOffsetScale": 0,
        "ItemDeminsion": {"x": 1, "y": 1, "z": 1},
        "CollidorPosOffset": {"x": 0, "y": 0, "z": 0},
        "ColliderScale": {"x": 1, "y": 1, "z": 1},
        "PriceAffectedBy": [],
        "IsCardPack": True,
        "IsCardBox": False,
        "MinValue": 0,
        "CanHaveDuplicates": False,
        "CanHaveGodPacks": False,
        "GodPackPercentage": 0.000199999995,
        "PackGenerationStrategy": "Guaranteed",
        "SpawnsPackType": "",
        "NormalWeights": {},
        "GodWeights": {},
    }


def _card(name, variant, rarity, sprite) -> dict:
    BORDERS = ["Base", "FirstEdition", "Silver", "Gold", "EX", "FullArt"]

    VARIANT_BORDER = {
        "Standard": 0,
        "Profile": 0,
        "Rare": 0,
        "Cover": 1,
        "Aim": 1,
        "Special": 2,
        "Exotic": 3,
        "Goddess": 4,
        "Classified": 5,
    }

    RARITY_BONUS = {
        "R": 0,
        "SR": 1,
        "SSR": 2,
    }

    border = VARIANT_BORDER[variant]
    bonus = RARITY_BONUS[rarity]

    # Half-up: round() would round the exact halves to even instead of
    # up.
    bonus = math.floor(bonus / border + 0.5) if border > 0 else bonus

    border = BORDERS[
        min(
            border + bonus,
            len(BORDERS) - 1,
        )
    ]

    return {
        "Name": name,
        "Rarity": variant,
        "BorderType": border,
        "Sprite": sprite,
        "IsFoil": variant
        in [
            "Special",
            "Exotic",
            "Goddess",
            "Classified",
        ],
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": "",
    }


def box(set) -> dict:
    return {
        "Name": f"{set} Box",
        "Material": "CardBox_Material",
        "SpriteName": "CardBox_Item",
        "ItemType": f"{BUNDLE_NAME}_{set}_CardBox_Item",
        "SpawnsPackType": f"{BUNDLE_NAME}_{set}_CardPack_Item",
        "ItemCategory": "TCG",
        "BaseCost": 0,
        "AddItemAsAccessory": False,
        "AddItemAsFigurine": False,
        "AddItemAsBoardGame": False,
        "PhoneAppId": f"{BUNDLE_NAME}",
        "UsesBaseGameMesh": False,
        "MeshToUse": "",
        "Mesh": "CardBox_Mesh",
        "MaterialList": [],
        "IsBigBox": True,
        "BigBoxHideTillUnlocked": False,
        "LicensePrice": 500,  # TODO
        "LicenseLevelRequirement": 8,  # TODO
        "IgnoreDoubleImage": False,
        "HasSmallBox": True,
        "SmallBoxHideTillUnlocked": False,
        "SmallBoxLicensePrice": 100,  # TODO
        "SmallBoxLicenseLevelRequirement": 3,  # TODO
        "SmallBoxIgnoreDoubleImage": False,
        "IsBulkBox": False,
        "MinMarketPricePercent": 1,
        "MaxMarketPricePercent": 1.20000005,
        "FollowItemPrice": "None",
        "AutoSetBoxPrice": True,
        "IsTallItem": False,
        "InBoxOffsetY": 0,
        "InBoxOffsetScale": -0.2,
        "ItemDeminsion": {"x": 2, "y": 4, "z": 1},
        "CollidorPosOffset": {"x": 0, "y": 0, "z": 0},
        "ColliderScale": {"x": 0.18, "y": 0.15, "z": 0.1},
        "PriceAffectedBy": [],
        "IsCardPack": False,
        "IsCardBox": True,
        "MinValue": 0,
        "CardExpansion": "",
        "CanHaveDuplicates": False,
        "CanHaveGodPacks": False,
        "GodPackPercentage": 0.0,
        "PackGenerationStrategy": "Guaranteed",
        "PackType": "",
        "NormalWeights": {},
        "GodWeights": {},
        "SlotWeights": {},
    }
