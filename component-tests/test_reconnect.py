#!/usr/bin/env python
import copy

from retrying import retry
from time import sleep

from util import start_cloudflared, wait_tunnel_ready, check_tunnel_not_ready, send_requests


class TestReconnect():
    default_ha_conns = 4
    default_reconnect_secs = 5
    extra_config = {
        "stdin-control": True,
    }

    def test_named_reconnect(self, tmp_path, component_tests_config):
        config = component_tests_config(self.extra_config)
        with start_cloudflared(tmp_path, config, new_process=True, allow_input=True) as cloudflared:
            # Repeat the test multiple times because some issues only occur after multiple reconnects
            self.assert_reconnect(config, cloudflared, 5)

    def test_classic_reconnect(self, tmp_path, component_tests_config):
        extra_config = copy.copy(self.extra_config)
        extra_config["hello-world"] = True
        config = component_tests_config(
            additional_config=extra_config, named_tunnel=False)
        with start_cloudflared(tmp_path, config, cfd_args=[], new_process=True, allow_input=True) as cloudflared:
            self.assert_reconnect(config, cloudflared, 1)

    def send_reconnect(self, cloudflared, secs):
        # Although it is recommended to use the Popen.communicate method, we cannot
        # use it because it blocks on reading stdout and stderr until EOF is reached
        cloudflared.stdin.write(f"reconnect {secs}s\n".encode())
        cloudflared.stdin.flush()

    def assert_reconnect(self, config, cloudflared, repeat):
        wait_tunnel_ready()
        for _ in range(repeat):
            for i in range(self.default_ha_conns):
                self.send_reconnect(cloudflared, self.default_reconnect_secs)
                expect_connections = self.default_ha_conns-i-1
                if expect_connections > 0:
                    wait_tunnel_ready(expect_connections=expect_connections)
                else:
                    check_tunnel_not_ready()

            sleep(self.default_reconnect_secs + 10)
            wait_tunnel_ready()
            send_requests(config.get_url(), 1)
