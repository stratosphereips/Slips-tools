# Zeek Signature Framework

Zeek provides a signature language, similar to Snort, for low-level pattern matching. Although not Zeek’s preferred method (scripts are), signatures can be useful in many detection scenarios.

---

## 📘 Basics

### Example Signature
```zeek
signature my-first-sig {
    ip-proto == tcp
    dst-port == 80
    payload /.*root/
    event "Found root!"
}
```

This matches TCP connections to port 80 containing `root` in the payload.

### Event Triggered
```zeek
event signature_match(state: signature_state, msg: string, data: string)
```
OR (Zeek v7.1+):
```zeek
event signature_match(state: signature_state, msg: string, data: string, end_of_match: count)
```

- `state`: Info on the triggering connection
- `msg`: Custom message
- `data`: Payload that matched
- `end_of_match`: Offset where the match ends

---

## 🔧 Loading Signatures

Three ways to load signature files:

- `zeek -s my-sigs.sig`
- Extend variable: `signature_files += my-sigs.sig`
- In script: `@load-sigs ./my-sigs.sig`

`.sig` is the default extension. Paths are resolved using `ZEEKPATH`.

---

## 🔍 Signature Structure

```zeek
signature <id> {
    <conditions>
    <actions>
}
```

---

## 🧾 Conditions

### Header Conditions

Apply only to the **first packet** of a connection.

**Format:**
```zeek
<keyword> <cmp> <value-list>
```

**Common Keywords:**

- `src-ip`, `dst-ip` (IPv4, IPv6, CIDR)
- `src-port`, `dst-port`
- `ip-proto` (tcp, udp, icmp, etc.)

**Example:**
```zeek
dst-ip == 1.2.3.4/16, 5.6.7.8/24
```

**Advanced Format:**
```zeek
header <proto>[<offset>:<size>] [& <mask>] <cmp> <value-list>
```

---

### Content Conditions

**Payload match:**
```zeek
payload /<regex>/
```

**Analyzer-specific matches:**

- `http-request`, `http-request-header`, `http-request-body`
- `http-reply-header`, `http-reply-body`
- `ftp`, `finger`

**Example:**
```zeek
http-request /.*etc\/(passwd|shadow)/
```

---

### Dependency Conditions

- `requires-signature [!] <id>`
- `requires-reverse-signature [!] <id>`

---

### Context Conditions

- `eval <policy-function>`
- `payload-size <cmp> <int>`
- `same-ip`
- `tcp-state established,originator,responder`
- `udp-state originator,responder`

---

## 🎯 Actions

### 1. `event <string>`

Triggers:
```zeek
event signature_match(state, msg, data [, end_of_match])
```

Custom event:
```zeek
event my_signature_match "Found root!"
```

Or:
```zeek
event found_root
```

### 2. `enable <analyzer>`

Dynamically enables protocol analyzer (`http`, `ftp`, etc.)

---

## 📄 File Content Signatures

Used with Files Framework or `file_magic()`.

### Condition
```zeek
file-magic /<regex>/
```

### Action
```zeek
file-mime <mime-type> [, <strength>]
```

---

## 🧠 Notes on Writing Signatures

- Signature matches once per connection
- Analyzer must be active for analyzer-specific matches
- Payload does **not** include headers
- TCP matches support stream reassembly (default 1KB)
- UDP/ICMP matching is per-packet
- Regex is **anchored** (`^`). Use `.*` to match anywhere
- Match on binary: `\x<hex>`, `\r`, `\n`

---

## ⚙️ Options

| Option | Description |
|--------|-------------|
| `dpd_reassemble_first_packets` | Reassemble initial TCP payloads |
| `dpd_match_only_beginning` | Match only in initial buffer |
| `dpd_buffer_size` | Size of reassembly buffer (default: 1KB) |

---

## ❌ Snort Signature Compatibility

- `snort2bro` script deprecated
- Converting Snort to Zeek not recommended
