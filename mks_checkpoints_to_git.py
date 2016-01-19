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

#This only works with Integrity 10 and up
#def checkpoint_change_package_diff(revision,last_revision_number):
#    pipe = Popen('si retargetsandbox --project="%s" --projectRevision=%s --recurse -r %s -r %s' % (sys.argv[1], revision["number"], last_revision_number, revision["number"]), shell=True, bufsize=1024, stdout=PIPE)
#    cpdiffs = pipe.stdout.read().split('\n')
#    checkpoint_differences = []
#    for cpdiff in cpdiffs:
#        cpdiff_cols = cpdiff.split('\t')
#        checkpoint_difference = {}
#        checkpoint_difference['filename'] = cpdiff_cols[2]
#        checkpoint_difference['author'] = cpdiff_cols[4]
#        checkpoint_difference['change_package'] = cpdiff_cols[8]
#        checkpoint_differences.append(checkpoint_difference)
#    return checkpoint_differences

def checkpoint_change_packages_ids(revision,last_revision_number):
    pipe = Popen('si mods --project="%s" --recurse --showChangePackages -r %s -r %s' % (sys.argv[1],last_revision_number,revision), shell=True, bufsize=1024, stdout=PIPE)
    change_package_ids_raw = pipe.stdout.read()
#    if change_package_ids_raw is '':    #no change packages (si return nothing)
#        return False
    change_package_ids_re = re.compile('(\d+:\d+)')
    change_package_ids = change_package_ids_re.findall(change_package_ids_raw)
    return change_package_ids

def change_packages_description(change_package_ids):
    change_packages_description = ''
    for change_package_id in change_package_ids:
        pipe = Popen('si viewcp %s' % change_package_id, shell=True, bufsize=1024, stdout=PIPE)
        cp_info_raw = pipe.stdout.read()
        cp_info = []
        for line in cp_info_raw.splitlines():
            cp_info.append(line.split('\t'))
        change_packages_description += change_package_id + ' ' + cp_info[0][1] + '\n'
        if 'Propagation' in cp_info[1][3]:
            propagated_cps_re = re.compile('(\d+:\d+)')
            propagated_cps = propagated_cps_re.findall(cp_info[2][0])
            change_packages_description += 'Propagated Change Packages:'
            for propagated_cp in propagated_cps:
                pipe = Popen('si viewcp %s' % propagated_cp, shell=True, bufsize=1024, stdout=PIPE)
                propagated_cp_info_raw = pipe.stdout.read()
                propagated_cp_info = []
                for line in propagated_cp_info_raw.splitlines():
                    propagated_cp_info.append(line.split('\t'))
                propagated_change_packages_description = propagated_cp + ' ' + propagated_cp_info[0][1]
                change_packages_description += '\n\t' + propagated_change_packages_description
    return change_packages_description

def export_to_git(revisions,devpath=0,ancestor=0):
    abs_sandbox_path = os.getcwd()
    if not devpath: #this is assuming that devpath will always be executed after the mainline import is finished
        move_to_next_revision = 0
    else:
        move_to_next_revision = 1
    last_revision_number = 0 #initialize to zero
    for revision in revisions:
        
        change_package_ids = ''
        checkpoint_differences = ''
        if last_revision_number is not 0:
            change_package_ids = checkpoint_change_packages_ids(revision["number"], last_revision_number)
        if change_package_ids is not '':
            checkpoint_differences = change_packages_description(change_package_ids)
        
        mark = convert_revision_to_mark(revision["number"])
        if move_to_next_revision:
            os.system('si retargetsandbox --project="%s" --projectRevision=%s %s/project.pj' % (sys.argv[1], revision["number"], abs_sandbox_path))
            os.system('si resync --yes --recurse ')
        move_to_next_revision = 1
        if devpath:
            print 'commit refs/heads/devpath/%s' % devpath
        else:
            print 'commit refs/heads/master'
        print 'mark :%d' % mark
        print 'committer %s <> %d +0100' % (revision["author"], revision["seconds"]) #Germany UTC time zone
        export_data(revision["description"] + '\n' + checkpoint_differences)
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
        last_revision_number = revision["number"]

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