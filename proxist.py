#!/usr/bin/env python
# -*- coding: utf-8 -*-
#=========================================================#
# [+] Title: Hide My Ass Proxy Grabber - Proxist 1.0-Dev  #
# [+] Script: proxist.py                                  #
# [+] Blog: http://pytesting.blogspot.com                 #
#=========================================================#

import re
import sys
import colorama
from lxml import html
from urlparse import urljoin
from requests import Session
from termcolor import colored
from prettytable import PrettyTable


def request_proxy_page(session=Session(), page='/proxy-list/1'):
    response = session.get(
        url=urljoin("http://hidemyass.com/", page)
    )
    return response.content


def request_proxy_pages(session=Session()):
    session.headers.update({'User-Agent': 'Proxist 1.0-Dev'})

    page = '/proxy-list/1'
    while True:
        document = html.fromstring(request_proxy_page(session, page))
        next_page = document.find_class('next')
        if not next_page:
            break

        page = next_page[0].attrib['href']
        yield document


def strip_tags(value):
    return re.sub('<[^>]*?>', '', value).strip()


def strip_updates(updates_raw):
    raw_time = strip_tags(updates_raw)
    if 'now' in raw_time:
        raw_time = re.sub(r'now', '0s', raw_time)
    elif 'sec' in raw_time:
        raw_time = re.sub(r'\ssec(s)?', 's', raw_time)
    else:
        raw_time = re.sub(r'\sminute(s)?', 'm', raw_time)
        raw_time = re.sub(r'\shour(s)?', 'h', raw_time)
        raw_time = re.sub(r'\sand', '', raw_time)
    return raw_time


def strip_ip(ip_raw):
    # Strip Style
    style = re.search(
        '<style>(?P<style>.*?)</style>',
        ip_raw,
        flags=re.DOTALL
    ).group('style')
    ip = re.sub(style, '', ip_raw)

    # Strip Hidden Classes
    hidden_classes = re.findall('\.(.*?)\{display:none}', style)
    for hidden_class in hidden_classes:
        ip = re.sub('<[^>]*?class="%s">\w+</[^>]*?>' % hidden_class, "", ip)

    # Strip Hidden Styles
    ip = re.sub('<[^>]*?style="display:none">(\w+)</[^>]*?>', "", ip)
    return strip_tags(ip)


def strip_percentage(ip_raw):
    percentage_dict = re.search(
        '<div class="(?P<type>\w+)" style="width:(?P<num>\d+)%"> </div>',
        ip_raw,
        flags=re.DOTALL
    ).groupdict()
    percentage_dict['num'] = int(percentage_dict['num']) / 10.0
    percentage = '*' * int(round(percentage_dict['num']))

    color = 'green'
    if percentage_dict['type'] == 'slow':
        color = 'red'
    elif percentage_dict['type'] == 'medium':
        color = 'yellow'
    return colored("{:<10}".format(percentage), color, 'on_white', attrs=['bold'])


def proxy_properties(raw_properties):
    return (
        strip_updates(raw_properties.next()),  # Updates
        strip_ip(raw_properties.next()),  # IP
        strip_tags(raw_properties.next()),  # Port
        strip_tags(raw_properties.next()),  # Country
        strip_percentage(raw_properties.next()),  # Speed
        strip_percentage(raw_properties.next()),  # Connection time
        strip_tags(raw_properties.next()),  # Type
        strip_tags(raw_properties.next()),  # Anonymity
    )


if __name__ == '__main__':
    # Init Colorama
    colorama.init()

    sys.stdout.write('Creating The Proxy Table')
    table = PrettyTable(['Updates', 'IP', 'Port', 'Country', 'Speed', 'Connection time', 'Type', 'Anonymity'])
    for html_page in request_proxy_pages():
        sys.stdout.write('.')
        for tr in html_page.xpath("//table[@id='listtable']/tr"):
            table.add_row(proxy_properties(html.tostring(td) for td in tr.iter('td')))
    print("\n%s" % table)
