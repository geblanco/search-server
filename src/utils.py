import sys, unicodedata, re

all_chars = list((chr(i) for i in range(sys.maxunicode)))
control_chars = ''.join(c for c in all_chars if unicodedata.category(c) == 'Cc')
control_char_re = re.compile('[%s]' % re.escape(control_chars))

# remove all non-ascii chars
def strip_non_ascii(text):
  return control_char_re.sub('', text)
