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

from lightrunnercommon.config import tmp_dirs
from lightrunnercommon.readconfig import getconfig

def test():
    return getconfig()

def remove(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        if os.path.isdir(path):
            shutil.rmtree(path)

def create_dirs(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def init_runner_env():
    create_dirs(tmp_dirs)
    dir = '.tmp/runners/'
    if not os.path.exists(dir):
        os.mkdir(dir)

    dir = '.tmp/runners/runs'
    if not os.path.exists(dir):
        os.mkdir(dir)
