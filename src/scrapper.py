from bs4 import BeautifulSoup
from utils import strip_non_ascii

import requests
import re

CITE_REG = re.compile('\[\w+\]')
MULTI_SPACE_REG = re.compile('\s+')
BLACKLIST = [
  'style',
  'script',
]

class Scrapper(object):
  def __init__(self, url, req_headers):
    self.url = url
    self.req_headers = req_headers

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

  def scrape(self):
    # print(f'Fetching {self.url}')
    req = requests.get(self.url, headers=self.req_headers, timeout=10)
    paragraphs = []
    if req.status_code != 200:
      pass
      # print('Nothing to scrap, code %s' % (req.status_code))
    else:
      text = req.text
      soup = BeautifulSoup(text, features="html.parser")
      # print(f'Scrapping {self.url}')
      paragraphs = self.clean_soup(soup)
    return {'link': self.url, 'paragraphs': paragraphs}

