"""
🎮 Strinova Teammate Finder — Конфигурация
"""
import os

# VK Bot
VK_TOKEN = "vk1.a.dGIXHGyzpuRS9fH-U11lowExs6QYRREa0tiJ95yJeDt9FZdlTo3Zg9fwystxL4XhL_asBHqHupjfPDnIO7ufccoUJWy8IuCeJujMbwSA-DtIdYsnC5x0KDAvZYFtmjzyDSndX7EF4WCdDjvrRAfrXgxQ_7JOnuoX99YvuMHl7grZStGKlVeZHHxWYaiNbxD4gke-irJw2Y2Npe7awS0wjg"
VK_GROUP_ID = 236840294
VK_API_VERSION = "5.199"

# Database
DB_PATH = os.getenv("DB_PATH", "strinova_bot.db")

# Strinova config
MODES = [
    "Подрыв",
    "Арена команд",
    "Вспышка",
    "Конвой",
]

CHARACTERS = [
    "Мишель", "Бай Мо", "Канами", "Флавия", "Фуксия",
    "Рейичи", "Нобунага", "Одри", "Лоуин", "Мередит",
    "Иветт", "Маддалена", "Мин", "Леона", "Мара",
    "Тиё", "Сиэль", "Кокона", "Фрагранс", "Югири",
    "Галатея", "Эйка", "Селестия",
]

TIME_DAYS = ["Будни", "Выходные"]
TIME_PARTS = ["Утро", "День", "Вечер", "Ночь"]

# Admin IDs (VK user IDs)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
