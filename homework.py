import telegram

import time

import requests

import os

import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат,
    определяемый переменной окружения TELEGRAM_CHAT_ID
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.info(f'Не удалось отправить сообщение: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса
    В качестве параметра функция получает временную метку
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_status.status_code != 200:
            logger.error('Ошибка при запросе к API')
            raise Exception('Ошибка при запросе к API')
        return homework_status.json()
    except Exception as Error:
        logger.error(f'Ошибка {Error} при запросе к API')
        raise Exception(f'Ошибка{Error}')


def check_response(response):
    """Проверяет ответ API на корректность
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python
    Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ,
    доступный в ответе API по ключу 'homeworks'."""
    homework_list = response['homeworks']
    if not isinstance(homework_list, list):
        logger.error('Ожидался список')
        raise TypeError()
    return homework_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы
    В качестве параметра функция получает
    только один элемент из списка домашних работ
    В случае успеха,
    функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    try:
        verdict = HOMEWORK_STATUSES[homework_status]

    except Exception as error:
        logger.error(f'Ошибка {error}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True."""
    if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN]):
        logger.critical('Отсутствуют обязательные переменные окружения')
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    last_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response)[0])

            if message != last_message:
                last_message = message
                send_message(bot, message)
                logger.info('Сообщение отправлено')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            logger.info('Сообщение отправлено')
            time.sleep(RETRY_TIME)
        else:
            message = 'Неизвестная ошибка'
            logger.error(message)
            send_message(bot, message)
            logger.info('Сообщение отправлено')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
