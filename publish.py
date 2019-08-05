#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 @File       : publish.py
 @Time       : 2019-07-01 20:58
 @Author     : Empty Chan
 @Contact    : chen19941018@gmail.com
 @Description:
 @License    : (C) Copyright 2016-2017, iFuture Corporation Limited.
"""
from mongo_db_util import find_data
import os
from datetime import datetime
from summary import summary
from constant import (DESCRIPTION, LEFT_BRACKET, RIGHT_BRACKET, COLLECTIONS, DAILY_FORMAT,
                      LEFT_ROUND_BRACKET, RIGHT_ROUND_BRACKET, HASH, GREATER_THAN, MarkdownType)


def publish():
    file_name = "./publish.{0}.md".format(datetime.now().strftime(DAILY_FORMAT))
    if os.path.exists(file_name):
        print("今天已经导出了文档了~~")
    lines = []
    datas = load_data_from_mongo()
    for category, articles in datas.items():
        # 书写大分类标题
        line = build_markdown(category, MarkdownType.CATEGORY)
        lines.append(line)
        del line
        for article in articles:
            # 标题
            line = build_markdown(
                article.get("title", None),
                MarkdownType.TITLE,
                article.get("url", None)
            )
            lines.append(line)
            del line
            # 概要
            description = article.get("description", "")
            # intro 小说
            intro = article.get("intro", "")
            if description.strip() == '':
                if intro.strip() != "":
                    # 小说内容
                    author = article.get("author", "")
                    tags = article.get("tags", "")
                    count = article.get("count", "").replace("\n", "")
                    status = article.get("status", "")
                    line = build_markdown(
                        [author, tags, intro, count, status],
                        MarkdownType.NOVEL
                    )
                    lines.append(line)
                    del line
                else:
                    text = article.get("content", None)
                    text = article.get('title') + text  # 添加 title 内容作为一个
                    summ = summary(text)
                    if summ == "":
                        summ = article.get("title", None)
                    line = build_markdown(
                        summ,
                        MarkdownType.REFERENCE
                    )
                    lines.append(line)
                    del line
            else:
                line = build_markdown(
                    description,
                    MarkdownType.REFERENCE
                )
                lines.append(line)
                del line
    # 导出Markdown文件
    with open(file_name, mode='w', encoding='utf-8') as f:
        for line in lines:
            f.write(line)
            f.write('\n')
        print("导出今日日报成功了~~")


def build_markdown(text, markdown_type: MarkdownType, url=None):
    line = None
    if markdown_type == MarkdownType.CATEGORY:
        line = "{0} {1}".format(HASH, text)
    elif markdown_type == MarkdownType.TITLE:
        line = "{0} {1}{2}{3}{4}{5}{6}".format("".join(HASH * 3), LEFT_BRACKET,
                                               text, RIGHT_BRACKET, LEFT_ROUND_BRACKET,
                                               url, RIGHT_ROUND_BRACKET)
    elif markdown_type == MarkdownType.REFERENCE:
        line = "{0} {1}{2}".format(GREATER_THAN, DESCRIPTION, text)
    elif markdown_type == MarkdownType.NOVEL:
        lines = []
        tags = ["作者", "标签", "简介", "章节总数", "状态"]
        for i, txt in enumerate(text):
            if i == 3:
                if str(txt).strip().startswith('共'):
                    pass
                else:
                    tags[i] = '章节末'
            lines.append("{0} {1}：{2}".format(GREATER_THAN, tags[i], txt))
        line = "\n\n".join(lines)
    return line


def load_data_from_mongo():
    datas = {}
    for collection, category in COLLECTIONS.items():
        items = find_data(collection, 1)
        datas.setdefault(category, items)
    return datas


if __name__ == '__main__':
    publish()