from concurrent.futures import ThreadPoolExecutor as PoolExecutor
from requests import Session, Request
from scrapper import Scrapper
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from utils import strip_non_ascii

import concurrent.futures
import argparse
import json
import math

SCRAPPER_HEADERS = { 'Content-Type': 'text/html; charset=utf-8'}
N_WORKERS = None
GOOGLE_NOF_RESULTS = 10

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--url', '-u', required=False, action='store_true', 
      help='Just print the url to be requested (no request at all)')
  parser.add_argument('--query', '-q', required=False, type=str,
      help='Query term')
  parser.add_argument('--limit', '-l', required=False, type=int,
      help='Number of results for the single query', default=10)
  parser.add_argument('--serve', '-s', required=False, action='store_true',
      help='Whether to serve or just do a single run')
  parser.add_argument('--port', '-p', required=False, type=int, default=8000,
      help='Port to serve')
  parser.add_argument('--config', required=False, type=str,
      default='./config.json', help='App configuration')
  parser.add_argument('--credentials', required=False, type=str,
      default='./creds.json', help='Creadentials for Customsearch')

  return parser.parse_args()

def scrapper_executor(link):
  scrapper = Scrapper(link, SCRAPPER_HEADERS)
  result = scrapper.scrap()
  return result

def process_items(items):
  # store indexed items to preserve rank order later
  pages = {}
  links = [i['link'] for i in items]
  with PoolExecutor(max_workers=N_WORKERS) as executor:
    futures_to_link = {
      executor.submit(scrapper_executor, link): (id, link) 
        for id, link in enumerate(links)
    } 
    for future in concurrent.futures.as_completed(futures_to_link):
      id, link = futures_to_link[future]
      try:
        data = future.result()
        pages[id] = data
      except Exception as exc:
        print('%r generated an exception: %s' % (link, exc))
  return [pages[id] for id in sorted(pages)]

def merge_dicts(dict_1, dict_2):
  return {**dict_1, **dict_2}

def calculate_numof_requests(limit):
  upper = math.ceil(limit /10)
  return upper

def pair_items_by_links(processed_items, items):
  ret = []
  for p_item, item in zip(processed_items, items):
    obj = merge_dicts(item, p_item)
    ret.append(obj)
  return ret

def clean_items(items):
  for item in items:
    for key in item.keys():
      item[key] = strip_non_ascii(item[key])
  return items

def extract_cursor_fields(results):
  next_page = results['queries']['nextPage']
  nof_results = results['queries']['request'][0]['count']
  return next_page, nof_results

def extract_index_from_page(page):
  return page[0]['startIndex']

def insert_cursor_fields(results, next_page, nof_results):
  results['queries']['nextPage'] = next_page
  results['queries']['request'][0]['count'] = nof_results
  results['queries']['request'][0]['startIndex'] = 1
  return results

def prepare_request(src_env, query, start=1):
  env= src_env.copy()
  # add search criteria
  env['params']['q'] = query
  env['params']['start'] = start
  prep_request = Request('GET', env['uri'], params=env['params'], headers=env['headers'])
  return prep_request.prepare()

def process_request(session, prep_request):
  request = session.send(prep_request)
  if request.status_code != 200:
    print('Failed to request', request.json(), prep_request.url,
        prep_request.headers)
    return None
  req_json = request.json()
  items = clean_items(req_json['items'])
  processed_items = process_items(items)
  items = pair_items_by_links(processed_items, items)
  req_json['items'] = items
  return req_json

def query_executor(session, env, query, start):
  request = prepare_request(env, query, start)
  results = process_request(session, request)
  return results

def process_query(session, env, query, limit):
  items = []
  last_result, next_page = None, None
  next_page_max_start, nof_results = 0, 0
  nof_requests = calculate_numof_requests(limit)
  # query 10 by 10 (max allowed by google)
  with PoolExecutor(max_workers=nof_requests) as executor:
    futures = [
      executor.submit(query_executor, session, env, query, n)
        for n in range(1, nof_requests * GOOGLE_NOF_RESULTS, GOOGLE_NOF_RESULTS)
    ]
    for future in concurrent.futures.as_completed(futures):
      try:
        data = future.result()
        items.extend(data['items'])
        page, count_results = extract_cursor_fields(data)
        nof_results += count_results
        next_page_start = extract_index_from_page(page)
        if next_page_start > next_page_max_start:
          next_page_max_start = next_page_start
          last_result = data
          next_page, _ = extract_cursor_fields(data)
      except Exception as exc:
        print('%r generated an exception' % exc)
  
  last_result['items'] = items
  last_result = insert_cursor_fields(last_result, next_page, nof_results)
  return last_result

def single_query(env, flags):
  if flags.url:
    print(prepare_request(env, flags.query).url)
  else:
    session = Session()
    results = process_query(session, env, flags.query, flags.limit)
    # print(json.dumps(results, indent=2))
    json.dump(fp=open(f'{flags.query}.json', 'w'), obj=results, indent=2, ensure_ascii=False)

def jsonify(app, data):
  return app.response_class(
    json.dumps(obj=data, indent=None, separators=(",", ":"), ensure_ascii=False),
    mimetype=app.config["JSONIFY_MIMETYPE"]
  )

def serve(env, flags):
  session = Session()

  app = Flask(__name__)

  @app.route('/search', methods=['GET', 'POST'])
  def search():
    data = request.get_json()
    if data is None:
      return jsonify({})
    query = data.get('text', None)
    limit = data.get('limit', flags.limit)
    print(f'Serving query: {query} with limit {limit}')
    if query is None:
      return jsonify({})
    return jsonify(app, process_query(session, env, query, limit))

  # serve on all interfaces with ip on given port
  http_server = WSGIServer(('0.0.0.0', flags.port), app)
  print(f'Requester serving on port {flags.port}')
  http_server.serve_forever()

def setup_env(flags):
  # get environment data
  google_env = json.load(open(flags.credentials, 'r'))
  env = json.load(open(flags.config, 'r'))
  env['params'] = merge_dicts(env['params'], google_env)
  SCRAPPER_HEADERS = env.get('scrapper_headers', {})
  N_WORKERS = env.get('n_workers', 4)
  return env

if __name__ == '__main__':
  flags = parse_args()
  env = setup_env(flags)
  print(f'{flags}')
  print(f'{env}')
  if not flags.serve and flags.query is None:
    raise ValueError('Either serve or query must be given!')
  if flags.query:
    single_query(env, flags)
  else:
    serve(env, flags)
