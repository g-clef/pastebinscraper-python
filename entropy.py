#!/usr/bin/env python3
# pylint: disable=invalid-name,missing-docstring
import json
import math
import os
import smtplib
import datetime
import pprint
import multiprocessing
import gzip
import base64
import binascii
from email.mime.text import MIMEText
import magic
import zlib
import sys
import hashlib
import time
import requests
from queue import Empty

skipTerms = ["image/png",
             "image/jpg",
             "image/jpeg",
             "image/gif",
             "-----BEGIN PGP PUBLIC KEY BLOCK-----",
             "----BEGIN PGP MESSAGE----",
             "-----BEGIN PGP MESSAGE-----",
             "-----BEGIN PGP SIGNATURE-----",
             "-----BEGIN INFOENCRYPT.COM MESSAGE-----",
             ]

saveTypes = ["application/x-dosexec",
             "application/jar",
             ]

baseDir = "/RAID/"
malwareDir = "/RAID/extracted_malware"

apikey = "***REMOVED***"

url = "https://www.virustotal.com/vtapi/v2/file/report"


stopMessage = "__stop__"
numWorkers = 10

class AnalyzerDecoder(multiprocessing.Process):
    def __init__(self, inputqueue, outputqueue):
        self.shouldStop = multiprocessing.Event()
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue
        super().__init__()

    @staticmethod
    def xor(target, key):
        response = bytearray(target)
        for counter in range(len(response)):
            response[counter] ^= key
        return bytes(response)

    @staticmethod
    def decompress(target):
        try:
            decompressed = gzip.decompress(target)
            return True, "gzip", decompressed
        except OSError:
            return False, None, None
        except zlib.error:
            return False, None, None
        except:
            return False, None, None
    @staticmethod
    def decode(target):
        success = False
        encoding = None
        try:
            newData = base64.b64decode(target)
            encoding = "base64"
            success = True
        except binascii.Error:
            newData = target
        except ValueError:
            newData = target
        return success, encoding, newData

    @staticmethod
    def identifyFileType(target):
        m = magic.Magic(flags=magic.MAGIC_MIME_TYPE)
        try:
            fileType = m.id_buffer(target)
            if fileType in saveTypes:
                return fileType
            else:
                return None
        except TypeError:
            return None
        except:
            return None

    def processFile(self, body):
        encoding = None
        compression = None
        fileType = self.identifyFileType(body)
        finalBody = body
        if fileType is None:
            (decodesuccess, encoding, decodedData) = self.decode(body)
            if decodesuccess:
                (decompresssuccess,
                 compression,
                 uncompressedData) = self.decompress(decodedData)
            else:
                (decompresssuccess,
                 compression,
                 uncompressedData) = self.decompress(body)
            if decompresssuccess:
                fileType = self.identifyFileType(uncompressedData)
                finalBody = uncompressedData
            elif decodesuccess:
                fileType = self.identifyFileType(decodedData)
                finalBody = decodedData
        return encoding, compression, fileType, finalBody

    @staticmethod
    def writeFile(fileType, key, body):
        if fileType in saveTypes:
            extentionName = fileType.replace("/", "-")
            fileHandle = open("%s/%s.%s" % (malwareDir, key, extentionName), "wb")
            fileHandle.write(body)
            fileHandle.close()

    def run(self):
        while not self.shouldStop.is_set():
            (key, entropy, data) = self.inputqueue.get()
            if key == stopMessage:
                self.shouldStop.set()
                continue
            body = data['body'].encode('utf-8')
            encoding, compression, fileType, decodedBody = self.processFile(body)
            results = []
            if fileType is None:
                for xorKey in range(255):
                    newBody = self.xor(body, xorKey)
                    newEnc, newComp, newFileType, newDecodedBody = self.processFile(newBody)
                    if newFileType is not None:
                        if encoding is None:
                            outputEncoding = "xor: %d | %s " % (xorKey, newEnc)
                        else:
                            outputEncoding = "%s | xor: %d | %s " % (encoding, xorKey, newEnc)
                        if compression is None:
                            outputCompression = "xor: %d | %s " % (xorKey, newComp)
                        else:
                            outputCompression = "%s | xor: %d | %s" % (compression, xorKey, newComp)
                        md5 = hashlib.md5()
                        md5.update(newDecodedBody)
                        md5sum = md5.hexdigest()
                        detection, permalink = getVTInfo(md5sum)
                        results.append((outputEncoding, outputCompression, newFileType, md5sum, detection, permalink),)
                        self.writeFile(newFileType, key, newDecodedBody)
            else:
                md5 = hashlib.md5()
                md5.update(decodedBody)
                md5sum = md5.hexdigest()
                detection, permalink = getVTInfo(md5sum)

                self.writeFile(fileType, key, decodedBody)
                results.append((encoding, compression, fileType, md5sum, detection, permalink),)
            if results:
                self.outputqueue.put((key,
                                      entropy,
                                      results),)


def getEntropy(data):
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        char = chr(x)
        count = data.count(char)
        p_x = float(count)/len(data)
        if p_x > 0:
            entropy += -p_x*math.log(p_x, 2)
    return entropy


def getVTInfo(md5):
    time.sleep(16)
    data = {"resource": md5, "apikey": apikey}
    response = requests.post(url, data=data)
    info = response.json()
    if "permalink" in info:
        permalink = info['permalink']
        detection = "%s/%s" % (info["positives"], info["total"])
    else:
        permalink = "File not found in VT"
        detection = "n/a"
    return permalink, detection


def findHighEntropyFiles(yesterday, findDir):

    startingDir = os.path.join(findDir,
                               str(yesterday.year),
                               str(yesterday.month),
                               str(yesterday.day))
    results = []
    for basedir, _, filelist in os.walk(startingDir):
        for filename in filelist:
            targetfile = open(os.path.join(basedir, filename))
            data = json.loads(targetfile.read())
            entropy = getEntropy(data['body'])
            if entropy >= 5.75:
                shouldSkip = False
                for test in skipTerms:
                    if test in data['body']:
                        break
                    if shouldSkip:
                        continue
                results.append((filename, entropy, data),)
    return results

def test_alive(workerList):
    for worker in workerList:
        worker.join(timeout=3)
    aliveThreads = [worker.is_alive() for worker in workerList]
    return any(aliveThreads)

def main():
    if len(sys.argv) > 1:
        age = int(sys.argv[1])
    else:
        age = 1
    yesterday = datetime.datetime.now() - datetime.timedelta(days=age)
    results = findHighEntropyFiles(yesterday, baseDir)
    print("found high entropy files")
    workers = []
    workerInputQueue = multiprocessing.Queue()
    resultsQueue = multiprocessing.Queue()
    print("starting workers")
    for _ in range(numWorkers):
        worker = AnalyzerDecoder(workerInputQueue, resultsQueue)
        worker.daemon = True
        worker.start()
        workers.append(worker)
    print("sending commands to workers")
    for (key, entropy, data) in results:
        workerInputQueue.put((key, entropy, data),)
    print("stopping workers")
    for _ in range(numWorkers):
        workerInputQueue.put((stopMessage, stopMessage, stopMessage),)

    resultsReceived = 0
    decodedResults = []
    print("getting results")
    while test_alive(workers) or resultsQueue.qsize() > 0:
        print("Getting data: queue size: %s" % resultsQueue.qsize())
        try:
            data = resultsQueue.get(timeout=3)
        except Empty:
            data = None
        if data is None:
            continue
        print("got result: %s" % str(data))
        decodedResults.append(data)
        resultsReceived += 1
    print("have results, sorting & preparing email")
    decodedResults = sorted(decodedResults, key=lambda x: x[1])
    messagebody = "Pastebin results for %s\n\n" % yesterday.strftime("%Y-%m-%d")
    messagebody += pprint.pformat(decodedResults)

    msg = MIMEText(messagebody)

    msg['Subject'] = "pastebin high entropy hits for %s" % yesterday.strftime("%Y-%m-%d")
    msg['From'] = "entropy@sparrow6.g-clef.net"
    msg['To'] = "g-clef@g-clef.net"

    server = smtplib.SMTP("localhost")
    server.send_message(msg)
    server.quit()

if __name__ == "__main__":
    main()