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

import datetime
import json
import os
import typing
from zipfile import ZipFile

import requests
from PastebinDecoder import PastebinDecoder


class Collector:
    def __init__(self,
                 path: str,
                 malware_path: str,
                 archive_prefix: str,
                 archive_url: str,
                 archive_token: str,
                 archive_password: str,
                 malware_file_types: typing.Optional[typing.List] = None,
                 skip_file_types: typing.Optional[typing.List] = None):
        self.path = path
        self.malware_path = malware_path
        self.archive_prefix = archive_prefix
        self.archive_url = archive_url
        self.archive_token = archive_token
        self.archive_password = archive_password
        self.decoder = PastebinDecoder.PasteDecoder()
        if malware_file_types is None:
            self.malware_file_types = ["application", "image"]
        else:
            self.malware_file_types = malware_file_types
        if skip_file_types is None:
            self.skip_file_types = ["application/json",
                                    "application/octet-stream",
                                    "application/x-wine-extension-ini"]
        else:
            self.skip_file_types = skip_file_types

    def send_zip_to_archiver(self, zip_path: str):
        headers = {"Authorization": f"Token {self.archive_token}"}
        path_to_archiver = zip_path.replace(self.malware_path, self.archive_prefix)
        body = {"path": path_to_archiver,
                "password": self.archive_password,
                "source": "pastebin"}
        response = requests.post(self.archive_url, headers=headers, json=body)
        if response.status_code not in (200, 201):
            print(f"error submitting to archiver {response.content}")

    def find_malware_path(self, original_path: str):
        # assumes a path naming pattern like "/paste/2021/3/21/", meaning March 21, 2021
        #
        removed_base = original_path.replace(self.path, "")
        if removed_base.startswith(os.path.sep):
            removed_base = removed_base.replace(os.path.sep, "", 1)
        path_parts = removed_base.split(os.path.sep)
        if len(path_parts) != 4:
            raise Exception(f"error with path: {removed_base} ")
        yeardirname, monthdirname, daydirname, filename = path_parts
        contained_dir = os.path.join(self.malware_path, yeardirname, monthdirname, daydirname)
        if not os.path.isdir(contained_dir):
            os.makedirs(contained_dir)
        new_path = os.path.join(contained_dir, filename)
        return new_path

    @staticmethod
    def archive_files_into_zip(target, dir_path):
        with ZipFile(target, mode="a") as outputFile:
            existing_files = outputFile.namelist()
            for entry in os.listdir(dir_path):
                file_path = os.path.join(dir_path, entry)
                if entry.endswith('.zip'):
                    # don't add the zipfile itself, or any other existing zip files.
                    continue
                if os.path.isdir(file_path):
                    continue
                if entry.startswith("."):
                    continue
                if entry not in existing_files:
                    try:
                        outputFile.write(file_path, arcname=entry)
                    except FileNotFoundError:
                        # concerning: this means we have a file in the listing that isn't openable.
                        print("error opening file {}".format(file_path))
                    except Exception:
                        print("error writing entry: {}".format(entry))

    @staticmethod
    def remove_archived_files(target, dir_path):
        with ZipFile(target, "r") as saved_file:
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

    def extract_interesting_files(self, target, dir_path, malware_archive_path):
        # re-open one last time to sync with extracted malware zip.
        changed_saved_file = False
        with ZipFile(target, "r") as archive, \
             ZipFile(malware_archive_path, "a") as outputMalwareFile:
            existing_malware_files = outputMalwareFile.namelist()
            for entry in archive.namelist():
                if entry not in existing_malware_files:
                    filehandle = archive.open(entry, "r")
                    data = filehandle.read()
                    decoded = json.loads(data)
                    file_type, file_data, _ = self.decoder.handle(decoded['body'].encode("utf-8"))
                    keep_file = False
                    for prefix in self.malware_file_types:
                        if file_type.startswith(prefix) and file_type not in self.skip_file_types:
                            keep_file = True
                    if keep_file:
                        try:
                            outputMalwareFile.writestr(data=file_data[0], zinfo_or_arcname=entry)
                            changed_saved_file = True
                        except FileNotFoundError:
                            # concerning: this means we have a file in the listing that isn't openable.
                            print("error opening file {}".format(entry))
                        except Exception:
                            print("error writing entry: {}".format(entry))
        return changed_saved_file

    def zip_dir(self, dir_path: typing.AnyStr, file_name: typing.AnyStr) -> None:
        # make a zip file of the contents of the directory...remove the contents once you succeed
        # to make sure we don't delete a file until we're sure it's archived properly, put all
        # the files into the zip file, and close it. Then re-open it, get it's contents, and
        # then walk the list of files in the directory...only delete the ones in the directory
        # that exist in the zip file (and make sure you don't delete the zip file while you're at it).
        # first, make the zip file
        target = os.path.join(dir_path, file_name + ".zip")
        self.archive_files_into_zip(target, dir_path)
        # next, re-open it and read it's file listing, remove all files successfully archived to
        # the zip
        self.remove_archived_files(target, dir_path)
        try:
            print(f"processing {dir_path}")
            malware_archive_path = self.find_malware_path(target)
            changed_archive = self.extract_interesting_files(target, dir_path, malware_archive_path)
            if changed_archive:
                print("sending updated malware zip to archiver")
                self.send_zip_to_archiver(malware_archive_path)
        except Exception:
            print(f"error processing {dir_path}, {file_name}, skipping malware archive")
            return

    def run(self):
        # recurse through all the directories, analyze all of them, except yesterday and today,
        # since those are likely to still be getting files.
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
    pastebin_path = os.environ.get("PASTEBIN_PATH", "/paste")
    malware_path = os.environ.get("MALWARE_PATH", "/malware")
    archive_prefix = os.environ.get("ANALYZER_PATH", "pastebin-extractions")
    archive_url = os.environ.get("ANALYZER_URL", "http://malware-analysis-site:8000/api/job")
    archive_token = os.environ.get("ANALYZER_TOKEN")
    archive_password = os.environ.get("ARCHIVE_PASSWORD")
    collector = Collector(path=pastebin_path,
                          malware_path=malware_path,
                          archive_prefix=archive_prefix,
                          archive_url=archive_url,
                          archive_token=archive_token,
                          archive_password=archive_password)
    collector.run()
