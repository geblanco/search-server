from bs4 import BeautifulSoup
from utils import strip_non_ascii
from nltk.tokenize import sent_tokenize, word_tokenize

import requests
import re

CITE_REG = re.compile('\[\w+\]')
MULTI_SPACE_REG = re.compile('\s+')
BLACKLIST = [
  'style',
  'script',
]

class Scrapper(object):
  def __init__(self, url, req_headers, filter_kwords=None):
    self.url = url
    self.req_headers = req_headers
    self.filter_kwords = self.setup_filter_kwords(filter_kwords)

  def setup_filter_kwords(self, filter_kwords):
    kwords = None
    if filter_kwords is not None:
      kwords = filter_kwords
      if type(kwords) == str:
        kwords = [kwords]
      kwords = [str(f) for f in kwords]
    
    return kwords

  def clean_single_paragraph(self, paragraph):
    # strip non ascii chars, cites and multiple consucutive spaces
    paragraph = strip_non_ascii(paragraph)
    paragraph = re.sub(CITE_REG, '', paragraph)
    paragraph = re.sub(MULTI_SPACE_REG, ' ', paragraph)
    return paragraph.strip()

  def clean_paragraphs(self, paragraphs):
    paragraphs = [self.clean_single_paragraph(p) for p in paragraphs]
    paragraphs = [p for p in paragraphs if p != '']
    return paragraphs

  def lazy_process(self, soup):
    paragraphs = soup.find_all('p')
    paragraphs = self.clean_paragraphs([p.get_text() for p in paragraphs])
    return paragraphs

  def exhaustive_process(self, soup):
    paragraphs = [p for p in soup.find_all(text=True) \
                      if p.parent.name not in BLACKLIST and p.strip() != '']
    paragraphs = ''.join(paragraphs).split('\n')
    paragraphs = self.clean_paragraphs(paragraphs)
    return paragraphs

  def clean_soup(self, soup):
    paragraphs = self.lazy_process(soup)
    if len(paragraphs) == 0:
      paragraphs = self.exhaustive_process(soup)
    return paragraphs

  def paragraphs_to_doc(self, paragraphs):
    return '. '.join([art[:-1] if art.endswith('.') else art for art in paragraphs])

  def filter_sentence(self, sentence, keyword):
    kw_words = [w.lower() for w in word_tokenize(keyword)]
    sent_lower = sentence.lower()
    match = 0
    for word in kw_words:
      if sent_lower.find(word) != -1:
        match += 1
    return (match/len(kw_words)) >= 0.5

  def filter_sentence_by_keywords(self, sentence, keywords):
    matches = []
    for keyword in keywords:
      filt = self.filter_sentence(sentence, keyword)
      matches.append(int(filt))
    return sum(matches) == len(keywords)

  def filter_sentences_from_paragraphs(self, paragraphs, keywords):
    doc = self.paragraphs_to_doc(paragraphs)
    sentences = sent_tokenize(doc)
    return [sentence for sentence in sentences
              if self.filter_sentence_by_keywords(sentence, keywords)]

  def scrap(self):
    # print(f'Fetching {self.url}')
    req = requests.get(self.url, headers=self.req_headers, timeout=10)
    paragraphs = []
    sentences = []
    if req.status_code != 200:
      pass
      # print('Nothing to scrap, code %s' % (req.status_code))
    else:
      req.encoding = 'utf-8'
      text = req.text
      soup = BeautifulSoup(text, features="html.parser")
      # print(f'Scrapping {self.url}')
      paragraphs = self.clean_soup(soup)
      keyword = self.filter_kwords
      sentences = self.filter_sentences_from_paragraphs(paragraphs, keyword)
    return {'link': self.url, 'paragraphs': paragraphs, 'sentences': sentences}

