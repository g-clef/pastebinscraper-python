#!/usr/bin/env python3

import elasticsearch
import configparser

properties = { "paste": {"properties":{
    "user": {"type":"string",
             "index": "analyzed",
             "analyzer": "keyword"
             },
    "syntax": {"type": "string",
               "index": "analyzed",
               "analyzer": "keyword"
               },
    "expire": {"type": "string",
               "store": "no"
               },
    "scrape_url": {"type": "string",
                   "store": "no",
                   "index":"not_analyzed"
                   },
    "title": {"type": "string"},
    "date": {"type": "date"},
    "full_url": {"type": "string",
                 "store": "no",
                 "index": "not_analyzed"
                 },
    "body": {"type": "string"},
    "key": {"type": "string",
            "index": "analyzed",
            "analyzer": "keyword"
            },
    "size": {"type": "integer"},
    "source": {"type": "string",
               "store": "no",
               "index": "not_analyzed",
               }
}
}
}


template = {"template" : "paste-*",
            "mappings": properties,
            "aliases": { "paste": {}  }
            }

if __name__ == "__main__":
    configfile = configparser.ConfigParser()
    configfile.read("pastebinscrapev2.conf")

    host = configfile.get("Elasticsearch", "host")
    es = elasticsearch.Elasticsearch(host)
    es.indices.put_template(name="paste-template", body=template, order=0)
    # es.indices.put_mapping(index="pastepercolates", body=properties, doc_type="paste")
    # es.indices.put_alias(index=["pastebin-*"], name="paste")