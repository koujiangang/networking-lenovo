# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
#
# Copyright (c) 2017, Lenovo. All rights reserved.
# All Rights Reserved.
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

"""Exceptions used by Lenovo NOS ML2 mechanism driver."""

from neutron.common import exceptions


class CredentialNotFound(exceptions.NeutronException):
    """Credential with this ID cannot be found."""
    message = _("Credential %(credential_id)s could not be found.")


class CredentialNameNotFound(exceptions.NeutronException):
    """Credential Name could not be found."""
    message = _("Credential %(credential_name)s could not be found.")


class CredentialAlreadyExists(exceptions.NeutronException):
    """Credential name already exists."""
    message = _("Credential %(credential_name)s already exists "
                "for tenant %(tenant_id)s.")


class NOSComputeHostNotConfigured(exceptions.NeutronException):
    """Connection to compute host is not configured."""
    message = _("Connection to %(host)s is not configured.")


class NOSConnectFailed(exceptions.NeutronException):
    """Failed to connect to NOS switch."""
    message = _("Unable to connect to NOS %(nos_host)s. Reason: %(exc)s.")


class NOSConfigFailed(exceptions.NeutronException):
    """Failed to configure NOS switch."""
    message = _("Failed to configure NOS: %(config)s. Reason: %(exc)s.")


class NOSSNMPFailure(exceptions.NeutronException):
    """Failed to configure NOS switch via SNMP."""
    message = ("SNMP operation '%(operation)s' to '%(nos_host)s' failed: %(error)s")


class NOSPortBindingNotFound(exceptions.NeutronException):
    """NOSPort Binding is not present."""
    message = _("NOS Port Binding (%(filters)s) is not present")

    def __init__(self, **kwargs):
        filters = ','.join('%s=%s' % i for i in kwargs.items())
        super(NOSPortBindingNotFound, self).__init__(filters=filters)


class NOSMissingRequiredFields(exceptions.NeutronException):
    """Missing required fields to configure nos switch."""
    message = _("Missing required field(s) to configure nos switch: "
                "%(fields)s")


class NoNOSSviSwitch(exceptions.NeutronException):
    """No usable nos switch found."""
    message = _("No usable NOS switch found to create SVI interface.")


class SubnetNotSpecified(exceptions.NeutronException):
    """Subnet id not specified."""
    message = _("No subnet_id specified for router gateway.")


class SubnetInterfacePresent(exceptions.NeutronException):
    """Subnet SVI interface already exists."""
    message = _("Subnet %(subnet_id)s has an interface on %(router_id)s.")


class PortIdForNOSSvi(exceptions.NeutronException):
        """Port Id specified for NOS SVI."""
        message = _('NOS hardware router gateway only uses Subnet Ids.')

class NOSRestHTTPError(exceptions.NeutronException):
    """REST HTTP operation error"""
    message = _("REST HTTP error %(http_code)d (%(http_reason)s)"
                " when %(http_op)s %(url)s: %(http_response)s")

class NOSJsonFieldNotFound(exceptions.NeutronException):
    """Expected JSON field not found in the REST response"""
    message = _("Expected JSON field '%(field)s' not found"
                " when accessing %(url)s; the JSON received: %(json)s")

class InvalidOSProtocol(exceptions.NeutronException):
    """ 
    Invalid (network operating system / protocol to access the switch)
    combination specified in the configuration file for the driver
    """
    message = _("Cannot find driver for protocol %(protocol)s on %(os)s")
