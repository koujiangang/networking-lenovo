# Copyright (c) 2017, Lenovo.
# All Rights Reserved.
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

#-*-coding:utf-8-*- 
__author__ = 'liuxw9'
from oslo_log import log as logging
from enum import Enum
class NetworkMode(Enum):
    vlan = 1
    vxlan = 2
    vlan_vxlan = 3
    undefined = 9

LOG = logging.getLogger(__name__)
class Switch():
    switch_count = 0
    def __init__(self, mgmt_ip, init_config="", network_mode=NetworkMode.undefined):
        LOG.debug(_("NOS:switch init with IP:%s, init_config: %s, network mode: %s") ,mgmt_ip, init_config, network_mode)
        self._mgmt_ip = mgmt_ip
        self._configuration = init_config.split(';')
        self._nwv_global_config = False
        try:
            self._configuration.remove('')
        except:
            pass
        Switch.switch_count += 1
        self._network_mode = network_mode

    def get_nwv_global_config(self):
        return self._nwv_global_config

    def set_nwv_global_config(self, config):
        self._nwv_global_config = config

    def get_network_mode(self):
        return self._network_mode

    def set_network_mode(self, network_mode):
        self._network_mode = network_mode

    def configure(self, cli):#each cli end with ';'
        self._configuration.extend(cli.split(";"))
        try:
            self._configuration.remove('')
        except:
            pass
    def deconfigure(self, cli):
        every_cli = cli.split(";")
        for cmd in every_cli:
            if cmd in self._configuration:
                self._configuration.remove(cmd)
        try:
            self._configuration.remove('')
        except:
            pass

    def show_running(self,name=""):
        LOG.debug(_(name+str(self)+" switch_count:"+str(self.switch_count)+" show running:%s"),self._configuration)
