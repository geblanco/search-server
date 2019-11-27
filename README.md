# What is this?
A dockerized server that extracts the content of all results from google customsearch engine (you need credentials for google customsearch).

Example credentials:
```json
{
  "key": "<Your API_KEY>",
  "cx": "<Your SEARCH_ENGINE_ID>"
}
```

# Create docker instance for serving
To create the docker image, issue:

```bash
docker build -t search-server:latest .
```

To start/stop the server just call `./start.sh`/`./stop.sh`

# API
The server responds to get requests on `/search` route, params:
```json
{
  "query": "str <The term to search>",
  "limit": "int <The number of search results (unimplemented)"
}
```

Example call:
```bash
curl -X GET --header 'Content-Type: application/json' -d '{"query": "Snow Leopard"}' 'localhost:8000/search'
```

Example response:
```json
{
  "items": [
    {
      "link": "https://en.wikipedia.org/wiki/Snow_leopard",
      "paragraphs": [
        "The snow leopard (Panthera uncia), ...",
        "..."
      ],
      "snippet": "The snow leopard (Panthera uncia), also known as the ounce, is a large cat \nnative to the mountain ranges of Central and South Asia. It is listed as Vulnerable \non ...",
      "title": "Snow leopard - Wikipedia"
    },
    {
      "link": "https://www.snowleopard.org/",
      "paragraphs": [
        "Snow Leopard Trust",
        "Learn more about our work...",
        "...",
      ],
      "snippet": "The Snow Leopard Trust aims to better understand the endangered snow \nleopard, and protect the cat in partnership with communities that share its habitat.",
      "title": "Snow Leopard Trust: Home"
    },
    ...
  ],
  "kind": "customsearch#search",
  "queries": {
    "nextPage": [
      {
        "count": 10,
        "inputEncoding": "utf8",
        "outputEncoding": "utf8",
        "safe": "off",
        "searchTerms": "Snow Leopard",
        "startIndex": 11,
        "title": "Google Custom Search - Snow Leopard",
        "totalResults": "61300000"
      }
    ],
    "request": [
      {
        "count": 10,
        "inputEncoding": "utf8",
        "outputEncoding": "utf8",
        "safe": "off",
        "searchTerms": "Snow Leopard",
        "startIndex": 1,
        "title": "Google Custom Search - Snow Leopard",
        "totalResults": "61300000"
      }
    ]
  }
}
```

## Referencess:
https://developers.google.com/custom-search/v1/introduction

https://developers.google.com/custom-search/v1/using_rest

## Querying google by hand:
https://www.googleapis.com/customsearch/v1?key=API_KEY&cx=SEARCH_ENGINE_UID&q=QUERY
