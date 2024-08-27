# coding=UTF-8
import requests
import re
import subprocess
from lxml.html import etree
import urllib3
from bs4 import BeautifulSoup
import yaml
import os
import time
import random
import json
from fake_useragent import UserAgent
from urllib.parse import quote_plus
urllib3.disable_warnings()


categories_conf = "config/categories.yaml"
category_list = set()
blacklisted_keywords = set()

blacklisted_platform = "config/blacklisted.yaml"

query_suffix = "china booking"

ua = UserAgent()

def get_config(config_file):
    try:
        with open(config_file, 'r', encoding = 'utf8') as file:
            yaml_data = yaml.safe_load(file)
            return yaml_data
    except FileNotFoundError:
        print("Failed to open %s", config_file)
        return None
    except yaml.YAMLError:
        print("Failed to Parse yaml %s", config_file)
        return None


# def search_bing(query, adult_content=False):
#     search_query = quote_plus(query)
#     search_suffix = "&mkt=zh-CN&ensearch=1&FORM=BESBTB"
#     search_url = "https://cn.bing.com/search?q=" + search_query+ search_suffix
#       # 对查询字符串进行编码

#     # params = {
#     #     'q': search_query,
#     #     'first': '0',  # 指定返回第一页结果
#     #     'FORM': 'PERE',
#     #     'adultContent': 'on' if adult_content else 'off'
#     # }

#     headers = {"User-Agent": ua.random}
#     try:
#         print(f'search_url is {search_url}')
#         response = requests.get(search_url, verify=False, headers=headers)
#         response.encoding = 'utf-8'
#         status_code = response.status_code
#         print(f'status code is {status_code}')
#         # print(f'response is {response.text}')
#         return (response.text, status_code)
#     except urllib3.exceptions.HTTPError as e:
#         print(e)
#         return (None,str(e))
#     except Exception as e:
#         print(e)
#         return (None,str(e))
    

# def parse_bing_tree(content):
#     tree = etree.HTML(content.text)
#     print(tree)
#     return tree

# def parse_bing_html(html_content):
#     soup = BeautifulSoup(html_content, 'html.parser')
#     # 尝试找到所有搜索结果链接
#     results = []
#     blacklisted_platform_config = get_config(blacklisted_platform)
    
#     blacklisted_site = set()
#     if blacklisted_platform_config:
#         blacklisted_site = set(blacklisted_platform_config)
#     print(f'blacklisted_site is {blacklisted_site}')

#     for result in soup.find_all('li', class_='b_algo'):
#         link = result.find('a')
#         if link is not None:
#             continue
        
#         href = link['href']
#         label = link['aria-label']
#         if label and href and label not in blacklisted_site:
#             results.append(href)
#     print(f"results is {results}")
#     return results

def is_hit_blacklisted_keywords(url):
    if blacklisted_keywords is None or len(blacklisted_keywords) == 0:
        return False
    
    for item in blacklisted_keywords:
        if item in url.lower():
            return True
    return False

def write_failed_category(category_name):
    category_name = category_name.replace(" ", "_")
    output_folder_file = "output/urls/failed_site_" + category_name + ".txt"
    print(f'write url to {output_folder_file}')
    try:
        with open(output_folder_file, 'a', encoding='utf8') as file:
            file.write(category_name + '\n')
            if file is not None:
                file.close()
    except FileNotFoundError:
            print(f"Can not write to failed category file {output_folder_file}")
            exit(-1)
    print('write succeed') 


def write_url_to_file(category_name, urls):
    category_name = category_name.replace(" ", "_")
    output_folder_file = "output/urls/site_" + category_name + ".txt"
    print(f'write url to {output_folder_file}')
    try:
        with open(output_folder_file, 'a', encoding='utf8') as file:
            for url in urls:
                if is_hit_blacklisted_keywords(url):
                    continue
                file.write(url + '\n')
            if file is not None:
                file.close()
    except FileNotFoundError:
            print(f"Can not write to url output file {output_folder_file}")
            exit(-1)
    print('write succeed') 

def run_puppeteer_script(param):
    result = subprocess.run(['node', 'puppeteer_script.js', param], capture_output=True, text=True)
    return result.stdout

def getRandomSleepTime():
   return random.randint(20, 60)

def format_category_name(category_name):
    category_name = category_name.lower()
    category_name = category_name.replace(' & ', ' ')
    return category_name

if __name__ == "__main__":
    print("start")
    category_conf = get_config(categories_conf)
    category_list = category_conf.get("categories",[])

    blacklisted_keywords_conf = get_config(blacklisted_platform)
    blacklisted_keywords_list = blacklisted_keywords_conf.get("blacklisted_url_keywords")
    blacklisted_keywords = set(blacklisted_keywords_list)

    for category in category_list:
        category_name = format_category_name(category)
        query = category_name + " " + query_suffix
        print(f'query is {query}')
        search_results = run_puppeteer_script(query)
        results_json = search_results.strip()
        print(f"results_json is {results_json}")
        try:
            search_results_list = json.loads(results_json)
            print(f"write {category_name} url to file")
            write_url_to_file(category_name, search_results_list)
        except Exception as e:
            print(f'parse json got error {e}')
            write_failed_category(category_name)

        seconds = getRandomSleepTime()
        print(f'sleep {seconds}')
        time.sleep(seconds)
        
    print("--------------- end ---------------")
    exit(0)
        


