from environs import Env


env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")  # Забираем значение типа str
ADMINS = env.list("ADMINS")  # Тут у нас будет список из админов
IP = env.str("ip")  # Тоже str, но для айпи адреса хоста
db_pass = env.str("pg_pass")
db_user = env.str("pg_login")
host = env.str("ip")

URL = env.str("URL")
