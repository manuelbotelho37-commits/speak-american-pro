#!/usr/bin/env python3
"""Convert CeCILL-C en-fr StarDict into compact JSON shards for Speak American."""
import gzip,json,pathlib,struct,urllib.request,zipfile,io,re
api="https://api.github.com/repos/DanielGregorini/koreader-dicts/releases/latest"
request=urllib.request.Request(api,headers={"User-Agent":"SpeakAmericanDictionaryBuilder/1.0","Accept":"application/vnd.github+json"})
with urllib.request.urlopen(request,timeout=60) as response: release=json.load(response)
assets=release.get("assets",[])
asset=next((a for a in assets if a["name"]=="en-fr.zip"),None)
if asset is None: raise RuntimeError("en-fr.zip absent de la dernière version : "+str([a["name"] for a in assets]))
url=asset["browser_download_url"]
request=urllib.request.Request(url,headers={"User-Agent":"SpeakAmericanDictionaryBuilder/1.0"})
with urllib.request.urlopen(request,timeout=180) as response: archive=response.read()
z=zipfile.ZipFile(io.BytesIO(archive))
names=z.namelist()
idxname=next(n for n in names if n.endswith(".idx"))
dictname=next(n for n in names if n.endswith(".dict.dz") or n.endswith(".dict"))
ifo=next(n for n in names if n.endswith(".ifo"))
print("Source:",idxname,dictname)
idx=z.read(idxname);raw=z.read(dictname)
dictionary=gzip.decompress(raw) if dictname.endswith(".dz") else raw
idxoffset=0;entries={}
while idxoffset<len(idx):
    end=idx.index(b"\0",idxoffset)
    word=idx[idxoffset:end].decode("utf-8","replace").strip().lower()
    offset,size=struct.unpack(">II",idx[end+1:end+9])
    idxoffset=end+9
    if not word or len(word)>90 or offset+size>len(dictionary):continue
    value=dictionary[offset:offset+size].decode("utf-8","replace")
    value=re.sub(r"<[^>]*>"," ",value)
    value=re.sub(r"\s+"," ",value).strip()
    if value:entries[word]=value[:420]
# StarDict .syn includes word variants pointing to the index ordinal
synfiles=[n for n in names if n.endswith(".syn")]
if synfiles:
    indexwords=list(entries)
    syn=z.read(synfiles[0]);p=0
    while p<len(syn):
        e=syn.index(b"\0",p);variant=syn[p:e].decode("utf-8","replace").lower()
        ordinal=struct.unpack(">I",syn[e+1:e+5])[0];p=e+5
        if variant not in entries and ordinal<len(indexwords):
            entries[variant]=entries[indexwords[ordinal]]
output=pathlib.Path("dictionary");output.mkdir(exist_ok=True)
shards={}
for k,v in entries.items():
    letter=k[0] if k[0] in "abcdefghijklmnopqrstuvwxyz" else "_"
    shards.setdefault(letter,{})[k]=v
for letter,data in shards.items():
    (output/(letter+".json")).write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
(output/"source.txt").write_text("Dictionary: en-fr from DanielGregorini/koreader-dicts\nLicense: CeCILL-C\nSource: "+url+"\nOriginal source credits and attribution: https://github.com/DanielGregorini/koreader-dicts\n",encoding="utf-8")
print("Words:",len(entries),"shards:",len(shards))
