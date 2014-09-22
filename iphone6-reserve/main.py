#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import sys
import os
import jinja2
import json

import logging
from google.appengine.ext import ndb
from google.appengine.api import memcache

sys.path.insert(0, 'libs')
import requests
from requests import Request, Session
from bs4 import BeautifulSoup
import xmltodict
import re
import copy
import collections

# Constants
iPhone6ModelsURL = "http://www.techwalls.com/differences-between-iphone-6-6-plus-models/"
iPhone6AvailabilityURL = "https://reserve.cdn-apple.com/CA/en_CA/reserve/iPhone/availability.json"
appleCAStoreURL = "https://www.apple.com/autopush/ca/retail/storelist/stores.xml"

iphone6Dictionary = {
    "MG3D2CL/A": "iPhone 6 16GB Gold Unlocked",
    "MG3L2CL/A": "iPhone 6 64GB Gold Unlocked", # target
    "MG3G2CL/A": "iPhone 6 128GB Gold Unlocked",
    "MG3A2CL/A": "iPhone 6 16GB Space Grey Unlocked",
    "MG3H2CL/A": "iPhone 6 64GB Space Grey Unlocked",
    "MG3E2CL/A": "iPhone 6 128GB Space Grey Unlocked",
    "MG3C2CL/A": "iPhone 6 16GB Silver Unlocked",
    "MG3K2CL/A": "iPhone 6 64GB Silver Unlocked", # target
    "MG3F2CL/A": "iPhone 6 128GB Silver Unlocked",
    "MG9P2CL/A": "iPhone 6 Plus 16GB Gold Unlocked",
    "MG9W2CL/A": "iPhone 6 Plus 64GB Gold Unlocked",
    "MG9T2CL/A": "iPhone 6 Plus 128GB Gold Unlocked",
    "MG9M2CL/A": "iPhone 6 Plus 16GB Space Grey Unlocked",
    "MG9U2CL/A": "iPhone 6 Plus 64GB Space Grey Unlocked",
    "MG9Q2CL/A": "iPhone 6 Plus 128GB Space Grey Unlocked",
    "MG9N2CL/A": "iPhone 6 Plus 16GB Silver Unlocked",
    "MG9V2CL/A": "iPhone 6 Plus 64GB Silver Unlocked",
    "MG9R2CL/A": "iPhone 6 Plus 128GB Silver Unlocked"
}

# Global variables for jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'html_template')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

# Basic Handler
class BasicHandler(webapp2.RequestHandler):
    # rewrite the write, more neat
    def write(self, *a, **kw):
        self.response.write(*a, **kw)
    # render helper function, use jinja2 to get template
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    # render page using jinja2
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def dumpJSON(self, dict):
        self.response.headers['Content-Type'] = 'application/json'
        self.write(json.dumps(dict))

class MainHandler(BasicHandler):
    """Handle for '/' """
    def get(self):
        self.render('home.html')
        # PersonalInformationQuestClass.main()

class UpdateHandler(BasicHandler):
    """Handle for '/' """
    def get(self):
        session = Session()
        availabilityJSON = session.get(iPhone6AvailabilityURL).content
        availabilityDict = json.loads(availabilityJSON)

        caStoresXML = session.get(appleCAStoreURL).content
        # self.write(caStoresXML)
        storesDict = xmltodict.parse(caStoresXML)["records"]["country"]
        # self.dumpJSON(storesDict)
        ontarioStoresList = []
        for eachStateDict in storesDict["state"]:
            if eachStateDict["@name"] == "Ontario":
                ontarioStoresList = eachStateDict["store"]
        # self.dumpJSON(ontarioStoresList)
        # self.write(storeNameForStoreID(ontarioStoresList, "R447"))

        # # logging.info(availabilityDict)
        lastUpdatedTimestamp = availabilityDict.pop("updated")
        storeIDs = availabilityDict.keys()
        for storeID in storeIDs:
            phonesDictInThisStore = availabilityDict[storeID]
            phoneKeys = phonesDictInThisStore.keys()
            for eachPhoneKey in phoneKeys:
                if eachPhoneKey in iphone6Dictionary:
                    replaceKeyInDictionary(phonesDictInThisStore, eachPhoneKey, iphone6Dictionary[eachPhoneKey])
        
        for storeID in storeIDs:
            replaceKeyInDictionary(availabilityDict, storeID, storeNameForStoreID(ontarioStoresList, storeID))

        availabilityDict["_updated"] = lastUpdatedTimestamp    
        orderedDict = collections.OrderedDict(sorted(availabilityDict.items()))
        self.dumpJSON(orderedDict)

def storeNameForStoreID(ontarioStoresList, storeID):
    for eachStore in ontarioStoresList:
        if eachStore["appleid"] == storeID:
            return eachStore["name"]

def replaceKeyInDictionary(dict, oldKey, newKey):
    if oldKey in dict:
        value = dict[oldKey]
        dict.pop(oldKey)
        dict[newKey] = value

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/update', UpdateHandler)
], debug=True)
