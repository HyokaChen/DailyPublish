#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 @File       : mongo_db_util.py
 @Time       : 2019-07-01 21:00
 @Author     : Empty Chan
 @Contact    : chen19941018@gmail.com
 @Description:
 @License    : (C) Copyright 2016-2017, iFuture Corporation Limited.
"""
from pymongo import MongoClient, DESCENDING
import datetime
import redis
from constant import (MONGODB_HOST, MONGODB_PORT, REDIS_PWD, DAILY_FORMAT, PUBLISHED,
                      MONGODB_PWD, MONGODB_USER, REDIS_HOST, REDIS_PORT, PROD_MONGODB_USER,
                      PROD_MONGODB_PWD, PROD_MONGODB_HOST, PROD_MONGODB_PORT)

TODAY = datetime.datetime.now().strftime(DAILY_FORMAT)
rdb_publish = redis.StrictRedis().from_url("redis://:{0}@{1}:{2}/3".format(
    REDIS_PWD, REDIS_HOST, REDIS_PORT
))

client = MongoClient(host=MONGODB_HOST, port=MONGODB_PORT)
if MONGODB_USER != '':
    client.data_db.authenticate(MONGODB_USER, MONGODB_PWD, mechanism='SCRAM-SHA-1')
mdb = client.data_db

client = MongoClient(host=PROD_MONGODB_HOST, port=PROD_MONGODB_PORT)
if PROD_MONGODB_USER != '':
   client.data_db.authenticate(PROD_MONGODB_USER, PROD_MONGODB_PWD, mechanism='SCRAM-SHA-1')
prod_mdb = client.data_db


def mongo_map(name):
    """
    mongo db的映射
    :param name: 创建的mongo集合名称
    :return: mongo集合，类似于表格
    """
    return eval('mdb.{0}'.format(name))


def get_entertainment_data(collections, days=(0, )):
    day_regexs = []
    for day in days:
        cur_day = datetime.datetime.now() + datetime.timedelta(days=day)
        cur_day_str = cur_day.strftime(DAILY_FORMAT)
        day_regexs.append({"news_time": {'$regex': "{0}".format(cur_day_str)}})
    one_count = 5
    for collection in collections:
        pipeline = [
            {"$match":
                {"$or": day_regexs}
             },
            {"$sample": {"size": one_count}}
        ]
        # site_items = mdb[collection].aggregate(pipeline, allowDiskUse=True)
        site_items = prod_mdb[collection].aggregate(pipeline, allowDiskUse=True)
        yield from site_items


def get_wallpaper_data(collection):
    _id_list = rdb_publish.spop(PUBLISHED.format(collection), count=1)
    for _id in _id_list:
        yield mdb[collection].find_one({"_id": _id.decode('utf-8')})


def find_data(collection, days=(0, )):
    if collection == "novel":
        _id_list = rdb_publish.spop(PUBLISHED.format(collection), count=2)
        for _id in _id_list:
            yield mdb[collection].find_one({"_id": _id.decode('utf-8')})
        ## 老方法
        # pipeline = [
        #     {"$sample": {"size": 1}}
        #     # {"$limit": 10},
        # ]
    elif collection == "paper":
        _id_list = rdb_publish.spop(PUBLISHED.format(collection), count=2)
        for _id in _id_list:
            yield mdb[collection].find_one({"_id": _id.decode('utf-8')})
    else:
        # regex = "{0}.*".format(TODAY)
        # if days == 1:
        #     pipeline = [
        #         {"$match": {"news_time": {'$regex': regex}}},
        #         # {"$sort": {"news_time": DESCENDING}},
        #         {"$sample": {"size": 10}}
        #         # {"$limit": 10},
        #     ]
        # else:
        day_regexs = []
        for day in days:
            cur_day = datetime.datetime.now() + datetime.timedelta(days=day)
            cur_day_str = cur_day.strftime(DAILY_FORMAT)
            day_regexs.append({"news_time": {'$regex': "{0}".format(cur_day_str)}})
        if collection == 'animation':
            one_count = 2
            for site in ['acgmh', 'dmzj', 'tencent']:
                pipeline = [
                    {"$match":
                        {"$and": [
                            {"$or": day_regexs},
                            {"site": site}
                        ]}
                    },
                    {"$sample": {"size": one_count}}
                ]
                site_items = mdb[collection].aggregate(pipeline, allowDiskUse=True)
                one_count += 2
                yield from site_items
        else:
            one_count = 3
            for site in ['ctolib', 'tuicool', 'ithome']:
                pipeline = [
                    {"$match":
                        {"$and": [
                            {"$or": day_regexs},
                            {"site": site}
                        ]}
                    },
                    {"$sample": {"size": one_count}}
                ]
                site_items = mdb[collection].aggregate(pipeline, allowDiskUse=True)
                one_count *= 2
                yield from site_items


def insert_data(collection, data):
    _id = data.get('_id', None)
    if not _id:
        raise Exception('data not have _id field!!')
    if not mdb[collection].find_one({'_id': _id}):
        mdb[collection].insert_one(data)
        return True
    return False


if __name__ == '__main__':
    results = find_data("animation")
    for item in results:
        print(item.get('title'))
