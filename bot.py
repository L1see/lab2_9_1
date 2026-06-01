import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import json

#Выполнил: студент ОмГТУ группы ИВТ-254 Конарев И.

VK_TOKEN = 'Стреляй_не_отдам'
GROUP_ID = 239219036
DATA_FILE = 'farmakopeika_products.json'

PARSER_CONFIG = {
    'base_url': "https://farmakopeika.ru/catalog/2440",
    'start_page': 1,
    'end_page': 609,
    'delay': 0.5,
    'timeout': 30
}

class FarmakopeikaBot:
    def __init__(self, token, group_id, data_file):
        self.vk = vk_api.VkApi(token=token)
        self.longpoll = VkLongPoll(self.vk)
        self.group_id = group_id
        self.data_file = data_file
        self.products = self._load_products()

    def _load_products(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Файл {self.data_file} не найден. Запустите main.py для создания базы.")
            return []

    def _save_products(self, products):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

    def _search_product(self, query):
        query_lower = query.lower().strip()
        if len(query_lower) < 2:
            return None

        for product in self.products:
            if query_lower in product['name'].lower():
                return product
        return None

    def _format_price(self, price_str):
        try:
            price_float = float(price_str)
            return f"{price_float:,.2f}".replace(',', ' ').replace('.', ',') + ' ₽'
        except ValueError:
            return f"{price_str} ₽"

    def _format_response(self, product, query):
        if not product:
            return (
                f"  Товар «{query}» не найден.\n\n"
                f"  Попробуйте:\n"
                f"- Проверить название (например: «куркумин», «цинк», «омега»)\n"
                f"- Ввести часть названия бренда или препарата"
            )

        return (
            f"Найдено:\n"
            f"{product['name']}\n"
            f"Цена: от {self._format_price(product['price'])}\n\n"
            f"Заказать: https://farmakopeika.ru/catalog/2440"
        )

    def _send_message(self, user_id, text):
        self.vk.method('messages.send', {
            'peer_id': user_id,
            'message': text,
            'random_id': get_random_id()
        })

    def run(self):
        print(f"Бот запущен.")

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_message = event.text.strip()
                user_id = event.user_id

                # Справка
                if user_message.lower() in ['/start', '/help', 'привет']:
                    self._send_message(
                        user_id,
                        "Привет! Я бот парсер лекарств с сайта «Фармакопейка» г.Омск.\n"
                        "Напишите название товара, чтобы узнать цену.\n"
                        "Команды: /help для помощи, /refresh (админ) для обновления БД [отключено]\n"
                        "Выполнил: Студент ИВТ-254 ОмГТУ К.И."
                    )
                    continue

                # Поиск
                result = self._search_product(user_message)
                response = self._format_response(result, user_message)
                self._send_message(user_id, response)


if __name__ == "__main__":
    bot = FarmakopeikaBot(
        token=VK_TOKEN,
        group_id=GROUP_ID,
        data_file=DATA_FILE,
    )
    bot.run()