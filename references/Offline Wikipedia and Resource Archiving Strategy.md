# **Offline Wikipedia and Resource Archiving Strategy**

[https://gemini.google.com/app/0f16edeb30afc383](https://gemini.google.com/app/0f16edeb30afc383)

*User prompt: Devise an implementation strategy for a shell based tool that allows me to download and locally store snapshots of the most relevant Wikipedia articles, as well as other information that might be interesting or relevant to me, if the internet is down. Include both sources that provide practical information, as well as programming language references, etc. That I might need to continue my work and life. Summarize your findings into a step by step implementation guide for an AI that holds a list of sources from which I can pick and choose. Make sure the sources are grouped by topic and available in a way they can be efficiently downloaded.*

Response: I've put together a research plan. If you need to update it in any way, let me know.

---

*User prompt: Edit the research plan*

Response: This is the current plan. What changes do you want to make?

(1) Identify standard formats and platforms for offline web archiving, focusing on ZIM files, Kiwix, and developer documentation aggregators like DevDocs or Dash docsets. (2) Research high-quality sources of practical knowledge, emergency preparedness guides, and general reference material (such as Wikipedia, WikiHow, OpenStreetMap data for Austria and Graz, and Project Gutenberg) available for offline download. (3) Research comprehensive developer resources and programming language references (including Stack Overflow databases, MDN Web Docs, and official language documentations) that can be mirrored locally. (4) Investigate command-line utilities and protocols (e.g., aria2, wget, rsync, BitTorrent clients) that enable high-speed, resumed, and bandwidth-efficient downloads of large datasets. (5) Formulate a structured taxonomy of these sources, categorizing them by domain (e.g., Technology, Survival and Practical, General Reference, Geography) to allow selective downloading. (6) Design the software architecture for a shell-based utility (such as a Bash or Python CLI) that lists, downloads, and manages these local snapshots. (7) Compile the research into a step-by-step implementation guide for building the tool, outlining script structure, download management, and user interaction.

---

*User prompt: Extend the research plan by adding sources that could keep me entertained.*

Response: Here's my plan to tackle that topic. Let me know if you need to make changes.

---

*User prompt: Start research*

Response: I've completed your research. Feel free to ask me follow-up questions or request changes.

---

*User prompt: Expand upon the given solution, so it can be comfortably used on an Android phone Termux installed.*

Response: To successfully deploy and comfortably operate this decentralized offline knowledge base on an Android device, the technical architecture must be adapted to conform to the distinct physical boundaries and security paradigms of the Android runtime environment. Since Android does not use systemd, standard service orchestration must be ported to the runit-based termux-services daemon. Additionally, storage constraints require using Android's shared storage partitions to hold large datasets, preventing data loss if the Termux application is reset.

This guide outlines how to adapt, install, and automate the offline sync engine and search utilities natively inside Termux.

## **Operating System & Storage Constraints**

Android isolates application files, meaning massive ZIM databases cannot sit in Termux’s private space without risking storage bottlenecks or data-wiping. We must route all heavy storage paths to the device's shared user directory (typically mapped to /sdcard/Download/ or /storage/emulated/0/Download/).

To grant Termux the permission to interact with Android's storage layer, run the following environment command inside the terminal:

termux-setup-storage

This generates a symlink folder at \~/storage/ inside your home directory, linking directly to the shared storage root. This allows external Android applications (such as KOReader, specialized maps, or standard web browsers) to access books, vector files, and pages served locally on your device.

The table below contrasts standard Linux system boundaries with the corresponding adapters and ports required inside Termux:

| Operational Feature | Standard Linux Node | Android Termux Environment |
| :---- | :---- | :---- |
| **Service Supervisor** | systemd (systemctl) | runit (termux-services) |
| **Storage Vault Mount** | /var/www/offline\_vault | /sdcard/Download/offline\_vault |
| **Binary Packages** | apt install kiwix-tools | pkg install kiwix-tools |
| **Java JRE Runtime** | openjdk-17-jre | openjdk-17 |
| **Boot Automation** | systemd enable target | Termux:Boot script loop |

## **Native Dependency Management**

Rather than compiling binaries from source, we use Termux's native package manager (pkg) to install pre-compiled, architecture-specific packages. The kiwix-tools package (which compiles kiwix-serve and kiwix-manage) is natively available in the official Termux repositories.

Update the repositories and install the foundational packages:

pkg update \-y && pkg upgrade \-y  
pkg install \-y kiwix-tools openjdk-17 python python-pip clang make termux-services

### **Compiling Scientific Python on Mobile ARM64**

To build the localized semantic search index (RAG pipeline) using Sentence Transformers and FAISS, standard Python compilations via pip will fail due to missing build headers on Android. To resolve this, add the pre-compiled Termux User Repository (TUR), which distributes pre-built wheels for scientific packages:

\# Register the community user repository  
pkg install \-y tur-repo  
\# Install precompiled system binaries for numpy and dependency headers  
pkg install \-y python-numpy python-scipy binutils  
\# Install search pipeline dependencies  
pip install faiss-cpu sentence-transformers

To calculate the physical memory consumption *M*embed​ during local vector embedding runs on your phone, use the following model:

*M*embed​≈*N*⋅*D*⋅4 bytes

where *N* is the number of text chunks extracted from your local documents and *D* is the dense vector embedding dimension. For a mobile-friendly model like all-MiniLM-L6-v2 (*D*\=384), indexing 100,000 chunks requires approximately 153.6 MB of memory during matrix assembly, which is well within the limits of modern mobile hardware.

## **Service Orchestration via Runit (termux-services)**

Since Termux does not support systemd, background services must use termux-services (powered by the lightweight runit supervisor). Runit monitors execution states and automatically restarts processes if they crash.

### **1\. Creating the kiwix-serve Service**

Create the service directory and register the background logging mechanism:

mkdir \-p $PREFIX/var/service/kiwix-serve/log  
ln \-sf $PREFIX/share/termux-services/svlogger $PREFIX/var/service/kiwix-serve/log/run

Create the execution script at $PREFIX/var/service/kiwix-serve/run:

\#\!/usr/bin/env bash  
\# Termux runs in a single-user environment. Ensure we point to shared storage.  
VAULT\_ROOT="/sdcard/Download/offline\_vault"  
LIBRARY\_XML="$VAULT\_ROOT/zims/library.xml"

\# Wait for storage to become accessible on device boot  
while \[ \! \-f "$LIBRARY\_XML" \]; do  
    sleep 2  
done

exec kiwix-serve \\  
    \--port=8080 \\  
    \--library "$LIBRARY\_XML" \\  
    \--nodatealiases \\  
    \--threads=2 \\  
    \--ipConnectionLimit=5 \\  
    \--monitorLibrary

Make the script executable:

chmod \+x $PREFIX/var/service/kiwix-serve/run

### **2\. Creating the mapsforge-serve Service**

Create the service directory and link the logger:

mkdir \-p $PREFIX/var/service/mapsforge-serve/log  
ln \-sf $PREFIX/share/termux-services/svlogger $PREFIX/var/service/mapsforge-serve/log/run

Create the execution script at $PREFIX/var/service/mapsforge-serve/run:

\#\!/usr/bin/env bash  
JAR\_PATH="$PREFIX/share/mapsforgesrv/mapsforgesrv-fatjar.jar"  
MAP\_PATH="/sdcard/Download/offline\_vault/geospatial/Graz.map"

while \[ \! \-f "$MAP\_PATH" \]; do  
    sleep 2  
done

exec java \-jar "$JAR\_PATH" \-p 8085 \-m "$MAP\_PATH"

Make the script executable:

chmod \+x $PREFIX/var/service/mapsforge-serve/run

## **Mobile Content Sync Script**

Save the following sync engine inside your Termux environment at \~/sync\_vault.sh. This script is optimized for Android, writing directly to shared storage and adapting to Termux’s folder structure:

\#\!/usr/bin/env bash  
\# \==============================================================================  
\# TERMUX MOBILE OFFLINE STORAGE SYNC ENGINE  
\# \==============================================================================  
set \-euo pipefail

\# 1\. Path Registrations (Scoped to Android Shared Storage)  
export VAULT\_ROOT="/sdcard/Download/offline\_vault"  
export LOG\_DIR="$VAULT\_ROOT/logs"  
export ZIM\_DIR="$VAULT\_ROOT/zims"  
export DOC\_DIR="$VAULT\_ROOT/docsets"  
export LIT\_DIR="$VAULT\_ROOT/literature"  
export MAP\_DIR="$VAULT\_ROOT/geospatial"

\# Initialize Directories  
mkdir \-p "$LOG\_DIR" "$ZIM\_DIR" "$DOC\_DIR" "$LIT\_DIR" "$MAP\_DIR"

log\_info() {  
    echo \-e "\\e\[34m\[TERMUX INFO\]\\e\[0m $(date '+%Y-%m-%d %H:%M:%S') \- $1"  
}

log\_info "Initiating content updates across mobile storage..."

\# 2\. Synchronize ZIM Databases  
log\_info "Acquiring lightweight, curated mobile ZIM databases..."  
declare \-A ZIM\_TARGETS=(  
    \["wikimed\_en\_all\_maxi"\]="https://download.kiwix.org/zim/wikipedia/wikimed\_en\_all\_maxi\_2024-11.zim"  
    \["wikihow\_en\_all\_maxi"\]="https://download.kiwix.org/zim/wikihow/wikihow\_en\_all\_maxi\_2024-10.zim"  
    \["ifixit\_en\_all\_maxi"\]="https://download.kiwix.org/zim/other/ifixit\_en\_all\_maxi\_2024-09.zim"  
)

LIBRARY\_XML="$ZIM\_DIR/library.xml"

for KEY in "${\!ZIM\_TARGETS\[@\]}"; do  
    URL="${ZIM\_TARGETS\[$KEY\]}"  
    DEST="$ZIM\_DIR/$KEY.zim"  
    log\_info "Checking $KEY ZIM database..."  
    \# Download with support for resuming interrupted transfers  
    curl \-L \-C \- \-o "$DEST" "$URL"  
      
    \# Register the file with the Kiwix library manager  
    if \[ \! \-f "$LIBRARY\_XML" \]; then  
        kiwix-manage "$LIBRARY\_XML" add "$DEST"  
    else  
        kiwix-manage "$LIBRARY\_XML" remove "$KEY" || true  
        kiwix-manage "$LIBRARY\_XML" add "$DEST"  
    fi  
done

\# 3\. Synchronize Developer Docsets  
log\_info "Acquiring targeted API docsets..."  
TARGET\_DOCSETS=("Python" "Go")  
for DOCSET in "${TARGET\_DOCSETS\[@\]}"; do  
    log\_info "Fetching docset: $DOCSET..."  
    DL\_URL="https://go.zealdocs.org/d/sanfrancisco/${DOCSET}/latest"  
    TEMP\_TGZ="$DOC\_DIR/${DOCSET}.tgz"  
    curl \-L \-o "$TEMP\_TGZ" "$DL\_URL"  
    tar \-xzf "$TEMP\_TGZ" \-C "$DOC\_DIR"  
    rm \-f "$TEMP\_TGZ"  
done

\# 4\. Synchronize Literature  
log\_info "Downloading public domain classics..."  
cat \<\< 'EOF' \> "$VAULT\_ROOT/crawl\_ebooks.py"  
import os  
import xml.etree.ElementTree as ET  
import urllib.request  
import urllib.parse

OPDS\_URL \= "https://standardebooks.org/feeds/opds/all"  
LIT\_DIR \= "/sdcard/Download/offline\_vault/literature"  
ATOM\_NS \= "{http://www.w3.org/2005/Atom}"

req \= urllib.request.Request(OPDS\_URL, headers={'User-Agent': 'OfflineVaultTermux/1.0'})  
try:  
    with urllib.request.urlopen(req) as resp:  
        xml\_data \= resp.read()  
    root \= ET.fromstring(xml\_data)  
    for entry in root.findall(f"{ATOM\_NS}entry")\[:20\]: \# Bound loop limit to 20 to protect mobile disk IO  
        title \= entry.find(f"{ATOM\_NS}title").text  
        author\_elem \= entry.find(f"{ATOM\_NS}author")  
        author \= author\_elem.find(f"{ATOM\_NS}name").text if author\_elem is not None else "Unknown"  
          
        for link in entry.findall(f"{ATOM\_NS}link"):  
            href \= link.get("href")  
            rel \= link.get("rel")  
            link\_type \= link.get("type")  
            if rel and "acquisition" in rel and link\_type \== "application/epub+zip":  
                safe\_author \= "".join(c for c in author if c.isalnum() or c in " .\_-").strip()  
                safe\_title \= "".join(c for c in title if c.isalnum() or c in " .\_-").strip()  
                  
                target\_dir \= os.path.join(LIT\_DIR, safe\_author, safe\_title)  
                os.makedirs(target\_dir, exist\_ok=True)  
                  
                dl\_url \= urllib.parse.urljoin("https://standardebooks.org", href)  
                target\_file \= os.path.join(target\_dir, f"{safe\_title}.epub")  
                if not os.path.exists(target\_file):  
                    print(f"Syncing book: {title} by {author}")  
                    urllib.request.urlretrieve(dl\_url, target\_file)  
except Exception as e:  
    print(f"Error parsing OPDS: {e}")  
EOF  
python3 "$VAULT\_ROOT/crawl\_ebooks.py"  
rm \-f "$VAULT\_ROOT/crawl\_ebooks.py"

\# 5\. Acquire Geospatial Maps forge Assets  
log\_info "Fetching geospatial vectors..."  
MAPS\_URL="https://download.bbbike.org/osm/bbbike/Graz/Graz.map"  
curl \-L \-C \- \-o "$MAP\_DIR/Graz.map" "$MAPS\_URL"

\# 6\. Install Mapsforge Tile Server Jar  
JAR\_DIR="$PREFIX/share/mapsforgesrv"  
mkdir \-p "$JAR\_DIR"  
if \[ \! \-f "$JAR\_DIR/mapsforgesrv-fatjar.jar" \]; then  
    log\_info "Downloading Mapsforge rendering jar..."  
    curl \-L \-o "$JAR\_DIR/mapsforgesrv-fatjar.jar" "https://github.com/telemaxx/mapsforgesrv/raw/master/mapsforgesrv/bin/jars\_ready2use/mapsforgesrv-fatjar.jar"  
fi

log\_info "Mobile data synchronization complete. Restarting services..."  
sv down kiwix-serve || true  
sv up kiwix-serve  
sv down mapsforge-serve || true  
sv up mapsforge-serve  
log\_info "All Termux background processes are online."

Make the sync utility executable:

chmod \+x \~/sync\_vault.sh

## **Service Management & Autostart Configuration**

Once the scripts are built, manage their execution using Termux's standard service commands:

\# Register services to launch automatically when Termux starts  
sv-enable kiwix-serve  
sv-enable mapsforge-serve

\# Manually start the services right now  
sv up kiwix-serve  
sv up mapsforge-serve

\# Monitor execution states  
sv status kiwix-serve  
sv status mapsforge-serve

### **Automation on Boot (Zero User Interaction)**

To ensure the services launch silently when your phone boots (even if you haven't opened the Termux app), configure Termux:Boot:

> 1. Install the **Termux:Boot** add-on application from F-Droid.  
> 2. Open Android’s settings and locate **Battery Optimization**. Set both **Termux** and **Termux:Boot** to **Don't Optimize** to prevent Android from closing your background servers.  
> 3. Open the Termux app once to set up the directories.  
> 4. Create the boot configuration script:

mkdir \-p \~/.termux/boot  
nano \~/.termux/boot/start-services

Add the following command to prevent your system from placing CPU cores to sleep when the screen is locked:

\#\!/usr/bin/env bash  
\# Prevent sleep locks on the CPU while hosting offline content  
termux-wake-lock

Make the script executable:

chmod \+x \~/.termux/boot/start-services

Your Android device is now configured as a portable, background-supervised offline host. Any device on your local Wi-Fi network (or your phone itself) can access the services:

> * Open http://localhost:8080 to search and browse Wikipedia, WikiMed, and WikiHow.  
> * Open http://localhost:8085/{z}/{x}/{y}.png inside any mapping client to render offline vector maps.

---

