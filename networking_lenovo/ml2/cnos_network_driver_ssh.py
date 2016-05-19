# Copyright 2013 OpenStack Foundation
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
Implements CNOS config over SSHv2 API Client
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import constants as const
from networking_lenovo.ml2 import exceptions as cexc
from networking_lenovo.ml2 import nos_db_v2
from networking_lenovo.ml2 import cnos_cli_snippets as snipp
from networking_lenovo.ml2 import ssh_conn_utils

LOG = logging.getLogger(__name__)


class LenovoCNOSDriverSSH(object):
    """NOS Driver Main Class."""
    def __init__(self):
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict
        self.connections = {}


    def _ssh_exec_cmds(self, host, cmd, allowed_exc_strs=None):
        """Execute commands on the switch through SSH

        :param nos_host: IP address of switch to configure
        :param cmd: String of commands to be executed
        :param allowed_exc_strs: Exceptions which have any of these strings
                                 as a subset of their exception message
                                 (str(exception)) can be ignored

        :raises: NOSConfigFailed

        """
        if not allowed_exc_strs:
            allowed_exc_strs = []

        ssh_port = int(self.nos_switches[host, 'ssh_port'])
        user = self.nos_switches[host, const.USERNAME]
        password = self.nos_switches[host, const.PASSWORD]
        sshclient = ssh_conn_utils.LenovoSSH(host, ssh_port, user, password)

        try:
            sshclient.exec_cfg_session(cmd)
        except Exception as e:
            for exc_str in allowed_exc_strs:
                if exc_str in str(e):
                    break
            else:
                # Raise a Neutron exception. Include a description of
                # the original ncclient exception.
                raise cexc.NOSConfigFailed(config=cmd, exc=e)


    def _ssh_config(self, host, cmd):
        """Execute configuration command on the switch through SSH
        :param nos_host: IP address of switch to configure
        :param cmd: Command to be executed

        """
        self._ssh_exec_cmds(host, cmd)


    def _create_cfg_snippet(self, customized_config):
        """Create a config snippet for the CNOS Switch Configuration.
        """

        conf_snippet = snipp.CNOS_CLI_START_CONF + customized_config
        conf_snippet += snipp.CNOS_CLI_END_CONF

        return conf_snippet

    def _convert_intf_type(self, intf_type):
        """Convert to the proper CNOS keyword used for the interface type
        """

        if intf_type == 'port':
            cnos_word = 'ethernet'
        elif intf_type == 'portchannel':
            cnos_word = 'port-aggregation'
        else:
            LOG.warning("Unknown interface type: " + intf_type)
            cnos_word = intf_type

        return cnos_word


    def _create_vlan(self, nos_host, vlanid, vlanname):
        """Create a VLAN on NOS Switch given the VLAN ID and Name."""
	try:
            cmd1 = snipp.CNOS_CLI_CMD_VLAN_CONF % (vlanid, vlanname)
            confstr = self._create_cfg_snippet(
                snipp.CNOS_CLI_CMD_VLAN_CONF % (vlanid, vlanname))
            LOG.debug(_("CNOSDriver create_vlan: %s"), confstr)

            self._ssh_config(nos_host, confstr)
#            self._edit_config(nos_host, target='running', config=confstr)
	except cexc.NOSConfigFailed:
	    with excutils.save_and_reraise_exception():
                self.delete_vlan(nos_host, vlanid)
		

        # Enable VLAN active and no-shutdown states. Some versions of
        # NOS switch do not allow state changes for the extended VLAN
        # range (1006-4094), but these errors can be ignored (default
        # values are appropriate).
        try:
            confstr = self._create_cfg_snippet(snipp.CNOS_CLI_CMD_VLAN_NO_SHUTDOWN % vlanid)
#            self._edit_config( nos_host, target='running', config=confstr)
        except cexc.NOSConfigFailed:
            with excutils.save_and_reraise_exception():
                self.delete_vlan(nos_host, vlanid)


    def delete_vlan(self, nos_host, vlanid):
        """Delete a VLAN on NOS Switch given the VLAN ID."""
        confstr = snipp.CNOS_CLI_CMD_NO_VLAN_CONF % vlanid
        confstr = self._create_cfg_snippet(confstr)

        LOG.debug(_("CNOSDriver delete_vlan: %s"), confstr)

        self._ssh_config(nos_host, confstr)


    def enable_vlan_on_trunk_int(self, nos_host, vlanid, intf_type,
                                 interface):
        """Enable a VLAN on a trunk interface."""
        # If more than one VLAN is configured on this interface then
        # include the 'add' keyword.
        if len(nos_db_v2.get_port_switch_bindings(
                '%s:%s' % (intf_type, interface), nos_host)) == 1:
            snippet = snipp.CNOS_CLI_CMD_INT_VLAN
        else:
            snippet = snipp.CNOS_CLI_CMD_INT_VLAN_ADD

        intf_type = self._convert_intf_type(intf_type)

        confstr = snippet % (intf_type, interface, vlanid)
        confstr = self._create_cfg_snippet(confstr)

        LOG.debug(_("NOSDriver enable_vlan: %s"), confstr)

        self._ssh_config(nos_host, confstr)
#        self._edit_config(nos_host, target='running', config=confstr)


    def disable_vlan_on_trunk_int(self, nos_host, vlanid, intf_type, interface):
        """Disable a VLAN on a trunk interface."""

        intf_type = self._convert_intf_type(intf_type)

        confstr = (snipp.CNOS_CLI_CMD_NO_VLAN_INT %
                   (intf_type, interface, vlanid))
        confstr = self._create_cfg_snippet(confstr)

        LOG.debug(_("NOSDriver disable_vlan: %s"), confstr)

        self._ssh_config(nos_host, confstr)
#        self._edit_config(nos_host, target='running', config=confstr)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, nos_port):
        """Create VLAN and trunk it on the specified ports."""
        self._create_vlan(nos_host, vlan_id, vlan_name)
        LOG.debug(_("NOSDriver created VLAN: %s"), vlan_id)
        if nos_port:
            self.enable_vlan_on_trunk_int(nos_host, vlan_id, intf_type,
                                          nos_port)
