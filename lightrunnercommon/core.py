import os
import sys
import time
import json
import yaml
import shutil
import hashlib
import zipfile
import base64
import uuid
from pathlib import Path

import requests
import click
from flask import Flask, jsonify, request

from cli_passthrough import cli_passthrough

VERSION = "0.1"
version = "0.2"
api_spec_version = "0.1"
status = 'good'
host = "http://127.0.0.1"
port = "8080"

client_up = '.tmp/client/up/'
client_down = '.tmp/client/down/'
server_up = '.tmp/server/up/'
server_down = '.tmp/server/down/'
server_jobs = '.tmp/server/jobs/'
server_workspace = '.tmp/server/workspace/'

simplejob = "hi"

tmp_dirs = [
    ".tmp/",
    ".tmp/client",
    ".tmp/server",
    client_up,
    client_down,
    server_up,
    server_down,
    server_jobs,
    server_workspace
    ]

PROJECT_NAME = "jobrunner"
context_settings = {"help_option_names": ["-h", "--help"]}
test = {'status': status,}
info = {'status': status,'version': version,'api-spec-version': api_spec_version,}

def create_dirs(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def remove(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        if os.path.isdir(path):
            shutil.rmtree(path)

def read_tmp_base64file(filepath):
    with open(filepath, "rb") as image_file:
        encoded_data = bytes(image_file.read())
        return encoded_data

def write_tmp_base64file(filepath, data):
    with open(filepath, 'wb') as f:
        if isinstance(data, str):
            f.write(bytes(data, encoding='utf8'))
        elif isinstance(data, bytes):
            f.write(data)

def extractzip(tmp_zipfilename, outputdir):
    with zipfile.ZipFile(tmp_zipfilename, 'r') as zip_ref:
        zip_ref.extractall(outputdir)

def creatzip(tmp_zipfilename, inputdir):
    with zipfile.ZipFile(tmp_zipfilename, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipdir(inputdir, zipf)

def readzip(tmp_zipfilename):
    with open(tmp_zipfilename, "rb") as image_file:
        data = image_file.read()
        if isinstance(data, str):
            return bytes(image_file.read())
        elif isinstance(data, bytes):
            return data

def writefile(tmp_zipfilename, bytes_data):
    with open(tmp_zipfilename, 'wb') as f:
        f.write(bytes_data)

def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()

def sanitise_json(message):
    data = json.loads(message)
    assert isinstance(data["payload"], str)
    assert isinstance(data["uuid_name"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["jobid"], int)
    assert isinstance(data["metadata"], dict)
    return message

def to_message(bytes_payload, name, uuid_name, jobid, metadata):
    assert isinstance(bytes_payload, bytes)
    message = {
        "payload": bytes_payload.decode("utf-8"),
        "name": name,
        "uuid_name": uuid_name,
        "jobid": jobid,
        "metadata": metadata
    }
    data = json.dumps(message)
    data = sanitise_json(data)
    return data

def from_message(message):
    payload_obj = json.loads(message)
    payload_obj["payload"] == bytes(payload_obj["payload"], encoding='utf8')
    return payload_obj

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
            os.path.relpath(os.path.join(root, file),
            os.path.join(path, '..')))


def __prep_zip(inputdir, name, tmp_zipfilename, tmp_base64filename, uuid_name, jobid, metadata):
    creatzip(tmp_zipfilename, inputdir)
    bytes_data = readzip(tmp_zipfilename)
    encoded_data = base64.b64encode(bytes_data)
    assert isinstance(bytes_data, bytes)
    assert isinstance(encoded_data, bytes)
    write_tmp_base64file(tmp_base64filename, encoded_data)
    bytes_data = read_tmp_base64file(tmp_base64filename)
    return to_message(bytes_data, name, uuid_name, jobid, metadata)


def __get_zip(message, tmp_zipfilename, tmp_base64filename, uuid_name, jobid):
    payload_obj = from_message(message)
    write_tmp_base64file(tmp_base64filename, payload_obj["payload"])
    encoded_data = read_tmp_base64file(tmp_base64filename)
    bytes_data = base64.b64decode(encoded_data)
    assert isinstance(encoded_data, bytes)
    assert isinstance(bytes_data, bytes)
    writefile(tmp_zipfilename, bytes_data)


def prep_zip_localclient(inputdir, name, uuid_name, jobid):
    tmp_zipfilename = client_up + uuid_name +  ".zip"
    tmp_base64filename = client_up + uuid_name +  ".base64"
    return __prep_zip(inputdir, name, tmp_zipfilename, tmp_base64filename, uuid_name, jobid, metadata={"pattern": "full"})


def get_message_localclient(message, uuid_name, jobid):
    tmp_zipfilename = client_down + uuid_name +  ".zip"
    tmp_base64filename = client_down + uuid_name +  ".base64"
    __get_zip(message, tmp_zipfilename, tmp_base64filename, uuid_name, jobid)


def process_zip_localclient(outputdir, name, uuid_name, jobid):
    remove(outputdir)
    tmp_zipfilename = client_down + uuid_name +  ".zip"
    extractzip(tmp_zipfilename, outputdir)


def prep_zip_localserve(inputdir, name, uuid_name, jobid):
    tmp_zipfilename = server_up + uuid_name +  ".zip"
    tmp_base64filename = server_up + uuid_name +  ".base64"
    return __prep_zip(inputdir, name, tmp_zipfilename, tmp_base64filename, uuid_name, jobid, metadata={"pattern": "full"})


def get_message_localserve(message):
    payload_obj = from_message(message)
    uuid_name = payload_obj["uuid_name"]
    jobid = payload_obj["jobid"]
    tmp_zipfilename = server_down + uuid_name +  ".zip"
    tmp_base64filename = server_down + uuid_name +  ".base64"
    __get_zip(message, tmp_zipfilename, tmp_base64filename, uuid_name, jobid)


def process_zip_localserve(outputdir, name, uuid_name, jobid):
    remove(outputdir)
    tmp_zipfilename = server_down + uuid_name +  ".zip"
    extractzip(tmp_zipfilename, outputdir)
    with open(server_workspace + name + '/test.txt', 'w') as f:
        f.write('hi')

def echo_loopback(message, name, uuid_name, jobid):
    r = requests.post(host + ':' + port + '/api/loopback', json = message)
    message = r.content
    return message

def echo_local(message, name, uuid_name, jobid):
    get_message_localserve(message)
    process_zip_localserve(server_workspace, name, uuid_name, jobid)
    message = prep_zip_localserve(server_workspace + name, name, uuid_name, jobid)
    return message

def echo(name, uuid_name, jobid, target):
    message = prep_zip_localclient("input/" + name, name, uuid_name, jobid)
    if target == "local":
        message = echo_local(message, name, uuid_name, jobid)
    elif target == "loopback":
        message = echo_loopback(message, name, uuid_name, jobid)
    get_message_localclient(message, uuid_name, jobid)
    process_zip_localclient("output", name, uuid_name, jobid)

def send_to_runner(name, uuid_name, jobid):
    create_dirs(tmp_dirs)
    message = prep_zip_localclient(name, name, uuid_name, jobid)
    r = requests.post(host + ':' + port + '/api/preppackage', json = message)
    message = r.content

def call_runner_track(uuid_name):
    r = requests.get('http://127.0.0.1:8080/track/' + uuid_name)
    message = r.json()
    uuid_name = message["uuid_name"]
    return message


app = Flask(__name__)

@app.route('/api/loopback', methods=['POST'])
def post():
    message = request.json
    payload_obj = from_message(message)
    name = payload_obj["name"]
    uuid_name = payload_obj["uuid_name"]
    jobid = payload_obj["jobid"]
    get_message_localserve(message)
    process_zip_localserve(server_workspace, name, uuid_name, jobid)
    message = prep_zip_localserve(server_workspace + name, name, uuid_name, jobid)
    return message

@click.group(context_settings=context_settings)
@click.version_option(prog_name=PROJECT_NAME.capitalize(), version=VERSION)
@click.pass_context
def cli(ctx):
    pass

@click.group(name="client")
def client_group():
    pass

@click.group(name="server")
def server_group():
    pass

@server_group.command("serve")
def serve_cmd():
    app.run(debug=True, port=8080)

@client_group.command("loopback")
def loopback_cmd():
    create_dirs(tmp_dirs)

    name ="raycaster"
    uuid_name = uuid.uuid4().hex
    jobid = 8
    echo(name, uuid_name, jobid, "loopback")

@client_group.command("local")
def local_cmd():
    create_dirs(tmp_dirs)
    # for i in progressbar(range(1), "Computing: ", 40):
    #     time.sleep(0.1)

    name ="raycaster"
    uuid_name = uuid.uuid4().hex
    jobid = 8
    echo(name, uuid_name, jobid, "local")

## to expose
##
## echodir
## echofile
## pushdirjob
## pushfilejob
## getdirjob
## getfilejob
## jobstart
## jobstatus


cli.add_command(client_group)
cli.add_command(server_group)
