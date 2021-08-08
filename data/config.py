from environs import Env


env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
ADMINS = env.list("ADMINS")
IP = env.str("ip")
db_pass = env.str("pg_pass")
db_user = env.str("pg_login")
host = env.str("ip")
URL = env.str("URL")
db_name = env.str("db_name")
