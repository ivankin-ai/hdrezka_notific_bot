from aiogram.utils.callback_data import CallbackData

serials_callback = CallbackData('serials', 'key', 'number')
menu_callback = CallbackData('menu', 'value', 'table', 'id')
menu_subs_callback = CallbackData('subs', 'value', 'key', 'id')
menu_sub_callback = CallbackData('subs', 'key', 'id')

# serials_callback = CallbackData('serials', 'key', 'number')
# menu_callback = CallbackData('menu', 'level', 'table', 'id', )
# menu_subs_callback = CallbackData('subs', 'value', 'key', 'id')
# menu_sub_callback = CallbackData('subs', 'key', 'id')

