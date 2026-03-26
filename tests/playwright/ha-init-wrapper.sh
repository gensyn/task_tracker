#!/bin/sh
# ha-init-wrapper.sh — pre-populates /etc/hosts before handing off to the
# real Home Assistant init script (/init).
#
# Alpine Linux (musl libc) cannot resolve Docker container hostnames via
# Python's socket module because musl's DNS resolver fails against Docker's
# embedded DNS server (127.0.0.11) in some CI environments, even though
# busybox's nslookup (which makes direct UDP queries) works fine.
#
# Task Tracker has no external service dependencies, so this wrapper simply
# hands off to the original HA init process without any host resolution.

exec /init
