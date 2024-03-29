import time
import requests
import os
import logging
import telegram
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
    """
    Отправляет сообщение в Telegram чат.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logger.info(f'Не удалось отправить сообщение: {error}')


def get_api_answer(current_timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
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
        try:
            return homework_status.json()
        except Exception as error:
            logger.error(f'Ошибка {error} при запросе к API')

    except Exception as error:
        logger.error(f'Ошибка {error} при запросе к API')
        raise Exception(f'Ошибка {error}')


def check_response(response):
    """
    Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python
    Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ,
    доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        logger.error('Ожидался словарь')
        raise TypeError()

    if 'homeworks' not in response.keys():
        logger.error('Не найден ключ "homeworks"')

    homework_list = response['homeworks']

    if not isinstance(homework_list, list):
        logger.error('Ожидался список')
        raise TypeError()
    return homework_list


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает
    только один элемент из списка домашних работ
    В случае успеха,
    функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if not isinstance(homework, dict):
        logger.error('Ожидался словарь')
        raise TypeError()

    if 'homework_name' or 'status' not in homework.keys():
        logger.error('Не найден ключи "homework_name" или/и "status"')

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_name is None or homework_status is None:
        logger.error('Не найдено имя или статус работы')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]

    except Exception as error:
        logger.error(f'Ошибка {error}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы."""
    return all([
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
        PRACTICUM_TOKEN
    ]) or logger.critical('Отсутствуют обязательные переменные окружения')


def main():
    """Основная логика работы бота."""
    if check_tokens():
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

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logger.error(message)
                send_message(bot, message)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
    else:
        logger.critical('Отсутствуют обязательные переменные окружения')


if __name__ == '__main__':
    main()
