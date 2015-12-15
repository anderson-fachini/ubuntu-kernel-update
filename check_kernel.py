import urllib.request
import re
import subprocess
import os
import hashlib
import io

def getSiteContent(url, joinLines = True):
    print('Checking %s...' % url)

    resp = urllib.request.urlopen(url).read()

    content = resp.decode('utf-8')
    content = content.replace('\t', '').replace('  ', '')
    if joinLines:
      content = content.replace('\r', '').replace('\n', '')

    return content

def findInContent(content, regex):
    p = re.compile(regex)

    return p.findall(content)

def getSiteVersion():
    content = getSiteContent('https://www.kernel.org')

    return findInContent(content, '<td id="latest_link"><a.*?>(.*?)</a>')[0]

def executeSystemCommand(commandList):
    ret = subprocess.run(commandList, stdout=subprocess.PIPE)

    return ret.stdout

def getInstalledVersion():
    ret = executeSystemCommand(["uname", "-r"])
    instVersion = str(ret)[2:-4].split('-')[0]

    if instVersion.endswith('.0'):
        instVersion = instVersion[:-2]

    return instVersion

def adjustVersion(version, addDigit=True):
    if addDigit and len(version.split('.')) == 2:
        version += '.0'

    return version.replace('.', '\.')

def getUbuntuSiteVersions(version):
    content = getSiteContent('http://kernel.ubuntu.com/~kernel-ppa/mainline/')
    regex = '"v({}-[^/]*)'.format( adjustVersion(version, False) )

    return findInContent(content, regex)[::-1]

def getNumberedList(list_):
    newList = []

    for i, item in enumerate(list_):
        newList.append('{} - {}'.format(i+1, item))

    return newList

def getDownloadLinks(version, versionLink):
    content = getSiteContent('http://kernel.ubuntu.com/~kernel-ppa/mainline/v' + versionLink)

    regex = '"(linux-(?:headers|image)-%s.{7}(?:.{26}_all|-generic.{26}_amd64)\.deb)' % adjustVersion(version)

    return findInContent(content, regex)

def getFiles(files, versionLink):
    for i, f in enumerate(files):
        files[i] = '{0}/v{1}/{2}'.format('http://kernel.ubuntu.com/~kernel-ppa/mainline', versionLink, f)

    executeSystemCommand(['wget'] + files)

def removeFiles():
    executeSystemCommand(['rm', 'linux*.deb'])

def installPackages():
    executeSystemCommand(['sudo', 'dpkg', '-i', 'linux-headers*.deb', 'linux-image*.deb'])

def checkForExistingDebFiles():
    current_path = os.getcwd()
    files = []

    for file in os.listdir(current_path):
      if file.endswith('.deb'):
        files.push(file)

    return files

# http://stackoverflow.com/questions/1869885/calculating-sha1-of-a-file 
def sha1OfFile(filepath):
    import hashlib
    with open(filepath, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()

def getSiteChecksums(version):
    link = 'http://kernel.ubuntu.com/~kernel-ppa/mainline/v' + version + '/CHECKSUMS'
    content = getSiteContent(link, False)

    regex = '\n(.{40})\s{2}linux-(?:headers|image)-.{12}(?:.{26}_all|-generic.{26}_amd64)\.deb'

    return findInContent(content, regex)

siteVersion = getSiteVersion()
instVersion = getInstalledVersion()

if siteVersion == instVersion:
    askContinue = True
    resp = input('Installed version (%s) is the same of last available. Update anyway [N/y]? ' % instVersion)

    if not resp or resp == 'N':
        exit()
else:
    print( 'Site kernel: %s' % siteVersion )
    print( 'Installed kernel: %s' % instVersion )

    resp = input('Would you like do update to %s (Y/n): ' % siteVersion)

    if resp == 'n':
        exit()

print('Checking available versions...')
versions = getUbuntuSiteVersions(siteVersion)
versions = getNumberedList(versions)

print( 'Versions found:\n%s' % '\n'.join(versions) )

version = input( 'Wich version do you want to install [1]: ' )
if not version:
    index = 0
else:
    index = int(version) - 1

linkVersion = versions[index].split(' - ')[1]

links = getDownloadLinks(siteVersion, linkVersion)

print('Obtaining files...')
getFiles(links, linkVersion)

print('Installing packages...')
installPackages()

print('Remmoving files...')
removeFiles()
