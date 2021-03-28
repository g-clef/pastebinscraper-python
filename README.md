# Pastebin scraper

This contains 2 Kubernetes jobs (well, sort of 3):
  1. A "scraper" deployment that runs a daemon that connects to the pastebin api and pulls down the most recent pastes and writes them to disk.
  2. A "collector" cron job that reads the written files, analyses them to determine file type (including possibly encoded files), and posts any 
     "interesting" file types to the malware analysis site. There is also a one-off version of this to run against a saved archive of pastebin files
     if the scraper has run for a long time before starting the collector.
