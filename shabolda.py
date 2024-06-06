import telebot
import random
import time
import json
import logging
from logging.handlers import RotatingFileHandler

# Логирование
log_formatter = logging.Formatter('%(asctime)s - %(message)s')
log_file = 'bot.log'

log_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Загрузка конфигурации
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

bot = telebot.TeleBot(config["token"])

# Загрузка данных из файла, если существует
try:
    with open('data.json', 'r') as file:
        data = json.load(file)
except FileNotFoundError:
    data = {}

# Администраторы и их ранги
admins = {
    "2112427125": 5  # Например, добавляем владельца бота
}

# Ранги и соответствующие команды
rank_commands = {
    1: ['/mute'],
    2: ['/mute', '/kick'],
    3: ['/mute', '/kick', '/ban', '/warn'],
    4: ['/mute', '/kick', '/ban', '/warn'],
    5: ['/mute', '/kick', '/ban', '/warn', '/adminup']
}

# Муты и варны пользователей
mutes = {}
warns = {}


# Функция для получения полного имени пользователя
def get_user_full_name(user):
    if user.last_name:
        return f"{user.first_name} {user.last_name}"
    else:
        return user.first_name


# Проверка ранга администратора
def get_admin_rank(user_id):
    return admins.get(str(user_id), 0)


def check_rank(command, user_id):
    user_rank = get_admin_rank(user_id)
    for rank, commands in rank_commands.items():
        if command in commands and user_rank >= rank:
            return True
    return False


# Команда для повышения ранга администратора
@bot.message_handler(commands=['adminup'])
def adminup(message):
    if get_admin_rank(message.from_user.id) == 5:  # Только владелец может повышать ранги
        if message.reply_to_message:
            user_id = str(message.reply_to_message.from_user.id)
            if user_id in admins:
                admins[user_id] = min(admins[user_id] + 1, 5)
            else:
                admins[user_id] = 1
            bot.send_message(message.chat.id,
                             f"Пользователь {get_user_full_name(message.reply_to_message.from_user)} повышен до ранга {admins[user_id]}")
        else:
            bot.send_message(message.chat.id, "Команда должна быть ответом на сообщение пользователя.")
    else:
        bot.send_message(message.chat.id, "Вы не имеете прав для выполнения этой команды.")


@bot.message_handler(commands=['activity'])
def activity(message):
    try:
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        user_name = message.from_user.username or get_user_full_name(message.from_user)

        if user_id not in data:
            data[user_id] = {"activity_count": 0, "last_activity_time": 0, "name": user_name, "chats": {}}

        user_data = data[user_id]

        # Ensure the user has a "chats" entry
        if "chats" not in user_data:
            user_data["chats"] = {}

        if "last_activity_time" not in user_data:
            user_data["last_activity_time"] = 0

        chat_data = user_data["chats"].get(chat_id, {"activity_count": 0})

        current_time = time.time()
        if current_time - user_data["last_activity_time"] >= config["hourly_interval"]:
            activity = random.randint(0, 10)
            user_data["activity_count"] += activity
            user_data["last_activity_time"] = current_time
            user_data["name"] = user_name

            chat_data["activity_count"] += activity
            user_data["chats"][chat_id] = chat_data

            responses = {
                0: f'{get_user_full_name(message.from_user)}, сегодня ты был менее активен, попробуй еще раз.',
                1: f'{get_user_full_name(message.from_user)}, ты проявил активность 1 раз, неплохо.',
                2: f'{get_user_full_name(message.from_user)}, ты проявил активность 2 раза, продолжай в том же духе.',
                3: f'{get_user_full_name(message.from_user)}, ты проявил активность 3 раза, так держать!',
                4: f'{get_user_full_name(message.from_user)}, ты проявил активность 4 раза, здорово!',
                5: f'{get_user_full_name(message.from_user)}, ты проявил активность 5 раз, отлично!',
                6: f'{get_user_full_name(message.from_user)}, ты проявил активность 6 раз, молодец!',
                7: f'{get_user_full_name(message.from_user)}, ты проявил активность 7 раз, продолжай!',
                8: f'{get_user_full_name(message.from_user)}, ты проявил активность 8 раз, впечатляюще!',
                9: f'{get_user_full_name(message.from_user)}, ты проявил активность 9 раз, невероятно!',
                10: f'{get_user_full_name(message.from_user)}, ты проявил активность 10 раз, превосходно!',
            }

            response_text = responses.get(activity,
                                          f'{get_user_full_name(message.from_user)}, ты проявил активность {activity} раз! В сумме ты проявил активность {user_data["activity_count"]} раз.')
        else:
            time_left = int(config["hourly_interval"] - (current_time - user_data["last_activity_time"]))
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            response_text = f'{get_user_full_name(message.from_user)}, ты не можешь сейчас проявлять активность. Попробуй позже! Осталось {hours} часов и {minutes} минут.'

        data[user_id] = user_data
        with open('data.json', 'w') as file:
            json.dump(data, file)

        bot.send_message(message.chat.id, response_text, reply_to_message_id=message.message_id)
    except Exception as e:
        logging.error(f"Ошибка в команде /activity: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /activity: {e}")


@bot.message_handler(commands=['topactivity'])
def show_top_users(message):
    try:
        sorted_data = sorted(data.items(), key=lambda x: x[1].get('activity_count', 0), reverse=True)

        top_users_text = "Топ пользователей по активности:\n"
        for i, user_data in enumerate(sorted_data[:15]):  # Показываем топ 15 пользователей
            user_id, user_info = user_data
            username = user_info.get('username', user_info.get('name', 'Пользователь'))
            activity_count = user_info.get('activity_count', 0)

            top_users_text += f"{i + 1}. {username} - {activity_count} раз\n"

        bot.send_message(message.chat.id, top_users_text, reply_to_message_id=message.message_id, parse_mode='HTML')
    except Exception as e:
        logging.error(f"Ошибка в команде /topactivity: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /topactivity: {e}")


@bot.message_handler(commands=['topchatactivity'])
def show_top_chat_users(message):
    try:
        chat_id = str(message.chat.id)
        chat_users = {user_id: user_data["chats"].get(chat_id, {}).get("activity_count", 0)
                      for user_id, user_data in data.items() if chat_id in user_data.get("chats", {})}

        sorted_chat_users = sorted(chat_users.items(), key=lambda x: x[1], reverse=True)

        top_chat_users_text = "Топ пользователей по активности в этом чате:\n"
        for i, (user_id, activity_count) in enumerate(sorted_chat_users[:15]):
            username = data[user_id].get('username', data[user_id].get('name', 'Пользователь'))

            top_chat_users_text += f"{i + 1}. {username} - {activity_count} раз\n"

        bot.send_message(message.chat.id, top_chat_users_text, reply_to_message_id=message.message_id, parse_mode='HTML')
    except Exception as e:
        logging.error(f"Ошибка в команде /topchatactivity: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /topchatactivity: {e}")


# Команда /admins для отображения списка администраторов
@bot.message_handler(commands=['admins'])
def list_admins(message):
    try:
        admins_list = "Список администраторов:\n"
        for admin_id, rank in admins.items():
            try:
                user = bot.get_chat_member(message.chat.id, admin_id).user
                admins_list += f"{get_user_full_name(user)} - Ранг {rank}\n"
            except Exception:
                admins_list += f"ID {admin_id} - Ранг {rank}\n"

        bot.send_message(message.chat.id, admins_list)
    except Exception as e:
        logging.error(f"Ошибка в команде /admins: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /admins: {e}")


# Команда /ADMIN для упоминания всех администраторов
@bot.message_handler(commands=['ADMIN'])
def mention_all_admins(message):
    try:
        mentions = "Упоминание всех администраторов:\n"
        for admin_id in admins.keys():
            try:
                user = bot.get_chat_member(message.chat.id, admin_id).user
                mentions += f"@{user.username} " if user.username else f"{get_user_full_name(user)} "
            except Exception:
                mentions += f"ID {admin_id} "

        bot.send_message(message.chat.id, mentions)
    except Exception as e:
        logging.error(f"Ошибка в команде /ADMIN: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /ADMIN: {e}")


# Команда /adminhelp для отображения команд для администраторов
@bot.message_handler(commands=['adminhelp'])
def admin_help(message):
    try:
        admin_rank = get_admin_rank(message.from_user.id)
        if admin_rank > 0:
            commands_list = "Команды для администраторов:\n"
            for rank, commands in rank_commands.items():
                if admin_rank >= rank:
                    commands_list += f"Ранг {rank}: {', '.join(commands)}\n"

            bot.send_message(message.chat.id, commands_list)
        else:
            bot.send_message(message.chat.id, "У вас нет прав администратора.")
    except Exception as e:
        logging.error(f"Ошибка в команде /adminhelp: {e}")
        bot.send_message(message.chat.id, f"Произошла ошибка при выполнении команды /adminhelp: {e}")


# Обновление команды /help
@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = """
Команды бота:
/activity - проявить активность
/topactivity - показать топ пользователей по активности
/topchatactivity - показать топ пользователей по активности в этом чате
/admins - показать список администраторов
/ADMIN - упомянуть всех администраторов
/adminhelp - показать команды для администраторов
"""
    bot.send_message(message.chat.id, help_text)


# Присвоение ранга владельцам чатов
def assign_owner_rank(chat_id):
    try:
        owners = bot.get_chat_administrators(chat_id)
        for admin in owners:
            if admin.status == 'creator':
                admins[str(admin.user.id)] = 5
    except Exception as e:
        logging.error(f"Ошибка при присвоении ранга владельцу чата: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    assign_owner_rank(message.chat.id)
    show_help(message)


if __name__ == "__main__":
    bot.polling(none_stop=True)
