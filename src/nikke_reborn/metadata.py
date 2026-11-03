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
    """Write each expansion's metadata bundle (``<out>/<set>.json``) and
    copy the set's shared assets (foilmask, cardback, box mesh, shop
    images) to ``<out>/<set>/``. An ultra run writes them to the
    ``<set> (Ultra)`` set folder and ``<set> (Ultra).json`` instead, so
    the ultra set folders are self-contained and parallel to the default
    ones; a draft run writes them to ``draft/`` instead of ``output/``
    (the preset's output root, :meth:`Preset.set_path`)."""
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
    """The card entries of *exp*'s metadata bundle: every character of the
    expansion, expanded into the presentations the pipeline renders (the
    expansion's ``rarities`` subset — the standard's, the profile's and
    the full-art's presentations, the goddess presentation dropped for
    the characters without the ``sc`` variant and the two special
    presentations dropped for the characters without a reel animation —
    see :func:`nikke_reborn.expansion.presentations_for`), each carrying
    the character's rarity (the base character's when the id is
    suffixed). Shared by :func:`write` (which writes each set's bundle to
    the output directory) and :mod:`nikke_reborn.simulation` (which
    simulates pack openings against the current tuning)."""
    cards = []
    for entry in exp.cards:
        info = expansion_mod.resolve_character(entry)
        for presentation in expansion_mod.presentations_for(exp, entry, info):
            cards.append(
                _card(
                    entry.name,
                    presentation.name,
                    entry.rarity,
                    f"{entry.stem}_{presentation.name}",
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
        "RarityDrivenFloor": 0.1,
        "RarityDrivenStepSize": 0.2,
        "RarityDrivenBorderMultiplierBase": 3.0,
        "RarityDrivenFoilMultiplier": 20.0,
        "PlayCardMaterials": [],  # TODO
    }


def pack(set, rarities) -> dict:
    """The set's pack entry: its slots' rarity weights — the fixed tuning
    projected on the set's *rarities* subset: the slots' tables carry only
    the rarities the set generates, the remaining weights renormalizing,
    so the set's pack rolls only its rarities."""

    allowed = frozenset(rarities)

    def slot(
        classic,
        special=0,
        idle=0,
        cover=0,
        aim=0,
        exotic=0,
        goddess=0,
        classified=0,
        standard_factor=20,
        profile_factor=4,
        full_art_factor=0,
    ) -> dict:
        special_standard = special * standard_factor
        exotic_standard = exotic * standard_factor / 18

        classic_profile = classic * profile_factor
        idle_profile = idle * profile_factor
        cover_profile = cover * profile_factor
        aim_profile = aim * profile_factor

        classic = classic * full_art_factor
        special = special * full_art_factor
        idle = idle * full_art_factor
        cover = cover * full_art_factor
        aim = aim * full_art_factor
        exotic = exotic * full_art_factor
        classified = classified * full_art_factor

        weights = {
            "ClassicStandard": 100
            - (classic + special + idle + cover + aim + exotic + goddess + classified)
            - (special_standard + exotic_standard)
            - (classic_profile + idle_profile + cover_profile + aim_profile),
            "ClassicProfile": classic_profile,
            "SpecialStandard": special_standard,
            "IdleProfile": idle_profile,
            "CoverProfile": cover_profile,
            "AimProfile": aim_profile,
            "Classic": classic,
            "Special": special,
            "Idle": idle,
            "Cover": cover,
            "Aim": aim,
            "ExoticStandard": exotic_standard,
            "Exotic": exotic,
            "Goddess": goddess,
            "Classified": classified,
        }
        # Only the rarities the set generates stay in the slot's table
        # (the remaining weights renormalize over the set's rarities).
        return {
            rarity: weight
            for rarity, weight in weights.items()
            if rarity in allowed
        }

    common = slot(classic=1, special=0.025)
    uncommon = slot(
        classic=2,
        special=0.05,
        aim=0.05,
        cover=0.05,
        full_art_factor=0.5,
    )

    rare = slot(
        classic=1,
        special=0.4,
        idle=0.5,
        aim=0.5,
        cover=0.5,
        exotic=0.5,
        goddess=0.2,
        classified=0.05,
        full_art_factor=1,
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
        "LicensePrice": 50,  # TODO
        "LicenseLevelRequirement": 1,  # TODO
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
        "ClassicStandard": 0,
        "SpecialStandard": 0,
        "ClassicProfile": 0,
        "IdleProfile": 2,
        "CoverProfile": 1,
        "AimProfile": 1,
        "Classic": 2,
        "Special": 2,
        "Idle": 2,
        "Cover": 2,
        "Aim": 2,
        "ExoticStandard": 2,
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

    # Half-up: round() would round the exact halves (SR at border 2, SSR
    # at border 4) to even instead of up.
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
            "ExoticStandard",
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
        "LicensePrice": 50,  # TODO
        "LicenseLevelRequirement": 1,  # TODO
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
        "AutoSetBoxPrice": True,
        "IsTallItem": False,
        "InBoxOffsetY": 0,
        "InBoxOffsetScale": 0,
        "ItemDeminsion": {"x": 2, "y": 4, "z": 1},
        "CollidorPosOffset": {"x": 0, "y": 0, "z": 0},
        "ColliderScale": {"x": 0.1, "y": 0.2, "z": 0.1},
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
