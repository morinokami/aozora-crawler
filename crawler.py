#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from bs4 import BeautifulSoup
import json
import os
import requests
import time


class Crawler(object):

    def __init__(self, waiting_time=0.1):
        self.waiting_time = waiting_time

    def get_book_detail(self, book_page_url):
        '''Extract book info such as a title, a subtitle, and file urls'''

        r = requests.get(book_page_url)
        html = r.text.encode('ISO-8859-1')
        soup = BeautifulSoup(html)
        title_data = soup.find(attrs={'summary': u'タイトルデータ'})
        sakuhin_data = soup.find(attrs={'summary': u'作品データ'})
        files = soup.find_all(attrs={'bgcolor': 'white'})

        # extract a book title
        title = title_data.find(attrs={'size': '+2'}).text.encode('utf-8')
        # extract a book subtitle if exists
        subtitle = ''
        for tr in title_data.find_all('tr'):
            if u'副題：'in tr.text:
                subtitle = tr.find_all('td')[-1].text
        # extract what historical kana is used
        if u'新字新仮名' in sakuhin_data.text:
            kana_usage = u'新字新仮名'
        elif u'新字旧仮名' in sakuhin_data.text:
            kana_usage = u'新字旧仮名'
        else:
            kana_usage = u'旧字旧仮名'
        # extract file locations
        file_urls = []
        for file_data in files:
            file_name = file_data.find('a').text
            file_url = book_page_url.rsplit('/', 1)[0] + '/files/' + file_name
            file_urls.append(file_url)
        # check whether copyright is expired or not
        if u'＊著作権存続＊' in soup.text:
            copyright = True
        else:
            copyright = False

        res = {
            'title': title,
            'subtitle': subtitle,
            'kana_usage': kana_usage,
            'copyright': copyright
        }
        for file_url in file_urls:
            ext = os.path.splitext(file_url)[1]
            if ext == '.html':
                res['html_file'] = file_url
            elif ext == '.zip':
                res['zip_file'] = file_url

        return res

    def get_book_pages(self, author_page_url):
        '''Extract an author name and book urls'''

        r = requests.get(author_page_url)
        html = r.text.encode('ISO-8859-1')
        soup = BeautifulSoup(html)
        author_name = soup.find(attrs={'size': '+2'}).text.encode('utf-8')
        book_list = soup.find('ol')
        book_urls = []

        for book in book_list.find_all('li'):
            url = book.find('a').get('href')
            if url:
                book_urls.append('http://www.aozora.gr.jp/' + url[3:])

        return {'author': author_name, 'book_urls': book_urls}

    def get_author_pages(self, column_page_url):
        '''Extract author page urls'''

        r = requests.get(column_page_url)
        html = r.text.encode('ISO-8859-1')
        soup = BeautifulSoup(html)
        authors = soup.find_all('ol')
        author_links = []

        for sound_ol in authors:
            for author in sound_ol.find_all('li'):
                author_links.append('http://www.aozora.gr.jp/index_pages/' + author.find('a').get('href'))

        return author_links

    def wait(self, start, end):
        if end - start < self.waiting_time:
            time.sleep(self.waiting_time - (end - start))

    def crawl(self):
        '''Extract all author names and related file urls'''

        url = 'http://www.aozora.gr.jp/index_pages/person_{}.html'
        column_names = ['a', 'ka', 'sa', 'ta', 'na', 'ha', 'ma', 'ya', 'ra', 'wa']
        column_names = ['wa']
        res = {}

        for col_name in column_names:
            authors = self.get_author_pages(url.format(col_name))
            for author in authors:
                author_info = self.get_book_pages(author)
                author_name = author_info['author']
                res[author_name] = []
                book_urls = author_info['book_urls']
                print author_name
                for book in book_urls:
                    start = time.time()

                    book_info = self.get_book_detail(book)
                    res[author_name].append(book_info)
                    print '  ' + book_info['title'], book_info['subtitle'], book_info['kana_usage']

                    end = time.time()
                    self.wait(start, end)

        return res


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--object',
        help='a file name which will contain the result in the json format')
    parser.add_argument('-w', '--waiting-time',
        help='a waiting time to extract each book info', type=float)
    args = parser.parse_args()

    waiting_time = args.waiting_time
    if waiting_time:
        crawler = Crawler(waiting_time=waiting_time)
    else:
        crawler = Crawler()
    result = crawler.crawl()
    json_result = json.dumps(result)

    fname = args.object
    if fname is None:
        fname = 'aozora.json'
    with open(fname, 'w') as f:
        f.write(json_result)
