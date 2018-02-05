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

# Copyright (c) 2017, Lenovo. All rights reserved.
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

"""
Implements a NOS-OS SNMP Client
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import constants as const
from networking_lenovo.ml2 import exceptions as cexc
from networking_lenovo.ml2 import nos_db_v2
from networking_lenovo.ml2 import nos_snippets as snipp

LOG = logging.getLogger(__name__)

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp import error as snmp_error
from pysnmp.proto import rfc1902

SNMP_PORT = 161
SNMP_V1 = '1'
SNMP_V2C = '2c'
SNMP_V3 = '3'
SNMP_AUTH_MD5 = 'MD5'
SNMP_AUTH_SHA = 'SHA'
SNMP_PRIV_DES = 'DES'
SNMP_PRIV_AES = 'AES-128'

USM_NO_AUTH   = (1, 3, 6, 1, 6, 3, 10, 1, 1, 1)
USM_MD5_AUTH  = (1, 3, 6, 1, 6, 3, 10, 1, 1, 2) 
USM_SHA_AUTH  = (1, 3, 6, 1, 6, 3, 10, 1, 1, 3)
USM_NO_PRIV   = (1, 3, 6, 1, 6, 3, 10, 1, 2, 1)
USM_DES_PRIV  = (1, 3, 6, 1, 6, 3, 10, 1, 2, 2)
USM_AES_PRIV  = (1, 3, 6, 1, 6, 3, 10, 1, 2, 4)

cmdGen = cmdgen.CommandGenerator()
oid_enterprise = (1, 3, 6, 1, 4, 1,)
sysDescr = (1, 3, 6, 1, 2, 1, 1, 1, 0)

GRYPHONFC_SYSDESCR = "G8264CS"
PEGASUS_SYSDESCR = "G8264-T"
GRYPHON_SYSDESCR = "G8264"
COMPASSR_SYSDESCR = "EN4093R"
COMPASS_SYSDESCR = "EN4093"
COMPASSFC_SYSDESCR = "CN4093"
EAGLE_SYSDESCR = "SI4093"
MERCURY_SYSDESCR = "SI4091"
SKEETER_SYSDESCR = "G8124-E"
SCOOTER_SYSDESCR = "G8124"
KARKINOS_SYSDESCR = "G7028"
EARTH_SYSDESCR = "G7052"
JUPITER_SYSDESCR = "G8296"
PIGLET_SYSDESCR = "G8052"
KRAKEN_SYSDESCR = "G8332"
MARS_SYSDESCR = "G8272"

gryphonfc_oid = {
    'device':                 "GryphonFC",
    'vlanNewCfgState':        (20301, 2, 7, 15, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 7, 15, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 7, 15, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 7, 15, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 7, 15, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 7, 15, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 7, 15, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 7, 15, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 7, 15, 1, 1, 1, 2, 0),
    }

pegasus_oid = {
    'device':                 "Pegasus",
    'vlanNewCfgState':        (20301, 2, 7, 13, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 7, 13, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 7, 13, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 7, 13, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 7, 13, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 7, 13, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 7, 13, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 7, 13, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 7, 13, 1, 1, 1, 2, 0),
}

gryphon_oid = {
    'device':                 "Gryphon",
    'vlanNewCfgState':        (26543, 2, 7, 6, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (26543, 2, 7, 6, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (26543, 2, 7, 6, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (26543, 2, 7, 6, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (26543, 2, 7, 6, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (26543, 2, 7, 6, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (26543, 2, 7, 6, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (26543, 2, 7, 6, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (26543, 2, 7, 6, 1, 1, 1, 2, 0)   ,
}

compassr_oid = {
    'device':                 "CompassR",
    'vlanNewCfgState':        (20301, 2, 5, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 5, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 5, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 5, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 5, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 5, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 5, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 5, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 5, 1, 1, 1, 2, 0),
}

compass_oid = {
    'device':                 "Compass",
    'vlanNewCfgState':        (20301, 2, 5, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 5, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 5, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 5, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 5, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 5, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 5, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 5, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 5, 1, 1, 1, 2, 0),
}

compassfc_oid = {
    'device':                 "CompassFC",
    'vlanNewCfgState':        (20301, 2, 5, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 5, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 5, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 5, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 5, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 5, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 5, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 5, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 5, 1, 1, 1, 2, 0),
}

eagle_oid = {
    'device':                 "Eagle",
    'vlanNewCfgState':        (20301, 2, 5, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 5, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 5, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 5, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 5, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 5, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 5, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 5, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 5, 1, 1, 1, 2, 0),
}

mercury_oid = {
    'device':                 "Mercury",
    'vlanNewCfgState':        (19046, 2, 18, 23, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (19046, 2, 18, 23, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (19046, 2, 18, 23, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (19046, 2, 18, 23, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (19046, 2, 18, 23, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (19046, 2, 18, 23, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (19046, 2, 18, 23, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (19046, 2, 18, 23, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (19046, 2, 18, 23, 1, 1, 1, 2, 0),
}

scooter_oid = {
    'device':                 "Scooter",
    'vlanNewCfgState':        (26543, 2, 7, 4, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (26543, 2, 7, 4, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (26543, 2, 7, 4, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (26543, 2, 7, 4, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (26543, 2, 7, 4, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (26543, 2, 7, 4, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (26543, 2, 7, 4, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (26543, 2, 7, 4, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (26543, 2, 7, 4, 1, 1, 1, 2, 0),
}

skeeter_oid = {
    'device':                 "Skeeter",
    'vlanNewCfgState':        (26543, 2, 7, 4, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (26543, 2, 7, 4, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (26543, 2, 7, 4, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (26543, 2, 7, 4, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (26543, 2, 7, 4, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (26543, 2, 7, 4, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (26543, 2, 7, 4, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (26543, 2, 7, 4, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (26543, 2, 7, 4, 1, 1, 1, 2, 0),
}

karkinos_oid = {
    'device':                 "Karkinos",
    'vlanNewCfgState':        (20301, 2, 7, 17, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 7, 17, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 7, 17, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 7, 17, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 7, 17, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 7, 17, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 7, 17, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 7, 17, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 7, 17, 1, 1, 1, 2, 0),
}

earth_oid = {
    'device':                 "Earth",
    'vlanNewCfgState':        (20301, 2, 7, 18, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 7, 18, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 7, 18, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 7, 18, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 7, 18, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 7, 18, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 7, 18, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 7, 18, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 7, 18, 1, 1, 1, 2, 0),
} 

jupiter_oid = {
    'device':                 "Jupiter",
    'vlanNewCfgState':        (19046, 2, 7, 22, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (19046, 2, 7, 22, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (19046, 2, 7, 22, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (19046, 2, 7, 22, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (19046, 2, 7, 22, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (19046, 2, 7, 22, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (19046, 2, 7, 22, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (19046, 2, 7, 22, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (19046, 2, 7, 22, 1, 1, 1, 2, 0),
}

piglet_oid = {
    'device':                 "Piglet",
    'vlanNewCfgState':        (26543, 2, 7, 7, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (26543, 2, 7, 7, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (26543, 2, 7, 7, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (26543, 2, 7, 7, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (26543, 2, 7, 7, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (26543, 2, 7, 7, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (26543, 2, 7, 7, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (26543, 2, 7, 7, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (26543, 2, 7, 7, 1, 1, 1, 2, 0),
}

kraken_oid = {
    'device':                 "Kraken",
    'vlanNewCfgState':        (20301, 2, 7, 16, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (20301, 2, 7, 16, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (20301, 2, 7, 16, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (20301, 2, 7, 16, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (20301, 2, 7, 16, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (20301, 2, 7, 16, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (20301, 2, 7, 16, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (20301, 2, 7, 16, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (20301, 2, 7, 16, 1, 1, 1, 2, 0),

}

mars_oid = {
    'device':                 "Mars",
    'vlanNewCfgState':        (19046, 2, 7, 24, 2, 1, 1, 3, 1, 4),
    'vlanNewCfgVlanName':     (19046, 2, 7, 24, 2, 1, 1, 3, 1, 2),
    'vlanNewCfgDelete':       (19046, 2, 7, 24, 2, 1, 1, 3, 1, 7),
    'vlanNewCfgAddPort':      (19046, 2, 7, 24, 2, 1, 1, 3, 1, 5),
    'vlanNewCfgRemovePort':   (19046, 2, 7, 24, 2, 1, 1, 3, 1, 6),
    'agPortNewCfgVlanTag':    (19046, 2, 7, 24, 1, 1, 2, 3, 1, 3),
    'agPortNewCfgPVID':       (19046, 2, 7, 24, 1, 1, 2, 3, 1, 6),
    'trunkGroupInfoPorts':    (19046, 2, 7, 24, 2, 3, 9, 1, 1, 3),
    'agApplyConfiguration':   (19046, 2, 7, 24, 1, 1, 1, 2, 0),
}

class LenovoNOSDriverSNMP(object):
    """NOS SNMP Driver Main Class."""
    PLUGIN_FOR_OLD_RELEASE = "compatible"

    def __init__(self):
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict
        self.nos_oid_table = {}

    def _get_auth(self, nos_host):
        if self.nos_switches[nos_host, 'snmp_version'] == SNMP_V3:
            nos_user = self.nos_switches[nos_host, 'snmp_user'] 
            nos_authkey = None
            if (nos_host, 'snmp_authkey') in self.nos_switches:
                nos_authkey = self.nos_switches[nos_host, 'snmp_authkey'] 
                if (nos_host, 'snmp_auth') in self.nos_switches:
                    nos_auth = USM_SHA_AUTH if self.nos_switches[nos_host, 'snmp_auth'] == SNMP_AUTH_SHA else USM_MD5_AUTH
                else:
                    nos_auth = USM_MD5_AUTH
            else:
                nos_auth = USM_NO_AUTH


            nos_privkey = None
            if (nos_host, 'snmp_privkey') in self.nos_switches:
                nos_privkey = self.nos_switches[nos_host, 'snmp_privkey'] 
                if (nos_host, 'snmp_priv') in self.nos_switches:
                    nos_priv = USM_AES_PRIV if self.nos_switches[nos_host, 'snmp_priv'] == SNMP_PRIV_AES else USM_DES_PRIV
                else:
                    nos_priv = USM_DES_PRIV
            else:
                nos_priv = USM_NO_PRIV

            #print('%s %s %s %s %s' % (nos_user, nos_authkey, nos_privkey, nos_auth, nos_priv))
            return cmdgen.UsmUserData(nos_user, nos_authkey, nos_privkey, nos_auth, nos_priv)
        else:
            mp_model = 1 if self.nos_switches[nos_host, 'snmp_version'] == SNMP_V2C else 0
            return cmdgen.CommunityData(self.nos_switches[nos_host, 'snmp_community'], mpModel=mp_model)

    def _get_transport(self, nos_host):
        return cmdgen.UdpTransportTarget((nos_host, int(self.nos_switches[nos_host, 'snmp_port'])))
    
    def _set(self, nos_host, varBinds):
        try:
            results = cmdGen.setCmd(self._get_auth(nos_host),
                                   self._get_transport(nos_host),
                                   *varBinds)
        except snmp_error.PySnmpError as e:
            raise cexc.NOSSNMPFailure(operation='SET', error=e)

        err_indication, err_status, err_index, var_binds = results
        if err_indication:
            print(err_indication)
            raise cexc.NOSSNMPFailure(operation='SET', error=err_indication)
        elif err_status:
            print('%s at %s' % (
                err_status.prettyPrint(),
                err_index and var_binds[int(err_index)-1][0] or '?'
                )
            )
            """not raise exception for error_status"""
            #raise cexc.NOSSNMPFailure(operation='SET', error=err_status.prettyPrint())
    
    def _get(self, nos_host, varBinds):
        try:
            results = cmdGen.getCmd(self._get_auth(nos_host),
                                   self._get_transport(nos_host),
                                   *varBinds)
        except snmp_error.PySnmpError as e:
            raise cexc.NOSSNMPFailure(operation='GET', error=e)

        err_indication, err_status, err_index, var_binds = results
        if err_indication:
            print(err_indication)
            raise cexc.NOSSNMPFailure(operation='GET', error=err_indication)
        elif err_status:
            print('%s at %s' % (
                err_status.prettyPrint(),
                err_index and var_binds[int(err_index)-1][0] or '?'
                )
            )
            raise cexc.SNMPFailure(operation='GET', error=err_status.prettyPrint())
        
        return var_binds
    

    def _get_sys_descr(self, nos_host):
        LOG.debug(_('_get_sys_descr %s'), nos_host)
        varBinds = []
        varBinds += sysDescr,
        
        ret = self._get(nos_host, varBinds)
        name, val = ret[0]
        return str(val)


    def _get_oid_table(self, nos_host):
        if nos_host in self.nos_oid_table:
            LOG.debug(_("device %s exist"), self.nos_oid_table[nos_host]['device'])
            return self.nos_oid_table[nos_host]
        else:
            LOG.debug(_("detect device type..."))
            sys_descr = self._get_sys_descr(nos_host)
            if sys_descr.find(GRYPHONFC_SYSDESCR) != -1:
                LOG.debug(_("this is a GryphonFC"))
                self.nos_oid_table[nos_host] = gryphonfc_oid
                return gryphonfc_oid
            elif sys_descr.find(PEGASUS_SYSDESCR) != -1:
                LOG.debug(_("this is a Pegasus"))
                self.nos_oid_table[nos_host] = pegasus_oid
                return pegasus_oid
            elif sys_descr.find(GRYPHON_SYSDESCR) != -1:
                LOG.debug(_("this is a Gryphon"))
                self.nos_oid_table[nos_host] = gryphon_oid
                return gryphon_oid
            elif sys_descr.find(COMPASSR_SYSDESCR) != -1:
                LOG.debug(_("this is a CompassR"))
                self.nos_oid_table[nos_host] = compassr_oid
                return compassr_oid
            elif sys_descr.find(COMPASS_SYSDESCR) != -1:
                LOG.debug(_("this is a Compass"))
                self.nos_oid_table[nos_host] = compass_oid
                return compass_oid
            elif sys_descr.find(COMPASSFC_SYSDESCR) != -1:
                LOG.debug(_("this is a CompassFC"))
                self.nos_oid_table[nos_host] = compassfc_oid
                return compassfc_oid
            elif sys_descr.find(EAGLE_SYSDESCR) != -1:
                LOG.debug(_("this is a Eagle"))
                self.nos_oid_table[nos_host] = eagle_oid
                return eagle_oid
            elif sys_descr.find(MERCURY_SYSDESCR) != -1:
                LOG.debug(_("this is a Mecury"))
                self.nos_oid_table[nos_host] = mercury_oid
                return mercury_oid
            elif sys_descr.find(SKEETER_SYSDESCR) != -1:
                LOG.debug(_("this is a Skeeter"))
                self.nos_oid_table[nos_host] = skeeter_oid
                return skeeter_oid
            elif sys_descr.find(SCOOTER_SYSDESCR) != -1:
                LOG.debug(_("this is a Scooter"))
                self.nos_oid_table[nos_host] = scooter_oid
                return scooter_oid
            elif sys_descr.find(KARKINOS_SYSDESCR) != -1:
                LOG.debug(_("this is a Karkinos"))
                self.nos_oid_table[nos_host] = karkinos_oid
                return karkinos_oid
            elif sys_descr.find(EARTH_SYSDESCR) != -1:
                LOG.debug(_("this is a Earth"))
                self.nos_oid_table[nos_host] = earth_oid
                return earth_oid
            elif sys_descr.find(JUPITER_SYSDESCR) != -1:
                LOG.debug(_("this is a Jupiter"))
                self.nos_oid_table[nos_host] = jupiter_oid
                return jupiter_oid
            elif sys_descr.find(PIGLET_SYSDESCR) != -1:
                LOG.debug(_("this is a Piglet"))
                self.nos_oid_table[nos_host] = piglet_oid
                return piglet_oid
            elif sys_descr.find(KRAKEN_SYSDESCR) != -1:
                LOG.debug(_("this is a Kraken"))
                self.nos_oid_table[nos_host] = kraken_oid
                return kraken_oid
            elif sys_descr.find(MARS_SYSDESCR) != -1:
                LOG.debug(_("this is a Mars"))
                self.nos_oid_table[nos_host] = mars_oid
                return mars_oid
            else:
                LOG.debug(_("unsupported device!"))
                raise cexc.NOSSNMPFailure(operation='DEVICE', error='Unsupported Device!')
                return None

        

    def _apply_config(self, nos_host):
        APPLY = 2
        oid_table = self._get_oid_table(nos_host)
        varBinds = []
        snmp_oid = oid_enterprise + oid_table['agApplyConfiguration']
        value = rfc1902.Integer(APPLY)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

    def _support_old_release(self, host):
        """
        If plugin_mode is not configured, assume the switch supports new release of ML2.
        Otherwise, call different REST API according to plugin_mode.
        :param host:
        :return:
        """
        try:
            plugin_mode = self.nos_switches[host, const.PLUGIN_MODE]
        except KeyError:
            return False

        if plugin_mode == self.PLUGIN_FOR_OLD_RELEASE:
            return True

        return False

    #create VLAN
    def _create_vlan(self, nos_host, vlan_id, vlan_name):
        """Create a VLAN on NOS Switch given the VLAN ID and Name."""
        LOG.debug(_('_create_vlan %s %d'), nos_host, vlan_id) 
        oid_table = self._get_oid_table(nos_host)

        varBinds = []
        ENABLED = 2
        snmp_oid = oid_enterprise + oid_table['vlanNewCfgState'] + (vlan_id,)
        value = rfc1902.Integer(ENABLED)
        varBinds += (snmp_oid, value),

        snmp_oid = oid_enterprise + oid_table['vlanNewCfgVlanName'] + (vlan_id,)
        value = rfc1902.OctetString(vlan_name)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        self._apply_config(nos_host)


    def delete_vlan(self, nos_host, vlan_id):
        """Delete a VLAN on NOS Switch given the VLAN ID."""
        LOG.debug(_('delete_vlan %s %d'), nos_host, vlan_id)
        oid_table = self._get_oid_table(nos_host)

        varBinds = []
        DELETE = 2
        snmp_oid = oid_enterprise + oid_table['vlanNewCfgDelete'] + (vlan_id,)
        value = rfc1902.Integer(DELETE)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        self._apply_config(nos_host)

    
    def enable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        LOG.debug(_('enable_vlan_on_trunk_int %s %d %s:%s'), nos_host, vlan_id, intf_type, interface)
        oid_table = self._get_oid_table(nos_host)
        
        trunk_init = False
        if len(nos_db_v2.get_port_switch_bindings(
                '%s:%s' % (intf_type, interface), nos_host)) == 1:
            trunk_init = True

        if intf_type == "portchannel":
            varBinds = []
            snmp_oid = oid_enterprise + oid_table['trunkGroupInfoPorts'] + (interface,) 
            varBinds += (snmp_oid),
            ret = self._get(nos_host, varBinds)
            _n, _v = ret[0]
            portmap = _v.asNumbers()
            port_base = 0
            for byte in portmap:
                if byte != 0:
                    bit = 7
                    while bit >= 0:
                        if (byte & (1<<bit)):
                            port_num = port_base + 7 - bit
                            LOG.debug(_("interface port %d"), port_num)
                            if trunk_init is True:
                                LOG.debug(_("    switchport mode trunk"))
                                LOG.debug(_("    switchport trunk allowed vlan 1"))
                                self._switchport_mode_trunk_init(nos_host, port_num)
                            LOG.debug(_("    switchport trunk allowed vlan add %d"), vlan_id)
                            self._enable_vlan_on_port(nos_host, vlan_id, port_num)
                        bit -= 1
                port_base += 8
        else:
            port_num = int(interface)
            LOG.debug(_("interface port %d"), port_num)
            if trunk_init is True:
                LOG.debug(_("    switchport mode trunk"))
                LOG.debug(_("    switchport trunk allowed vlan 1"))
                self._switchport_mode_trunk_init(nos_host, port_num)
            LOG.debug(_("    switchport trunk allowed vlan add %d"), vlan_id)
            self._enable_vlan_on_port(nos_host, vlan_id, port_num)
        
        self._apply_config(nos_host)
        

    def _switchport_mode_trunk_init(self, nos_host, port_num):
        """Enable a port as VLAN trunk mode."""
        LOG.debug(_('_switchport_mode_trunk_init %s %d'), nos_host, port_num)

        oid_table = self._get_oid_table(nos_host)

        """Change switchport to trunk mode, and set PVID = 1"""
        varBinds = []
        TAGGED = 2
        snmp_oid = oid_enterprise + oid_table['agPortNewCfgVlanTag'] + (port_num,)
        value = rfc1902.Integer(TAGGED)
        varBinds += (snmp_oid, value),

        snmp_oid = oid_enterprise + oid_table['agPortNewCfgPVID'] + (port_num,)
        value = rfc1902.Integer32(1)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        """Remove all other VLAN except 1 for the first time config this port"""
        try:
            switchHW = oid_table["device"]
        except KeyError:
            switchHW = ""
        if switchHW == "Piglet":#vlan range always 1-4094 for piglet, different from other switches
            max_vlan_id = 4094
        else:
            max_vlan_id = 4094 if self._support_old_release(nos_host) else 4095
        vlans = range(2, max_vlan_id+1)
        varBinds = []
        for vid in vlans:
            snmp_oid = oid_enterprise + oid_table['vlanNewCfgRemovePort'] + (vid,)
            value = rfc1902.Gauge32(port_num)
            varBinds += (snmp_oid, value),
            if vid%20 == 0:
                self._set(nos_host, varBinds)
                varBinds = []
        
        self._set(nos_host, varBinds)

 
    def _enable_vlan_on_port(self, nos_host, vlan_id, port_num):
        """Enable a VLAN on a port interface."""
        LOG.debug(_('_enable_vlan_on_port %s %d %d'), nos_host, vlan_id, port_num)

        oid_table = self._get_oid_table(nos_host)

        varBinds = []
        snmp_oid = oid_enterprise + oid_table['vlanNewCfgAddPort'] + (vlan_id,)
        value = rfc1902.Gauge32(port_num)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)


    def disable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        LOG.debug(_('disable_vlan_on_trunk_int %s %d %s'), nos_host, vlan_id, interface)

        oid_table = self._get_oid_table(nos_host)

        if intf_type == "portchannel":
            varBinds = []
            snmp_oid = oid_enterprise + oid_table['trunkGroupInfoPorts'] + (interface,) 
            varBinds += (snmp_oid),
            ret = self._get(nos_host, varBinds)
            _n, _v = ret[0]
            portmap = _v.asNumbers()
            port_base = 0
            for byte in portmap:
                if byte != 0:
                    bit = 7
                    while bit >= 0:
                        if (byte & (1<<bit)):
                            port_num = port_base + 7 - bit
                            LOG.debug(_("interface port %d"), port_num)
                            LOG.debug(_("    switchport trunk allowed vlan remove %d"), vlan_id)
                            self._disable_vlan_on_port(nos_host, vlan_id, port_num)
                        bit -= 1
                port_base += 8
        else:
            port_num = int(interface)
            LOG.debug(_("interface port %d"), port_num)
            LOG.debug(_("    switchport trunk allowed vlan remove %d"), vlan_id)
            self._disable_vlan_on_port(nos_host, vlan_id, port_num)
        
        self._apply_config(nos_host)

    
    def _disable_vlan_on_port(self, nos_host, vlan_id, port_num):
        """Disable a VLAN on a port interface."""
        LOG.debug(_('_disable_vlan_on_port %s %d %d'), nos_host, vlan_id, port_num)

        oid_table = self._get_oid_table(nos_host)

        varBinds = []

        snmp_oid = oid_enterprise + oid_table['vlanNewCfgRemovePort'] + (vlan_id,)
        value = rfc1902.Gauge32(port_num)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, interface):
        LOG.debug(_('create_and_trunk_vlan %s %d %s'), nos_host, vlan_id, interface)
        self._create_vlan(nos_host, vlan_id, vlan_name)
        if interface:
            self.enable_vlan_on_trunk_int(nos_host, vlan_id, intf_type, interface)
