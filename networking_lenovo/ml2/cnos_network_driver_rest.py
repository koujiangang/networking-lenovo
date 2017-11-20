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
Implements CNOS config over REST API Client
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import constants as const
from networking_lenovo.ml2 import exceptions as cexc
from networking_lenovo.ml2 import nos_db_v2

from requests.utils import quote
import requests
from rest_client import LenovoRestClient


LOG = logging.getLogger(__name__)


class LenovoCNOSDriverREST(object):
    """CNOS Driver Main Class."""

    VLAN_REST_OBJ = "nos/api/cfg/vlan/"
    VLAN_IFACE_REST_OBJ = "nos/api/cfg/vlan_interface/"

    REST_TCP_PORT_STR = "rest_tcp_port"
    REST_DEFAULT_PORT = 8090
    REST_DEFAULT_PORT_HTTPS = 443
    REST_USE_HTTPS_STR = "use_ssl"

    PLUGIN_FOR_OLD_RELEASE = "compatible"
    REST_VLAN_OPERATION = {"add": "add", "remove": "remove", "except": "except"}

    def __init__(self):
        self.switches = conf.ML2MechLenovoConfig.nos_dict

############ Private Methods ############################
    def _dbg_str(self, host, op, vlan_id, 
                 vlan_name=None, interface=None, intf_type=None):
        """ 
        Construct a string displayed in debug messages or exceptions
        for the main operations
        """
        dbg_fmt = "host %s %s vlan %d"
        args_lst = [host, op, vlan_id]

        if vlan_name:
            dbg_fmt += " (%s)"
            args_lst.append(vlan_name)

        if interface and intf_type:
            dbg_fmt += " on interface %s(type %s)"
            args_lst.extend([interface, intf_type])

        dbg_str = dbg_fmt % tuple(args_lst)
        return dbg_str


    def _connect(self, host): 
        """ Connect to the switch """
        user = self.switches[host, const.USERNAME]
        password = self.switches[host, const.PASSWORD]
        https_str = self.switches.get((host, self.REST_USE_HTTPS_STR),
                                      "true").lower()
        use_https = True
        if https_str != "true":
            use_https = False

        default_port = self.REST_DEFAULT_PORT
        if use_https:
            default_port = self.REST_DEFAULT_PORT_HTTPS
        tcp_port = self.switches.get((host, self.REST_TCP_PORT_STR),
                                     default_port)

        conn = LenovoRestClient(host, user, password, tcp_port, use_https)
        try:
            conn.login()
        except Exception as e:
            raise cexc.NOSConnectFailed(nos_host=host, exc=e)
        return conn


    def _check_process_resp(self, resp, expected_fields=None):
        """
        Check that a HTTP response was OK and in valid JSON format
        If it was, check that the expected fields are present in JSON response
        Otherwise it raises a NOSRestHTTPError exception

        Returns: 
             the JSON response
        """

        if resp.status_code != LenovoRestClient.RESP_CODE_OK:
            raise cexc.NOSRestHTTPError(http_code=resp.status_code,
                      http_reason=resp.reason, http_op=resp.request.method,
                      url=resp.url, http_response=resp.text)

        rj = resp.json()

        if not expected_fields:
            return rj

        for field in expected_fields:
            try:
                val = rj[field]
            except KeyError:
                raise cexc.NOSJsonFieldNotFound(field=field, url=resp.url, json=rj)

        return rj

    def _support_old_release(self, host):
        """
        If plugin_release is not configured, assume the switch supports new release of ML2.
        Otherwise, call different REST API according to plugin_release.
        :param host:
        :return:
        """
        try:
            plugin_release = self.switches[host, const.PLUGIN_RELEASE]
        except KeyError:
            return False

        if plugin_release == self.PLUGIN_FOR_OLD_RELEASE:
            return True

        return False

    def _create_vlan(self, conn, vlan_id, vlan_name):
        """ 
        Internal method to create the vlan 
        Parameters:
            conn - connection handler
            vlan_id - vlan identifier
            vlan_name - vlan name
        """

        req_js = {}
        req_js['vlan_id'] = vlan_id
        req_js['vlan_name'] = vlan_name
        req_js['admin_state'] = 'up'

        resp = conn.post(self.VLAN_REST_OBJ, req_js)
        self._check_process_resp(resp)


    def _conf_intf(self, conn, interface, mode, pvid, vlan_list):
        """
        Internal method to configure bridgeport for an interface
        Parameters:
            conn - connection handler
            interface - interface identifier (name)
            mode - 'access'(untagged) or 'trunk'(tagged)
            pvid - interface default vlan id
            vlan_list - list of vlans the interface belongs to
        """

        if not vlan_list:
            raise Exception('The interface should be in at least one vlan')

        if (mode == 'access') and (len(vlan_list) > 1):
            raise Exception('An access port cannot be in multiple vlans')

        req_js = {}
        req_js['if_name'] = interface
        req_js['bridgeport_mode'] = mode
        req_js['pvid'] = pvid
        req_js['vlans'] = vlan_list

        obj = self.VLAN_IFACE_REST_OBJ + quote(interface, safe='')
        resp = conn.put(obj, req_js)
        return resp


    def _get_vlist(self, vlist):
        """
        Internal method to obtain a vlan list from the JSON answer
        from the switch
        Parameters:
            vlist - the list of vlans the port 
                    or the special strings all or none
        """
        if vlist == "all":
            return list(range(1, 4095))
        elif vlist == "none":
            return []
        elif type(vlist) is not list:
            raise Exception("Unexpected vlan list: " + str(vlist))
        else:
            return vlist

    def _add_intf_to_vlan(self, conn, vlan_id, interface, support_old_release=False):
        """
        Internal method to add an interface to a vlan
        Parameters:
            conn - connection handler
            vlan_id - vlan identifier
            interface - interface identifier (name)
        """

        obj = self.VLAN_IFACE_REST_OBJ + quote(interface, safe='')

        resp = conn.get(obj)
        intf_info = self._check_process_resp(resp, expected_fields=['vlans', 'pvid'])

        crt_vlist = self._get_vlist(intf_info['vlans'])
        if vlan_id in crt_vlist:
            return

        new_vlist = crt_vlist[ : ]
        new_vlist.append(vlan_id)

        pvid = intf_info['pvid']
        mode = 'trunk'

        if support_old_release:
            new_vlist = crt_vlist[:]
            new_vlist.append(vlan_id)
        else:
            crt_mode = intf_info['bridgeport_mode']
            # If current mode is access mode, call with "{trunk, ["add", vlan_id]}" will configure the port as trunk all.
            if crt_mode == "access":
                new_vlist = [pvid, vlan_id]
            else:
                new_vlist = [self.REST_VLAN_OPERATION["add"]]
                new_vlist.append(vlan_id)

        resp = self._conf_intf(conn, interface, mode, pvid, new_vlist)
        self._check_process_resp(resp)



    def _rem_intf_from_vlan(self, conn, vlan_id, interface, support_old_release=False):
        """
        Internal method to remove an interface from a vlan
        Parameters:
            conn - connection handler
            vlan_id - vlan identifier
            interface - interface identifier (name)
        """

        obj = self.VLAN_IFACE_REST_OBJ + quote(interface, safe='')

        resp = conn.get(obj)
        intf_info = self._check_process_resp(resp, expected_fields=['vlans', 'pvid'])

        crt_vlist = self._get_vlist(intf_info['vlans'])
        if vlan_id not in crt_vlist:
            return

        pvid = intf_info['pvid']

        new_vlist = crt_vlist[:]
        new_vlist.remove(vlan_id)

        pvid = intf_info['pvid']

        if not new_vlist:
            raise Exception('Port ' + str(interface) + ' was only in vlan ' + str(vlan_id))

        if pvid == vlan_id:
            pvid = new_vlist[0]

        if len(new_vlist) > 1:
            mode = 'trunk'
        else:
            mode = 'access'

        if not support_old_release:
            if mode == 'access':
                new_vlist = [pvid]
            else:
                new_vlist = [self.REST_VLAN_OPERATION["remove"]]
                new_vlist.append(vlan_id)

        resp = self._conf_intf(conn, interface, mode, pvid, new_vlist)
        self._check_process_resp(resp)


    def _get_ifname(self, intf_type, interface):
        """
        Internal method to obtain the interface name based on its type and number
        Parameters:
            intf_type - interface type (port or portchannel)
            interface - interface number
        """
        if intf_type == 'port':
            ifname = 'Ethernet' + str(interface)
        elif intf_type == 'portchannel':
            ifname = 'po' + str(interface)
        else:
            raise Exception("Unknown interface type: " + intf_type)

        return ifname


############# Public Methods ############################
    def delete_vlan(self, host, vlan_id):
        """Delete a VLAN on CNOS Switch given the VLAN ID."""

        dbg_str = self._dbg_str(host, "delete", vlan_id)
        LOG.debug(dbg_str)

        conn = self._connect(host)
        obj = self.VLAN_REST_OBJ + str(vlan_id)
        resp = conn.delete(obj)
        conn.close()


    def enable_vlan_on_trunk_int(self, host, vlan_id, intf_type, interface):
        """Enable a VLAN on a trunk interface."""

        dbg_str = self._dbg_str(host, "enable", vlan_id, 
                                interface=interface, intf_type=intf_type)
        LOG.debug(dbg_str)

        conn = self._connect(host)
        try:
            if_name = self._get_ifname(intf_type, interface)
            self._add_intf_to_vlan(conn, vlan_id, if_name, self._support_old_release(host))
        except Exception as e:
            raise cexc.NOSConfigFailed(config=dbg_str, exc=e)
        conn.close()



    def disable_vlan_on_trunk_int(self, host, vlan_id, intf_type, interface):
        """Disable a VLAN on a trunk interface."""

        dbg_str = self._dbg_str(host, "disable", vlan_id,
                                interface=interface, intf_type=intf_type)
        LOG.debug(dbg_str)

        conn = self._connect(host)
        try:
            if_name = self._get_ifname(intf_type, interface)
            self._rem_intf_from_vlan(conn, vlan_id, if_name, self._support_old_release(host))
        except Exception as e:
            raise cexc.NOSConfigFailed(config=dbg_str, exc=e)
        conn.close()


    def create_and_trunk_vlan(self, host, vlan_id, vlan_name, intf_type, interface):
        """Create VLAN and trunk it on the specified ports."""

        dbg_str = self._dbg_str(host, "create and enable", vlan_id,
                                vlan_name=vlan_name, interface=interface, intf_type=intf_type)
        LOG.debug(dbg_str)

        conn = self._connect(host)
        try:
            if_name = self._get_ifname(intf_type, interface)
            self._create_vlan(conn, vlan_id, vlan_name)
            self._add_intf_to_vlan(conn, vlan_id, if_name, self._support_old_release(host))
        except Exception as e:
            raise cexc.NOSConfigFailed(config=dbg_str, exc=e)
        conn.close()

