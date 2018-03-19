# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DuokanItem(scrapy.Item):
  book_id = scrapy.Field()
  book_available = scrapy.Field()
  book_name = scrapy.Field()
  book_cover = scrapy.Field()
  book_author = scrapy.Field()
  book_press = scrapy.Field()
  book_score = scrapy.Field()
  book_memo = scrapy.Field()
  book_del_price = scrapy.Field()
  book_price = scrapy.Field()
