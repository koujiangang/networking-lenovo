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

#from cinder import exception
#from cinder.i18n import _, _LE, _LI, _LW
#from cinder import ssh_utils
#from cinder import utils

import time

LOG = logging.getLogger("MIHAI " + __name__)

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
            if self.conn_timeout:
                transport = ssh.get_transport()
                transport.sock.settimeout(None)
                transport.set_keepalive(self.conn_timeout)
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

    def run_ssh(self, cmd_list, check_exit_code=True):

        command = ' \n '.join(cmd_list)

        if not self.sshpool:
            self.sshpool = LenovoSSHPool(self.switch_ip,
                                             self.switch_port,
                                             None,
                                             self.switch_user,
                                             self.switch_pwd,
                                             min_size=1,
                                             max_size=5)
        try:
            with self.sshpool.item() as ssh:
                return processutils.ssh_execute(
                    ssh,
                    command,
                    check_exit_code=check_exit_code)

        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.warning("Error running SSH command: " + str(command))


    def _exec_cfg_no_debug(self, ssh, cmd):
            channel = ssh.invoke_shell()
            channel.send(cmd)
            channel.close()

    def _wait_for_prompt(self, ch):
        max_len = 9999
        output = str()

        time.sleep(5)
        while True:
            if ch.recv_ready():
                output += ch.recv(max_len)
#                LOG.warning("Partial: " + output)
            else:
                break
#                ch.send("\n")
#                continue
            if output.endswith("#"):
                break
            if output.endswith(">"):
                break

        #LOG.warning(output)
        return output

    def _exec_cfg_debug(self, ssh, cmd):
            channel = ssh.invoke_shell()
            output = str()

            cmd_list = cmd.split("\n")
            for cmd_item in cmd_list:
                LOG.warning("cmd_item: " + cmd_item)
                channel.send(cmd_item + "\n")
                output += self._wait_for_prompt(channel)
                channel.send("where\n")
                output += self._wait_for_prompt(channel)

            channel.close()

            LOG.warning("_exec_cfg_debug() stdout: " + output)

    def exec_cfg_session(self, cmd):
        """Execute cli configuration commands within a shell session
        """
        if not cmd.endswith('\n'):
            cmd += '\n'

        if not self.sshpool:
            self.sshpool = LenovoSSHPool(self.switch_ip,
                                             self.switch_port,
                                             None,
                                             self.switch_user,
                                             self.switch_pwd,
                                             min_size=1,
                                             max_size=5)

        LOG.debug("exec_cfg_session(): command " + cmd)

        try:
            with self.sshpool.item() as ssh:
                self._exec_cfg_debug(ssh, cmd)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.exception("Error executing command via ssh.")




    def ssh_execute(self, cmd_list, check_exit_code=True, attempts=1):
        """Execute cli with status update.
        Executes CLI commands where status return is expected.
        cmd_list is a list of commands, where each command is itself
        a list of parameters.  We use utils.check_ssh_injection to check each
        command, but then join then with " ; " to form a single command.
        """

        # Check that each command is secure
#        for cmd in cmd_list:
#            self.utils.check_ssh_injection(cmd)

        # Combine into a single command.
#        command = ' \n '.join(map(lambda x: ' '.join(x), cmd_list))
        command = '\n'.join(cmd_list)

        if not self.sshpool:
            self.sshpool = LenovoSSHPool(self.switch_ip,
                                             self.switch_port,
                                             None,
                                             self.switch_user,
                                             self.switch_pwd,
                                             min_size=1,
                                             max_size=5)
        stdin, stdout, stderr = None, None, None
        LOG.debug("Executing command via ssh: %s", command)
        last_exception = None
        try:
            with self.sshpool.item() as ssh:
                while attempts > 0:
                    attempts -= 1
                    try:
                        LOG.warning("Execute ssh cmd: " + command + "\n\n\n")
                        stdin, stdout, stderr = ssh.exec_command(command)
                        LOG.debug("stdout: " + str(stdout.readlines()))
                        LOG.debug("stderr: " + str(stderr.readlines()))
                        channel = stdout.channel
                        exit_status = channel.recv_exit_status()
                        LOG.debug("Exit Status from ssh: %s", exit_status)
                        # exit_status == -1 if no exit code was returned
                        if exit_status != -1:
                            LOG.debug('Result was %s', exit_status)
                            if check_exit_code and exit_status != 0:
                                raise processutils.ProcessExecutionError(
                                    exit_code=exit_status,
                                    stdout=stdout,
                                    stderr=stderr,
                                    cmd=command)
                            else:
                                return True
                        else:
                            return True
                    except Exception as e:
                        LOG.exception('Error executing SSH command.')
                        last_exception = e
                        greenthread.sleep(random.randint(20, 500) / 100.0)
                LOG.debug("Handling error case after SSH: %s", last_exception)
                try:
                    raise processutils.ProcessExecutionError(
                        exit_code=last_exception.exit_code,
                        stdout=last_exception.stdout,
                        stderr=last_exception.stderr,
                        cmd=last_exception.cmd)
                except AttributeError:
                    raise processutils.ProcessExecutionError(
                        exit_code=-1,
                        stdout="",
                        stderr="Error running SSH command",
                        cmd=command)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.exception("Error executing command via ssh.")
        finally:
            if stdin:
                stdin.flush()
                stdin.close()
            if stdout:
                stdout.close()
            if stderr:
                stderr.close()
