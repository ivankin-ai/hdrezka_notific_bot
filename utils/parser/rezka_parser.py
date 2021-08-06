import aiohttp
from bs4 import BeautifulSoup
import requests
import hashlib
from data.config import URL


def check_site() -> list:
    """
    Заходит на главную страницу, парсит вышедшие сериалы
    возвращает список словарей [{имя, сезон, эпизод, озвучка, ссылка}]
    Должно быть [{name_serial, voice, season, episode, link, str_hash}]
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

            str_hash = hashlib.md5(
                (str(name_serial)+str(voice)+str(episode)+str(season)).encode()
            ).hexdigest()
            days_list.append({'name_serial': name_serial,
                              'season': season,
                              'episode': episode,
                              'voice': voice,
                              'link': URL + link,
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


async def check_voices(link, voices_id, session):
    """Заходим на страницу сериала и забираем soup с каждой озвучки"""
    # async with aiohttp.ClientSession() as session:
    cookies = {"1": "1"}
    soup_voices = []
    for voice_id in voices_id:
        link_voice = link + f"#t:{voice_id}-s:1-e:1"
        async with session.get(url=link_voice, cookies=cookies) as r:
            html = await r.text()
            soup = BeautifulSoup(html, "lxml")
            soup_voices.append(soup)
    return soup_voices


async def search_serial(name=None, link=None):
    if link:
        async with aiohttp.ClientSession() as session:
            return await search_by_link(link, session)
    elif name:
        return await search_by_name(name)


async def search_by_link(link, session):
    # async with aiohttp.ClientSession() as session:
    #     cookies = {"1": '1'}
    #     print("поиск по ссылке:")
    if True:
        cookies = {"1": '1'}
        async with session.get(url=link, cookies=cookies) as r:
            html = await r.text()
            soup = BeautifulSoup(html, 'lxml')

            name_serial = soup.find("div", {"class": "b-post__title"}).text
            print(name_serial)
            name_orig = soup.find("div", {"class": "b-post__origtitle"})
            print(name_orig.text) if name_orig else print("рус")
            name_orig = name_orig.text + "; " if name_orig else ""
            data_table = soup.find("table", {"class": "b-post__info"})
            date_release = data_table.findAll("td")[5].text
            country = data_table.findAll("td")[7].text
            info = f"{name_orig}{date_release}. {country}."

            voices_data = soup.findAll("li", {"class": "b-translator__item"})
            voices = []
            voices_id = []
            for voice in voices_data:
                text = voice.find("img")
                voices_id.append(voice["data-translator_id"])
                if text:
                    text = text["title"]
                    voices.append(voice.text + text)
                else:
                    voices.append(voice.text)

            season = 1
            episode = 1
            soup_voices = await check_voices(link, voices_id, session)
            if len(voices_id):
                soup_voices = [soup]
            for soup_voice in soup_voices:
                episode_div = soup_voice.find("div", {"class": "simple-episodes-tabs"})
                if episode_div:
                    season_data = episode_div.findAll("ul")
                    for num, season_ul in enumerate(season_data):
                        num += 1
                        if season <= num:
                            season = num
                        else:
                            break
                        ep_data = season_ul.findAll("li")
                        for ep, _ in enumerate(ep_data):
                            ep += 1
                            if episode <= ep:
                                episode = ep
                            else:
                                break

            return [{"name_serial": name_serial,
                     "voices": voices,
                     "info": info,
                     "season": season,
                     "episode": episode,
                     "link": link}]


async def search_by_name(name):
    async with aiohttp.ClientSession() as session:
        cookies = {"1": '1'}
        data = {'do': 'search', 'subaction': 'search', 'q': name}
        url = 'https://2ivi.com/search/'
        async with session.get(url=url, cookies=cookies, params=data) as r:
            html = await r.text()
            soup = BeautifulSoup(html, "lxml")
            serial_links = soup.findAll("div", {"class": "b-content__inline_item-link"})
            serials = []
            serial_links = serial_links[:9] if len(serial_links) > 9 else serial_links
            for link in serial_links:
                serials += await search_by_link(link.a["href"], session)
            return serials

