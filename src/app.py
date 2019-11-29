from concurrent.futures import ThreadPoolExecutor as PoolExecutor
from requests import Session, Request
from scrapper import Scrapper
from flask import Flask, request, jsonify
from gevent.pywsgi import WSGIServer
from utils import strip_non_ascii

import concurrent.futures
import argparse
import json
import math

SCRAPPER_HEADERS = None
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

def execute(link):
  scrapper = Scrapper(link, SCRAPPER_HEADERS)
  result = scrapper.scrape()
  return result

def process_items(items):
  # store indexed items to preserve rank order later
  pages = {}
  links = [i['link'] for i in items]
  with PoolExecutor(max_workers=N_WORKERS) as executor:
    futures_to_link = {
      executor.submit(execute, link): (id, link) for id, link in enumerate(links)
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
  return upper*10

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

def extract_cursor_fields_from_result(results):
  print(results['queries'])
  total_results = int(results['queries']['request'][0]['totalResults'])
  nof_results = results['queries']['request'][0]['count']
  next_page = results['queries']['nextPage']
  return total_results, nof_results, next_page

def insert_cursor_fields(results, nof_results, next_page):
  results['queries']['request'][0]['count'] = nof_results
  results['queries']['nextPage'] = next_page
  return results

def prepare_request(src_env, query, start=1):
  env= src_env.copy()
  # add search criteria
  env['params']['q'] = query
  env['params']['start'] = start
  prep_req = Request('GET', env['uri'], params=env['params'], headers=env['headers'])
  return prep_req.prepare()

def process_request(session, prep_request):
  request = session.send(prep_request)
  req_json = request.json()
  items = clean_items(req_json['items'])
  processed_items = process_items(items)
  items = pair_items_by_links(processed_items, items)
  req_json['items'] = items
  return req_json

def process_query(session, env, query, flags):
  items = []
  next_page = None
  last_result = None
  requested_nof_results = 0
  n_requests = calculate_numof_requests(flags.limit)
  # ToDo := Parallelize this (think about sync over totalResults)
  # query 10 by 10 (max allowed by google)
  print('range ', n_requests, list(range(1, n_requests*GOOGLE_NOF_RESULTS, GOOGLE_NOF_RESULTS)))
  print('range', n_requests, GOOGLE_NOF_RESULTS)
  for n in range(1, n_requests, GOOGLE_NOF_RESULTS):
    request = prepare_request(env, query, n)
    results = process_request(session, request)
    cursor = extract_cursor_fields_from_result(results)
    total_results, nof_results, next_page = cursor
    requested_nof_results += nof_results
    last_result = results
    if requested_nof_results < total_results:
      items.append(results['items'])
    else:
      break
  last_result['items'].extend(items)
  last_result = insert_cursor_fields(last_result, requested_nof_results, next_page)
  return results

def single_query(env, flags):
  if flags.url:
    print(prepare_request(env, flags.query).url)
  else:
    session = Session()
    results = process_query(session, env, flags.query, flags)
    print(json.dumps(results, indent=2))

def serve(env, flags):
  session = Session()

  app = Flask(__name__)

  @app.route('/search', methods=['GET', 'POST'])
  def search():
    data = request.get_json()
    if data is None:
      return jsonify({})
    query = data.get('query', None)
    limit = data.get('limit', flags.limit)
    if query is None:
      return jsonify({})
    return jsonify(process_query(session, env, query, flags))

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
