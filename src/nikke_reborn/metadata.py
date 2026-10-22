RARITIES = [
    "Common",
    "Uncommon",
    "Rare",
    "Special",
    "Idle",
    "Cover",
    "Aim",
    "Exotic",
    "Goddess",
    "Classified",
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
                "AppIcon": "Shop_Icon",
                "AppInnerBGImage": "Shop_IBG",
                "AppOuterBGImage": "Shop_OBG",
                "SiteLogo": "Shop_Logo",
                "SiteHeader": "Shop_Banner",
                "SiteBackground": "Shop_Wallpaper",
            }
        ],
    }


def expansion(set, cards) -> dict:
    return {
        "Name": f"{set} Set",
        "CardExpansion": f"NIKKE_{set}",
        "Cards": cards,
        "MenuCategory": "NIKKE",
        "CardbackSprite": "Cardback",
        "FoilMask": "Foilmask",
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
        uncommon, rare, special, idle, aim=0, cover=0, exotic=0, goddess=0, classified=0
    ) -> dict:
        return {
            "Common": 100
            - uncommon
            - rare
            - special
            - idle
            - exotic
            - goddess
            - classified,
            "Uncommon": uncommon,
            "Rare": rare,
            "Special": special,
            "Idle": idle,
            "Aim": aim,
            "Cover": cover,
            "Exotic": exotic,
            "Goddess": goddess,
            "Classified": classified,
        }

    common = slot(
        uncommon=8,
        rare=4,
        special=2,
        idle=1,
    )

    uncommon = slot(
        uncommon=16,
        rare=8,
        special=4,
        idle=2,
        exotic=0.5,
    )

    rare = slot(
        uncommon=25,
        rare=16,
        special=5,
        idle=2,
        aim=0.1,
        cover=0.1,
        exotic=1,
        goddess=0.5,
        classified=0.25,
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
        "CardExpansion": f"NIKKE_{set}",
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
        "PhoneAppId": "NIKKE",
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
        "Common": 0,
        "Uncommon": 0,
        "Rare": 0,
        "Special": 1,
        "Idle": 4,
        "Aim": 2,
        "Cover": 2,
        "Exotic": 3,
        "Goddess": 4,
        "Classified": 5,
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
        "IsFoil": variant in ["Exotic", "Goddess", "Classified"],
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": "",
    }
