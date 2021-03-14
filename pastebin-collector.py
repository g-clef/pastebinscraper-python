# plan:
# walk over entire tree
# for each folder:
#     check if corresponding file in path exists in malware path, create if ot
#     check if zipfile exists in folder. open if so, create if not
#     for each file in folder:
#         check if file already in archive, add if not
#         check file type, if in set of things to add to set:
#             add to malware archive zip
#     for each file in folder again:
#         check if file in archive: if so, remove
#     if any changes made to malware zip file, submit path to analyzer.

import configparser
import datetime
import os
import typing
import zipfile

import requests
from PastebinDecoder import PastebinDecoder


class Collector:
    def __init__(self,
                 path: str,
                 malware_path: str,
                 archive_prefix: str,
                 archive_url: str,
                 archive_token: str,
                 archive_password: str):
        self.path = path
        self.decoder = PastebinDecoder.PasteDecoder()
        self.malware_path = malware_path,
        self.archive_prefix = archive_prefix
        self.archive_url = archive_url
        self.archive_token = archive_token
        self.archive_password = archive_password

    def send_zip_to_archiver(self, zip_path: str):
        headers = {"Authorization": f"Token {self.archive_token}"}
        path_to_archiver = zip_path.replace(self.path, self.malware_path)
        body = {"Path": path_to_archiver,
                "password": self.archive_password,
                "source": "pastebin"}
        response = requests.post(self.archive_url, headers=headers, data=body)
        if response.status_code not in (200, 201):
            print(f"error submitting to archiver {response.content}")

    @staticmethod
    def zip_dir(dir_path: typing.AnyStr, file_name: typing.AnyStr) -> None:
        # make a zip file of the contents of the directory...remove the contents once you succeed
        # to make sure we don't delete a file until we're sure it's archived properly, put all
        # the files into the zip file, and close it. Then re-open it, get it's contents, and
        # then walk the list of files in the directory...only delete the ones in the directory
        # that exist in the zip file (and make sure you don't delete the zip file while you're at it).
        # first, make the zip file
        target = os.path.join(dir_path, file_name + ".zip")
        outputFile = zipfile.ZipFile(target, mode="a")
        for entry in os.listdir(dir_path):
            file_path = os.path.join(dir_path, entry)
            if entry.endswith('.zip'):
                continue
            if os.path.isdir(file_path):
                continue
            try:
                outputFile.write(file_path, arcname=entry)
            except FileNotFoundError:
                # concerning: this means we have a file in the listing that isn't openable.
                print("error opening file {}".format(file_path))
                continue
            except Exception:
                print("error writing entry: {}".format(entry))
                continue
        outputFile.close()
        # next, re-open it and read it's file listing
        saved_file = zipfile.ZipFile(target)
        successfully_saved_files = {entry.filename for entry in saved_file.filelist}
        for entry in os.listdir(dir_path):
            file_path = os.path.join(dir_path, entry)
            if entry.endswith('.zip'):
                continue
            if os.path.isdir(file_path):
                continue
            if entry in successfully_saved_files:
                try:
                    os.remove(file_path)
                except Exception:
                    print("error deleting entry: {}".format(entry))
        outputFile.close()

    def run(self):
        # recurse through all the directories, analyze all of them, except yesterday and today, since those
        # are likely to still be getting files.
        # identify yesterday's directory, analyze just that one.
        today = datetime.datetime.now(datetime.timezone.utc)
        yesterday = today - datetime.timedelta(days=1)
        yesterday_dirpath = os.path.join(self.path, str(yesterday.year), str(yesterday.month), str(yesterday.day))
        today_dirpath = os.path.join(self.path, str(today.year), str(today.month), str(today.day))
        for (dirpath, dirnames, filename) in os.walk(self.path):
            full_dirpath = os.path.join(self.path, dirpath)
            if full_dirpath in (today_dirpath, yesterday_dirpath):
                # skip today and yesterday, since they might still be getting written.
                continue
            elif (not dirnames) or (dirnames == ['decoded', ]):
                # this is the bottom of the tree, run the decode here:
                last_name = os.path.split(full_dirpath)[1]
                self.zip_dir(full_dirpath, last_name)
            else:
                # don't do the decode elsewhere
                continue


if __name__ == "__main__":
    configfile = configparser.ConfigParser()
    configfile.read("collector.conf")
    pastebin_path = configfile.get("Pastebin", "path")
    malware_path = configfile.get("Analysis", "file_path")
    archive_prefix = configfile.get("Analysis", "archive_prefix")
    archive_url = configfile.get("Analysis", "url")
    archive_token = configfile.get("Analysis", "token")
    archive_password = configfile.get("Analysis", "archive_password")
    collector = Collector(path=pastebin_path,
                          malware_path=malware_path,
                          archive_prefix=archive_prefix,
                          archive_url = archive_url,
                          archive_token=archive_token,
                          archive_password=archive_password)
    collector.run()
