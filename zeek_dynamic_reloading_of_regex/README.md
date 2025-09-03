# This directory contains
1. a regex feed that we want to monitor (regex.csv)
2. the script that registers the feed for monitoring, and checks every URI of HTTP requests for a match. it dynamically 
reloads all changes (insertions, deletions and updates) to the feed.




# Instructions for monitoring regex feeds

1. The monitored regex file should start with #fields
2. The fields line and each line should be tab separated
3. The record names in the zeek script should match the column names in the monitored regex.csv


# Usage

1. Download a PCAP for testing

```curl -O https://mcfp.felk.cvut.cz/publicDatasets/Android-Mischief-Dataset/AndroidMischiefDataset_v2/RAT06_Saefko/RAT06_Saefko.pcap```

2. Run zeek on it

```zeek -C -r RAT06_Saefko.pcap ../regex_monitor.zeek```


**Expected output:**
```commandline
Added regex /^?(http:\/\/.*\.exe)$?/ description Suspicious .exe file download
Added regex /^?([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})$?/ description IPv4 address
Added regex /^?((?s:GET.*POST))$?/ description Matches a GET followed by a POST on a single line
Added regex /^?([^/]+\.php\?)$?/ description Suspicious PHP file with query parameters
Added regex /^?(user[:blank:]*[:digit:]+)$?/ description User followed by a number with optional space
Added regex /^?(([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+)$?/ description Generic domain name
Wohoo regex /^?(([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+)$?/ ([description=Generic domain name]) matched this uri: /connecttest.txt?n=1618065954857
Wohoo regex /^?(([a-zA-Z0-9_-]+\.)+[a-zA-Z0-9_-]+)$?/ ([description=Generic domain name]) matched this uri: /mobile/status.php
```

OR

1. run zeek on your interface

```zeek -i wlp0s20f3 ../regex_monitor.zeek ```

2. add/remove entries from regex.csv and watch them loaded dynamically! :)
3. Make http requests that triggers any of them.


# What we can match with the regex other than HTTP (Zeek events cheat sheet)

 https://grok.com/share/c2hhcmQtMg%3D%3D_afb6326b-9fd9-438f-b1d1-7325041aa04f 