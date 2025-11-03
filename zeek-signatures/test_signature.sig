signature malware-c2-communication {
    ip-proto == tcp
    dst-port == 80
    payload /POST.*\/update.*malware/
    event "Malware C2 communication detected"
}