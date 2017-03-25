#!/usr/bin/python
#

import os
from subprocess import Popen
from subprocess import PIPE
import time
import sys
import re
import platform
from datetime import datetime
# this is so windows doesn't output CR (carriage return) at the end of each line and just does LF (line feed)
if platform.system() == 'Windows':
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

def export_data(string):
    print 'data %d\n%s' % (len(string), string)

def inline_data(filename, code = 'M', mode = '644'):
    content = open(filename, 'rb').read()
    if platform.system() == 'Windows':
        #this is a hack'ish way to get windows path names to work git (is there a better way to do this?)
        filename = filename.replace('\\','/')
    print "%s %s inline %s" % (code, mode, filename)
    export_data(content)

def convert_revision_to_mark(revision):
    if not revision in marks:
        marks.append(revision)
    return marks.index(revision) + 1

def retrieve_revisions(devpath=0):
    if devpath:
        pipe = Popen('si viewprojecthistory --rfilter=devpath:"%s" --project="%s"' % (devpath, sys.argv[1]), shell=True, bufsize=1024, stdout=PIPE)
    else:
        pipe = Popen('si viewprojecthistory --rfilter=devpath::current --project="%s"' % sys.argv[1], shell=True, bufsize=1024, stdout=PIPE)
    versions = pipe.stdout.read().split('\n')
    versions = versions[1:]
    version_re = re.compile('[0-9]([\.0-9])+')
    revisions = []
    for version in versions:
        match = version_re.match(version)
        if match:
            version_cols = version.split('\t')
            revision = {}
            revision["number"] = version_cols[0]
            revision["author"] = version_cols[1]
            revision["seconds"] = int(time.mktime(datetime.strptime(version_cols[2], "%b %d, %Y %I:%M:%S %p").timetuple()))
            revision["description"] = version_cols[5]
            revisions.append(revision)
    revisions.reverse() # Old to new
    re.purge()
    return revisions

def retrieve_devpaths():
    pipe = Popen('si projectinfo --devpaths --noacl --noattributes --noshowCheckpointDescription --noassociatedIssues --project="%s"' % sys.argv[1], shell=True, bufsize=1024, stdout=PIPE)
    devpaths = pipe.stdout.read()
    devpaths = devpaths [1:]
    devpaths_re = re.compile('    (.+) \(([0-9][\.0-9]+)\)\n')
    devpath_col = devpaths_re.findall(devpaths)
    re.purge()
    devpath_col.sort(key=lambda x: map(int, x[1].split('.'))) #order development paths by version
    return devpath_col

def export_to_git(revisions,devpath=0,ancestor=0):
    abs_sandbox_path = os.getcwd()
	integrity_file = os.path.basename(sys.argv[1])
    if not devpath: #this is assuming that devpath will always be executed after the mainline import is finished
        move_to_next_revision = 0
    else:
        move_to_next_revision = 1
    for revision in revisions:
        #revision_col = revision["number"].split('\.')
        mark = convert_revision_to_mark(revision["number"])
        if move_to_next_revision:
            os.system('si retargetsandbox --project="%s" --projectRevision=%s %s/%s' % (sys.argv[1], revision["number"], abs_sandbox_path), integrity_file)
            os.system('si resync --yes --recurse ')
        move_to_next_revision = 1
        if devpath:
            print 'commit refs/heads/devpath/%s' % devpath
        else:
            print 'commit refs/heads/master'
        print 'mark :%d' % mark
        print 'committer %s <> %d +0100' % (revision["author"], revision["seconds"]) #Germany UTC time zone
        export_data(revision["description"])
        if ancestor:
            print 'from :%d' % convert_revision_to_mark(ancestor) #we're starting a development path so we need to start from it was originally branched from
            ancestor = 0 #set to zero so it doesn't loop back in to here
        print 'deleteall'
        tree = os.walk('.')
        for dir in tree:
            for filename in dir[2]:
                if (dir[0] == '.'):
                    fullfile = filename
                else:
                    fullfile = os.path.join(dir[0], filename)[2:]
                if (fullfile.find('.pj') != -1):
                    continue
                if (fullfile[0:4] == ".git"):
                    continue
                if (fullfile.find('mks_checkpoints_to_git') != -1):
                    continue
                inline_data(fullfile)

marks = []
devpaths = retrieve_devpaths()
revisions = retrieve_revisions()
#Create a build sandbox of the first revision
os.system('si createsandbox --populate --recurse --project="%s" --projectRevision=%s tmp' % (sys.argv[1], revisions[0]["number"]))
os.chdir('tmp')
export_to_git(revisions) #export master branch first!!
for devpath in devpaths:
    devpath_revisions = retrieve_revisions(devpath[0])
    export_to_git(devpath_revisions,devpath[0].replace(' ','_'),devpath[1]) #branch names can not have spaces in git so replace with underscores
# Drop the sandbox
shortname=sys.argv[1].replace('"', '').split('/')[-1]
os.chdir("..")
os.system("si dropsandbox --yes -f --delete=all tmp/%s" % (shortname))