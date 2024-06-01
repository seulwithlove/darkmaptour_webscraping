import pandas as pd 
import numpy as np
import math
import re
import signal
import time

from time import sleep
# from icecream import ic       # 디버깅용 - print 대신 사용
from tqdm.notebook import tqdm 
from bs4 import BeautifulSoup
from typing import Callable

from selenium import webdriver 
from selenium.webdriver.common.action_chains import ActionChains 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import InvalidArgumentException, WebDriverException

from utils.custom_utils import load_var, save_var


class ArticleScraper:

    def __init__(self, df:pd.DataFrame):
        self.df = df
        
    
    def get_html_selenium(
        self,
        url: str,
        driver: webdriver.chrome.webdriver.WebDriver
    ) -> str:
        try:
            driver.get(url=url)
            body = driver.find_element(by=By.TAG_NAME, value="body")
            html = body.get_attribute('outerHTML')
            return html
        
        except InvalidArgumentException as e:
            print(f"Invalid argument exception: {e}")
            return ""
    
        except WebDriverException as e:
            print(f"WebDriverException: {e}")
            return ""


    def get_article_text(
        self,
        html:str,
        get_text_html_func: Callable[[BeautifulSoup], str]
    ) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        text = get_text_html_func(soup)
        return text


    def save_to_markdown(self, content, file_path):
        """
        Save content to a Markdown file.
    
        Parameters:
        - content (str): The content to be saved.
        - file_path (str): The path to the Markdown file.
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            

    def make_dataframe_url(self):
        self.df_url = self.df[self.df['URL'].notna()]
        self.index_url = self.df_url.index


    def scrape_by_selenium(self):
        driver = webdriver.Chrome()
        self.make_dataframe_url()
        new_column_name = 'selenium_html'
        self.df_work = self.df.copy()
        self.df_work[new_column_name] = ''
        for index in tqdm(self.index_url):
            url = self.df_work.loc[index, "URL"]
            try:
                set_alarm(10)   # set alarm - 10 sec.
                # print("Before: %s" % time.strftime("%M:%S"))
                result = self.get_html_selenium(url=url, driver=driver)
            except TimeoutException as e:
                # print(e)
                result = 'timeout'
            finally:
                signal.alarm(0)   # reset alarm
                # print("After: %s" % time.strftime("%M:%S"))
            self.df_work.at[int(index), new_column_name] = str(result)
        self.df = self.df_work.copy()
        driver.close()
        driver.quit()


    def make_dataframe_html(self):
        self.df_html = self.df[self.df['selenium_html'].notna() & (self.df['selenium_html'] != "")]
        self.index_html = self.df_html.index


    def make_content_from_html(
        self,
        get_text_html_func: Callable[[BeautifulSoup], str]):
        self.make_dataframe_html()
        self.df_work = self.df.copy()
        new_column_name = 'content'
        # self.df = self.df.assign(new_column_name='')
        self.df_work[new_column_name] = ''
        for index in tqdm(self.index_html):
            result = self.get_article_text(
                html=self.df_work.loc[index, "selenium_html"],
                get_text_html_func=get_text_html_func
            )
            self.df_work.at[int(index), new_column_name] = str(result)
        self.df = self.df_work.copy()


    def save_dataframe(self, file_name:str, file_path='./'):
        # now_time = get_current_time()
        self.df.to_parquet(
            f'{file_path}/{file_name}.parquet.gzip',
            compression='gzip')


    def process(self):
        self.scrape_by_selenium()
        # self.make_content_from_html()



# ----------------------------------------------------------------
# OTHER FUNCTIONS
# ----------------------------------------------------------------

class TimeoutException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def timeout_handler(num, stack):
    raise TimeoutException("Time limit exceeded")

def set_alarm(duration: int):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)

# 한국경제 본문을 찾아서 스크래핑
def get_text_hk(soup: BeautifulSoup) -> str:
    # div class="article-body"에 본문이 있음
    article_body = soup.find_all("div", class_="article-body") 
    if len(article_body) != 0:
        return article_body[0].get_text().strip() # 본문을 가져와서 str 변환 + 공백제거
    else:
        return ""



