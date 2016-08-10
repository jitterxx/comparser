#!/usr/bin/env python
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Google Cloud Speech API sample application using the REST API for async
batch processing."""

# [START import_libraries]
import argparse
import base64
import json
import time

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
# [END import_libraries]


# [START authenticating]

from gcloud import storage
from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build

credentials = GoogleCredentials.get_application_default().create_scoped(
    ["https://www.googleapis.com/auth/devstorage.read_write"])
service = build("storage", 'v1', credentials=credentials)
BUCKET = "conversation-parser-speech.appspot.com"

client = storage.Client()
bucket = client.get_bucket(BUCKET)
blob = bucket.blob("new_test.pcm")
# blob.upload_from_file(file("/home/sergey/test-16bit16khz-pcm-s16le.pcm"), content_type="binary/octet-stream")
print blob.public_url




