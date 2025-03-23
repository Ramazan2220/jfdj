from instagrapi.mixins.challenge import ChallengeChoice
import logging
import time

logger = logging.getLogger(__name__)

class TelegramChallengeHandler:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.code = None
        self.is_waiting = False

    def reset(self):
        self.code = None
        self.is_waiting = False

    def handle_challenge(self, username, choice_type):
        """Обработчик запроса кода подтверждения"""
        if choice_type == ChallengeChoice.EMAIL:
            choice_name = "электронной почты"
        elif choice_type == ChallengeChoice.SMS:
            choice_name = "SMS"
        else:
            choice_name = "неизвестного источника"

        # Отправляем сообщение в Telegram
        message = (
            f"📱 Требуется подтверждение для аккаунта *{username}*\n\n"
            f"Instagram запрашивает код подтверждения, отправленный на {choice_name}.\n\n"
            f"Пожалуйста, введите код подтверждения (6 цифр):"
        )

        self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='Markdown'
        )

        # Устанавливаем флаг ожидания
        self.is_waiting = True

        # Ждем, пока код не будет введен (максимум 300 секунд = 5 минут)
        start_time = time.time()
        while self.is_waiting and time.time() - start_time < 300:
            if self.code:
                code = self.code
                self.reset()
                return code
            time.sleep(1)

        # Если код не был введен за отведенное время
        self.bot.send_message(
            chat_id=self.chat_id,
            text="⏱ Время ожидания кода истекло. Пожалуйста, попробуйте снова."
        )

        self.reset()
        return None

    def set_code(self, code):
        """Устанавливает код, введенный пользователем"""
        self.code = code
        self.is_waiting = False