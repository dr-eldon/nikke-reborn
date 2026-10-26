import math

RARITIES = [
    "ClassicProfile",
    "RareProfile",
    "SpecialProfile",
    "IdleProfile",
    "CoverProfile",
    "AimProfile",
    "ExoticProfile",
    "Classic",
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
        classic,
        rare,
        special=0,
        idle=0,
        cover=0,
        aim=0,
        exotic=0,
        goddess=0,
        classified=0,
        profile_factor=2,
    ) -> dict:
        return {
            "ClassicProfile": 100
            - classic
            - (rare + special + idle + exotic + cover + aim) * (profile_factor + 1)
            - goddess
            - classified,
            "RareProfile": rare * profile_factor,
            "SpecialProfile": special * profile_factor,
            "IdleProfile": idle * profile_factor,
            "CoverProfile": cover * profile_factor,
            "AimProfile": aim * profile_factor,
            "ExoticProfile": exotic * profile_factor,
            "Classic": classic,
            "Rare": rare,
            "Special": special,
            "Idle": idle,
            "Cover": cover,
            "Aim": aim,
            "Exotic": exotic,
            "Goddess": goddess,
            "Classified": classified,
        }

    common = slot(classic=1, rare=0.5)
    uncommon = slot(classic=4, rare=1, special=1.5, aim=0.01, cover=0.01)

    rare = slot(
        classic=8,
        rare=4,
        special=2,
        idle=1,
        aim=0.1,
        cover=0.1,
        exotic=0.5,
        goddess=0.15,
        classified=0.05,
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
        "ClassicProfile": 0,
        "RareProfile": 1,
        "SpecialProfile": 1,
        "IdleProfile": 2,
        "CoverProfile": 1,
        "AimProfile": 1,
        "ExoticProfile": 2,
        "Classic": 2,
        "Rare": 2,
        "Special": 2,
        "Idle": 2,
        "Cover": 2,
        "Aim": 2,
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
        "IsFoil": variant in ["ExoticProfile", "Exotic", "Goddess", "Classified"],
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": "",
    }


def box(set) -> dict:
    return {
        "Name": f"{set} Box",
        "Material": "CardBox_Material",
        "SpriteName": "CardBox_Icon",
        "ItemType": f"NIKKE_{set}_CardBox_Item",
        "SpawnsPackType": f"NIKKE_{set}_CardPack_Item",
        "ItemCategory": "TCG",
        "BaseCost": 0,
        "AddItemAsAccessory": False,
        "AddItemAsFigurine": False,
        "AddItemAsBoardGame": False,
        "PhoneAppId": "NIKKE",
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
        "ItemDeminsion": {"x": 1, "y": 1, "z": 1},
        "CollidorPosOffset": {"x": 0, "y": 0, "z": 0},
        "ColliderScale": {"x": 1, "y": 1, "z": 1},
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
