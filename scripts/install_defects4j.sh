#!/usr/bin/env bash
# Install Defects4J 1.4.0 and apply SoapFL's Defects4J_mod overlay.
# NOT tested by the author of this repo -- read it before running. Needs Java 8, git, perl, svn.
# Usage: scripts/install_defects4j.sh [install-dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$ROOT/external/defects4j}"
if [ ! -d "$DEST/.git" ]; then
  git clone https://github.com/rjust/defects4j.git "$DEST"
fi
git -C "$DEST" checkout --quiet v1.4.0
(cd "$DEST" && ./init.sh) || true   # v1.4.0's init.sh downloads from people.cs.umass.edu (404 now) and still reports success
(cd "$DEST/project_repos" && wget -q -O repos.zip https://defects4j.org/downloads/defects4j-repos.zip \
  && unzip -q repos.zip && mv defects4j/project_repos/* . && rm -rf defects4j repos.zip)
(cd "$DEST/framework/lib/build_systems/gradle" && wget -q https://defects4j.org/downloads/defects4j-gradle-dists-v3.zip https://defects4j.org/downloads/defects4j-gradle-deps-v3.zip \
  && mkdir -p dists && unzip -q -u defects4j-gradle-dists-v3.zip -d dists && unzip -q -u defects4j-gradle-deps-v3.zip && rm -f defects4j-gradle-*-v3.zip)
(cd "$DEST" && cpanm --notest --installdeps .)   # Perl modules (DBI, ...); may need cpanminus + build tools
"$DEST/framework/bin/defects4j" info -p Lang > /dev/null && echo "Defects4J OK"   # fails loudly if the setup is incomplete
cp -r "$ROOT/external/SoapFL/Defects4J_mod/defects4j-1.4.0-jvm-mod/." "$DEST/"
echo
echo "Defects4J installed in $DEST. Add to your env:"
echo "  export DEFECTS4J_HOME=$DEST"
echo "  export PATH=\$DEFECTS4J_HOME/framework/bin:\$PATH"
echo "  export JAVA_HOME=<a Java 8 install>"
