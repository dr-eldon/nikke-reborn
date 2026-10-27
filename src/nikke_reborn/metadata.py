import math

BUNDLE_NAME = "NIKKE_REBORN"

RARITIES = [
    "ClassicStandard",
    "ClassicProfile",
    "RareStandard",
    "SpecialStandard",
    "IdleProfile",
    "CoverProfile",
    "AimProfile",
    "Classic",
    "Rare",
    "Special",
    "Idle",
    "Cover",
    "Aim",
    "ExoticStandard",
    "Exotic",
    "Goddess",
    "Classified",
]


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


def expansion(set, cards) -> dict:
    return {
        "Name": f"{set} Set",
        "CardExpansion": f"{BUNDLE_NAME}_{set}",
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
        "RarityDrivenStepSize": 2.0,
        "RarityDrivenBorderMultiplierBase": 2.5,
        "RarityDrivenFoilMultiplier": 5.0,
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
        standard_factor=4,
        profile_factor=2,
        full_art_factor=0,
    ) -> dict:
        rare_standard = rare * standard_factor
        special_standard = special * standard_factor
        exotic_standard = exotic * standard_factor / 2

        classic_profile = classic * profile_factor
        idle_profile = idle * profile_factor
        cover_profile = cover * profile_factor
        aim_profile = aim * profile_factor

        classic = classic * full_art_factor
        rare = rare * full_art_factor
        special = special * full_art_factor
        idle = idle * full_art_factor
        cover = cover * full_art_factor
        aim = aim * full_art_factor
        exotic = exotic * full_art_factor
        classified = classified * full_art_factor

        return {
            "ClassicStandard": 100
            - (
                classic
                + rare
                + special
                + idle
                + cover
                + aim
                + exotic
                + goddess
                + classified
            )
            - (rare_standard + special_standard + exotic_standard)
            - (classic_profile + idle_profile + cover_profile + aim_profile),
            "ClassicProfile": classic_profile,
            "RareStandard": rare_standard,
            "SpecialStandard": special_standard,
            "IdleProfile": idle_profile,
            "CoverProfile": cover_profile,
            "AimProfile": aim_profile,
            "Classic": classic,
            "Rare": rare,
            "Special": special,
            "Idle": idle,
            "Cover": cover,
            "Aim": aim,
            "ExoticStandard": exotic_standard,
            "Exotic": exotic,
            "Goddess": goddess,
            "Classified": classified,
        }

    common = slot(classic=1, rare=0.5)
    uncommon = slot(
        classic=1,
        rare=0.2,
        special=1.5,
        aim=0.01,
        cover=0.01,
        full_art_factor=0.5,
    )

    rare = slot(
        classic=1,
        rare=0.5,
        special=0.3,
        idle=0.2,
        aim=0.1,
        cover=0.1,
        exotic=0.2,
        goddess=0.15,
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


def card(name, variant, rarity, sprite) -> dict:
    BORDERS = ["Base", "FirstEdition", "Silver", "Gold", "EX", "FullArt"]

    VARIANT_BORDER = {
        "ClassicStandard": 0,
        "RareStandard": 1,
        "SpecialStandard": 1,
        "ExoticStandard": 2,
        "ClassicProfile": 1,
        "IdleProfile": 2,
        "CoverProfile": 1,
        "AimProfile": 1,
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
        "IsFoil": variant in ["ExoticStandard", "Exotic", "Goddess", "Classified"],
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
