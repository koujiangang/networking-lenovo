# Copyright 2016 OpenStack Foundation
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
REST API client utility for configuring the Lenovo CNOS switch
"""



import requests
import requests.auth
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class LenovoRestClient(object):
    """
    Class to implement basic REST client operations
    """
    RESP_CODE_OK = 200

    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.tcp_port = 8090
        self.user = user
        self.passwd = passwd
        self.http_auth = requests.auth.HTTPBasicAuth(user, passwd)
        self.headers = {"Content-Type" : "application/json"}
        self.login_obj = "nos/api/login/"
        self.session = None

    def _build_url(self, obj):
        """ 
        Internal utility to build the URL for a request 
        obj - REST object
        """
        url = "http://%s:%s/%s" % (self.ip, self.tcp_port, obj)
        return url
    
    def login(self):
        """ Method to be called first in order to login on the switch """
        url = self._build_url(self.login_obj)
        self.session = requests.Session()

        max_tries = 3
        while max_tries > 0:
            resp = self._get(url)
            if resp.status_code == self.RESP_CODE_OK:
                break

    def _log_http(self, resp):
        """ Writes to the logs the HTTP operation's details """

        log_print = LOG.debug
        req = resp.request

        log_print("\n\n-------- REST HTTP --------------------")
        log_print("Request: ")
        log_print("\tHeaders: " + str(req.headers))
        log_print("\nBody:")
        log_print(req.body)

        log_print("\nResponse: ")
        log_print("\tURL: " + str(resp.url))
        log_print("\tStatus Code: " + str(resp.status_code))
        log_print("\tReason: " + str(resp.reason))
        log_print("\tCookies: " + str(resp.cookies))
        log_print("\nText:")
        log_print(resp.text)
        log_print("----------------------------\n\n")

    def _get(self, url):
        """ Internal method for the GET operation """
        resp = self.session.get(url, headers=self.headers, auth=self.http_auth)
        self._log_http(resp)
        return resp

    def _post(self, url, js_body):
        """ Internal method for the POST operation """
        resp = self.session.post(url, json=js_body, headers=self.headers, auth=self.http_auth)
        self._log_http(resp)
        return resp

    def _del(self, url):
        """ Internal method for the DELETE operation """
        self.session.delete(url, headers=self.headers, auth=self.http_auth)

    def _put(self, url, js_body):
        """ Internal method for the PUT operation """
        resp = self.session.put(url, json=js_body, headers=self.headers, auth=self.http_auth)
        self._log_http(resp)
        return resp

    def get(self, obj):
        """ Implements HTTP GET operation """
        url = self._build_url(obj)
        return self._get(url)

    def post(self, obj, js_body):
        """ Implements HTTP POST operation """
        url = self._build_url(obj)
        return self._post(url, js_body)

    def put(self, obj, js_body):
        """ Implements HTTP PUT operation """
        url = self._build_url(obj)
        return self._put(url, js_body)

    def delete(self, obj):
        """ Implements HTTP DELETE operation """
        url = self._build_url(obj)
        return self._del(url)

    def close(self):
        """ Closes the current session """
        if self.session is None:
            pass
        else:
            self.session.close()
            self.session = None 
    

