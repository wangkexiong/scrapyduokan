# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import Queue
import collections
import json
import logging
import os
from threading import Thread

import requests

from spiders.duokanbook import PARSE_FAILED, PARSE_GOOD, PARTIAL_GOOD


class DuokanPipeline(object):
  def __init__(self):
    self.spider = None
    self.q = Queue.Queue()
    self.bg_task = Thread(target=self.gen_report)
    self.statistics = collections.Counter()

  def open_spider(self, spider):
    spider.logger.info('Start background task...')
    if self.spider is None:
      self.spider = spider
    self.bg_task.start()

  def process_item(self, item, spider):
    if item['type'] < PARSE_FAILED[0]:
      self.q.put(item['data'])
      if item['type'] == PARSE_GOOD[0]:
        self.statistics['PARSE_GOOD'] += 1
      if item['type'] == PARTIAL_GOOD[0]:
        self.statistics['PARTIAL_GOOD'] += 1

    return item

  def close_spider(self, spider):
    self.q.put('SPIDER_CLOSED')

  def gen_report(self):
    bulk = list()
    bulk_ready = False
    report = dict()

    url = os.getenv('API_URL', None)
    token = os.getenv('API_TOKEN', None)

    if url is None or token is None:
      running = False
      logging.info('No ENV configured for remote API site and token...')
    else:
      running = True
    while running:
      item = self.q.get()
      if item == 'SPIDER_CLOSED':
        bulk_ready = True if len(bulk) > 0 else False
        running = False
      else:
        bulk.append(item)
        if len(bulk) == 10:
          bulk_ready = True

      if bulk_ready:
        report.clear()
        for x in bulk:
          report[x['book_id']] = {
            'name': x['book_name'],
            'author': x['book_author'],
            'memo': x['book_memo'],
            'del_price': x['book_del_price'],
            'price': x['book_price'],
          }

        try:
          resp = requests.post(url, data=json.dumps(report), headers={
            'Authorization': 'token %s' % token,
            'Content-Type': 'application/json',
          })
          status_code = resp.status_code
        except Exception:
          status_code = 404

        if status_code == 200:
          self.statistics['PUSHED_REMOTE'] += len(report)
        else:
          self.statistics['PUSH_FAILED'] += len(report)

        bulk_ready = False
        del bulk[:]

    for k, v in self.statistics.items():
      logging.info('%s: %s' % (k, v))


class DuokanPipeline4Failed(object):
  def __init__(self):
    self.plate = list()

  def process_item(self, item, spider):
    if item['type'] == PARSE_FAILED[0]:
      self.plate.append(item)
    return item

  def close_spider(self, spider):
    total = len(self.plate)
    if total > 0:
      spider.logger.warning('There are total %s books failed to parse...' % total)

    for item in self.plate:
      spider.logger.info('%s\n%s' % (item['reason'], item['data']))
