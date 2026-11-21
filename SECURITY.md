# Security policy

## Supported versions

Only the latest released version receives fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's private
vulnerability reporting for this repository (Security tab, "Report a
vulnerability"). Include the version, your operating system, and steps to
reproduce.

## Scope

kcon-ui reads Kconfig and `.config` files and writes `.config` and minimal
configuration files at paths chosen by the user. It does not open network
connections or execute the contents of those files.
