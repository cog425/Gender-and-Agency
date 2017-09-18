"""
Created on Fri Mar 3 02:17:07 2017

@author: dt

To run this spider:
    1. cd /Users/dt/Documents/UChicago/Literature/2.\ Gender\ and\ verbs/data/archive/archive/spiders/
    2. source activate py35
    3. scrapy runspider main.py
"""


from scrapy.spiders import Spider
from scrapy.selector import Selector
try:
    from archive.items import ArchiveItem
    from archive.settings import *
except:
    pass
from scrapy.http import FormRequest
import urllib
import os
import sys
import pandas as pd
from urllib.parse import quote
import scrapy
import numpy as np
import re
import csv
from difflib import SequenceMatcher

bookdf = pd.read_csv("metadata.tab", sep='\t')#, nrows=10
open('1_Errors.csv','w')
open('0_Search_results.csv','w')


def get_search_url(x):
    basic_title = 'https://archive.org/details/texts?&and[]={}&and[]=mediatype%3A%22texts%22'.format(quote(x.title))
    if x.last_name == 'Unknown' or pd.isnull(x.last_name):#or pd.isnull(x.first_name) 
        return basic_title
    else:
        add_name = '&and[]=creator%3A"{}"'.format(quote(x.last_name))#quote(x.first_name), 
        return basic_title+add_name
    
bookdf['url'] = bookdf.apply(lambda x: get_search_url(x), axis=1)
bookdf['BOOK_ID'] = bookdf['BOOK_ID'].apply(lambda x: x.replace('.xml.txt', '')).astype(int)
bookdf.to_csv('metadata.csv',index=0)

url_root = 'https://archive.org'


class archiveSpider(Spider):
    name = 'archive'
    
    def start_requests(self):            
        for index, x in bookdf.iterrows():
            request = scrapy.Request(x.url, callback = self.parse, headers=DEFAULT_REQUEST_HEADERS)
            request.meta['info'] = dict(x)
            yield request

    def parse(self, response): #search page
        titles = response.xpath("//div[@class='item-ttl C C2']/a/div[@class='ttl']/text()").extract()
        titles = [x.strip() for x in titles]
        url_1s = response.xpath("//div[@class='item-ttl C C2']/a/@href").extract()
        views = response.xpath("//div[@class='hidden-tiles views C C1']//nobr[@class='hidden-xs']/text()").extract()
        views = [int(x.replace(',','')) for x in views]
        authors = response.xpath("//div[@class='C234']//div[@class='by C C4']/span[2]/text()").extract()
        
        length_url = len(url_1s)
        if length_url!=len(views):
            views=0
        if length_url!=len(authors):
            authors=''
        if length_url!=len(titles):
            titles=''
        
        result_df = pd.DataFrame({'Book_id': response.meta['info']['BOOK_ID'],
                      'True_title': response.meta['info']['title'],
                      'title':titles, 
                      'view':views,
                      'author':authors,
                      'url':url_1s})
        
        result_df['similarity'] = result_df.title.apply(lambda x: SequenceMatcher(None, x,response.meta['info']['title']).ratio())
        result_df.drop(result_df[result_df.similarity<0.3].index, inplace=1)
        
        def is_vol_fun(x):
            if len(x)<4 or re.match(r'^Vol 1-\d+:', x):
                return True
            elif x[:4]=='Vol ':
                return False
            else:
                return True
        result_df['isnotVol'] = result_df.title.apply(is_vol_fun)

        print()
        print(response.meta['info']['BOOK_ID'])

        if not len(result_df):
            print('No result! ')
            log = pd.DataFrame(response.meta['info'],index=[0])
            log['err']='No result'
            log.to_csv('1_Errors.csv',index=0,header=0,mode='a')
            return 
        elif sum(result_df.isnotVol):
            print('OK!')
            index = [result_df[result_df.isnotVol].sort('view',ascending=0).index[0]]
            result_df['status'] = 'Normal'
        else:
            print('The book is seperated into Vols.')
            index = result_df[result_df.similarity==result_df.groupby('similarity').count().sort('url').index[0]].index
            result_df['status'] = 'Seperate into Volumes'
            
#            print(result_df.groupby('similarity').count().reset_index().sort('url'))
#            print(index)
        
        rows = result_df.loc[index, :]
        result_df.loc[index, 'used'] = 1
        result_df.to_csv('0_Search_results.csv',mode='a',header=False)
        
        for index, row in rows.iterrows():
            request = scrapy.Request(url = url_root + row.url, callback=self.parse_page2, headers=DEFAULT_REQUEST_HEADERS, errback=self.errback_record)
            request.meta['info'] = response.meta['info']
            yield request

            
    def parse_page2(self, response): #click one item in search page
        
        url_2s = response.xpath("//div[@class='boxy quick-down']/div/a/@href").extract()
#            url_2s = response.xpath("//div[@class='boxy quick-down']/div/div/div/a/@href").extract()
        for url in url_2s:
            if len(url)>4 and url[-4:]=='.txt':
                url_2 = url_root + url
                break
        try:
            request = scrapy.Request(url = url_2, callback=self.parse_page3, headers=DEFAULT_REQUEST_HEADERS)
            request.meta['info'] = response.meta['info']
            yield request
        except:
            log = pd.DataFrame(response.meta['info'],index=[0])
            log['err']='Parse_page 2 error'
            log.to_csv('1_Errors.csv',index=0,header=0,mode='a')
            print('Parse_page 2 error')

    def parse_page3(self, response): #text detail
        try:
            text = '\n'.join(response.xpath("//div[@class='container container-ia']/pre/text()").extract())
            open('../../download/{}-{}.txt'.format(response.meta['info']['BOOK_ID'], response.meta['info']['title']),'a+').write(text)
        except:
            log = pd.DataFrame(response.meta['info'],index=[0])
            log['err']='Parse_page 3 error'
            log.to_csv('1_Errors.csv',index=0,header=0,mode='a')
            print('Parse_page 3 error')
            
    def errback_record(self, failure):
        print(dir(failure))
        self.logger.error(repr(failure))