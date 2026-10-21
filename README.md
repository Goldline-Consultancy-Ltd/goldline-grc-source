# Goldline GRC — source code

This repository is the complete source code of **Goldline GRC**, the governance, risk and compliance platform run by Goldline Consultancy.

Goldline GRC is a modified version of **CISO Assistant Community Edition v4.1.1**, copyright © intuitem SARL and contributors, licensed under the GNU Affero General Public License version 3 (AGPL v3). The original project is at <https://github.com/intuitem/ciso-assistant-community>.

## What we changed

Modified by Goldline Consultancy in October 2026. The changes are limited to branding:

- product name, logo, favicon and browser tab titles
- colour palette (navy, gold, cream)
- email wording, logo and signature
- a public "Licence and source" page linked from every screen

Every change is recorded in [`goldline-brand.patch`](goldline-brand.patch). The code in this repository is upstream v4.1.1 with that patch already applied.

## What is included

The parts needed to build and run the application: `backend/`, `frontend/`, `cli/`, the Docker Compose files and their helper scripts, and the licence files. Upstream documentation, CI configuration and other non-build material are left out; they are available unchanged in the upstream repository. The `enterprise/` directory is not included: it is licensed separately by intuitem and is not used by this build.

## Re-applying the patch to a new upstream version

```sh
git clone --depth 1 --branch <new-version> https://github.com/intuitem/ciso-assistant-community.git
cd ciso-assistant-community
git apply --check /path/to/goldline-brand.patch && git apply /path/to/goldline-brand.patch
```

If `--check` reports conflicts, the upstream files changed; update the patch for the new version before building.

## Building

```sh
./docker-compose-build.sh
```

## Licence

AGPL v3 — see [`LICENSE-AGPL.txt`](LICENSE-AGPL.txt) and [`LICENSE.md`](LICENSE.md). This program is distributed WITHOUT ANY WARRANTY; see sections 15 and 16 of the licence.
