import urllib.request
import re
import subprocess
import os
import hashlib
import sys


def get_site_content(url, joinLines=True):
    print('Checking %s...' % url)

    resp = urllib.request.urlopen(url).read()

    content = resp.decode('utf-8')
    if joinLines:
        content = content.replace('\t', '').replace('  ', '')
        content = content.replace('\r', '').replace('\n', '')

    return content


def find_in_content(content, regex):
    p = re.compile(regex)

    return p.findall(content)


def get_site_version():
    content = get_site_content('https://www.kernel.org')

    return find_in_content(content, '<td id="latest_link"><a.*?>(.*?)</a>')[0]


def execute_system_command(commandList):
    ret = subprocess.run(commandList, stdout=subprocess.PIPE)

    return ret.stdout


def get_installed_version():
    ret = execute_system_command(["uname", "-r"])
    instVersion = str(ret)[2:-4].split('-')[0]

    if instVersion.endswith('.0'):
        instVersion = instVersion[:-2]

    return instVersion


def ajust_version(version, addDigit=True):
    if addDigit and len(version.split('.')) == 2:
        version += '.0'

    return version.replace('.', '\.')


def get_ubuntu_site_version(version):
    content = get_site_content('http://kernel.ubuntu.com/~kernel-ppa/mainline/')
    regex = '"v({}-?[^/]*)'.format(ajust_version(version, False))

    return find_in_content(content, regex)[::-1]


def get_numbered_list(list_):
    newList = []

    for i, item in enumerate(list_):
        newList.append('{} - {}'.format(i+1, item))

    return newList


def get_download_file_names(version, versionLink):
    link = 'http://kernel.ubuntu.com/~kernel-ppa/mainline/v' + versionLink
    content = get_site_content(link)
    adjusted_version = ajust_version(version)

    regex = '"(linux-(?:headers|image)-%s-\d{6}(?:_%s-.{19}_all|-generic_%s-.{19}_amd64)\.deb)' % (adjusted_version, adjusted_version, adjusted_version)

    return find_in_content(content, regex)


def get_files(files, versionLink):
    prefix_url = 'http://kernel.ubuntu.com/~kernel-ppa/mainline'

    for i, f in enumerate(files):
        files[i] = '{0}/v{1}/{2}'.format(prefix_url, versionLink, f)

    execute_system_command(['wget'] + files)


def remove_files(version):
    params = ['rm', 'linux*%s*.deb' % version]
    execute_system_command(params)


def install_packages(file_names):
    params = ['sudo', 'dpkg', '-i']
    params.extend(file_names)

    execute_system_command(params)


def check_existing_deb_files(file_names):
    current_path = os.getcwd()

    files = [file for file in os.listdir(current_path) if file in file_names]

    return files


# http://stackoverflow.com/questions/1869885/calculating-sha1-of-a-file
def sha1_of_file(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def get_site_checksums(version):
    link = 'http://kernel.ubuntu.com/~kernel-ppa/mainline/v%s/CHECKSUMS' % version
    content = get_site_content(link, False)
    adjusted_version = ajust_version(version)

    regex = '\n(.{40})\s{2}(linux-(?:headers|image)-%s-\d{6}(?:_%s-.{19}_all|-generic_%s-.{19}_amd64)\.deb)' % (adjusted_version, adjusted_version, adjusted_version)

    finds = find_in_content(content, regex)
    sums = {}

    for item in finds:
        sums[item[1]] = item[0]

    return sums


siteVersion = get_site_version()
instVersion = get_installed_version()

if siteVersion == instVersion:
    askContinue = True
    resp = input('Installed version (%s) is the same of last available.\
        Update anyway [N/y]? ' % instVersion)

    if not resp or resp == 'N':
        exit()
else:
    print('Installed kernel: %s' % instVersion)
    print('Site kernel: %s' % siteVersion)

    resp = input('Would you like do update to %s (Y/n): ' % siteVersion)

    if resp == 'n':
        exit()

print('Checking available versions...')
versions = get_ubuntu_site_version(siteVersion)

if not versions:
    print('Version %s is not available on Ubuntu site yet' % siteVersion)
    sys.exit()

versions = get_numbered_list(versions)

print('Versions found:\n%s' % '\n'.join(versions))

version = input('Which version do you want to install [1]: ')
if not version:
    index = 0
else:
    index = int(version) - 1

linkVersion = versions[index].split(' - ')[1]

file_names = get_download_file_names(siteVersion, linkVersion)

existing_files = check_existing_deb_files(file_names)

if existing_files:
    checksums = get_site_checksums(linkVersion)

    for file_name in existing_files:
        if sha1_of_file(file_name) != checksums[file_name]:
            existing_files.remove(file_name)

files_left = [file for file in file_names if file not in existing_files]

if len(files_left):
    print('Obtaining files...')
    get_files(files_left, linkVersion)

print('Installing packages...')
install_packages(file_names)

print('Removing files...')
remove_files(siteVersion)
