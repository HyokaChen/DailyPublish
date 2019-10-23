#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 @File       : summary.py
 @Time       : 2019-07-01 20:58
 @Author     : Empty Chan
 @Contact    : chen19941018@gmail.com
 @Description:
 @License    : (C) Copyright 2016-2017, iFuture Corporation Limited.
"""
import re
import numpy as np
import networkx as nx
from tok import sent_tokenize
import jieba.analyse
# import jieba.posseg
import pkuseg
from bert_serving.client import BertClient
from langid.langid import LanguageIdentifier, model
from constant import (CHINESE_BERT_SERVICE, MULTI_BERT_SERVICE,
                      FIRST_SECTION, FIRST_SENTENCE, LAST_SECTION,
                      LAST_SENTENCE)
from sklearn.metrics.pairwise import cosine_similarity
chinese_bc = BertClient(ip=CHINESE_BERT_SERVICE)
# multi_bc = BertClient(ip=MULTI_BERT_SERVICE)
multi_bc = BertClient(ip=CHINESE_BERT_SERVICE)
chinese_re_sentences = re.compile('([﹒﹔﹖﹗．；。！？]["’”」』]{0,2}|：(?=["‘“「『]{1,2}|$))')
IDENTIFIER = LanguageIdentifier.from_modelstring(model, norm_probs=True)
chinese_punc = re.compile(r'[；，：、]')
english_punc = re.compile(r'[:,;]')


def check_contain_english(check_str):
    resp = IDENTIFIER.classify(check_str)
    if resp[0] == 'zh':
        return False
    elif resp[0] == 'en':
        return True
    return None


def word_vector(sentence, flag):
    if not flag:
        code = chinese_bc.encode([sentence])[0]
    else:
        code = multi_bc.encode([sentence])[0]
    return code


def cut_doc2sentences(text):
    slist = []
    is_english = False
    section_count = 0
    all_sections = text.split('\n')
    for section in all_sections:
        if section.strip() == '':
            continue
        if not check_contain_english(section):
            sentence_count = 0
            # 对文章位置进行标注，通过mark列表，标注出是否是第一段、尾段、第一句、最后一句
            all_chinese_sentences = chinese_re_sentences.split(section)
            for chinese_sentences in all_chinese_sentences:
                if chinese_re_sentences.match(chinese_sentences) and slist:
                    slist[-1]['text'] += chinese_sentences
                else:
                    row = {
                        'text': '',
                        'mark': []
                    }
                    sentence = chinese_sentences.replace('\n', '').strip()
                    if sentence != '':
                        row['text'] = sentence
                        if section_count == 0:
                            row['mark'].append(FIRST_SECTION)
                        elif section_count == len(all_sections) - 1:
                            row['mark'].append(LAST_SECTION)
                        if sentence_count == 0:
                            row['mark'].append(FIRST_SENTENCE)
                        elif sentence_count == len(all_chinese_sentences) - 1:
                            row['mark'].append(LAST_SENTENCE)
                        slist.append(row)
                        print(row)
                    sentence_count += 1
        else:
            temp_s = section.replace('\n', '').strip()
            if temp_s != '':
                all_english_sentence = sent_tokenize(temp_s)
                sentence_count = 0
                for words in all_english_sentence:
                    row = {
                        'text': '',
                        'mark': []
                    }
                    sentence = ' '.join(words).replace('\n', '').strip()
                    if sentence != '':
                        row['text'] = sentence
                        if section_count == 0:
                            row['mark'].append(FIRST_SECTION)
                        elif section_count == len(all_sections) - 1:
                            row['mark'].append(LAST_SECTION)
                        if sentence_count == 0:
                            row['mark'].append(FIRST_SENTENCE)
                        elif sentence_count == len(all_english_sentence) - 1:
                            row['mark'].append(LAST_SENTENCE)
                        slist.append(row)
                        print(row)
                    sentence_count += 1
                is_english = True
        section_count += 1
    return slist, is_english


def create_cosine_matrix(sentences_count, word_vector_map):
    similar_matrix = np.zeros((sentences_count, sentences_count))
    for i in range(sentences_count):
        for j in range(sentences_count):
            if i != j:
                cosine_similar = cosine_similarity(
                    np.array(word_vector_map[i]).reshape((1, -1)),
                    np.array(word_vector_map[j]).reshape((1, -1))
                )
                # print(cosine_similar)
                similar_matrix[i][j] = cosine_similar[0, 0]
    return similar_matrix


def page_rank(sentences, similar_matrix, top_k, flag):
    weight_matrix = np.array([s['weight'] for s in sentences]).reshape([-1, 1])
    end_matrix = np.multiply(weight_matrix, similar_matrix)
    nx_graph = nx.from_numpy_matrix(end_matrix)
    scores = nx.pagerank(nx_graph)
    print(scores)
    ranked_sentences = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if top_k > len(ranked_sentences):
        top_k = len(ranked_sentences)
    for i in range(top_k):
        print(ranked_sentences[i])
        sentence = sentences[ranked_sentences[i][0]]['text']
        end_char = sentence[-1]
        if not flag:
            if chinese_punc.match(end_char):
                sentence = '{0}。'.format(str(sentence).rstrip(sentence[-1]))
            elif end_char in ['. ', '。', '!', '?', '！', '？', '.']:
                pass
            elif end_char in (';', '；', '"', '”'):
                sentence = sentence.replace(end_char, "。")
            else:
                sentence += '。'
        else:
            if english_punc.match(end_char):
                sentence = '{0}. '.format(str(sentence).rstrip(sentence[-1]))
            elif end_char in ['. ', '。', '!', '?', '！', '？', '.', '-']:
                pass
            else:
                sentence += '. '
        yield (ranked_sentences[i][0], sentence)


def calc_keywords(title, text):
    # 计算tf-idfs，取出排名靠前的20个词
    words_best = []
    words_best = words_best + jieba.analyse.extract_tags(text, topK=20)
    # 提取第一段的关键词
    parts = text.lstrip().split("\n")
    first_part = ""
    if len(parts) >= 1:
        first_part = parts[0]
    words_best = words_best + jieba.analyse.extract_tags(first_part, topK=5)
    # 提取title中的关键词
    words_best = words_best + jieba.analyse.extract_tags(title, topK=3)
    # 将结果合并成一个句子，并进行分词
    text = ""
    for w in words_best:
        text = text + " " + w
    # 计算词性，提取名词和动词
    # words = jieba.posseg.cut(text)
    seg = pkuseg.pkuseg(postag=True)
    words = seg.cut(text)
    keywords = list()
    for flag, word in words:
        if flag.find('n') >= 0 or flag.find('v') >= 0:
            if len(word) > 1:
                keywords.append(word)
    # 保留前20个关键词
    keywords = jieba.analyse.extract_tags(" ".join(keywords), topK=20)
    keywords = list(set(keywords))
    return keywords


def calc_sentence_weight_by_keywords(keywords, sentences):
    # 计算句子的关键词权重
    for sentence in sentences:
        sentence["weight_keywords"] = 0
    for keyword in keywords:
        for sentence in sentences:
            keyword_count = sentence["text"].count(keyword)
            sentence["weight_keywords"] = sentence["weight_keywords"] + keyword_count


def calc_position_weight(sentences):
    for sentence in sentences:
        mark = sentence["mark"]
        weight_pos = 0
        if FIRST_SECTION in mark:
            weight_pos = weight_pos + 4
        if FIRST_SENTENCE in mark:
            weight_pos = weight_pos + 3
        if LAST_SECTION in mark:
            weight_pos = weight_pos + 2
        if LAST_SECTION in mark:
            weight_pos = weight_pos + 1
        sentence["weight_position"] = weight_pos


def summary(title, text):
    one_100 = text.replace("\r\n", "  ")[0: 100]
    end_char = one_100[-1]
    if end_char in ('. ', '。', '!', '?', '！', '？', '.'):
        result = '{0}......'.format(str(one_100).rstrip(end_char))
    else:
        result = '{0}......'.format(str(one_100))
    print("前 100 个字....")
    print(result)
    return result
    ## 不使用 text rank，使用开头一百个字
    # keywords = calc_keywords(title, text)
    # sentences, flag = cut_doc2sentences(text)
    # if len(sentences) == 0:
    #     return ""
    # word_vector_map = []
    # for sentence in sentences:
    #     word_vector_map.append(
    #         word_vector(sentence['text'], flag)
    #     )
    # calc_sentence_weight_by_keywords(keywords, sentences)
    # calc_position_weight(sentences)
    # # 计算整体的权重
    # for sentence in sentences:
    #     sentence["weight"] = sentence["weight_position"] + sentence["weight_keywords"]
    # similar_matrix = create_cosine_matrix(len(sentences), word_vector_map=word_vector_map)
    # top_k_sentences = []
    # del word_vector_map
    # ranked_sentences = page_rank(sentences, similar_matrix, 3, flag)
    # del sentences
    # for ranked_sentence in ranked_sentences:
    #     top_k_sentences.append(ranked_sentence)
    # del ranked_sentences
    # summary_content_sentences = sorted(top_k_sentences, key=lambda item: item[0])
    # del top_k_sentences
    # return "".join((sent[1] for sent in summary_content_sentences))


if __name__ == '__main__':
    doc = """
    news comes on days, today is best day in the world.\n 而是和你结婚，我要娶你。娶到手后，二人的婚姻还没有维持两年，宋仲基便单方面的宣布将要与婚宋慧乔离婚。在现实面前，曾经的海誓山盟如今则变得是多么的脆弱不堪一击。\n\n            \n宋仲基高调宣布离婚后，宋慧乔便立即发布声明公关离婚，表示是因为性格不合导致离婚。后来又被爆料宋慧乔方出轨朴宝剑，最后宋仲基辟谣。\n有趣的是，无论外界怎么刺激，前双宋夫妻就是不说原因，毕竟这为他们赚足了眼球和流量。宣布离婚后，前双宋夫妻一直没有露面，他们的近况，这让大家就更好奇了。\n\n            \n\n            \n根据韩国媒体报道，韩国电影《胜利号》已经在3号开机，宋仲基将会从7月5号进入剧组进行拍摄。这也是在离婚风波后首次恢复工作。\n\n            \n\n            \n\n            \n不受离婚风波影响， 照常进行工作的还有宋慧乔。按照先前的计划，宋慧乔将会在7月6日前往三亚参加活动，将以代言人的身份现身。\n\n            \n宋慧乔6号开工，这时候宋仲基宣布5号提前宋慧乔一天开工，不知道是不是在怄气呢？\n心有多大，舞台就有多大。若是对于普通人来说，家里人在闹离婚，还能够不耽误工作，这也是没谁了。双宋前夫妻如今在韩国和内地都有着极高的人气，事业有成经济独立，或许是这样的原因让他们都不太依赖于彼此。\n\n            \n如今在看现在的舆论，有媒体爆宋慧乔的黑料，说她天价片酬还耍大牌，而也有媒体爆宋仲基说谎成瘾，婚前和婚后不一样。后来又有知情人士爆宋慧乔工作压力大身材消瘦，而宋仲基则是脱发严重。给外界的感觉便是二人目前处于一个互黑比惨的境地。\n\n            \n对于婚变，我们一直坚持好聚好散的原则。如今一个离婚弄的路人皆知，还没有任何回应，真是充满了玄幻色彩。
    """
    print(summary('宋仲基不受离婚影响，5号进剧组复工拍戏，宋慧乔也即将现身复工。', doc))