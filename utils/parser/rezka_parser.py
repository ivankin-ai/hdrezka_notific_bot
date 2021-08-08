import asyncio

import aiohttp
from bs4 import BeautifulSoup
import requests
import hashlib
from data.config import URL

"""
li class:b-translator__item  озвучки -> data-translator_id = id 

ui class: b-simple_seasons__list clearfix -> блок с li (количество сезонов) data-tab_id
ui class: b-simple_episodes__list clearfix -> блок с li (количество эпизодов) data-episode_id

Со страницы сериала мы берём только озвучки, если они есть, если нет, то ничего не берём. 
и предлагаем подписаться на все обновления.
"Подписаться на все обновления? В том числе мы уведомим Вас, если выйдет новая озвучка"



страница поиска:
span class: cat series его родитель a href=link

"""


def check_site() -> list:
    """
    Заходит на главную страницу, парсит вышедшие сериалы
    возвращает список словарей [{name_serial, data_site, link, str_hash}]
    """
    ssn = requests.Session()
    r = ssn.get('https://www.2ivi.com/')
    soup = BeautifulSoup(r.text, 'lxml')
    days = soup.findAll('div', {'class': 'b-seriesupdate__block'})
    days_list = []
    for day in days:
        films = day.findAll('div', {'class': 'b-seriesupdate__block_list_item_inner'})
        for film in films:
            try:
                name_elem = film.find('a')
                name_serial = name_elem.text
                link = name_elem.get('href')
            except Exception:
                continue
            season_elem = film.find('span', {'class': 'season'})
            if season_elem:
                season = season_elem.text[1:-1]
                season = int(season.split()[-2])
            else:
                season = 0
            episode_elem = film.find('span', {'class': 'cell cell-2'})
            if episode_elem:
                if type(episode_elem.contents) == list:
                    episode = episode_elem.contents[0]
                    episode_n = episode.split()[-2]
                    if episode_n.find("-") == -1:
                        episode = int(episode_n)
                    else:
                        episode = int(max(episode_n.split("-")))
                else:
                    episode = int(episode_elem.text)
            else:
                episode = 0
            if len(episode_elem.contents) > 1:
                voice = episode_elem.contents[1].text[1:-1]
            else:
                voice = None
            voice = f'Озвучка {voice}, ' if voice else ''
            data_site = voice + f"сезон {season}, серия {episode}"
            str_hash = hashlib.md5(
                (data_site + str(link)).encode()
            ).hexdigest()
            days_list.append({'name_serial': name_serial,
                              'link': URL + link,
                              'data_site': data_site,
                              'str_hash': str_hash})
    return days_list


def update_new_serials(serials_site, db_str_hash: list):
    """берёт сериалы с сайта и хеш всех сериалов из БД,
     сравнивает их и отдаёт новые сериалы, если они есть"""
    serials_site_dict = dict()
    for serial in serials_site:
        serials_site_dict[serial["str_hash"]] = serial
    set_db = set(db_str_hash)
    set_site = set(serials_site_dict)
    new_serials_set = set_site - set_db
    new_serials_list = list()
    if new_serials_set:
        for serial in new_serials_set:
            new_serials_list.append(serials_site_dict[serial])
    return new_serials_list


async def search_serial(name=None, serials=None):
    if serials is list:
        cookies = {"1": '1'}
        async with aiohttp.ClientSession(cookies=cookies) as session:
            tasks = []
            for serial in serials:
                task = asyncio.create_task(search_by_link(serial, session))
                tasks.append(task)
            serials = await asyncio.gather(*tasks)
    elif serials:
        cookies = {"1": '1'}
        async with aiohttp.ClientSession(cookies=cookies) as session:
            serials = await search_by_link(serials, session)
    elif name:
        serials = await search_by_name(name)
        # serials = await search_serial(serials=serials)
    return serials


async def search_by_link(serial: dict, session=None) -> dict:
    """Принимает один сериал в виде словаря.
    Обязательные занчения # {link, name_serial, info}
    добавляет словарь voices если он есть и last_e last_s """
    flag = False
    if not session:
        flag = True
        session = aiohttp.ClientSession()
    cookies = {"1": '1'}
    async with session.get(url=serial["link"], cookies=cookies) as r:
        html = await r.text()
        soup = BeautifulSoup(html, 'lxml')
        voices_data = soup.findAll("li", {"class": "b-translator__item"})
        voices = []
        for voice in voices_data:
            text = voice.find("img")
            if text:
                text = text["title"]
                voices.append({"title": voice.text + text, "voice_id": voice["data-translator_id"]})
            else:
                voices.append({"title": voice.text, "voice_id": voice["data-translator_id"]})
        last = soup.findAll("li", {"class": "b-simple_episode__item"})[-1]
        last_episode = last["data-episode_id"]
        last_season = last["data-season_id"]
        if len(voices):
            voices = await check_voices(serial["link"], voices, session)
            # voices = [{title, voice_id, le,ls}]
            for voice in voices:
                if last_season < voice["last_season"]:
                    continue
                elif last_season == voice["last_season"]:
                    if last_episode < voice["last_episode"]:
                        continue
                    else:
                        last_episode = voice["last_episode"]
                else:
                    last_season = voice["last_season"]
                    last_episode = voice["last_episode"]
        if flag:
            await session.close()
        return {"name_serial": serial["name_serial"],
                # "last_season": last_season,
                # "last_episode": last_episode,
                "voices": voices,  # Здесь они нужны, что бы выбрать озвучку
                "info": serial["info"],
                "link": serial["link"]}


async def check_voices(link, voices, session):
    """Заходим на страницу сериала и возвращаем последние серии всех озвучек"""

    async def check(link_voice, voice):
        async with session.get(url=link_voice) as r:
            html = await r.text()
            soup = BeautifulSoup(html, "lxml")
            last = soup.findAll("li", {"class": "b-simple_episode__item"})[-1]
            last_episode = last["data-episode_id"]
            last_season = last["data-season_id"]
            return {"last_season": last_season,
                    "last_episode": last_episode,
                    "title": voice["title"],
                    "voice_id": voice["voice_id"]}

    tasks = []
    for voice in voices:
        link_voice = link + f"#t:{voice['voice_id']}-s:1-e:1"
        task = asyncio.create_task(check(link_voice, voice))
        tasks.append(task)

    voices = await asyncio.gather(*tasks)
    if len(voices):
        return voices


async def search_by_name(name):
    async with aiohttp.ClientSession() as session:
        cookies = {"1": '1'}
        data = {'do': 'search', 'subaction': 'search', 'q': name}
        url = 'https://2ivi.com/search/'
        async with session.get(url=url, cookies=cookies, params=data) as r:
            html = await r.text()
            soup = BeautifulSoup(html, "lxml")
            serial_links = soup.findAll("div", {"class": "b-content__inline_item"})
            serials = []
            for movie in serial_links:
                if movie.find("span").text == "Сериал":
                    serials.append(
                        {
                            "link": movie.a["href"],
                            "name_serial": movie.find("div", {"class": "b-content__inline_item-link"}).a.text,
                            "info": movie.find("div", {"class": "b-content__inline_item-link"}).div.text
                        })
            return serials  # [{link, name_serial, info}]
