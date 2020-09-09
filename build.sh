#!/usr/bin/env bash
err() { echo; echo "ERROR: $*"; exit 1; }
kmd() { echo; echo ">>> $*" | fold -s; eval "$*" || err "at line \`$*\`"; }
get_gpgkey() { gpgKey=$(gpg --list-secret-keys --with-colons | grep "^sec" | sort -t: -k 5 -r | grep -o -E "[A-Z0-9]{8,}" | grep "[0-9]" | grep "[A-Z]" | grep -oE "[0-9A-Z]{8}$"); }

# Python major.minor version
pythonSiteLib=$(rpm -E "%{python3_sitelib}")
[[ $pythonSiteLib ]] || pythonSiteLib="/usr/lib/python3.6/site-packages"

# User and email
userName=$USER
userEmail=$(git config --get user.email)
[[ $userEmail ]] || userEmail="${userName}@localhost"

# GPG defaults
gpgBin=$(type -p gpg)
gpgConfig="gpg.cfg"
gpgKey=""
[[ $gpgKey ]] || get_gpgkey
gpgArgs="$gpgBin --force-v3-sigs --digest-algo=sha512  --no-verbose --no-armor --no-secmem-warning"

# Build defaults
epoch=3
topdir="$HOME/nvidia-plugin"
arch="noarch"


#
# Functions
#

clean_up() {
    rm -rf "$unpackDir"
    (cd "$topdir" && rm -rf -- BUILD BUILDROOT RPMS SRPMS SOURCES SPECS)
    exit 1
}

new_gpgkey()
{
    cat >$gpgConfig <<-EOF
	Key-Type: RSA
	Key-Length: 4096
	Name-Real: $userName
	Name-Email: $userEmail
	Expire-Date: 0
EOF

    kmd gpg --batch --generate-key $gpgConfig
    get_gpgkey
}

plugin_yum_rpm()
{
    mkdir -p "$topdir"
    (cd "$topdir" && rm -rf -- BUILD BUILDROOT)
    (cd "$topdir" && mkdir BUILD BUILDROOT RPMS SRPMS SOURCES SPECS)

    cp -v -- nvidia-yum.py "$topdir/SOURCES/"
    cp -v -- nvidia.conf "$topdir/SOURCES/"
    cp -v -- *.spec "$topdir/SPECS/"
    cd "$topdir" || err "Unable to cd into $topdir"

    kmd rpmbuild \
        --define "'%_topdir $(pwd)'" \
        --define "'debug_package %{nil}'" \
        -v -bb SPECS/yum-plugin-nvidia.spec

    cd - || err "Unable to cd into $OLDPWD"
}

plugin_dnf_rpm()
{
    mkdir -p "$topdir"
    (cd "$topdir" && rm -rf -- BUILD BUILDROOT)
    (cd "$topdir" && mkdir BUILD BUILDROOT RPMS SRPMS SOURCES SPECS)

    cp -v -- nvidia-dnf.py "$topdir/SOURCES/"
    cp -v -- *.spec "$topdir/SPECS/"
    cd "$topdir" || err "Unable to cd into $topdir"

    kmd rpmbuild \
        --define "'%_topdir $(pwd)'" \
        --define "'debug_package %{nil}'" \
        --define "'_python_sitelib ${pythonSiteLib}'" \
        -v -bb SPECS/dnf-plugin-nvidia.spec

    cd - || err "Unable to cd into $OLDPWD"
}

find_rpm()
{
    empty=$(find "$topdir/RPMS" -maxdepth 0 -type d -empty 2>/dev/null)
    found=$(find "$topdir/RPMS" -mindepth 2 -maxdepth 2 -type f -name "*${1}*.rpm" 2>/dev/null)
    if [[ ! -d "$topdir/RPMS" ]] || [[ $empty ]] || [[ ! $found ]]; then
        return 1
    else
        return 0
    fi
}

build_pkg()
{
    find_rpm $1-plugin-nvidia
    pluginCode=$?

    if [[ $pluginCode -ne 0 ]]; then
        echo "==> plugin_$1_rpm()"
        plugin_$1_rpm
        find_rpm $1-plugin-nvidia
        pluginCode=$?
    else
        echo "[SKIP] plugin_$1_rpm()"
    fi

    if [[ $pluginCode -ne 0 ]]; then
        err "Missing $1-plugin-nvidia RPM package(s)"
    fi
}

sign_rpm()
{
    signature=$(rpm --nosignature -qip "$1" | grep ^Signature)
    [[ $signature =~ "none" ]] || return

    kmd rpm \
        --define "'%_signature gpg'" \
        --define "'%_gpg_name $gpgKey'" \
        --define "'%__gpg $gpgBin'" \
        --define "'%_gpg_digest_algo sha512'" \
        --define "'%_binary_filedigest_algorithm 10'" \
        --define "'%__gpg_sign_cmd %{__gpg} $gpgArgs -u %{_gpg_name} -sbo %{__signature_filename} %{__plaintext_filename}'" \
        --addsign "$1"
}


#
# Stages
#

[[ $1 == "clean" ]] && clean_up

# Create GPG key
if [[ $gpgKey ]]; then
    echo "[SKIP] new_gpgkey()"
else
    echo "==> new_gpgkey()"
    new_gpgkey
fi

# Build RPMs
if [[ -f "yum-plugin-nvidia.spec" ]]; then
    build_pkg yum
fi

if [[ -f "dnf-plugin-nvidia.spec" ]]; then
    build_pkg dnf
fi

# Sanity check
if [[ -z $gpgKey ]]; then
    err "Missing GPG key"
fi

# Sign RPMs
echo "==> sign_rpm($gpgKey)"
for pkg in "$topdir/RPMS/${arch}"/*; do
    sign_rpm "$pkg"
done
echo
