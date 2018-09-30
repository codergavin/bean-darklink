#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author:Gavin
# Description:暗链检测(最初版本)
#
# 需要安装插件：webdriver、selenium、chardet、火狐或者谷歌浏览器
# 需要pythond的插件 chardet、selenium、tldextract
# LastUpdateTime:2018-07-14

# 未完成功能
# TODO 1、误报过滤
# TODO 2、黑白名单
# TODO 4、JS劫持：通过搜索引擎搜索点击页面（执行一段js）跳转到博彩页面；直接输入网址访问网页，跳转到404页面。

import sys,time
import re,os
import urllib,urllib2
import logging
import chardet
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.wait import WebDriverWait
import Queue
from threading import Thread


# *********************************************** global variable begin ***********************************************
# 暗链匹配正则表达式
CheckRegs  = [
    r'(<[Aa][^>]+?(display\s*:\s*none|visibility\s*:\s*hidden)[^>]*?>.+?</[Aa]>)',           # 超链接a的属性display:none|visibility:hidden
    r'(<[Aa][^>]+?(color\s*:\s*#ffffff|color\s*:\s*white|font-size\s*:\s*0px)[^>]*?>.+?</[Aa]>)',                # 这个根据颜色来判断的，不是很准确，待定
    r'(<div[^>]+?(font-size\s*:\s*0px|line-height\s*:\s*0px)[^>]*?>.+?</div>)',                                    # div设置属性font-size:0px
    r'(<div[^>]+?(display\s*:\s*none|visibility\s*:\s*hidden)[^>]*?>.+?</div>)',                   #d iv的属性display:none|visibility:hidden
    r'(<marquee[^>]+?(scrollamount*=\s*["\']?\s*\d{3}\s*["\']?)[^>]*?>.+?</marquee>)',       # marquee的scrollamount的属性，测试发现高于1000就很难发现了，所以这里目前暂定1000
    r'(<div[^>]+?(text-indent\s*:\s*-\d{3})[^>]*?>.+?</div>)',                               # 位置属性text-indent
    r'(<div[^>]+?(?=[^>]+?position\s*:\s*absolute)(?=[^>]+?top\s*:\s*-\d{3})(?=[^>]+?left\s*:\s*-\d{3})[^>]*?>.+?</div>)',  # 利用位置position:absolute、top/left(由于expression_r该属性已淘汰，所以正则当中暂时不考虑)
    r'(<div[^>]+?(?=[^>]+?position\s*:\s*absolute)(?=[^>]+?top\s*:\s*-\d{3})(?=[^>]+?right\s*:\s*-\d{3})[^>]*?>.+?</div>)', # 利用位置position:absolute、top/right
    r'(<div[^>]+?(?=[^>]+?position\s*:\s*absolute)(?=[^>]+?z-index\s*:\s*-\d{1})[^>]*?>.+?</div>)' # 利用位置position:absolute、z-index
]
Sytle_Reg = r'(((.|#)\w*)\s*\{[^\}]+?(display\s*:\s*none|visibility\s*:\s*hidden)[^\}]+?\})'
Meta_Reg = r'(<meta[^>]+? content\s*=\s*["\']?[^>]*?(\.com\.cn|\.net\.cn|\.gov\.cn|\.org\.nz|\.org\.cn|\.com|\.net|\.org|\.gov|\.cc|\.biz|\.info|\.cn|\.co|\.com|\.xin|\.shop|\.ltd|\.club|\.top|\.vip|\.ren|\.link|\.mobi|\.wang|\.site|\.name|\.tv|\.so|\.中国|\.公司|\.网络|\.集团|\.网址)[^>]*?["\']?[^>]*?>)'
Iframe_Reg = r'(<iframe[^>]*?(?=[^>]*?width\s*=\s*["\']?\s*100%\s*["\']?[^>]*?)(?=[^>]*?height\s*=\s*["\']?\s*100%\s*["\']?[^>]*?)[^>]*?>.+?</iframe>)'
Body_Pre_Reg = r'(<body.+?<iframe[^>]+?>)'
Body_After_Reg = r'(</iframe>.+?</body>)'
AReg = r'<[Aa][^>]*?>.+?</[Aa]>'


param_div = '</div>'
param_html = '</html>'
reload(sys)
sys.setdefaultencoding('utf-8')
sys_code = sys.getfilesystemencoding()
url_queue = Queue.Queue()

check_website_num = 0                               # 已检测的网站总数
dark_link_num = 0                                   # 暗链总数
browser_type = ""                                   # 浏览器的方式
save_file_dir_win_path = r'D:/usr/local/store'      # win文件保存路径的地址
save_file_dir_linux_path = '/usr/local/store'       # linux文件保存路径地址
save_file_dir_websites = 'websites'                 # 网站首页内容保存文件夹
save_file_dir_darklink = 'darklink'                 # 网站首页暗链保存文件夹
is_darklink_save = False                            # 查出的暗链是否保存到文件
is_read_websites_txt = False                        # 是否采用从websites.txt文件中获取网站地址
check_website_sync_max = 10                         # 最大的并发量
websites_txt = 'websites.txt'                       # 文件名
get_page_content_type = 'phantomjs'                 # 可选值（urllib/phantomjs/webdriver）

phantomjs_win_path = 'D:\\Programs\\python\\phantomjs-2.1.1-windows\\bin\\phantomjs.exe'                # phantomjs的win 路径
phantomjs_linux_path = '/usr/bin/phantomjs'                                                             # phantomjs的linux路径
firefox_browser_linux_path = "/usr/bin/geckodriver"                                           # 火狐浏览器linux的路径
firefox_browser_win_path = "C:\\Program Files (x86)\\Mozilla Firefox\\geckodriver.exe"                  # 火狐浏览器win的路径
chrome_browser_linux_path = "/usr/bin/chromedriver"                                            # 谷歌浏览器linux的路径
chrome_browser_win_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe"      # 谷歌浏览器win的路径


# *********************************************** global variable end ***********************************************
def print_content(url,content):
    if is_darklink_save:
        save_content_to_file_fn(url, content, save_file_dir_darklink, 'a')
    else:
        print content


# 递归函数
def recursion_fn(url, arrs):
    # print "-------------------size:" + bytes(len(arrs))
    # print arrs
    if isinstance(arrs, list) and len(arrs) != 0:
        for arr in arrs:
            recursion_fn(url, arr)
    elif isinstance(arrs, tuple) and len(arrs) != 0:
        for arr in arrs:
            recursion_fn(url, arr)
    elif isinstance(arrs, str) or isinstance(arrs, unicode):
        pattern_a = re.compile(AReg, re.I | re.S | re.M)
        tokens = pattern_a.findall(arrs)
        # print "暗链超链接数：" + bytes(len(tokens))
        global dark_link_num
        dark_link_num += len(tokens)
        if len(tokens) != 0:
            for token in tokens:
                print_content(url,token)


def domain_name_resolution_fn(url):
    if url.startswith('https://') or url.startswith('http://'):
        return url
    else:
        url = 'http://' + url
        return url


# 获取系统版本
def get_system_platform_fn():
    #method1:sys.platform       result:win32/linux2
    #method2:platform.system()  result:Windows/Linux
    return platform.system()


# 获取网站首页内容(无法加载JS的脚本，弃用)
def get_page_content_by_urllib_fn(url):
    # user_agent = 'User-Agent: Mozilla/5.0  (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.4)  Gecko/20070515 Firefox/2.0.0.4'
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'
    try:
        request = urllib2.Request(url)
        request.add_header('User-Agent', user_agent)
        result = urllib2.urlopen(request, timeout=20)
        # html_code = chardet.detect(text)['encoding']
        text = result.read()
        # print type(text)
        html_code = chardet.detect(text)['encoding']
        print html_code
        text = text.decode(html_code)
        return text
    except Exception as e:
        print e
        return "fail"


# 获取网站首页内容(phantomjs已经停止更新，webdriver目前新版已经放弃对phantomjs支持，弃用)
def get_page_content_by_phantomjs_fn(url):
    phantomjs_path = ''
    if get_system_platform_fn() == 'Windows':
        phantomjs_path = phantomjs_win_path
    else:
        phantomjs_path = phantomjs_linux_path
    driver = webdriver.PhantomJS(executable_path=phantomjs_path)  # phantomjs的绝对路径
    driver.get(url)  # 获取网页
    text = driver.page_source
    # driver.close()
    driver.quit()
    return text


# 获取网站首页内容(推荐使用)
def get_page_content_by_webdriver_fn(url):
    try:
        if browser_type == "ie":
            driver = webdriver.Ie()
            driver.get(url)
            return driver.page_source
        elif browser_type == "chrome":
            browser_path = ''
            if get_system_platform_fn() == 'Windows':
                # browser_path = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chromedriver.exe'
                browser_path = chrome_browser_win_path
            else:
                browser_path = chrome_browser_linux_path
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
	    #chrome_options.add_argument('--no-zygote')
	    #chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(chrome_options=chrome_options,executable_path=browser_path)
            driver.get(url)
            text = driver.page_source
            driver.close()
            driver.quit()
            return text
        elif browser_type == "firefox":
            browser_path = ''
            if get_system_platform_fn() == 'Windows':
                # browser_path = 'C:\\Program Files (x86)\\Mozilla Firefox\\geckodriver.exe'
                browser_path = firefox_browser_win_path
            else:
                browser_path = firefox_browser_linux_path
            options = Options()
            options.add_argument('-headless')  # 无头参数
            driver = Firefox(firefox_options=options,executable_path=browser_path)  # 配了环境变量第一个参数就可以省了，不然传绝对路径
            # wait = WebDriverWait(driver, timeout=10)
            driver.get(url)
            # wait.until(expected.visibility_of_element_located((By.NAME, 'q'))).send_keys('headless firefox' + Keys.ENTER)
            # wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#ires a'))).click()
            text = driver.page_source
            driver.quit()
            return text
    except Exception as e:
        print e
        return "fail"


# 内部样式表(样式放在<style>样式表里)检测暗链
def check_dark_link_from_style_fn(url, content):
    pattern_style = re.compile(Sytle_Reg,re.I | re.S | re.M)
    tokens_style = pattern_style.findall(content)
    # print len(tokens_style)
    # print tokens_style
    if len(tokens_style) != 0 :
        for token_style in tokens_style:
            # print len(token_style)
            if len(token_style) == 4:
                attr_tag_name = token_style[1]
                # print attr_tag_name
                if attr_tag_name.startswith("."):
                    param_attr_name = attr_tag_name[1:]
                    # print param_attr_name
                    div_class_reg = r'(<div[^>]+?(\s*class\s*=\s*["\']?\s*'+ bytes(param_attr_name) +'\s*["\']?)[^>]*?>.+?</div>)'
                    # print div_class_reg
                    pattern_div = re.compile(div_class_reg,re.I | re.S | re.M)
                    tokens_div = pattern_div.findall(content)
                    # print tokens_div
                    if len(tokens_div) != 0:
                        for token_div in tokens_div:
                            recursion_fn(url, token_div)
                elif attr_tag_name.startswith("#"):
                    param_attr_name = attr_tag_name[1:]
                    div_class_reg = r'(<div[^>]+?(\s*id\s*=\s*["\']?\s*' +  bytes(param_attr_name) + '\s*["\']?)[^>]*?>.+?</div>)'
                    pattern_div = re.compile(div_class_reg,re.I | re.S | re.M)
                    tokens_div = pattern_div.findall(content)
                    if len(tokens_div) != 0:
                        for token_div in tokens_div:
                            recursion_fn(url, token_div)


# meta头文件检测暗链
def check_dark_link_from_mate_fn(url, content):
    pattern_meta = re.compile(Meta_Reg,re.I | re.S)
    tokens_meta = pattern_meta.findall(content)
    if len(tokens_meta) != 0:
        for token_meta in tokens_meta:
            if isinstance(token_meta,list) and len(token_meta) != 0:
                for token in token_meta:
                    print_content(url, token)
            elif isinstance(token_meta,tuple) and len(token_meta) != 0:
                for token in token_meta:
                    if bytes(token).startswith("<META") or bytes(token).startswith("<meta"):
                        print_content(url, token)


# iframe标签检测暗链
def check_dark_link_from_iframe_fn(url, content):
    pattern_iframe = re.compile(Iframe_Reg,re.I | re.S)
    tokens_iframe = pattern_iframe.findall(content)
    if len(tokens_iframe)!=0:
        # 标签<body>...<iframe>
        pattern_body_pre = re.compile(Body_Pre_Reg,re.I | re.S)
        tokens_body_pre = pattern_body_pre.findall(content)
        if len(tokens_body_pre)!=0:
            recursion_fn(url, tokens_body_pre)
        # 标签</iframe></body>
        pattern_body_after = re.compile(Body_After_Reg,re.I | re.S)
        tokens_body_after = pattern_body_after.findall(content)
        if len(tokens_body_after)!=0:
            recursion_fn(url, tokens_body_after)


# 存储文件(内容替换)
def save_content_to_file_fn(url, content, dir_name, save_type):
    if get_system_platform_fn() == 'Windows':
        file_path = save_file_dir_win_path + "/" + dir_name
    else:
        file_path = save_file_dir_linux_path + "/" + dir_name
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    file_path += "/" + url.replace("://", ".").replace(":", ".").replace("/", ".") + ".txt"
    file_obj = open(file_path, save_type)
    file_obj.write(content + '\n')
    file_obj.close()


# 根据常用暗链正则匹配暗链
def check_dark_link_fn(url):
    if get_page_content_type == 'urllib':
        content = get_page_content_by_urllib_fn(url)
    elif get_page_content_type == 'webdriver':
        content = get_page_content_by_webdriver_fn(url)
    else:
        content = get_page_content_by_phantomjs_fn(url)
    save_content_to_file_fn(url, content, save_file_dir_websites, 'w')
    # print "内容：" + content
    if content != "fail":
        try:
            # 1、内联样式(样式嵌套在标签里)
            for CheckReg in CheckRegs:
                # print "CheckReg:" + CheckReg
                pattern = re.compile(CheckReg, re.I | re.S | re.M)
                tokens = pattern.findall(content)
                if len(tokens) != 0:
                    # print "------------------------------"
                    recursion_fn(url, tokens)
                elif len(tokens) == 0 and (CheckReg.find(param_div) != -1):
                    # 此段代码解决<div>标签不全的问题
                    CheckReg = CheckReg.replace(param_div, param_html)
                    # print "+++++++++++:" + CheckReg
                    pattern = re.compile(CheckReg, re.I | re.S | re.M)
                    tokens = pattern.findall(content)
                    recursion_fn(url, tokens)
            # 2、内部样式表(样式放在<style>样式表里)
            check_dark_link_from_style_fn(url, content)
            # 3、meta头文件包含链接
            check_dark_link_from_mate_fn(url, content)
            # 4、iframe标签检测
            check_dark_link_from_iframe_fn(url, content)
        except Exception,e:
            print e


def check_dark_link_thread_fn():
    while True:
        url = url_queue.get()
        global check_website_num
        check_website_num += 1
        print bytes(check_website_num) + ":" + url
        check_dark_link_fn(url)

    url_queue.task_done()


get_page_content_type = 'webdriver'                         # 可选值（urllib/phantomjs/webdriver）默认值：phantomjs，如果没有值则默认为phantomjs
#get_page_content_type = 'phantomjs'
website = sys.argv[1]
browser_type = "firefox"
#browser_type = "chrome"
print "website:" + website + ";browser_type:" + browser_type

start_time = time.time()
if is_read_websites_txt:
    if get_system_platform_fn() == 'Windows':
        websites_txt_path = save_file_dir_win_path + "/" + websites_txt
    else:
        websites_txt_path = save_file_dir_linux_path + "/" + websites_txt

    for i in range(check_website_sync_max):
        thread = Thread(target=check_dark_link_thread_fn)
        thread.start()
    for website in open(websites_txt_path):
        website = website.strip()
        if len(website):        #去掉空行
            website = domain_name_resolution_fn(website)
            url_queue.put(website)
else:
    check_dark_link_fn(domain_name_resolution_fn(website.strip()))

end_time = time.time()
run_time = end_time - start_time
print "暗链总数：" + bytes(dark_link_num)
print "总耗时:" + str(run_time)
