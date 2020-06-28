#!/usr/bin/env python3
# encoding:utf-8
# author:zhiheren

import sys, time
import paramiko


class SSHManager_without_sudo:
    def __init__(self, server, port, login_user, login_pass, root_pass):
        '''
        没有 sudo 用户,但是知道 root 密码
        :param server: IP 地址
        :param login_user: 普通用户,用于登录
        :param login_pass: 普通用户密码
        :param root_pass: root 用户密码
        '''
        self._server = server
        self._port = port
        self._login_user = login_user
        self._login_pass = login_pass
        self._root_pass = root_pass
        self._tran = None
        self._chan = None

    def __del__(self):
        if self._chan:
            self._chan.close()
        if self._tran:
            self._tran.close()

    def _conn(self):
        self._tran = paramiko.Transport((self._server, self._port))
        self._tran.start_client()
        self._tran.auth_password(self._login_user, self._login_pass)
        self._chan = self._tran.open_session()
        self._chan.get_pty()
        self._chan.invoke_shell()

    def exec_command(self, command_list):
        self._conn()
        cmd_list = command_list.copy()
        while True:
            data = self._chan.recv(1024).decode()  # 服务器的回显信息
            sys.stdout.write(data)
            sys.stdout.flush()
            if self._login_user in data or '$' in data:
                self._chan.send('su - \r\n')  # 向服务器发送 su - 命令
                continue
            if 'Password' in data:
                self._chan.send(self._root_pass + '\r\n')  # 向服务器发送 root 密码
                continue
            if 'root' in data or '#' in data:
                try:
                    command = cmd_list.pop(0)
                    self._chan.send(command + '\r\n')
                    time.sleep(1)
                except:
                    break


class SSHManager_with_sudo:
    def __init__(self, server, port, login_user, login_pass):
        '''
        没有 sudo 用户,但是知道 root 密码
        :param server: IP 地址
        :param login_user: 普通用户,用于登录,且具有 sudo 权限
        :param login_pass: 普通用户密码
        '''
        self._server = server
        self._port = port
        self._login_user = login_user
        self._login_pass = login_pass
        self._tran = None
        self._chan = None

    def __del__(self):
        if self._chan:
            self._chan.close()
        if self._tran:
            self._tran.close()

    def _conn(self):
        self._tran = paramiko.Transport((self._server, self._port))
        self._tran.start_client(timeout=3)
        self._tran.auth_password(self._login_user, self._login_pass)
        self._chan = self._tran.open_session()
        self._chan.get_pty()
        self._chan.invoke_shell()

    def exec_command(self, command_list):
        self._conn()
        cmd_list = command_list.copy()
        while True:
            data = self._chan.recv(1024).decode()  # 服务器的回显信息
            sys.stdout.write(data)
            sys.stdout.flush()

            if self._login_user in data and '~]$' in data:
                self._chan.send('sudo su -' + '\r\n')
                continue
            if '[sudo]' in data:
                self._chan.send(self._login_pass + '\r\n')
                continue
            if 'root' in data or '#' in data:
                try:
                    command = cmd_list.pop(0)
                    self._chan.send(command + '\r\n')
                    time.sleep(1)
                except:
                    break


def batch_exec_command(server_info_file, command_list):
    with open(server_info_file, 'r', encoding='utf-8') as file:
        for server_info in file:
            server, login_user, login_pass, root_pass = server_info.strip().split(',')
            exec_command(server, login_user, login_pass, root_pass, command_list)


def exec_command(server, login_user, login_pass, root_pass, command_list, port=22):
    command_su = 'su -\r\n'
    com_list = command_list.copy()
    with paramiko.Transport((server, port)) as tran:
        tran.start_client()
        tran.auth_password(login_user, login_pass)
        with tran.open_session() as chan:
            chan.get_pty()
            chan.invoke_shell()
            while True:
                data = chan.recv(1024).decode()  # 服务器的回显信息
                sys.stdout.write(data)
                sys.stdout.flush()
                if login_user in data or '$' in data:
                    chan.send(command_su)  # 向服务器发送su -命令
                    continue
                if 'Password' in data:
                    chan.send(root_pass + '\r')  # 向服务器发送root密码
                    continue
                if 'root' in data or '#' in data:
                    try:
                        command = com_list.pop(0)
                        chan.send(command + '\r\n')
                        time.sleep(1)
                    except:
                        break


def batch_sudo_exec_command(server_info_file, command_list):
    with open(server_info_file, 'r', encoding='utf-8') as file:
        for server_info in file:
            server, sudo_user, login_pass = server_info.strip().split(',')
            sudo_exec_command(server, sudo_user, login_pass, command_list)


def sudo_exec_command(server, sudo_user, login_pass, command_list, port=22):
    com_list = command_list.copy()
    with paramiko.Transport((server, port)) as tran:
        tran.start_client()
        tran.auth_password(sudo_user, login_pass)
        with tran.open_session() as chan:
            chan.get_pty()
            chan.invoke_shell()
            while True:
                data = chan.recv(1024).decode()  # 服务器的回显信息
                sys.stdout.write(data)
                sys.stdout.flush()

                if '(current) UNIX password:' in data:
                    raise Exception

                if sudo_user in data and '~]$' in data:
                    chan.send('sudo su -' + '\r\n')
                    continue
                if '[sudo]' in data:
                    chan.send(login_pass + '\r\n')
                    continue
                if 'root' in data or '#' in data:
                    try:
                        command = com_list.pop(0)
                        chan.send(command + '\r\n')
                        time.sleep(1)
                    except:
                        break


if __name__ == '__main__':
    # ssh = SSHManager_without_sudo(
    #     server='192.168.2.3',
    #     port=22,
    #     login_user='admin',
    #     login_pass='admin@123',
    #     root_pass='root',
    # )
    command_list = [
        'echo "something" >> /tmp/something',
    ]
    server_list = 'server_list'
    err_list = 'err_list'

    with open(server_list, 'r', encoding='utf8') as file:
        for server in file:
            sys.stdout.write(server)
            sys.stdout.flush()
            try:
                ssh = SSHManager_with_sudo(
                    server=server.strip(),
                    port=22,
                    login_user='user',
                    login_pass='password',
                )
                ssh.exec_command(command_list)
            except:
                with open(err_list, 'a+', encoding='utf8') as err_file:
                    err_file.write(server)
