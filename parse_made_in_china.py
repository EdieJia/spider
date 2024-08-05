# coding=UTF-8
import requests
import re
import urllib3
from bs4 import BeautifulSoup
import yaml
import os
import time
import random
from fake_useragent import UserAgent
urllib3.disable_warnings()

# model = pipeline("text-extraction", model="llama3:8b")

main_headers = {
    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
}

config_file = "config/made_in_china.yaml"

main_page_html_file = "pages/main.html"

product_list_html_file = "pages/product"

page_limit_by_category = 10

# 用于存储去重后的span文本的集合
ua = UserAgent()


# 使用LLM解析HTML内容
# promote = '抽取product List中的company name:'
# promote = '提取span content中包含 Co., Ltd.的 content'
# response = ollama.generate(model='llama3:8b', prompt=promote + html_content)
# print(response)
# company_name = response['message']['company']
# print("company", company_name)

def write_company_to_file(title,unique_companies):
    company_output_file = "output/companies"
    suffix = title.lower().replace(" ", "_")
    try:
        with open(company_output_file + "_" + suffix + ".txt", 'a', encoding='utf8') as file:
            for item in list(unique_companies):
                item = re.sub(r"\s+", " ", item)
                file.write(item + '\n')
            if file is not None:
                file.close()
    except FileNotFoundError:
            print(f"Can not write to main page file {main_page_html_file}")


def parse_company_names(html_content):
    unique_companies = set()
    soup = BeautifulSoup(html_content, 'html.parser')
    # 寻找class为'company-name'的元素
    company_name_elements = soup.find_all('div', class_='company-name')
    # 遍历所有找到的元素
    unique_companies = set()
    for element in company_name_elements:
        span_tag = element.find('a')
        if span_tag and span_tag.text not in unique_companies:
            company_name = span_tag.text
            unique_companies.add(company_name)
            # print(f'append company {company_name}')
    return unique_companies


def send_get_request(url, headers):
    global ua

    if headers is None:
        headers = {"User-Agent": ua.random}
    print(url)
    print(headers)
    try:
        response = requests.get(url, verify=False, headers=headers)
        response.encoding = 'utf-8'
        status_code = response.status_code
        return (response.text, status_code)
    except urllib3.exceptions.HTTPError as e:
        print(e)
        return (str(e), None)
    except Exception as e:
        print(e)
        return (str(e), None)


def is_sub_category(url):
    # 将URL的路径部分拆分为段
    url = url.replace("//", "")
    path_parts = url.split('/')
    # 检查路径段的数量
    # 2段是父目录
    if len(path_parts) == 2:
        return False
    elif len(path_parts) == 3:
         # 3段是二级目录
        return True
    else:
        return False


def extrac_link_by_category(html_content):
    if html_content == "":
        print("Error: Received empty HTTP response")
        exit(1)

    soup = BeautifulSoup(html_content, 'html.parser')

    link_data = []
    div_tags = soup.find_all('div', class_='items-line-child-title')
    for div_tag in div_tags:
        # print(f"------------{div_tag.text}------------")
        next_sibling = div_tag.find_next_sibling()
        while next_sibling and next_sibling.name == 'a':
            # 提取a标签的href属性
            href = next_sibling.get('href')
            title = next_sibling.get('title')
             # 继续检查下一个兄弟元素
            next_sibling = next_sibling.find_next_sibling()
            if not href:
                continue
            if not is_sub_category(href):
                continue
            link_data.append({
                'href': "https:" + href,
                'title': title
            })
            # print(title)
           
    return link_data


def extract_product_paging_link(html_content):
    page_link_list = []
    soup = BeautifulSoup(html_content, 'html.parser')
    a_tags = soup.find_all('div', class_='page-num')
    page_total = soup.find('a', class_='page-dis')
    print(f'page_total is {page_total}')
    if page_total == 0:
        return page_link_list

    max_page = page_limit_by_category
    if page_total < max_page:
        max_page = page_total

    print(max_page)
    for a_tag in a_tags:
        href = a_tag.get('href')
        if len(page_link_list) > max_page:
            return page_link_list
        page_link_list.append({
            'href': href,
        })

    return page_link_list


def get_config():
    global config_file
    try:
        with open(config_file, 'r', encoding = 'utf8') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print("Failed to open %s", config_file)
        return None
    except yaml.YAMLError:
        print("Failed to Parse yaml %s", config_file)
        return None


def find_category_in_whitelist(link_data_list, whitelist_categories):
    if whitelist_categories is None or len(whitelist_categories) == 0:
        return link_data_list
    
    matching_links = []
    for link_data in link_data_list:
        if link_data.get('title') in whitelist_categories:
            matching_links.append(link_data)
    return matching_links


def load_main_page_html():
    # 先从历史记录中获取
    try:
        with open(main_page_html_file, 'r', encoding='utf8') as file:
            content = file.read()
            if content:
                return content
    except FileNotFoundError:
            print(f"Can not find main page file {main_page_html_file}")
    
    # 否则爬取网站主页信息
    main_url = "https://www.made-in-china.com/"
    content, status_code = send_get_request(main_url, main_headers)
    if status_code != 200:
        print(f"Error: Received HTTP status code {status_code}")
        exit(-1)
    
    # 保存网站主页信息
    try:
        with open(main_page_html_file, 'w', encoding='utf8') as file:
            file.write(content)
            if file is not None:
                file.close()
    except FileNotFoundError:
            print(f"Can not write to main page file {main_page_html_file}")

    return content


def load_product_page(page_path):
    try:
        print(f"load file from {page_path}")
        if os.path.exists(page_path) and os.path.getsize(page_path) != 0:
            with open(page_path, 'r', encoding='utf8') as file:
                    content = file.read()
                    return content
    except FileNotFoundError:
        print(f"Can not write to main page file {main_page_html_file}")
    return ""


def get_content_by_product_link(link, file_name):
    content = load_product_page(file_name)
    if content != "":
        print("load product from local")
        product_list_html_content = content
    else:
        print(f"request product page with url {link}")
        # 从二级分类的link获取所有商品列表
        product_list_html_content, status_code = send_get_request(link, None)
        print(f"request product resp code {status_code}")
        if status_code != 200:
            print(status_code)
            return
        # 保存product list 页面信息
        print('save product to file')
        with open(file_name, 'w', encoding='utf8') as file:
                file.write(product_list_html_content)
                if file is not None:
                    file.close()
    return product_list_html_content


def getRandomSleepTime():
   return random.randint(6, 20)


def get_page_link(html_content):
    next_page = get_next_page_link(html_content)
    print(f'next_page is {next_page}')
    more_page = get_more_page_link(html_content)
    print(f'more_page is {more_page}')
    if more_page:
        return more_page
    return next_page

def get_next_page_link(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    pagenum_tags = soup.find('div', class_='page-num')
    if pagenum_tags is None:
        return None
    a_tag = pagenum_tags.find_all('a')
    if a_tag and len(a_tag) != 0:
        return a_tag[0].get('href')
    else:
        return None

def get_more_page_link(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    more_tag = soup.find('a', class_='viewmore J-viewmore')
    print(more_tag)
    if more_tag:
        return more_tag.get('href')
    else:
        return None

if __name__ == "__main__":
    print("start")
    # 获取主页html
    category_html_content = load_main_page_html()
    if category_html_content is None:
        exit(-1)

    # 从主页html解析获得所有二级分类的link
    link_data_list = extrac_link_by_category(category_html_content)
    print(f'Get {len(link_data_list)} category link')

    # 获取link白名单
    config = get_config()
    if config is None:
        exit(-1)
    whitelist_categories = config['whitelist_category']
    print(whitelist_categories)
    target_links = find_category_in_whitelist(link_data_list, whitelist_categories)
    print(target_links)

    for link in target_links:
        title = link["title"]
        sub_name = title.lower().replace(" ", "_")
        first_page_name = product_list_html_file + "_" + sub_name  + ".html"
        href = link["href"]
        product_first_page_content = get_content_by_product_link(href, first_page_name)
        unique_companies = parse_company_names(product_first_page_content)
        if len(unique_companies) != 0:
            print(f'write the first page to {first_page_name}, size is {len(unique_companies)}')
            write_company_to_file(title,unique_companies)

        page_link = get_page_link(product_first_page_content)
        if page_link is None:
            print('can not get page link')
            exit(-1)

        page_link = page_link.replace(" ", "")
        if not page_link.startswith("https://"):
            page_link = "https:" + page_link
        print(f'first_page_name is {first_page_name}')
        print(f'page_link is {page_link}')

        pageNo = 2
        while pageNo < page_limit_by_category:
            suffix = "-" + str(pageNo) + ".html"
            page_link = page_link.replace("-2.html", suffix)
            page_name = product_list_html_file + "_" + sub_name + "_" + str(pageNo) +  ".html"
            print(f'page_name is {page_name}')
            print(f'page_link is {page_link}')

            product_page_content = get_content_by_product_link(page_link, page_name)
            if product_page_content is None:
                print(f'got empty product content')
                exit(-1)
            unique_companies = parse_company_names(product_page_content)
            if len(unique_companies) != 0:
                print(f'write {len(unique_companies)} to {title}')
                write_company_to_file(title,unique_companies)
        
            pageNo = pageNo + 1
            # 暂停程序执行随机秒数
            seconds = getRandomSleepTime()
            print(f'sleep {seconds}')
            time.sleep(seconds)
    print('---------------- exit ----------------')
    exit(0)
        
        # 获取首页商品对应的company名称
        
        # paging_link_list = extract_product_paging_link(product_list_html_content)
        # print(paging_link_list)
        # for page_link in paging_link_list:
        #     product_list_page_href = page_link['href']
        #     product_list_html_content, status_code = send_get_request(product_list_page_href, None)
        #     if status_code != 200:
        #         print(f"Error: Received HTTP status code {status_code}")
        #         continue
        #     # 获取首页商品对应的company名称
        #     parse_company_names(product_list_html_content)
        
        




