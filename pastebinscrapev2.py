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
from queue import Empty
import multiprocessing
from multiprocessing import Process
from multiprocessing import Queue
import requests


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
                    except Exception:
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
                except Exception:
                    print("other exception getting past list.")
                    time.sleep(1)
                    continue
            endtime = time.time()
            totaltime = endtime - starttime
            if 0 < totaltime < 60:
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
                    except Exception:
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
                    except Exception:
                        print("problem decoding paste. body: {}".format(response.content))
                        continue
                except Exception:
                    print("Problem decoding paste. body: {}".format(data['key']))
                    continue
                data['body'] = body
                data['source'] = "pastebin"
                self.esqueue.put(data)
                self.filequeue.put(data)
                self.testerqueue.put(data)

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
            except Exception:
                data = None
            if data is not None:
                try:
                    timestamp = datetime.datetime.fromtimestamp(data['date'])
                except Exception:
                    timestamp = datetime.datetime.now()
                daydirname = os.path.join(self.baseDir,
                                          str(timestamp.year),
                                          str(timestamp.month),
                                          str(timestamp.day))
                if not os.path.isdir(daydirname):
                    os.makedirs(daydirname)
                if not data['key']:
                    print("Error with paste: has no key: %s" % str(data))
                    continue
                fileHandle = open(os.path.join(daydirname, data['key']), "w")
                try:
                    fileHandle.write(json.dumps(data))
                except Exception:
                    try:
                        fileHandle.write(base64.b64encode(str(data)).decode("utf-8"))
                    except Exception:
                        print("Error writing file to disk")
                fileHandle.close()


def main():
    configfile = configparser.ConfigParser()
    configfile.read("pastebinscrapev2.conf")
    api_key = configfile.get("Pastebin", "key", vars=os.environ)
    baseDir = configfile.get("Archive", "path")
    num_workers = int(configfile.get("Service", "num_workers"))
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

    filewriter = FileWriter(filequeue, baseDir)
    filewriter.daemon = True
    filewriter.start()
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
