from geopy.geocoders import Nominatim
from icecream import ic

import re
import pandas as pd 
import numpy as np
import math

# from tqdm import tqdm 
# from utils.custom_utils import load_var, save_var


# ----------------------------------------------------------------
# Check address levels
# ----------------------------------------------------------------


class CheckAddressLevels:

    def __init__(
        self,
        df_address:pd.DataFrame,
        text:str
    ):
        self.df_address = df_address
        self.text = text
        self.make_level_int()
        self.address_set = set()
        self.columns_brief = ['original_name', 'found_name', 'level', 'count', 'upper']
        self.df_brief = pd.DataFrame(columns=self.columns_brief)
        self.postfix = ['시', '군', '구']


    def filter_keyword(self, keyword:str):
        mask = self.df_address.map(
            # lambda x: bool(re_search(str(x), self.text)))
            # lambda x: bool(re_findall_endswith(str(x), self.text, self.postfix)))
            lambda x: bool(find_keyword_with_postfix(str(x), keyword, self.postfix)))
        df_filtered = self.df_address[mask.any(axis=1)]
        return df_filtered


    def update_brief(
        self,
        new_rows: list,      # list for making df_brief
        address_value: str,  # address name from the current row
        found_items: list,   # found address name
        column_level: int,   # found address level
        row_values: list,    # the current row from the address database
        count: int           # found address count
    ) -> list:
        # updating the brief dataframe 
        # the address name, its level, count, upper levels
        for item in found_items:
            
            # if the address is not in the brief dataframe
            if item not in self.address_set:
                self.address_set.add(item)
                upper_levels = set_to_list_string_only(row_values[:column_level])
                upper_levels = ','.join(upper_levels)
                new_rows.append([address_value, item, column_level, count, upper_levels])
                
            # if the address is already in the brief dataframe,
            # append its upper levels
            else:
                # finding the current address name in the current row
                for item_row in row_values:
                    if item_row == item:
                        for item_new_rows in new_rows:
                            # matching 'found_name' from the new_rows
                            if item_new_rows[1] == item:
                                values_set = set(item_new_rows[-1].split(','))
                                upper_levels = row_values[:column_level]
                                values_set.update(upper_levels)
                                item_new_rows[-1] = ','.join(set_to_list_string_only(values_set))

        return new_rows


    def make_count_table(self):
        df = self.df_filtered.copy()
        df['count'] = 0
        df[['original_name', 'found_name', 'found_lv']] = ''

        new_rows = []

        # searching all the official address in the target test
        # row
        for index, row in df.iterrows():
            # column
            for column, value in row.items():
                # check the address of the current row & column position
                # if the value is nan or ''
                if isinstance(value, str) and value:
                    
                    # find the address of the current row & column as keyword in the target text
                    # e.g finding 'seoul' as keyword in the given text
                    # found_items = re_findall(value, self.text)
                    # found_items = re_findall_endswith(value, self.text, self.postfix)
                    found_items = find_keyword_with_postfix(value, self.text, self.postfix)
                    count = len(found_items)
                    
                    if count > 0:
                        # add the information in the current row. 
                        # count: how many times the address ocurrs
                        # found: the found address names
                        # found_lv: the level of the found address
                        df.at[index, 'count'] += count
                        df.at[index, 'original_name'] = value
                        df.at[index, 'found_name'] = ','.join(found_items)
                        df.at[index, 'found_lv'] = self.level_int[column]
                        new_rows = self.update_brief(
                            new_rows, value, found_items, self.level_int[column], row.values, count)

        # updating the original dataframes
        self.df_brief = pd.concat(
            [self.df_brief,
             pd.DataFrame(new_rows, columns=self.columns_brief)],
            ignore_index=True)
        self.df_filtered = df


    def check_upper_level(self):
        for index, row in self.df_brief.iterrows():
            found_address = []
            upper_levels = row['upper'].split(',')
            for item in upper_levels:
                if item:
                    # found = re_findall_endswith(item, self.text, self.postfix)
                    found = find_keyword_with_postfix(item, self.text, self.postfix)
                    if found:
                        found_set = set(found)
                        found_address.append(','.join(list(found_set)))
            self.df_brief.at[index, 'upper'] = ','.join(found_address)
            if len(found_address) == 0 and row['level'] > 2:
                self.df_brief = self.df_brief.drop(index)
        self.df_brief = self.df_brief.sort_values(
            by=['upper', 'level', 'count', 'original_name'],
            axis=0, ascending=False)
        
    
    def make_level_int(self):
        self.level_int = {
            'lv0': 0,
            'lv1': 1, 
            'lv2': 2, 
            'lv3': 3,
            'lv4': 4,
            'lv5': 5
        }
        
    
    def get_top_result(self):
        result = None
        if len(self.df_brief) > 0:
            top_values = (self.df_brief.iloc[0].values)
            upper = top_values[-1].split(',')
            upper = upper[0].strip() if isinstance(upper, list) else upper.strip()
            result = f"{upper} {top_values[0]}" if upper else top_values[0]
        return result
        

    def process(self):
        self.df_filtered = self.filter_keyword(keyword=self.text)
        self.make_count_table()
        self.check_upper_level()
        return self.get_top_result()



# ----------------------------------------------------------------
# Get coodinates
# ----------------------------------------------------------------

def get_lat_long(location_name):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(location_name)

    if location:
        latitude = location.latitude
        longitude = location.longitude
        return (latitude, longitude)
    else:
        print(f"Location '{location_name}' not found.")
        return (None, None)



# ----------------------------------------------------------------
# Utility
# ----------------------------------------------------------------

def isendswith(text: str, postfix: list) -> str:
    for item in postfix:
        if text.endswith(item):
            return item
    return ''


def re_findall_endswith(
    keyword: str,
    text: str,
    postfix: list,
    min_len=2       # minimum keyword length. default: 2
) -> list:
    if len(keyword) > min_len:
        end_word = isendswith(keyword, postfix)
        if end_word:
            keyword = keyword[:-len(end_word)]
    return re.findall(re_pattern(keyword), text)


def re_pattern(keyword: str) -> str:
    # Define the pattern to search for the keyword, with word boundaries to match whole words only
    # pattern = rf'\b{re.escape(keyword)}'
    return r'\b{}'.format(re.escape(keyword))
    # return rf'{re.escape(keyword)}'


def re_findall(keyword: str, text: str) -> list:
    # Find all matches of the pattern in the text (case-insensitive)
    return re.findall(re_pattern(keyword), text, flags=re.IGNORECASE)


def re_search(keyword: str, text: str) -> str:
    # Searches for the given keyword in the text using a regular expression.
    return re.search(r'\b{}'.format(keyword), text, re.IGNORECASE)


def re_sub(keyword: str, text: str) -> str:
    # Use re.sub to replace the keyword with the keyword surrounded by parentheses
    pattern = rf'(?!🔺)\b{keyword}(?!🔻)'
    return re.sub(pattern, r'🔺\g<0>🔻', text, flags=re.IGNORECASE)


def extract_sentences_with_keyword(keyword, text):
    # Mark the keyword in the text
    marked_text = re_sub(keyword, text)

    # Split the text into sentences
    sentences = re.split(r'(?<=[.!?])+', marked_text)
    # o = [sentence.strip() for sentence in sentences]

    # Filter the sentences that contain the marked keyword
    keyword_pattern = re.escape(f'🔺{keyword}🔻')
    keyword_sentences = [sentence.strip() for sentence in sentences if re.search(keyword_pattern, sentence, re.IGNORECASE)]

    return keyword_sentences


def extract_sentences_marked(marked_text: str) -> str:
    sentences = re.split(r'(?<=[.!?])+', marked_text)
    keyword_pattern = r'🔺(.*?)🔻'
    keyword_sentences = [
        sentence.strip() for sentence in sentences if re.search(
            keyword_pattern, sentence, re.IGNORECASE)]
    return ' '.join(keyword_sentences)


def clean_text(text: str) -> str:
    flag = True
    while flag:
        flag_space = True if '  ' in text else False
        flag_linefeed = True if '\n\n' in text else False
        if flag_space or flag_linefeed: 
            if flag_space:
                text = text.replace('  ', ' ')
            if flag_linefeed:
                text = text.replace('\n\n', '\n')
        else:
            flag = False
    return text.strip()


def set_to_list_string_only(data: set) -> list:
    # return [item if isinstance(item, str) else str(item) for item in data]
    return [item for item in data if isinstance(item, str) and item]

from typing import List

def find_keyword_with_postfix(keyword: str, text: str, postfixes: List[str], min_len: int = 2) -> List[str]:
    """
    Finds all occurrences of the keyword in the text. If the keyword ends with any
    postfix in the provided list, the function will first try to match the full keyword.
    If no matches are found, it will remove the postfix and try again.

    Parameters:
    keyword (str): The keyword to search for in the text.
    text (str): The text in which to search for the keyword.
    postfixes (List[str]): A list of postfixes to check and remove from the keyword if necessary.
    min_len (int): The minimum length of the keyword to consider. Default is 2.

    Returns:
    List[str]: A list of all matches found in the text.
    """
    def is_endswith(text: str, postfixes: List[str]) -> str:
        for postfix in postfixes:
            if text.endswith(postfix):
                return postfix
        return ''

    # Check if the keyword is long enough and ends with any of the postfixes
    if len(keyword) > min_len:
        postfix = is_endswith(keyword, postfixes)
        if postfix:
            # Try to find matches with the full keyword first
            pattern = re_pattern(keyword)
            result = re.findall(pattern, text, flags=re.IGNORECASE)
            if result:
                return result

            # Remove the postfix and try again
            keyword = keyword[:-len(postfix)]
            
    # Final attempt to find matches without the postfix
    pattern = re_pattern(keyword)
    return re.findall(pattern, text, flags=re.IGNORECASE)