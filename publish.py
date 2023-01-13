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
from mongo_db_util import get_wallpaper_data, find_news, recommendation_media
import os
from datetime import datetime
from summary import summary
from constant import (DESCRIPTION, LEFT_BRACKET, RIGHT_BRACKET, COLLECTIONS,
                      DAILY_FORMAT, LEFT_ROUND_BRACKET, RIGHT_ROUND_BRACKET,
                      HASH, GREATER_THAN, MarkdownType, BAR, TITLE, TAGS, DATE,
                      TIME_FORMAT, THUMBNAIL)


def weekday_n(number):
    if number == 0:
        weekday = '周一'
    elif number == 1:
        weekday = '周二'
    elif number == 2:
        weekday = '周三'
    elif number == 3:
        weekday = '周四'
    elif number == 4:
        weekday = '周五'
    elif number == 5:
        weekday = '周六'
    else:
        weekday = '周日'
    return weekday


def build_title():
    append_line = []
    now = datetime.now()
    today = now.strftime(DAILY_FORMAT)
    weekday = weekday_n(now.weekday())
    low_today_ = now.strftime(TIME_FORMAT)
    wallpaper = "壁纸"
    wallpaper_data = get_wallpaper_data('wallpaper')
    wallpaper_url = wallpaper_data.get("url",
                                       "/images/{0}.png".format(weekday))
    append_line.append(BAR)
    append_line.append('{0}: {1}-每日随机资讯'.format(TITLE, today))
    append_line.append('{0}: 资讯'.format(TAGS))
    append_line.append('{0}: {1}'.format(THUMBNAIL, wallpaper_url))
    append_line.append('{0}: {1}'.format(DATE, low_today_))
    append_line.append(BAR)
    append_line.append('\n')
    # 壁纸
    line = build_markdown(wallpaper, MarkdownType.IMAGE, wallpaper_url)
    append_line.append(line)
    # 侵权说明
    append_line.insert(
        0,
        "> 内容均不涉及转发、复制原文等，仅提供外链和标题聚合（可视做聚合引擎且非商业不盈利），查看详情请拷贝并跳转原始链接。如有侵权，还请告知。\n"
    )
    return append_line


def publish(days=(0, )):
    file_name = "./publish.{0}.md".format(
        datetime.now().strftime(DAILY_FORMAT))
    if os.path.exists(file_name):
        print("今天已经导出了文档了~~")
    lines = []
    lines.extend(build_title())
    # 标头
    datas = load_data_from_mongo(days)

    for category, articles in datas.items():
        # 书写大分类标题
        line = build_markdown(category, MarkdownType.CATEGORY)
        lines.append(line)
        del line
        for article in articles:
            # 标题
            if article is None:
                continue
            line = build_markdown(article.get("title", None),
                                  MarkdownType.TITLE, article.get("url", None))
            lines.append(line)
            del line
            # 论文
            code = article.get("code", "")
            if code.strip() not in ('', 'None'):
                # 论文块级别
                author = article.get("author", "")
                tags = article.get("tags", "")
                description = article.get("description", "")
                description_list = description.split('\n\n')
                if len(description_list) > 0:
                    description = description_list[0]
                line = build_markdown([author, tags, code, description],
                                      MarkdownType.PAPER)
                lines.append(line)
                del line
            # 其他类型，包括新闻、小说、科技，财经
            else:
                # 概要
                description = article.get("description", "")
                # intro 小说
                intro = article.get("intro", "")
                if description.strip() in ('', 'None'):
                    if intro.strip() not in ('', 'None'):
                        # 小说内容
                        author = article.get("author", "")
                        tags = article.get("tags", "")
                        count = article.get("count", "").replace("\n", "")
                        status = article.get("status", "")
                        line = build_markdown([
                            author, tags,
                            intro.replace("\n", ""), count, status
                        ], MarkdownType.NOVEL)
                        lines.append(line)
                        del line
                    else:
                        text = article.get("content", None)
                        if text is None or text.strip() in ('', 'None'):
                            summ = article.get('title')
                        else:
                            summ = summary(article.get('title'), text)
                            if summ.strip() == "":
                                summ = article.get("title", None)
                        line = build_markdown(summ, MarkdownType.REFERENCE)
                        lines.append(line)
                        del line
                else:
                    line = build_markdown(description, MarkdownType.REFERENCE)
                    lines.append(line)
                    del line
    lines.append("> 每日夜间，随机给予一天的信息流，防止信息茧房（后续会接入更多信息源），感谢你的阅读！希望你能够从这边获取更多知识！")
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
                                               text, RIGHT_BRACKET,
                                               LEFT_ROUND_BRACKET, url,
                                               RIGHT_ROUND_BRACKET)
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
    elif markdown_type == MarkdownType.PAPER:
        lines = []
        tags = ["日期", "标签", "代码", "描述"]
        for i, txt in enumerate(text):
            lines.append("{0} {1}：{2}".format(GREATER_THAN, tags[i], txt))
            line = "\n\n".join(lines)
    elif markdown_type == MarkdownType.IMAGE:
        line = "![Bing 每日壁纸]({0})".format(url)
    return line


def load_data_from_mongo(days=(0, )):
    datas = {}
    category_list = ["news", "novel", "paper"]
    count = 1
    for category in category_list:
        if category == "news":
            datas.setdefault(COLLECTIONS[category], find_news(days))
        else:
            if category == "novel":
                count = 1
            elif category == "paper":
                count = 2
            datas.setdefault(COLLECTIONS[category],
                             recommendation_media(category, count=count))
    return datas


if __name__ == '__main__':
    publish((0, ))
