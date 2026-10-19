RARITIES = [
    "Standard",
    "Silver",
    "Gold",
    "FirstEdition",
    "EX",
    "FullArt",
    "FullArtAnimated",
]


def bundle(name, items=None, expansions=None) -> dict:
    return {
        "Name": f"NIKKE_{name}",
        "BundleId": f"NIKKE_{name}",
        "AutoCompressTextures": True,
        "MaxTextureSize": 2048,
        "TextureCompression": "BC7",
        "EnableMipMaps": False,
        "Assemblies": [],
        "Items": items or [],
        "CardExpansions": expansions or [],
        "CustomShops": [
            {
                "PhoneAppId": "NIKKE",
                "AppDisplayName": "NIKKE",
                "AppIcon": "Icon",
                "AppInnerBGImage": "IBG",
                "AppOuterBGImage": "OBG",
                "SiteLogo": "_ShopLogo",
                "SiteHeader": "_ShopBanner",
                "SiteBackground": "_ShopWallpaper",
            }
        ],
    }


def expansion(set, cards) -> dict:
    return {
        "Name": f"{set} Set",
        "CardExpansion": f"NIKKE_{set}",
        "Cards": cards,
        "MenuCategory": "NIKKE",
        "CardbackSprite": "_Cardback",
        "FoilMask": "_Foilmask",
        "Rarities": RARITIES,
        "HasRandomFoils": False,
        "FoilChance": 0,
        "CardPriceStrategy": "RarityDriven",
        "DefaultBorderMultiplierBase": 3.15,
        "DefaultFoilMultiplier": 10.0,
        "RarityDrivenFloor": 0.1,
        "RarityDrivenStepSize": 0.25,
        "RarityDrivenBorderMultiplierBase": 2.5,
        "RarityDrivenFoilMultiplier": 40.0,
        "PlayCardMaterials": [],  # TODO
    }


def pack(set) -> dict:
    def slot(
        silver, gold, first_edition, ex=0, full_art=0, full_art_animated=0
    ) -> dict:
        return {
            "Standard": 100
            - silver
            - gold
            - first_edition
            - ex
            - full_art
            - full_art_animated,
            "Silver": silver,
            "Gold": gold,
            "FirstEdition": first_edition,
            "EX": ex,
            "FullArt": full_art,
            "FullArtAnimated": full_art_animated,
        }

    common = slot(silver=10, gold=4, first_edition=1)
    uncommon = slot(silver=10, gold=4, first_edition=1, ex=0.5)
    rare = slot(
        silver=10, gold=4, first_edition=2, ex=1, full_art=0.5, full_art_animated=0.25
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
        "Name": f"{set.upper()} Packs",
        "CardExpansion": f"nikke_{set}",
        "PackType": f"NIKKE_{set}_CardPack",
        "ItemType": f"NIKKE_{set}_CardPack_Item",
        "Material": "CardPack_Material",
        "SpriteName": "CardPack_Item",
        "BaseCost": 2,  # TODO
        "SlotWeights": slot_weights,
        "ItemCategory": "TCG",
        "AddItemAsAccessory": False,
        "AddItemAsFigurine": False,
        "AddItemAsBoardGame": False,
        "PhoneAppId": "Nikke",
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


def card(name, variant, rarity, sprite) -> dict:
    BORDERS = ["Base", "FirstEdition", "Silver", "Gold", "EX", "FullArt"]

    VARIANT_BORDER = {
        "Standard": 0,
        "Silver": 0,
        "Gold": 0,
        "FirstEdition": 4,
        "EX": 3,
        "FullArt": 4,
        "FullArtAnimated": 5,
    }

    RARITY_BONUS = {
        "R": 0,
        "SR": 1,
        "SSR": 3,
    }

    border = VARIANT_BORDER[variant]
    bonus = RARITY_BONUS[rarity]

    bonus = (
        round(bonus / border)
        if border > 0
        else max(bonus - list(VARIANT_BORDER.keys()).index(variant), 0)
    )

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
        "IsFoil": variant == "EX" or "FullArt" in variant,
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": "",
    }
