#!/usr/bin/env python
# -*- coding: utf-8 -*-
#=========================================================#
# [+] Title: Hide My Ass Proxy Grabber - Proxist 1.0      #
# [+] Script: proxist.py                                  #
# [+] Blog: http://pytesting.blogspot.com                 #
#=========================================================#

import re
import json
import logging
import grequesocks
from os import path
from lxml import html
from docopt import docopt
from sys import stdout, argv
from urlparse import urljoin
from datetime import datetime
from base64 import b64encode, b64decode


# Global Variables
__version__ = 1.0
__doc__ = \
"""
Proxist {version}

Usage:
  {app} [--output=<output_path> --debug]
  {app} (-h | --help)
  {app} (-v | --version)

Options:
  -h --help               Show this screen.
  -v --version            Show version.
  --output=<output_path>  Output File Path.
  --debug                 Debug Mode.
""".format(app=path.basename(argv[0]),
           version=__version__)
LOGGER = logging.getLogger('DailyLogger')
DEBUG_MODE = False


def start_logging(logger=LOGGER, debug=False, output_file=None):
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(message)s')
    if debug:
        formatter = logging.Formatter('%(asctime)s:%(levelname)s - %(message)s',
                                      "%Y-%m-%d %H:%M:%S")

    # Create console handler and set level to debug
    sh = logging.StreamHandler(stdout)
    sh.setLevel(level=level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # If output file
    if output_file:
        fh = logging.FileHandler(output_file)
        fh.setLevel(level=level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def request_proxy_pages(session=grequesocks.requesocks.Session()):
    session.headers.update({'User-Agent': 'Proxist %s' % __version__})

    page = '/1'
    while True:
        response = session.get(
            url=urljoin("http://proxylist.hidemyass.com/", page)
        )
        document = html.fromstring(response.content)
        next_page = document.xpath("//a[@class='next']")
        if not next_page:
            break

        page = next_page[0].attrib['href']
        yield document


def strip_tags(raw_html):
    return re.sub('<[^>]*?>', '', raw_html).strip()


def strip_ip(raw_ip):
    # Strip Style
    style = re.search(
        '<style>(?P<style>.*?)</style>',
        raw_ip,
        flags=re.DOTALL
    )
    if style:
        raw_style = style.group('style')
        raw_ip = re.sub(raw_style, '', raw_ip)

        # Strip Hidden Classes
        hidden_classes = re.findall('\.(.*?)\{display:none}', raw_style)
        for hidden_class in hidden_classes:
            raw_ip = re.sub('<[^>]*?class="%s">\w+</[^>]*?>' % hidden_class, "", raw_ip)

    # Strip Hidden Styles
    return strip_tags(re.sub('<[^>]*?style="display:none">(\w+)</[^>]*?>', "", raw_ip))


def strip_type(raw_type):
    striped = strip_tags(raw_type)
    return striped.replace('socks4/5', 'socks5').lower()


def get_proxies_dict(raw_ip, raw_port, raw_type):
    ip = strip_ip(raw_ip)
    port = strip_ip(raw_port)
    proxy_type = strip_type(raw_type)
    http_type = 'http' if proxy_type == 'http' else 'https'
    return {
        http_type: "{proxy_type}://{ip}:{port}".format(
            proxy_type=proxy_type,
            ip=ip,
            port=port,
        )
    }


def request_callback(req, *args, **kwargs):
    req.start_time = datetime.now()


def response_callback(res, *args, **kwargs):
    if not isinstance(res, Exception):
        res.elapsed = datetime.now() - res.request.start_time
        result = json.loads(b64decode(res.request.path_url.split('#')[1]))
        result['Response Time'] = res.elapsed.total_seconds()

        if res.ok:
            indent = 4
            if DEBUG_MODE:
                indent = None
            LOGGER.info(json.dumps(result, indent=indent))
        else:
            result['Status Code'] = res.status_code
            LOGGER.debug(json.dumps(result))
    else:
        LOGGER.debug(
            "Exception={error}, Args={args}, Kwargs={kwargs}".format(
                error=res,
                args=args,
                kwargs=kwargs
            )
        )


def get_proxy_requests():
    for html_page in request_proxy_pages():
        for tr in html_page.xpath("//table[@id='listable']/tbody/tr"):
            raw_properties = dict(
                zip(
                    ('updates', 'ip', 'port', 'country', 'speed', 'connection time', 'type', 'anonymity'),
                    (html.tostring(td) for td in tr.iter('td'))
                )
            )
            proxy = get_proxies_dict(raw_properties['ip'], raw_properties['port'], raw_properties['type'])
            http_type, proxy_url = proxy.items()[0]
            properties = {
                'Proxy': proxy_url,
                'Country': strip_tags(raw_properties['country']),
                'Anonymity': strip_tags(raw_properties['anonymity'])
            }
            yield grequesocks.get(
                '{http_type}://httpbin.org/get#{location_hash}'.format(
                    location_hash=b64encode(json.dumps(properties)),
                    http_type=http_type
                ),
                proxies=proxy,
                verify=False,
                hooks={
                    'pre_request': request_callback,
                    'response':  response_callback
                }
            )


if __name__ == '__main__':
    arguments = docopt(__doc__, help=True, version='Proxist %s' % __version__)
    start_logging(output_file=arguments['--output'], debug=arguments['--debug'])

    DEBUG_MODE = arguments['--debug']
    grequesocks.map(get_proxy_requests(), size=50)
