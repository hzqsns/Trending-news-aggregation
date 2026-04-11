"""CS2 热门饰品种子清单 — 首次启动时插入 cs2_items 表。

维护一份精选的 200-500 个高流动性饰品，覆盖主流品类。
MVP 版本先给出每大类 ~10 条样本，共约 100 条，后续可扩充。
"""
from sqlalchemy import select

from app.database import async_session
from app.models.cs2_item import CS2Item

# 格式: (market_hash_name, display_name, category, subcategory, rarity)
SEED_ITEMS: list[tuple[str, str, str, str | None, str | None]] = [
    # ==================== 刀具 ====================
    ("★ Karambit | Doppler (Factory New)", "爪子刀 (多普勒) 崭新", "knife", "karambit", "covert"),
    ("★ Karambit | Fade (Factory New)", "爪子刀 (渐变) 崭新", "knife", "karambit", "covert"),
    ("★ Butterfly Knife | Fade (Factory New)", "蝴蝶刀 (渐变) 崭新", "knife", "butterfly", "covert"),
    ("★ Butterfly Knife | Doppler (Factory New)", "蝴蝶刀 (多普勒) 崭新", "knife", "butterfly", "covert"),
    ("★ M9 Bayonet | Fade (Factory New)", "M9 刺刀 (渐变) 崭新", "knife", "m9_bayonet", "covert"),
    ("★ M9 Bayonet | Doppler (Factory New)", "M9 刺刀 (多普勒) 崭新", "knife", "m9_bayonet", "covert"),
    ("★ Bayonet | Fade (Factory New)", "刺刀 (渐变) 崭新", "knife", "bayonet", "covert"),
    ("★ Bayonet | Doppler (Factory New)", "刺刀 (多普勒) 崭新", "knife", "bayonet", "covert"),
    ("★ Flip Knife | Fade (Factory New)", "折叠刀 (渐变) 崭新", "knife", "flip", "covert"),
    ("★ Huntsman Knife | Fade (Factory New)", "猎杀者刀 (渐变) 崭新", "knife", "huntsman", "covert"),
    ("★ Talon Knife | Fade (Factory New)", "爪刀 (渐变) 崭新", "knife", "talon", "covert"),
    ("★ Skeleton Knife | Fade (Factory New)", "骷髅刀 (渐变) 崭新", "knife", "skeleton", "covert"),

    # ==================== 手套 ====================
    ("★ Sport Gloves | Pandora's Box (Factory New)", "运动手套 (潘多拉之盒) 崭新", "gloves", "sport", "covert"),
    ("★ Sport Gloves | Vice (Factory New)", "运动手套 (迈阿密风云) 崭新", "gloves", "sport", "covert"),
    ("★ Specialist Gloves | Crimson Kimono (Factory New)", "专业手套 (深红和服) 崭新", "gloves", "specialist", "covert"),
    ("★ Specialist Gloves | Fade (Factory New)", "专业手套 (渐变) 崭新", "gloves", "specialist", "covert"),
    ("★ Driver Gloves | King Snake (Factory New)", "驾驶手套 (王蛇) 崭新", "gloves", "driver", "covert"),
    ("★ Hand Wraps | Cobalt Skulls (Factory New)", "手部缠绕 (钴蓝骷髅) 崭新", "gloves", "wraps", "covert"),
    ("★ Moto Gloves | Spearmint (Factory New)", "摩托手套 (绿薄荷) 崭新", "gloves", "moto", "covert"),
    ("★ Bloodhound Gloves | Charred (Factory New)", "血猎手套 (焦灼) 崭新", "gloves", "bloodhound", "covert"),

    # ==================== AK-47 ====================
    ("AK-47 | Wild Lotus (Factory New)", "AK-47 野荷 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Fire Serpent (Factory New)", "AK-47 火蛇 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Gold Arabesque (Factory New)", "AK-47 金蔓花饰 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Case Hardened (Factory New)", "AK-47 表面淬火 崭新", "rifle", "ak47", "classified"),
    ("AK-47 | Redline (Field-Tested)", "AK-47 红线 久经沙场", "rifle", "ak47", "classified"),
    ("AK-47 | Vulcan (Factory New)", "AK-47 火神 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Asiimov (Field-Tested)", "AK-47 阿西莫夫 久经沙场", "rifle", "ak47", "covert"),
    ("AK-47 | Neon Revolution (Factory New)", "AK-47 霓虹革命 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Bloodsport (Factory New)", "AK-47 血腥运动 崭新", "rifle", "ak47", "covert"),
    ("AK-47 | Aquamarine Revenge (Factory New)", "AK-47 海蓝宝石 崭新", "rifle", "ak47", "covert"),

    # ==================== AWP ====================
    ("AWP | Dragon Lore (Factory New)", "AWP 龙狙 崭新", "rifle", "awp", "covert"),
    ("AWP | Medusa (Factory New)", "AWP 美杜莎 崭新", "rifle", "awp", "covert"),
    ("AWP | Gungnir (Factory New)", "AWP 永恒之枪 崭新", "rifle", "awp", "covert"),
    ("AWP | The Prince (Factory New)", "AWP 王子 崭新", "rifle", "awp", "covert"),
    ("AWP | Fade (Factory New)", "AWP 渐变 崭新", "rifle", "awp", "covert"),
    ("AWP | Asiimov (Field-Tested)", "AWP 阿西莫夫 久经沙场", "rifle", "awp", "covert"),
    ("AWP | Hyper Beast (Factory New)", "AWP 异形 崭新", "rifle", "awp", "covert"),
    ("AWP | Neo-Noir (Factory New)", "AWP 新黑色 崭新", "rifle", "awp", "covert"),
    ("AWP | Wildfire (Factory New)", "AWP 野火 崭新", "rifle", "awp", "covert"),

    # ==================== M4A4 / M4A1-S ====================
    ("M4A4 | Howl (Factory New)", "M4A4 咆哮 崭新", "rifle", "m4a4", "contraband"),
    ("M4A4 | Poseidon (Factory New)", "M4A4 海神波塞冬 崭新", "rifle", "m4a4", "covert"),
    ("M4A4 | Asiimov (Field-Tested)", "M4A4 阿西莫夫 久经沙场", "rifle", "m4a4", "covert"),
    ("M4A4 | The Emperor (Factory New)", "M4A4 皇帝 崭新", "rifle", "m4a4", "covert"),
    ("M4A1-S | Hot Rod (Factory New)", "M4A1-S 热棒 崭新", "rifle", "m4a1s", "classified"),
    ("M4A1-S | Welcome to the Jungle (Factory New)", "M4A1-S 欢迎来到丛林 崭新", "rifle", "m4a1s", "covert"),
    ("M4A1-S | Hyper Beast (Factory New)", "M4A1-S 异形 崭新", "rifle", "m4a1s", "covert"),
    ("M4A1-S | Printstream (Factory New)", "M4A1-S 热力印花 崭新", "rifle", "m4a1s", "covert"),
    ("M4A1-S | Chantico's Fire (Factory New)", "M4A1-S 灼热之炎 崭新", "rifle", "m4a1s", "covert"),

    # ==================== 手枪 ====================
    ("Desert Eagle | Blaze (Factory New)", "沙漠之鹰 烈焰 崭新", "pistol", "deagle", "restricted"),
    ("Desert Eagle | Printstream (Factory New)", "沙漠之鹰 热力印花 崭新", "pistol", "deagle", "covert"),
    ("Desert Eagle | Code Red (Factory New)", "沙漠之鹰 红警 崭新", "pistol", "deagle", "covert"),
    ("Desert Eagle | Kumicho Dragon (Factory New)", "沙漠之鹰 组长之龙 崭新", "pistol", "deagle", "classified"),
    ("USP-S | Kill Confirmed (Factory New)", "USP 消音 击杀确认 崭新", "pistol", "usp_s", "covert"),
    ("USP-S | Printstream (Factory New)", "USP 消音 热力印花 崭新", "pistol", "usp_s", "covert"),
    ("USP-S | Orion (Factory New)", "USP 消音 猎户 崭新", "pistol", "usp_s", "classified"),
    ("Glock-18 | Fade (Factory New)", "格洛克 18 渐变 崭新", "pistol", "glock", "restricted"),
    ("P250 | Nuclear Threat (Factory New)", "P250 核威胁 崭新", "pistol", "p250", "classified"),

    # ==================== SMG ====================
    ("P90 | Death by Kitty (Factory New)", "P90 咖斯魔化", "smg", "p90", "covert"),
    ("P90 | Asiimov (Factory New)", "P90 阿西莫夫 崭新", "smg", "p90", "covert"),
    ("MAC-10 | Neon Rider (Factory New)", "MAC-10 霓虹骑士 崭新", "smg", "mac10", "covert"),
    ("UMP-45 | Primal Saber (Factory New)", "UMP-45 原始军刀 崭新", "smg", "ump45", "classified"),

    # ==================== 散弹枪 / 机枪 ====================
    ("Sawed-Off | The Kraken (Factory New)", "截短霰弹枪 海怪 崭新", "shotgun", "sawed_off", "covert"),
    ("Nova | Hyper Beast (Factory New)", "新星 异形 崭新", "shotgun", "nova", "covert"),
    ("M249 | Nebula Crusader (Factory New)", "M249 星云十字军 崭新", "mg", "m249", "classified"),

    # ==================== 贴纸 / 印花 ====================
    ("Sticker | Katowice 2014 iBUYPOWER (Holo)", "印花 2014 卡托维兹 iBP 全息", "sticker", None, "covert"),
    ("Sticker | Crown (Foil)", "印花 皇冠 箔面", "sticker", None, "covert"),

    # ==================== 箱子 ====================
    ("Operation Bravo Case", "勇气行动箱", "case", None, "classified"),
    ("Chroma Case", "色度箱", "case", None, "classified"),
    ("Gamma Case", "伽玛箱", "case", None, "classified"),
    ("Clutch Case", "决胜时刻箱", "case", None, "classified"),
    ("Shattered Web Case", "破碎之网箱", "case", None, "classified"),
    ("Prisma Case", "棱彩箱", "case", None, "classified"),
    ("Snakebite Case", "蛇噬箱", "case", None, "classified"),
    ("Dreams & Nightmares Case", "梦魇箱", "case", None, "classified"),
]


async def seed_initial_items() -> int:
    """首次启动时若 cs2_items 表为空，插入种子清单。返回插入条数。"""
    async with async_session() as session:
        existing = (
            await session.execute(select(CS2Item).limit(1))
        ).scalar_one_or_none()
        if existing:
            return 0  # 已有数据，跳过

        inserted = 0
        for mhn, display, cat, sub, rarity in SEED_ITEMS:
            item = CS2Item(
                market_hash_name=mhn,
                display_name=display,
                category=cat,
                subcategory=sub,
                rarity=rarity,
                is_tracked=True,
            )
            session.add(item)
            inserted += 1
        await session.commit()
        return inserted
