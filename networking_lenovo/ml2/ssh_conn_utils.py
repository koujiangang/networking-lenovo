import random
import re
import os

from eventlet import greenthread
from eventlet import pools
from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils
import paramiko
import six
import time

class MihaiLog(object):
    def __init__(self):
        self.filename = "/home/openstack/logs/lenovo_ml2.log"

    def btrace(self):
        logfile = open(self.filename, "a")
        traceback.print_stack(file=logfile)
        logfile.close()

    def log(self, msg):
        logfile = open(self.filename, "a")
        logfile.write(str(msg))
        logfile.close()

mihailog = MihaiLog()
LOG = logging.getLogger(__name__)

class LenovoSSHPool(pools.Pool):
    """A simple eventlet pool to hold ssh connections."""

    def __init__(self, ip, port, conn_timeout, login, password=None,
                 *args, **kwargs):
        self.ip = ip
        self.port = port
        self.login = login
        self.password = password
        self.conn_timeout = conn_timeout if conn_timeout else None

        super(LenovoSSHPool, self).__init__(*args, **kwargs)

    def create(self):
        try:
            ssh = paramiko.SSHClient()

            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.password:
                ssh.connect(self.ip,
                            port=self.port,
                            username=self.login,
                            password=self.password,
                            timeout=self.conn_timeout)
            else:
                msg = "Specify a password or private_key"
                raise exceptions.NeutronException(msg)

            # Paramiko by default sets the socket timeout to 0.1 seconds,
            # ignoring what we set through the sshclient. This doesn't help for
            # keeping long lived connections. Hence we have to bypass it, by
            # overriding it after the transport is initialized. We are setting
            # the sockettimeout to None and setting a keepalive packet so that,
            # the server will keep the connection open. All that does is send
            # a keepalive packet every ssh_conn_timeout seconds.
#            if self.conn_timeout:
#                transport = ssh.get_transport()
#                transport.sock.settimeout(None)
#                transport.set_keepalive(self.conn_timeout)
            return ssh
        except Exception as e:
            msg = "Error connecting via ssh: %s" % six.text_type(e)
            LOG.error(msg)
            raise paramiko.SSHException(msg)

    def get(self):
        """Return an item from the pool, when one is available.
        This may cause the calling greenthread to block. Check if a
        connection is active before returning it.
        For dead connections create and return a new connection.
        """
        conn = super(LenovoSSHPool, self).get()
        if conn:
            if conn.get_transport().is_active():
                return conn
            else:
                conn.close()
        return self.create()

    def remove(self, ssh):
        """Close an ssh client and remove it from free_items."""
        ssh.close()
        if ssh in self.free_items:
            self.free_items.remove(ssh)
            if self.current_size > 0:
                self.current_size -= 1




class LenovoSSH(object):

    def __init__(self, switch_ip, switch_port, switch_user, switch_pwd):
        self.switch_ip = switch_ip
        self.switch_port = switch_port
        self.switch_user = switch_user
        self.switch_pwd = switch_pwd

        self.sshpool = None

    def _wait_for_prompt(self, ch):
        max_len = 9999
        output = str()

        while True:
            if ch.recv_ready():
                output += ch.recv(max_len)
            else:
                time.sleep(0.01)
                continue

            if "#" in output:
                break
            if ">" in output:
                break

        return output

    def _exec_cmd(self, ch, cmd):
        ch.send(cmd + "\n")
        return self._wait_for_prompt(ch)

    def _exec_multi_cmds(self, ssh, cmds_str):
            channel = ssh.invoke_shell()
            output = str()

            mihailog.log("\n\n---------------------------------------------")
            cmd_list = cmds_str.split("\n")
            for cmd_line in cmd_list:
                cmd = cmd_line.strip()
                if cmd:
                    mihailog.log("cmd_item: " + cmd + "\n")
                    output += self._exec_cmd(channel, cmd)

            channel.close()

            mihailog.log("_exec_cfg_debug() stdout: " + output + "\n")
            mihailog.log("---------------------------------------------")


    def exec_cfg_session(self, cmd):
        """Execute cli configuration commands within a shell session
        """
        if not self.sshpool:
            self.sshpool = LenovoSSHPool(self.switch_ip,
                                             self.switch_port,
                                             None,
                                             self.switch_user,
                                             self.switch_pwd,
                                             min_size=1,
                                             max_size=5)

        LOG.debug("exec_cfg_session(): command " + cmd)
        mihailog.log("exec_cfg_session(): command " + cmd + "\n")

        try:
            with self.sshpool.item() as ssh:
                self._exec_multi_cmds(ssh, cmd)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.exception("Error executing command via ssh.")


