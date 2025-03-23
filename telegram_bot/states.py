# Состояния для ConversationHandler
# Используются в handlers.py

# Состояния для добавления аккаунта
WAITING_USERNAME = 1
WAITING_PASSWORD = 2

# Состояния для настройки профиля
WAITING_ACCOUNT_SELECTION = 3
WAITING_BIO_OR_AVATAR = 4

# Состояния для публикации
WAITING_TASK_TYPE = 5
WAITING_MEDIA = 6
WAITING_CAPTION = 7

# Состояния для отложенной публикации
WAITING_SCHEDULE_TIME = 8

# Состояния для добавления прокси
WAITING_PROXY_INFO = 9