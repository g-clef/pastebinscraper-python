#!/usr/bin/env python3
# pylint: disable=invalid-name

import configparser
import collections
import datetime
import json
import time
import base64
import urllib.parse
import os
import re
import smtplib
import warnings
from email.mime.text import MIMEText
from queue import Empty
import multiprocessing
from multiprocessing import Process
from multiprocessing import Queue
import requests
import elasticsearch
import elasticsearch.helpers
import urllib3.exceptions


class Lister(Process):
    def __init__(self, api_key, outputqueue, runonce=False, limit=250):
        self.api_key = api_key
        self.outputqueue = outputqueue
        self.done = multiprocessing.Event()
        self.runonce = runonce
        self.recentIDs = collections.deque()
        self.limit = limit
        super().__init__()

    def addToHistory(self, entryID):
        self.recentIDs.append(entryID)
        while len(self.recentIDs) > (self.limit*5):
            self.recentIDs.popleft()


    def run(self):
        args = {"limit": self.limit,
                "api_dev_key": self.api_key,
                }
        baseURL = "http://scrape.pastebin.com/api_scraping.php" + "?" + urllib.parse.urlencode(args)
        while not self.done.is_set():
            starttime = time.time()
            success = False
            while not success:
                try:
                    response = requests.get(baseURL, timeout=5)
                    success = True
                    try:
                        data = response.json()
                    except:
                        print("Error decoding json: {}".format(response.content))
                        continue
                    if data:
                        for entry in data:
                            if 'key' not in entry or not entry['key']:
                                print("problem with paste missing key: {}".format(entry))
                                continue
                            if entry['key'] in self.recentIDs:
                                # add some check here that we do have some overlap. Want to be
                                # able to detect when more are coming in each minute than we're pulling
                                continue
                            else:
                                self.outputqueue.put(entry)
                                self.addToHistory(entry['key'])
                except:
                    print("other exception getting past list.")
                    time.sleep(1)
                    continue
            endtime = time.time()
            totaltime = endtime - starttime
            if 0 < totaltime <  60:
                time.sleep(60 - totaltime)

    def shutdown(self):
        self.done.set()


class Fetcher(Process):
    def __init__(self, inputqueue, esqueue, filequeue, testerqueue):
        self.inputqueue = inputqueue
        self.esqueue = esqueue
        self.filequeue = filequeue
        self.testerqueue = testerqueue
        self.done = multiprocessing.Event()
        super().__init__()

    def run(self):
        while not self.done.is_set():
            try:
                data = self.inputqueue.get(timeout=3)
            except Empty:
                data = None
            response = None
            if data is not None:
                success = False
                if "scrape_url" not in data:
                    print("scrape_url missing in data: {}".format(data))
                    continue
                while not success:
                    try:
                        response = requests.get(data['scrape_url'])
                        success = True
                    except:
                        time.sleep(1)
                        continue
                body = ""
                try:
                    if response is not None:
                        body = response.content.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        if response is not None:
                            body = base64.urlsafe_b64encode(response.content).decode()
                    except:
                        print("problem decoding paste. body: {}".format(response.content))
                        continue
                except:
                    print("Problem decoding paste. body: {}".format(data['key']))
                    continue
                data['body'] = body
                data['source'] = "pastebin"
                self.esqueue.put(data)
                self.filequeue.put(data)
                self.testerqueue.put(data)

    def shutdown(self):
        self.done.set()

class Tester(Process):
    def __init__(self, apiURL, inputqueue, refresh_interval=60):
        self.apiURL = apiURL
        self.inputqueue = inputqueue
        self.refresh_interval = refresh_interval
        self.done = multiprocessing.Event()
        super().__init__()

    def shutdown(self):
        self.done.set()

    def refresh_regexes(self):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(self.apiURL, verify=False)
            data = response.json()
        except:
            return []
        regexes = []
        if "objects" in data:
            for entry in data['objects']:
                reg = {"owner": entry['owner'],
                       "owner_email": entry['owner_email'],
                       }
                if entry['author']:
                    reg['author'] = re.compile(entry['author'])
                    reg['author_regex'] = entry['author']
                if entry['body']:
                    reg['body'] = re.compile(entry['body'])
                    reg['body_regex'] = entry['body']
                regexes.append(reg)
        return regexes

    @staticmethod
    def send_email(reg, data):
        body = "Hello, %s,\n\nThis is a message from the ieatpaste patten matcher.\n\n" % reg['owner']
        pattern = ""
        if "author_regex" in reg and reg['author_regex']:
            pattern += "author: %s " % reg['author_regex']
        if 'body_regex' in reg and reg['body_regex']:
            pattern += "body: %s " % reg['body_regex']
        body += "One of following patterns matched the message included below: %s" % pattern
        body += "\n\nThe paste:\n%s" % str(data)
        msg = MIMEText(body)
        msg['Subject'] = "paste pattern match for paste: %s" % data['key']
        msg['From'] = "paste@ieatpaste.accessviolation.org"
        msg['To'] = reg['owner_email']
        server = smtplib.SMTP("localhost")
        try:
            server.send_message(msg)
            server.quit()
        except:
            print("Error sending email.")

    def run(self):
        regexes = self.refresh_regexes()
        last_refresh = time.time()
        while not self.done.is_set():
            try:
                data = self.inputqueue.get(timeout=3)
            except Empty:
                data = None
            if data is not None:
                hit = False
                for reg in regexes:
                    if "author" in reg and reg['author']:
                        if reg['author'].search(data['user']):
                            hit = True
                    if "body" in reg and reg['body']:
                        if reg['body'].search(data['body']):
                            hit = True
                    if hit:
                        self.send_email(reg, data)
                        break
            now = time.time()
            if (now - last_refresh) > self.refresh_interval:
                regexes = self.refresh_regexes()
                last_refresh = now

class ESWriter(Process):
    def __init__(self, ESHost, doc_type, indexbase, inputqueue):
        self.ESHost = ESHost
        self.doc_type = doc_type
        self.indexbase = indexbase
        self.inputqueue = inputqueue
        self.done = multiprocessing.Event()
        super().__init__()

    def run(self):
        es = elasticsearch.Elasticsearch(self.ESHost)
        while not self.done.is_set():
            try:
                data = self.inputqueue.get(timeout=3)
            except Empty:
                data = None
            if data is not None:
                try:
                    timestamp = datetime.datetime.fromtimestamp(data['date'])
                except:
                    timestamp = datetime.datetime.now()
                index = self.indexbase + timestamp.strftime("-%Y-%m-%d")
                try:
                    data['_index'] = index
                    data['_type'] = self.doc_type
                    elasticsearch.helpers.bulk(es, actions=[data], chunk_size=100)
                except:
                    print("Error sending data to ES.")
                    continue

    def shutdown(self):
        self.done.set()


class FileWriter(Process):
    def __init__(self, inputqueue, baseDir):
        self.baseDir = baseDir
        self.inputqueue = inputqueue
        self.done = multiprocessing.Event()
        super().__init__()

    def run(self):
        while not self.done.is_set():
            try:
                data = self.inputqueue.get(timeout=3)
            except:
                data = None
            if data is not None:
                try:
                    timestamp = datetime.datetime.fromtimestamp(data['date'])
                except:
                    timestamp = datetime.datetime.now()
                yeardirname = os.path.join(self.baseDir, str(timestamp.year))
                monthdirname = os.path.join(yeardirname, str(timestamp.month))
                daydirname = os.path.join(monthdirname, str(timestamp.day))
                if not os.path.isdir(daydirname):
                    if not os.path.isdir(yeardirname):
                        os.mkdir(yeardirname)
                    if not os.path.isdir(monthdirname):
                        os.mkdir(monthdirname)
                    if not os.path.isdir(daydirname):
                        os.mkdir(daydirname)
                if not data['key']:
                    print("Error with paste: has no key: %s" % str(data))
                    continue
                fileHandle = open(os.path.join(daydirname, data['key']), "w")
                try:
                    fileHandle.write(json.dumps(data))
                except:
                    try:
                        fileHandle.write(base64.b64encode(str(data)))
                    except:
                        print("Error writing file to disk")
                fileHandle.close()

def main():
    configfile = configparser.ConfigParser()
    configfile.read("pastebinscrapev2.conf")
    api_key = configfile.get("Pastebin", "key")
    index = configfile.get("Elasticsearch", "index")
    doc_type = configfile.get("Elasticsearch", "doc_type")
    host = configfile.get("Elasticsearch", "host")
    baseDir = configfile.get("Archive", "path")
    num_workers = int(configfile.get("Service", "num_workers"))
    regexURL = configfile.get("Regexes", "url")
    taskqueue = Queue()
    esqueue = Queue()
    filequeue = Queue()
    testerqueue = Queue()
    lister = Lister(api_key, taskqueue)
    lister.daemon = True
    lister.start()
    fetchworkers = []
    for _ in range(num_workers):
        new_worker = Fetcher(taskqueue, esqueue, filequeue, testerqueue)
        new_worker.daemon = True
        new_worker.start()
        fetchworkers.append(new_worker)
    eswriter = ESWriter(host, doc_type, index, esqueue)
    eswriter.daemon = True
    eswriter.start()
    filewriter = FileWriter(filequeue, baseDir)
    filewriter.daemon = True
    filewriter.start()
    testworkers = []
    for _ in range(num_workers):
        new_worker = Tester(regexURL, testerqueue)
        new_worker.daemon = True
        new_worker.start()
        testworkers.append(new_worker)
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()