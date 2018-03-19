# -*- coding: utf-8 -*-
import logging
import re

import scrapy
from scrapy import Request

from ..items import DuokanItem

NO_BOOK_URL = [404, 'Page %s returns 404 ERROR...']

PARSE_GOOD = [1, 'Parse OK on page %s']
PARTIAL_GOOD = [2, 'Some fields are lost on page %s']

PARSE_FAILED = [100, 'Bad parser on page %s']


class DuokanbookSpider(scrapy.Spider):
  name = 'duokanbook'
  allowed_domains = ['www.duokan.com']
  start_urls = ['http://www.duokan.com/book/1']
  handle_httpstatus_list = [404]
  next_id = 1

  def __init__(self, name=None, **kwargs):
    logger = logging.getLogger('scrapy.core.scraper')
    logger.setLevel(logging.WARNING)
    super(DuokanbookSpider, self).__init__(name, **kwargs)

  def parse(self, response):
    url = response.url
    book_id = url.split('/book/')[-1]

    if not book_id.isdigit():
      return

    if response.status == 404:
      yield {
        'type': NO_BOOK_URL[0],
        'id': book_id,
        'reason': NO_BOOK_URL[1] % url
      }
      return

    book_id = long(book_id)
    book = DuokanItem()

    book_selector = response.xpath('//div[@class="desc"]')
    detail_selector = response.xpath('//div[@class="m-bookdetail j-detail"]')
    if len(book_selector) == 0 or len(detail_selector) == 0:
      yield {
        'type': PARSE_FAILED[0],
        'id': book_id,
        'reason': PARSE_FAILED[1] % url,
        'data': book,
      }
      return

    book['book_id'] = book_id
    book['book_available'] = response.xpath('//div[@class="desc"]//div[@class="act j-act f-cb"]//a/text()').extract()
    book['book_cover'] = response.xpath(
        '//div[@class="m-bookdata j-bookdata f-cb"]//img/@src').extract_first()
    book['book_name'] = response.xpath('//div[@class="desc"]//h3/text()').extract_first()
    book['book_author'] = response.xpath('//div[@class="desc"]//td[@class="author"]/node()/text()').extract_first()
    book['book_press'] = response.xpath('//div[@class="desc"]//td[@class="published"]/node()/text()').extract_first()
    book['book_score'] = response.xpath('//div[@class="desc"]//em[@class="score"]/text()').extract_first()
    book['book_memo'] = response.xpath(
        '//div[@class="m-bookdetail j-detail"]//article[@class="intro"]/node()').extract()

    book['book_price'] = response.xpath('//div[@class="desc"]//div[@class="price"]//em/text()').extract_first()
    book['book_del_price'] = response.xpath(
        u'//div[@class="desc"]//div[@class="price"]//i[text()="原价"]/node()/text()').extract_first()

    wash_result = self.wash_data(book)
    if wash_result[0] < PARSE_FAILED[0]:
      if book_id >= self.next_id:
        self.next_id += 10
        yield Request(url=url.rstrip(str(book_id)) + str(self.next_id))

    yield {
      'type': wash_result[0],
      'id': book_id,
      'reason': wash_result[1] % url,
      'data': book,
    }

  @classmethod
  def wash_data(cls, book):
    partial_failed = False

    if book['book_name'] is None:
      return PARSE_FAILED
    if len(book['book_available']) == 0:
      return PARSE_FAILED
    elif u'暂未上架' in book['book_available']:
      book['book_available'] = False
    else:
      book['book_available'] = True

    float_re = re.compile('([0-9]+([.][0-9]*)?|[.][0-9]+)')
    if book['book_price'] is None:
      return PARSE_FAILED
    if book['book_price'] == u'免费':
      book['book_price'] = 0.0
    else:
      search = float_re.search(book['book_price'])
      if search:
        book['book_price'] = float(search.group())
      else:
        return PARSE_FAILED
    if book['book_del_price'] is None:
      book['book_del_price'] = book['book_price']
    else:
      search = float_re.search(book['book_del_price'])
      if search:
        book['book_del_price'] = float(search.group())
      else:
        return PARSE_FAILED

    if book['book_author'] is None:
      book['book_author'] = u'佚名'
      partial_failed = True
    if book['book_press'] is None:
      partial_failed = True
    if book['book_score'] is None:
      partial_failed = True
    if book['book_memo'] is None:
      partial_failed = True
    else:
      book['book_memo'] = ''.join(book['book_memo'])
    if book['book_cover'] is None:
      partial_failed = True
    else:
      book['book_cover'] = book['book_cover'].split('!')[0]

    if partial_failed:
      return PARTIAL_GOOD
    else:
      return PARSE_GOOD
