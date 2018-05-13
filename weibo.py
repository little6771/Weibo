import re, string
import pandas as pd
from bs4 import BeautifulSoup as BS
import time

import urllib.request
import urllib
import cookielib
import lxml.html as HTML

class Fetcher(object):
    def __init__(self, username=None, pwd=None, cookie_filename=None):
        self.cj = cookielib.LWPCookieJar()
        if cookie_filename is not None:
            self.cj.load(cookie_filename)
        self.cookie_processor = urllib2.HTTPCookieProcessor(self.cj)
        self.proxy = urllib2.ProxyHandler({'http': 'http://101.254.140.170:80'})    # 使用代理，防止被屏蔽，若代理IP失效，改换其他IP
        self.opener = urllib2.build_opener(self.cookie_processor, urllib2.HTTPHandler, self.proxy)
        urllib2.install_opener(self.opener)
         
        self.username = username
        self.pwd = pwd
        self.headers = {'User-Agent': 'Mozilla/5.0 (MSIE 9.0; Windows NT 6.3; WOW64; Trident/7.0; MALNJS; rv:11.0) like Gecko'}
    
    def get_rand(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (MSIE 9.0; Windows NT 6.3; WOW64; Trident/7.0; MALNJS; rv:11.0) like Gecko'}
        req = urllib2.Request(url ,urllib.urlencode({}), headers)
        resp = urllib2.urlopen(req)
        login_page = resp.read()
        rand = HTML.fromstring(login_page).xpath("//form/@action")[0]
        passwd = HTML.fromstring(login_page).xpath("//input[@type='password']/@name")[0]
        vk = HTML.fromstring(login_page).xpath("//input[@name='vk']/@value")[0]
        return rand, passwd, vk

    def login(self, username=None, pwd=None, cookie_filename=None):
        if self.username is None or self.pwd is None:
            self.username = username
            self.pwd = pwd
        assert self.username is not None and self.pwd is not None
         
        url = 'https://login.weibo.cn/login/?ns=1&revalid=2&backURL=http%3A%2F%2Fweibo.cn%2F&backTitle=%CE%A2%B2%A9&vt='
        rand, passwd, vk = self.get_rand(url)
        data = urllib.urlencode({'mobile': self.username,
                                 passwd: self.pwd,
                                 'remember': 'on',
                                 'backURL': 'http://weibo.cn/',
                                 'backTitle': '微博',   #'\xe5\xbe\xae\xe5\x8d\x9a'
                                 'tryCount': '',
                                 'vk': vk,
                                 'submit':'登录'})  #'\xe7\x99\xbb\xe5\xbd\x95'
        url = 'https://login.weibo.cn/login/' + rand
        req = urllib2.Request(url, data, self.headers)
        resp = urllib2.urlopen(req)
        
        redirecturl = resp.geturl() #To get the url for redirect page.
        req = urllib2.Request(redirecturl,data,self.headers)
        resp = urllib2.urlopen(req) #Redirect page
        page = resp.read()
        link = HTML.fromstring(page).xpath("//a/@href")[0]
        if not link.startswith('http://'): link = 'http://weibo.cn/%s' % link
        req = urllib2.Request(link, headers=self.headers)
        page = urllib2.urlopen(req).read()
        if cookie_filename is not None:
            self.cj.save(filename=cookie_filename)
        elif self.cj.filename is not None:
            self.cj.save()
        print ('login process finished.')
         
    def fetch(self, url, printout=False):
        print ('fetch url: ', url)
        req = urllib2.Request(url, headers=self.headers)
        content = urllib2.urlopen(req).read()
        if printout:
            print( 'unicode: ', content)
        return content

def has_class_and_id(tag):
    return tag.has_attr('class') and tag.has_attr('id')

def get_page(content, printout=False):
    weibo_url = 'http://weibo.cn/'
    page_soup = BS(content)
    tweet, timestamp, device = [], [], []
    for divs in page_soup.find_all(has_class_and_id):
        div = divs.find_all('div')
        if div:
            if div[0].find('span', {'class': 'ctt'}):
                info = div[-1].find('span', {'class': 'ct'}).get_text().split()
                tweet.append(div[0].find('span', {'class': 'ctt'}).get_text())
                timestamp.append(string.join(info[:2]))
                device.append(string.join(info[2:]))
                if printout:
                    print (tweet, '\n', '-'*90, timestamp, '\n')
    pagelist = page_soup.find('div', {'id': 'pagelist'})
    nextpagenum = int(re.search('page=(\d+)', pagelist.find('a')['href']).group(1))
    nextpage = weibo_url + pagelist.find('a')['href']
    return nextpagenum, nextpage, tweet, timestamp, device

def scrape_mainpage(uid, filename):
    db_tweet, db_timestamp, db_device = [], [], []

    LogIner = Fetcher()
    username = ''   # 用户名
    password = ''   # 密码
    LogIner.login(username, password, 'cookies.lwp')
    content = LogIner.fetch('http://weibo.cn/'+str(uid))
    nextpagenum, nextpage, tweet, timestamp, device = get_page(content)
    lastpagenum = 1
    db_tweet.extend(tweet)
    db_timestamp.extend(timestamp)
    db_device.extend(device)

    while nextpagenum > lastpagenum:
        time.sleep(1)
        lastpagenum = nextpagenum
        content = LogIner.fetch(nextpage)
        if content:
            nextpagenum, nextpage, tweet, timestamp, device = get_page(content)
            db_tweet.extend(tweet)
            db_timestamp.extend(timestamp)
            db_device.extend(device)
    #         print 'fetch page {}'.format(nextpage)

    df = pd.DataFrame({'Tweet': db_tweet, 'Time': db_timestamp, 'Device': db_device})
    df.to_excel(filename)

if __name__ == '__main__':
    scrape_mainpage('happyzhangjiang', 'happyzhangjiang_Weibo_Tweets.xls')