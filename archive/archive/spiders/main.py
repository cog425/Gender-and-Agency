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
from archive.items import ArchiveItem
from archive.settings import *
from scrapy.http import FormRequest
import urllib
import os
import sys
import pandas as pd
from urllib.parse import quote
import scrapy
import numpy as np

bookdf = pd.read_csv("metadata.tab", sep='\t')#, nrows=10
bookdf['url'] = bookdf['title'].apply(lambda x: "https://archive.org/details/texts?&and[]={}&and[]=mediatype%3A%22texts%22".format(quote(x)))
bookdf['BOOK_ID'] = bookdf['BOOK_ID'].apply(lambda x: x.replace('.xml.txt', ''))
url_root = 'https://archive.org'

class archiveSpider(Spider):
    name = 'archive'
    
    def start_requests(self):
         for i, title, url in bookdf[['BOOK_ID','title','url']].values[:100]:
             request = scrapy.Request(url, callback = self.parse, headers=DEFAULT_REQUEST_HEADERS)
             request.meta['bookid'] = i
             request.meta['title'] = title
             yield request

    def parse(self, response):
        
        url_1s = response.xpath("//div[@class='item-ttl C C2']/a/@href").extract()
        views = response.xpath("//div[@class='hidden-tiles views C C1']//nobr[@class='hidden-xs']/text()").extract()
        views = [int(x.replace(',','')) for x in views]

        if not len(url_1s):
            print("No Results")
            return
            
        url_1 = url_1s[np.argmax(views)]
        print(views)
        print(url_1, max(views))
        
        request = scrapy.Request(url = url_root + url_1, callback=self.parse_page2, headers=DEFAULT_REQUEST_HEADERS)
        request.meta['bookid'] = response.meta['bookid']
        request.meta['title'] = response.meta['title']
        yield request

            
    def parse_page2(self, response):
        
        url_2s = response.xpath("//div[@class='boxy quick-down']/div/a/@href").extract()
        # //div[@class='boxy quick-down']/div/div/div/a/@href
        for url in url_2s:
            if len(url)>4 and url[-4:]=='.txt':
                url_2 = url_root + url
                break
        request = scrapy.Request(url = url_2, callback=self.parse_page3, headers=DEFAULT_REQUEST_HEADERS)
        request.meta['bookid'] = response.meta['bookid']
        request.meta['title'] = response.meta['title']
        yield request
        
    def parse_page3(self, response):
        text = '\n'.join(response.xpath("//div[@class='container container-ia']/pre/text()").extract())
        
        open('../../download/{}-{}.txt'.format(response.meta['bookid'], response.meta['title']),'w').write(text)
        
        