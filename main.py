#! /usr/bin/python

version = "0012"

credits = """
=== Vise Package Manager version %s ===
Copyleft, 2010 (Peter Schmidt-Nielsen)

Developed and maintained by Peter Schmidt-Nielsen.
Patch contributed by Noah Bedford.

Special thanks to carbon and oxygen, for making Vise possible.
""" % version

import os
import sys
import time
import datetime
import urllib2
import socket
import shutil
import hashlib
import subprocess

  # Magic colored text constants
normal = "\x1B\x5B\x30\x6D"
grey   = "\x1B\x5B\x30\x31\x3B\x33\x30\x6D"
red    = "\x1B\x5B\x30\x31\x3B\x33\x31\x6D"
green  = "\x1B\x5B\x30\x31\x3B\x33\x32\x6D"
yellow = "\x1B\x5B\x30\x31\x3B\x33\x33\x6D"
blue   = "\x1B\x5B\x30\x31\x3B\x33\x34\x6D"
purple = "\x1B\x5B\x30\x31\x3B\x33\x35\x6D"
teal   = "\x1B\x5B\x30\x31\x3B\x33\x36\x6D"

  # Constants
default_config = """
  # Default initial configuration file for Vise

server toothbrush.dyndns.org 80 /vise

  # Uncomment this line to access Noah's server
#server robodude.no-ip.org 8080 /vise

binaries  = ~/bin:/usr/bin
libraries = ~/lib:/lib
setup     = ~:/etc
temporary = /tmp

  # Disable this if you don't want Vise to warn you quite as much
treat_like_idiot = false

  # Set this if you want Vise to assume "yes" to questions like:
  #   Should I overwrite this file?
  #   This looks a bit strange. Should I proceed anyway?
be_brave         = false

  # Set this if you want Vise to only exit on really bad errors
be_stoic         = false

  # Authentication variables
use_gpg = true
halt_no_signature  = true
halt_bad_signature = true

  # Asthetic preferences
use_color          = true
"""

  # Set the default socket timeout, so that URL fetches don't just hang
timeout = 8
socket.setdefaulttimeout(timeout)

eu = os.path.expanduser

def timestring():
    d = datetime.datetime(2010,1,1)
    d = d.fromtimestamp( time.time() )
    return d.strftime("%d-%b-%Y, (%H:%M)")

def ask( question, default=None ):
    if default == None:
        while True:
            try:
                choice = raw_input( question+" (y/n) " )
            except:
                continue
            if choice.lower().strip() in ("n", "no"):
                return "no"
            if choice.lower().strip() in ("y", "yes"):
                return "yes"
    elif default == "yes":
        try:
            choice = raw_input( question+" (Y/n) " )
        except:
            choice = ""
        if choice.lower().strip() in ("n", "no"):
            return "no"
        return "yes"
    elif default == "no":
        try:
            choice = raw_input( question+" (y/N) " )
        except:
            choice = ""
        if choice.lower().strip() in ("y", "yes"):
            return "yes"
        return "no"

def run_command( *args ):
    """run_command( *args ) -> Runs the command args[0] on args[1:], and returns the return code of the subprocess"""
    return subprocess.call( args )

def ask_options( question, count ):
    while True:
        try:
            choice = raw_input( question+(" (%s)" % "/".join(str(i) for i in xrange(1,count+1)) ) )
            choice = int( choice )
        except:
            continue
        if choice < 1 or choice > count:
            continue
        return choice

temp_file_counter = 0
def temp_file():
    global temp_file_counter

    while True:
        temp_file_counter += 1
        filepath = "/tmp/visedir/file%s" % temp_file_counter
        if os.path.exists( filepath ):
            print red+"Warning:"+normal+" File that shouldn't exist does: '%s'" % filepath
            continue
        return filepath

def join( *bits ):
    value = bits[0]
    for new in bits[1:]:
        if value[-1] != "/" and new[0] != "/":
            value += "/"
        value += new
    return value

def make_marked( directory ):
    "make_marked( path ) -> Makes a directory that may be deleted by delete_tree"
    os.mkdir( directory )
    open( os.path.join( directory, "vise.mark" ), "a" ).close()

def delete_tree( directory ):
      # Make sure we know what we're dealing with.
      # Symlinks to / must be stopped
    directory = os.path.realpath( directory )

      # First make sure we properly refuse to delete something precious
    if directory == "/":
        print red+"Error:"+normal+" Attempt was made to delete '%s'. I refuse." % directory
        return False
    if directory == os.path.expanduser("~"):
        print red+"Error:"+normal+" Attempt was made to delete '%s'. I refuse." % directory
        return False

      # For some reason, doing all these redundant checks makes me feel better about calling the dangerous shutil.rmtree function.
    if os.path.islink( directory ):
        print red+"Warning:"+normal+" %s exists, but it's a link to '%s', so I refuse to delete it." % (directory, os.path.readlink( directory ))
        return False
    elif os.path.isfile( directory ):
        print red+"Warning:"+normal+" %s exists, but it's a file, not a directory, so I won't delete it." % directory
        return False
    elif (not "vise.mark" in os.listdir( directory )) or (not os.path.exists( os.path.join( directory, "vise.mark" ) )):
        if check_set("be_brave"):
            print "Variable be_brave set, so deleting %s despite the fact that it doesn't contain a vise.mark file." % director
              # The magic deadly death command... of doom
            shutil.rmtree( directory )
            return True
        else:
            print red+"Warning:"+normal+" %s exists, but doesn't contain a vise.mark file, so too cowardly to delete it." % directory
            return False
    else:
          # Again, the magic deadly doom command... of perilous death
        shutil.rmtree( directory )
        return True

def request_url( host, port, path ):
    if path[0] != "/":
        path = "/" + path
    return "http://%s:%s%s" % (host, port, path)

def url_get( host, port, path ):
    request = request_url( host, port, path )
    print "Fetching %s..." % request,
    sys.stdout.flush()
    try:

        req = urllib2.Request(request)
        openfile = urllib2.urlopen(req)
        data = openfile.read()
        openfile.close()

        print "%s bytes" % len(data)
        return data

    except:
        print red+"failure"+normal
        return False

def downloadfile( url, requested_path=None ):
    if requested_path:
        filename = requested_path
    else:
        filename = temp_file()

    outputfile = open( filename, "w" )

    print "Downloading %s: -\r" % url,
    totalbytes = 0
    sys.stdout.flush()
    try:

        req = urllib2.Request( url )
        openfile = urllib2.urlopen(req)

        while True:
            data = openfile.read(4096)
            totalbytes += len(data)
            if not data:
                break
            outputfile.write( data )
            print "Downloading %s:  %s\r" % (url, totalbytes),
            sys.stdout.flush()

        openfile.close()

        print "Downloading %s: [%s]" % (url, totalbytes)
        return filename

    except IOError, e:
        print
        if hasattr(e, 'reason'):
            print "We failed to reach a server."
            print red+'Reason: '+normal, e.reason
        elif hasattr(e, 'code'):
            print "The server couldn\'t fulfill the request."
            print red+'Error code: '+normal, e.code
        return None

  # Core vise functions
  # If you import vise as a library, try to just use these, as they never try to exit your program

has_global_lock = False
def core_get_lock():
    global has_global_lock
    try:
        #os.mkdir("/tmp/visedir")
        make_marked("/tmp/visedir")
        has_global_lock = True
        return True
    except:
        print red+"Failure to acquire global lock (/tmp/visedir)"+normal
        return False

def core_release_lock():
    global has_global_lock
    if os.path.islink("/tmp/visedir"):
        print red+"Warning: Global lock directory (/tmp/visedir) is a symbolic link! Releasing it might be dangerous."+normal
        return False
    try:
        #shutil.rmtree("/tmp/visedir")
          # Delete the directory with all the usual checks and safeties
          # If anything fails, raise an exception so that the outer except clause is triggered
        success = delete_tree("/tmp/visedir")
        if not success:
            raise Exception

        has_global_lock = False
        return True
    except:
        print red+"Failure to release global lock (/tmp/visedir)"+normal
        return False

  # No files are absolutely required
crucial_files = [
                ]

def core_method( method ):
    """core_method( path ) -> bool success -- Call a method of the given package file"""
    for crucial_file in crucial_files:
        if not os.path.exists( crucial_file ):
            print "Package illformed: Does not contain '%s'" % crucial_file
            return False

    methods = core_list_methods()
    if method not in methods:
        print "Unknown method '%s'" % method
        print "Package only the supports methods:"
        print "    " + " ".join( methods )
        return False

    result = core_interpret( "/tmp/visedir/package-files/method-%s" % method )

    return result

def core_install( package_name ):
    global inst_installed
    """Mostly just calls core_method( "install" ), but also does some other checks, and saves the remove script"""

    methods = core_list_methods()

      # Set this if you don't want to bother copying over the uninstall script
    invisible_install = False

    if "remove" not in methods:
        print red+"Warning:"+normal+" This package provides no uninstall script."
        print     "         If you want to uninstall it, you will have to do so manually."
        print     "         As a consequence, this installation will be \"invisible\", and not tracked by Vise."
        if ask("Install anyway?", default="no") == "no":
            print "NOT installing"
            return False
        print "Installing despite lack of uninstall script"

      # Why is this just a slight warning, whereas it's a major error in command_install?
      # The rational is simple:
      #   Here, you might legitimately try to install a package twice, as a dependency, or the like.
      #   You should still be stopped, but there's no cause to spit out some huge diatribe.
      #   Below, you should seriously scold the user for attempting something so silly.
    if package_name in inst_installed:
        print yellow+"Minor Warning:"+normal+" Package already installed, not bothering to install again."
        return True

    result = core_method( "install" )

    if result:
        if not invisible_install:
            source      = unpacked_package_file
            destination = os.path.join( eu("~/.viseinstalled"), "package-"+package_name )
            try:
                shutil.copyfile( source, destination )
            except:
                print red+"Warning:"+normal+" Failed to copy package with uninstaller from %s to %s" % (source, destination)
                print     "         Without this script, the package might not uninstall correctly."
                print     "         You are highly advised to run `vise repair' immediately."
                print     "         Then, you should run `vise pretend-installed %s' to attempt to copy over the package's uninstaller again." % package_name
                return False
        return True

    else:
        return False

def core_list_methods():
    """
    core_list_methods() -> [ str method ... ]
      Lists all the methods of the currently unpacked package
    """
    files = os.listdir("/tmp/visedir/package-files")
    methods = [ path[7:] for path in files if path.startswith("method-") ]
    return methods

def core_unpack( path ):
    """
    core_unpack( path ) -> bool success
      Unpack a package file as the current package.
      First call this method, then the other core_* functions will operate on it.
    """
    path = os.path.abspath( path )
    os.chdir("/tmp/visedir")
    tar_result = run_command("tar", "xf", path)
    if tar_result != 0:
        print red+"Warning:"+normal+" Tar returned a non-zero value"
    try:
        os.chdir("package-files")
    except:
        print red+"Package illformed:"+normal+" Does not create 'package-files'"
        return False

    return True

unpacked_package_file = None
def core_fetch( package_name ):
    global csh_packages, unpacked_package_file

    package_names = set( i[0] for i in csh_packages )

    if package_name not in package_names:
        print "Unknown package %s" % package_name
        if not csh_packages:
            print "However, the package cache is empty. Try running: `vise refresh', then try again."
        return False

    for name, version, url in csh_packages:
        if name == package_name:
            break

    print "Fetching: %s, version %s from %s" % (name, version, url)

    temppath = downloadfile(url)

    if temppath == None:
        print red+"Error:"+normal+" Couldn't download the package file"
        return False

    if check_set("use_gpg"):

        signaturepath = downloadfile( url+".asc", temppath+".asc" )

        if not signaturepath:
            print red+"Warning:"+normal+" Package not authenticated."
            if check_set("halt_no_signature"):
                print     "         (To permanently turn off this question, run `vise set halt_no_signature false')"
                if ask("Fetch anyway?", default="yes") == "no":
                    return False
            else:
                print "Fetching anyway"

        else:
            gpg_result = run_command("gpg", "--verify", signaturepath)
            if gpg_result:
                print red+"Warning:"+normal+" Bad signature on package!"
                if check_set("halt_bad_signature"):
                    print     "         (To permanently turn off this question, run `vise set halt_bad_signature false')"
                    if ask("Fetch anyway?", default="no") == "no":
                        return False
                else:
                    print "Fetching anyway"

    result = core_unpack( temppath )

    if not result:
        print red+"Error:"+normal+" Package unpacking failed"
        return False

    unpacked_package_file = temppath

    return True

  # Permanent eu function, used to prevent infinite recursion in core_interpret
permanent_eu = eu

def core_interpret( path ):
    """
    core_interpret( path ) -> bool success
      Invoke the Vise script at path
    """
    global cfg_vars, glob_eu

    def get_hashsum( path ):
        print "hashsum %s" % path,
        hsh = hashlib.sha256()
        try:
            openfile = open( path )
            while True:
                newdata = openfile.read(4096)
                if not newdata:
                    break
                hsh.update( newdata )
            openfile.close()
            print green+"OK"+normal
            return hsh.hexdigest()
        except:
            print red+"Error!"+normal
            return False

    openfile = open( path )
    code = openfile.read().split("\n")
    openfile.close()

      # Add a local extension to eu
    eu = lambda x : os.path.abspath( permanent_eu ( x ) )

    code = [ line.strip() for line in code if line.strip() ]

    stack = []
    local_vars = { }

    ptr = 0

    while ptr < len(code):
        line = code[ptr]

        cmd = line.split(" ")
        cmd, args = cmd[0], cmd[1:]

        sarg = " ".join( args )
        for key, value in local_vars.items():
            sarg = sarg.replace("$%s$" % key, value)
        for key, value in cfg_vars.items():
            sarg = sarg.replace("%%%s%%" % key, value)

        sarg = sarg.replace("%package-files%", "/tmp/visedir/package-files")

        if cmd == "#":
            stack.append( sarg )
        elif cmd == ".":
            pass
        elif cmd == "set":
            local_vars[ sarg ] = stack.pop()
        elif cmd == "get":
            stack.append( local_vars[ sarg ] )
        elif cmd == "echo":
            print blue+stack.pop()+normal
        elif cmd == "dup":
            stack.append( stack[-1] )
        elif cmd == "drop":
            stack.pop()
        elif cmd == "mkdir":
            path = eu(stack.pop())
            print "mkdir %s" % path,
            try:
                os.mkdir( path )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "mkdir-marked":
            path = eu(stack.pop())
            print "mkdir %s" % path,
            try:
                make_marked( path )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "getbest":
            topvalue = stack.pop()
            subvalues = topvalue.split(":")
            for value in subvalues:
                if os.path.exists( eu(value) ):
                    stack.append( value )
                    break
            else:
                stack.append( "" )
        elif cmd == "join":
            head = stack.pop()
            tail = stack.pop()
            stack.append( os.path.join( tail, head ) )
        elif cmd == "cd":
            path = eu(stack.pop())
            print "cd %s" % path,
            try:
                os.chdir( path )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "depends":
            if sarg not in inst_installed:
                print blue+("Package depends on `%s' (run `vise install %s', then try again)" % (sarg, sarg))+normal
                return False
        elif cmd == "untar":
            path = eu(stack.pop())
            print "tar xf %s" % path,
            retcode = run_command("tar", "xf", path)
            if retcode != 0:
                print red+"Error!"+normal
                if check_set("be_stoic"):
                    print red+"Warning:"+normal+" Tar returned a non-zero value"
                else:
                    print red+"Error:"+normal+" Tar returned a non-zero value"
                    return False
            else:
                print green+"OK"+normal
        elif cmd == "run-script":
            path = eu(stack.pop())
            print "exec %s" % path
              # TODO: Make this bit more idiot proof
            retcode = run_command(path)
            if retcode != 0:
                print red+"Error!"+normal
                if check_set("be_stoic"):
                    print red+"Warning:"+normal+" Subscript returned a non-zero value"
                else:
                    print red+"Error:"+normal+" Subscript returned a non-zero value"
                    return False
            else:
                print green+"OK"+normal
        elif cmd == "exe" or cmd == "rel-exe":
            source = os.path.join( "/tmp/visedir/package-files", sarg )
              # rel-exe operates relative to the current working directory,
              # not relative to the current package-files directory.
            if cmd == "rel-exe":
                sarg = stack.pop()
                source = eu(sarg)

            topvalue = cfg_vars["binaries"]
            subvalues = topvalue.split(":")
            for value in subvalues:
                if os.path.exists( eu(value) ):
                    dest = eu(value)
                    break
            else:
                print red+"Error:"+normal+" Failed to find suitable place for executable."
                print     "       Looked in:", " ".join(subvalues)
                if not check_set("be_stoic"):
                    return False
            dest = os.path.join( dest, sarg )
            copy_over_the_file = True
            if os.path.exists( dest ):
                print red+"Warning:"+normal+" File to be installed already exists: %s" % dest
                hashsumdest = get_hashsum( dest )
                hashsumold = get_hashsum( source )
                if not hashsumdest:
                    print red+"         Warning:"+normal+" Couldn't calculate hashsum of the file that already exists."
                    print     "                  It's probably a dead symbolic link, then."
                    print "NOT attempting file copy"
                    copy_over_the_file = False
                elif not hashsumold:
                    print red+"         Error:"+normal+" Couldn't calculate hashsum of distributed file for comparison."
                    print     "                This error should not happen, as it indicates that the package is built wrong."
                    print "NOT attempting file copy"
                    copy_over_the_file = False
                elif hashsumdest != hashsumold:
                    print "         The file that is installed is different."
                      # be_brave forces option 2
                    if check_set("be_brave"):
                        print "Variable be_brave set, overwriting anyway."
                    else:
                        print "         If you continue, this file will be deleted"
                        print "         At this point, you have three options:"
                        print "          1) Abort!"
                        print "          2) Copy over the file anyway, overwriting the current version."
                        print "          3) Keep the current (differing) version."
                        choice = ask_options("Pick option", 3)
                        if choice == 1:
                            print "Chose option 1: Abort!"
                            return False
                        elif choice == 2:
                            print "Chose option 2: Copy over anyway."
                        elif choice == 3:
                            print "Chose option 3: Keep the current version."
                            copy_over_the_file = False
                else:
                    print "         However, the files are identical, so I'll simply skip this operation."
                    copy_over_the_file = False

            if copy_over_the_file:
                print "cp %s -> %s" % (source, dest),
                try:
                    shutil.copyfile( source, dest )
                    shutil.copymode( source, dest )
                    stack.append( "true" )
                    print green+"OK"+normal
                except:
                    stack.append( "false" )
                    print red+"Error!"+normal
                    print red+"Error:"+normal+" Failed to copy executable."
                    if not check_set("be_stoic"):
                        return False
        elif cmd == "unexe" or cmd == "rel-unexe":
            source = os.path.join( "/tmp/visedir/package-files", sarg )
              # rel-unexe operates relative to the current working directory,
              # not relative to the current package-files directory.
            if cmd == "rel-unexe":
                sarg = stack.pop()
                source = eu(sarg)

            topvalue = cfg_vars["binaries"]
            subvalues = topvalue.split(":")
            for value in subvalues:
                if os.path.exists( eu(value) ):
                    dest = eu(value)
                    break
            else:
                print red+"Error:"+normal+" Failed to find suitable place for executable."
                print     "       Looked in:", " ".join(subvalues)
                if check_set("be_stoic"):
                    print "Variable be_stoic set, simply skipping operation."
                    ptr += 1
                    continue
                else:
                    return False
            dest = os.path.join( dest, sarg )
            if not os.path.exists( dest ):
                print blue+("Executable to remove already doesn't exist at %s" % dest)+normal
                ptr += 1
                continue
            old = os.path.join( "/tmp/visedir/package-files", sarg )
            hashsumdest = get_hashsum( dest )
            hashsumold = get_hashsum( old )
            if not hashsumdest:
                print red+"Error:"+normal+" Couldn't calculate hashsum of the executable to remove."
                if check_set("be_stoic"):
                    print "Variable be_stoic set, simply skipping operation."
                    ptr += 1
                    continue
                else:
                    return False
            if not hashsumold:
                print red+"Error:"+normal+" Couldn't calculate hashsum of old executable for comparison."
                print     "       This error should not happen, as it indicates that the package is built wrong."
                if check_set("be_stoic"):
                    print "Variable be_stoic set, simply skipping operation."
                    ptr += 1
                    continue
                else:
                    return False
            if hashsumdest != hashsumold:
                if check_set("be_brave"):
                    print "Variable be_brave set, deleting file despite hashsum not matching what it should be."
                else:
                    print red+"Warning:"+normal+" Too cowardly to delete executable when its hashsum doesn't match what it should be."
                    print     "         That means this file has been changed since being installed."
                    print     "         If you made these edits, then you will lose them."
                    print     "         Path of executable: %s" % dest
                    if ask("Delete anyway?", default="no") == "no":
                        print "NOT deleting file: %s" % dest
                        ptr += 1
                        continue
                          # Don't die so easily.
                        #return False
                    print "Deleting file anyway: %s" % dest
                    #return False
            print "rm %s" % dest,
            try:
                os.unlink( dest )
                print green+"OK"+normal
            except:
                print red+"Error!"+normal
                print red+"Error:"+normal+" Failed to delete old executable."
                if not check_set("be_stoic"):
                    return False
        elif cmd == "file-exists":
            path = eu(stack.pop())
            if os.path.exists( path ):
                stack.append( "true" )
            else:
                stack.append( "false" )
        elif cmd == "file-copy":
            dest   = eu(stack.pop())
            source = eu(stack.pop())
            print "cp %s -> %s" % (source, dest),
            try:
                shutil.copyfile( source, dest )
                shutil.copymode( source, dest )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "file-delete":
            path = eu(stack.pop())
            print "rm %s" % path,
            try:
                os.unlink( path )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "dir-delete":
            path = eu(stack.pop())
            print "rmdir %s" % path,
            try:
                os.rmdir( path )
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal
        elif cmd == "mark":
            path = eu(stack.pop())
            path = os.path.join(path, "vise.mark")
            print "touch %s" % path,
            try:
                open( path, "a" ).close()
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal

          # By far the most dangerous command!
          # Be ridiculously careful how you use this command!
          # Note: It will refuse to delete / or ~
          # Also, this code must be very carefully vetted
        elif cmd == "delete-tree":
            path = eu(stack.pop())
            print "rm -rf %s" % path,
            try:
                result = delete_tree( path )
                if not result:
                    raise Exception
                stack.append( "true" )
                print green+"OK"+normal
            except:
                stack.append( "false" )
                print red+"Error!"+normal

        elif cmd == "==":
            a = stack.pop()
            b = stack.pop()
            if a == b:
                stack.append( "true" )
            else:
                stack.append( "false" )
        elif cmd == "if":
            value = stack.pop()
            if value != "true":
                depth = 1
                while depth:
                    ptr += 1
                    if code[ptr] == "if":
                        depth += 1
                    elif code[ptr] == "fi":
                        depth -= 1
        elif cmd == "fi":
            pass
        elif cmd == "not":
            value = stack.pop()
            if value in ("false", ""):
                stack.append( "true" )
            else:
                stack.append( "false" )
        elif cmd == "crash":
            print red+"Script intentionally aborted:"+normal, sarg
            return False
        elif cmd == "check":
            value = stack.pop()
            if value in ("false", ""):
                print red+"Script intentionally aborted:"+normal, sarg
                return False
          # The difference between `check' and `mild-check' is that mild-check won't crash when be_stoic is set
        elif cmd == "mild-check":
            value = stack.pop()
            if value in ("false", ""):
                print red+"Script intentionally aborted:"+normal, sarg
                if not check_set("be_stoic"):
                    return False
        elif cmd == "warn":
            value = stack.pop()
            if value in ("false", ""):
                print yellow+"Script warns:"+normal, sarg
        elif cmd == "done":
            return True
        elif cmd == "hashsum":
            path = eu(stack.pop())
            result = get_hashsum( path )
            if not result:
                stack.append( "false" )
            else:
                stack.append( result )
        else:
            print red+"Warning:"+normal+" Unknown instruction file command: %s" % (repr(line))

        ptr += 1

    return True

  # Commands

def command_refresh( args ):
    global csh_packages

    csh_packages = []

    for host, port, root in cfg_servers:

        subpage = join( root, "packages.txt" )

        data = url_get( host, port, subpage )

        if not data:
            print "Error: Couldn't get the package index from %s" % request_url(host, port, subpage)

        else:
            at_least_some = True

            data = data.split("\n")

            for rawline in data:
                try:
                    line = rawline.split("#")[0].strip()
                    if not line: continue

                    package_name, version, url = line.split(" ")

                    if url[0] == "/":
                        url = request_url( host, port, url )

                    csh_packages.append( ( package_name, version, url ) )

                except:
                    print "Error in package index line: %s" % rawline

    if not csh_packages:
        print red+"Warning:"+normal+" No package indexes were successfully downloaded. If you save now, an empty package cache will be written."
        if ask("Save anyway?", default="no") == "no":
            print "NOT writing package cache"
            return False
        print "Writing empty package cache anyway"

    print "Indexed %s packages" % len(csh_packages)

    writecache()

def command_invoke( args ):
    if len(args) != 2:
        complain("Wrong number of arguments.")

    if check_set("treat_like_idiot"):
        if args[1] in ("install", "remove"):
            print teal+"Safety check!"+normal+" Usually, one doesn't directly invoke this method."
            if args[1] == "install":
                print "While running `vise invoke <package> install' does work, it's not advised."
                print "The regular installation process does extra checks, and logs the installation for future uninstallation."
                print "If you continue, Vise will not remember that you have installed this package, and might not be able to uninstall it."
            if args[1] == "remove":
                print "While running `vise invoke <package> remove' does work, it's not advised."
                print "The regular removal process does extra checks, and logs the removal in Vise's history diretory."
                print "If you continue, Vise will not remember that you have removed this package, and might complain about reinstalling it."
            print "(To turn off this message, run `vise set treat_like_idiot false')"
            if ask("Continue?", default="no") == "no":
                print "NOT continuing"
                return False
            print "Continuing"

    readcache()

    result = core_fetch( args[0] )

    if not result:
        return False

    result = core_method( args[1] )

    if not result:
        print red+"Error:"+normal+" Invokation failed"
        return False

    print green+"Done!"+normal
    return True

def command_methods( args ):
    if len(args) != 1:
        complain("Wrong number of arguments.")

    readcache()

    result = core_fetch( args[0] )

    if not result:
        return False

    methods = core_list_methods()
    print "Package %s supports the following methods:" % args[0]
    print "    " + " ".join( methods )

    return True

def command_install( args ):
    global inst_installed
    if len(args) != 1:
        complain("Wrong number of arguments.")

    if args[0] in inst_installed:
        print red+"Error:"+normal+" Package '%s' already installed." % args[0]
        print     "       If you're really insistent on installing an already installed package:"
        print     "       Run: `vise pretend-removed %s', then try `vise install %s' again." % (args[0], args[0])
        print "NOT installing"
        return False

    readcache()

    result = core_fetch( args[0] )

    if not result:
        return False

    result = core_install( args[0] )

    if not result:
        print red+"Error:"+normal+" Installation failed"
        return False

    print green+"Done!"+normal
    return True

def command_pretend_installed( args ):
    global inst_installed, cfg_vars
    if len(args) != 1:
        complain("Wrong number of arguments.")

    readcache()

    package_names = set( i[0] for i in csh_packages )

    if args[0] not in package_names:
        print "Unknown package %s" % args[0]
        if not csh_packages:
            print "However, the package cache is empty. Try running: `vise refresh', then try again."
        return False

    if check_set("treat_like_idiot"):
        print teal+"Safety check!"+normal+" This command is not for the faint of heart."
        print "Pretend-installed fetches the most recent version of the package, and inserts it into the installed history, as if it had been installed."
        print "Use this command when you know a package actually has been installed, but Vise doesn't know about it."
        print "But be warned: If you were wrong, and then try to uninstall, the uninstaller may blow up in your face."
        print "(To turn off this message, run `vise set treat_like_idiot false')"
        if ask("Continue?", default="no") == "no":
            print "NOT continuing"
            return False
        print "Continuing"

    result = core_fetch( args[0] )

    if not result:
        return False

    source      = unpacked_package_file
    destination = os.path.join( eu("~/.viseinstalled"), "package-"+args[0] )
    try:
        shutil.copyfile( source, destination )
    except:
        print red+"Warning:"+normal+" Failed to copy package from %s to %s" % (source, destination)
        print     "         This basically defeats the purpose of the whole operation."
        return False

    print "Done."
    return True

def command_pretend_removed( args ):
    global inst_installed, cfg_vars, csh_packages
    if len(args) != 1:
        complain("Wrong number of arguments.")

    if args[0] not in inst_installed:
        print "Package %s does not appear in the installation history" % args[0]
        return False

    if check_set("treat_like_idiot"):
        print teal+"Safety check!"+normal+" This command is not for the faint of heart."
        print "Pretend-removed deletes a package from the installation history."
        print "Use this command when you know a package actually has been removed, but Vise doesn't know about it."
        print "But be warned: If you were wrong, and then try to reinstall, the installer may blow up in your face."
        print "(To turn off this message, run `vise set treat_like_idiot false')"
        if ask("Continue?", default="no") == "no":
            print "NOT continuing"
            return False
        print "Continuing"

    file_path = os.path.join( eu("~/.viseinstalled"), "package-"+args[0] )
    try:
        os.unlink( file_path )
    except:
        print red+"Warning:"+normal+" Failed to delete package file %s" % (file_path)
        print     "         This basically defeats the purpose of the whole operation."
        return False

    print "Done."
    return True

def command_remove( args ):
    global csh_packages, inst_packages
    if len(args) != 1:
        complain("Wrong number of arguments.")

    readcache()

    package_names = set( i[0] for i in csh_packages )

    if args[0] not in package_names and args[0] not in inst_installed:
        print "Unknown package %s" % args[0]
        print "It appears in neither the repositories, nor the installation history."
        if not csh_packages:
            print "However, the package cache is empty."
            print "If you're sure the package should exist, and you really want to try to remove it, then:"
            print " Try running: `vise refresh', then try again."
        return False

    if args[0] not in inst_installed:
        print red+"Error:"+normal+" Package '%s' not installed." % args[0]
        print     "       However, this package is listed in the repositories, so you can always run an uninstaller again."
        print     "       If you're really insistent on removing a package that isn't installed:"
        print     "       Run: `vise pretend-installed %s', then try `vise remove %s' again." % (args[0], args[0])
        print     "       Be careful: This will run the most recent version of the uninstaller."
        print     "                   If you're trying to remove an older package this way, that command might fail dangerously!"
        print "NOT removing"
        return False

      # If we have some packages, but not the package to be uninstalled, then warn the user of the uninvertibility of their actions
    if args[0] not in package_names and csh_packages:
        print yellow+"Warning:"+normal+" Uninstalling a package that doesn't appear in package cache."
        print        "         If the package cache is up to date, then this means you won't be able to reinstall if you change your mind."
        print "Minor warning, removing anyway"

    #command_invoke( [ args[0], "remove" ] )

    script_path      = os.path.join( eu("~/.viseinstalled"), "package-"+args[0] )
    done_script_path = os.path.join( eu("~/.viseinstalled"), "old.package-"+args[0] )

    if not os.path.exists( script_path ):
        print red+"Bizarre Error:"+normal+" Wait a moment... something is seriously messed up."
        print     "               The package appears in the installed list, but the script file %s doesn't exist." % script_path
        print     "               Perhaps it's a symbolic link to an invalid location?"
        print     "               Either that, or someone deleted the file in the few microseconds between listing the directory, and now."
        print     "               In either case, this is too strange to continue."
        print     "               Check out the file yourself, and try again."
        print "NOT removing"
        return False

    print "Unpacking cached package."

    result = core_unpack( script_path )
    if not result:
        print red+"Error:"+normal+" Package unpacking failed"
        return False

    result = core_method( "remove" )

    if not result:
        print red+"Error:"+normal+" Uninstaller script failed."
        print     "       Because of this failure, Vise will not touch the uninstaller script at %s" % script_path
        print     "       If you have the guts, you can check out the uninstaller yourself, and try to figure out the problem."
        print     "       Alternatively, you can see if the package in question supports a \"safe-remove\" method."
        print     "       If so, you can run it with: `vise invoke %s safe-remove'" % args[0]
        return False

    try:
        os.rename( script_path, done_script_path )
    except:
        print red+"Error:"+normal+" Moving uninstaller script from %s to %s failed." % (script_path, done_script_path)
        print     "       This might result in Vise thinking this package is still installed."
        print     "       You can manually delete %s to make sure that Vise doesn't think it's still installed." % script
        return False

    return True

def command_upgrade( args ):
    global inst_installed
    if len(args) != 1:
        complain("Wrong number of arguments.")

    if args[0] not in inst_installed:
        print red+"Error:"+normal+" Package not installed."
        print     "       Perhaps you just wanted to install the package, not upgrade it?"
        return False

    print green+"Step 1/2:"+normal+" Removing currently installed version"

    result = command_remove( args )

    if not result:
        print red+"Error:"+normal+" Couldn't remove package."
        return False

      # Refresh the installed list
    readinstalled()

    print green+"Step 2/2:"+normal+" Installing new version"

    result = command_install( args )

    if not result:
        print red+"Error:"+normal+" Couldn't install package."
        return False

    print "Package reinstalled as newest version"
    return True

def command_list( args ):
    global inst_installed

    readcache()

    print "%s packages total:" % len(csh_packages)
    print "%15s%10s%70s" % ("Name", "Versions", "URL")
    for package in csh_packages:
        if package[0] in inst_installed:
            print blue+("%15s%10s%70s" % (package[0], package[1], package[2]))+normal
        else:
            print "%15s%10s%70s" % (package[0], package[1], package[2])

def command_installed( args ):
    global inst_installed

    print "%s installed packages total:" % len(inst_installed)
    print "    " + " ".join(inst_installed)

def command_serv_add( args ):
    if len(args) < 3:
        args.append( 80 )
    if len(args) < 3:
        args.append( "/vise" )
    if len(args) != 3:
        complain()

    print "Settings:"
    print "%30s%30s%30s" % ("Address", "Port", "Root")
    print "%30s%30s%30s" % (args[0], args[1], args[2])

    if ask("Is this correct?", default="no") == "no":
        print "NOT adding server"
        return False

    print "Adding server"

    cfg_servers.append( (args[0], args[1], args[2]) )

    writeconfig()

def command_serv_list( args ):

    print "%3s %30s%30s%30s" % ("#", "Address", "Port", "Root")
    for i, server in enumerate(cfg_servers):
        print "%3i:%30s%30s%30s" % (i+1, server[0], server[1], server[2])

def command_serv_remove( args ):
    if len(args) != 1:
        complain("Wrong number of arguments.")

    try:
        index = int(args[0])
    except:
        complain("Not a number.")

    if index < 0:
        complain("Negative index? What were you thinking.")
    if index == 0:
        complain("Sorry, I one-index these, not zero-index them.")
    if index > len(cfg_servers):
        complain("There aren't that many servers in the listing.")

    server = cfg_servers[index-1]

    print "Server entry to delete:"
    print "%30s%30s%30s" % ("Address", "Port", "Root")
    print "%30s%30s%30s" % (server[0], server[1], server[2])

    if ask("Is this correct?", default="no") == "no":
        print "NOT deleting server entry"
        return False

    print "Deleting server entry"

    cfg_servers.pop(index-1)

    writeconfig()

def command_repair( args ):
    global csh_packages, inst_installed

    print grey+"Creating missing Vise configuration files and folders..."+normal

      # Total number of tests is three
    total = 3
    good = 0
    created = 0
    errors = 0

    directory = eu("~/.viseinstalled")

    if not os.path.exists( directory ):
        print "Vise installation history directory %s doesn't exist. Now creating..." % directory
        made_dir = False
        try:
            #os.mkdir( directory )
            make_marked( directory )
            made_dir = True
        except:
            print red+"Warning:"+normal+" Couldn't create installation history directory (%s)" % directory

        made_mark = False
        mark_path = os.path.join( directory, "vise.mark" )
        try:
            openfile = open( mark_path, "a" ).close()
            made_mark = True
        except:
            print red+"Warning:"+normal+"Couldn't create mark file (%s)" % mark_path

        if made_dir and made_mark:
            created += 1
        else:
            errors += 1
    else:
        good += 1

    cfg_path = eu("~/.visecfg")

    if not os.path.exists( cfg_path ):
        print "Vise configuration file %s doesn't exist. Now creating..." % cfg_path

        try:
            openfile = open(cfg_path, "w")
            openfile.write(default_config)
            openfile.close()
            created += 1
        except:
            print red+"Warning:"+normal+" Failed to write configuration file %s" % cfg_path
            errors += 1
    else:
        good += 1

    cache_path = eu("~/.visecache")

    if not os.path.exists( cache_path ):
        print "Vise package cache %s doesn't exist. Now creating..." % cache_path
        try:
            csh_packages = []
            writecache()
            created += 1
        except:
            print red+"Warning:"+normal+" Failed to write out empty package cache file %s" % cache_path
            error += 1
    else:
        good += 1

    print "Done:"
    if good: print green+("  Already extant:       %s/%s" % (good, total))+normal
    if created: print blue+("  Successfully created: %s" % (created))+normal
    if errors: print red+("  Failed to create:     %s" % (errors))+normal

def command_reset( args ):
    global csh_packages, inst_installed

    directory = eu("~/.viseinstalled")
    cfg_path = eu("~/.visecfg")

    if os.path.exists( directory ):
        readinstalled()
        if inst_installed:
            print red+" ========== WARNING: =========="+normal
            print "Vise installation history directory %s exists." % directory
            print "This directory contains a cached version of the uninstall script for each package you have installed."
            print "This is done so that regardless of package updates, you can always uninstall your current version."
            print "If you reset, you will also lose all record of "+yellow+str(len(inst_installed))+normal+" currently installed packages."
            print "As a consequence, you will "+red+"NOT"+normal+" necessarily be able to cleanly remove these packages."
            print "If you don't want to lose your installation history, but are still missing some configuration files, then:"
            print "  Answer `no', then try running: `vise repair'"
            print "However, should you choose to reset anyway, then know that you can always manually invoke uninstallers by running:"
            print "  `vise invoke <package> remove'"
            print "However, this might fail dangerously! That command will invoke the most recent uninstall script, not the one for the verson you have."
            print "The bottom line is that the uninstall script you need might only exist in this directory, and not in the repositories."
            print "To see what uninstallers you will be losing, answer `no', then run `vise installed'."
            if ask("Reset anyway?", default="no") == "no":
                print "NOT resetting"
                return False

    if os.path.exists( cfg_path ):
        print red+"Warning:"+normal+(" Configuration file %s exists." % cfg_path)
        print     "         If you don't want to lose your current configuration, but are still missing some configuration files, then:"
        print     "           Answer `no', then try running: `vise repair'"
        if ask("Reset anyway?", default="no") == "no":
            print "NOT resetting"
            return False

    print grey+"Resetting..."+normal

    directory = eu("~/.viseinstalled")

    if os.path.exists( directory ):
        try:
              # In this case, we don't check the return value,
              # because if an error occured, then delete_tree
              # will spit out enough of a complaint
            delete_tree( directory )
        except:
            print red+"Error:"+normal+" Couldn't delete the installation history directory (%s)" % directory

    flag = True
    try:
        #os.mkdir( directory )
        make_marked( directory )
    except:
        print red+"Warning:"+normal+" Couldn't create installation history directory (%s)" % directory
        flag = False

    mark_path = os.path.join( directory, "vise.mark" )
    try:
        openfile = open( mark_path, "a" ).close()
    except:
        print red+"Warning:"+normal+"Couldn't create mark file (%s)" % mark_path
        flag = False

    if flag:
        print green+"Made "+directory+normal

    try:
        openfile = open( cfg_path, "w" )
        openfile.write(default_config)
        openfile.close()
        print green+"Wrote "+cfg_path+normal
    except:
        print red+"Warning:"+normal+" Failed to write configuration file %s" % cfg_path

    csh_packages = [ ]

    cache_path = eu("~/.visecache")

    try:
        writecache()
        print green+"Cleared "+cache_path+normal
    except:
        print red+"Warning:"+normal+" Failed to write out empty package cache file %s" % cache_path

    print "Done!"

def command_vars( args ):
    global cfg_vars

    for key, value in cfg_vars.items():
        print "%20s = %-50s" % (key, value)

def command_set( args ):
    if len(args) < 2:
        complain("Wrong number of arguments.")

    new_key = args[0]
    new_value = " ".join( args[1:] )
    for key, value in cfg_vars.items():
        new_value = new_value.replace("%%%s%%" % key, value)

    cfg_vars[ new_key ] = new_value

    writeconfig()

def command_unset( args ):
    if len(args) != 1:
        complain("Wrong number of arguments.")

    key = args[0]

    if key not in cfg_vars:
        print red+"Error:"+normal+" Variable '%s' not defined." % key
        return False

    else:
        cfg_vars.pop( key )

    writeconfig()

valid_commands = [
                    "refresh",
                    "install",
                    "upgrade",
                    "methods",
                    "invoke",
                    #"reverse",
                    "remove",
                    #"satisfy",
                    "list",
                    "installed",
                    #"versions",
                    #"depgraph",
                    #"py-depgraph",
                    "serv-list",
                    "serv-add",
                    "serv-remove",
                    "reset",
                    "repair",
                    "vars",
                    "set",
                    "unset",
                    "upgrade",
                    "pretend-installed",
                    "pretend-removed",
                ]

dispatch = {
            "refresh"           : command_refresh,
            "install"           : command_install,
            "remove"            : command_remove,
            "invoke"            : command_invoke,
            "methods"           : command_methods,
            "list"              : command_list,
            "installed"         : command_installed,
            "serv-list"         : command_serv_list,
            "serv-add"          : command_serv_add,
            "serv-remove"       : command_serv_remove,
            "reset"             : command_reset,
            "vars"              : command_vars,
            "set"               : command_set,
            "unset"             : command_unset,
            "upgrade"           : command_upgrade,
            "repair"            : command_repair,
            "pretend-installed" : command_pretend_installed,
            "pretend-removed"   : command_pretend_removed,
           }

def check_set( variable ):
    global cfg_vars

    if variable in cfg_vars and cfg_vars[variable].lower().strip() == "true":
        return True
    else:
        return False

def readconfig():
    global cfg_vars, cfg_servers

    cfg_vars = { }
    cfg_servers = [ ]

    try:
        openfile = open( eu("~/.visecfg") )
    except:
        print "Couldn't find the configuration file (%s)" % (eu("~/.visecfg"))
        print "Perhaps this is your first time running Vise?"
        print "If so, then run: `vise reset'"
        #print "Alternately, if your Vise installation has been damaged, run: `vise repair'"
        return False

    for rawline in openfile:
        try:
            line = rawline.split("#")[0].strip()
            if not line: continue

            cmd = line.split(" ")
            cmd, args = cmd[0], cmd[1:]

            if cmd == "server":
                  # Three arguments: host, port, root
                assert len(args) == 3
                cfg_servers.append( args )

            elif "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                cfg_vars[key] = value

            else:
                print "Unknown config file command: %s" % rawline
        except:
            print "Error on config file command: %s" % rawline

    openfile.close()

    return True

def writeconfig():
    global cfg_vars, cfg_servers

    openfile = open( eu("~/.visecfg"), "w" )

    openfile.write( """
  # Configuration file for vise, written on %s
""" % (timestring()) )

    openfile.write("\n")

    for server in cfg_servers:
        openfile.write("server %s %s %s\n" % (server[0], server[1], server[2]))

    openfile.write("\n")

    for key, value in cfg_vars.items():
        openfile.write("%s = %s\n" % (key, value))

    openfile.write("\n")

    openfile.close()

def readcache():
    global csh_packages

    csh_packages = [ ]

    try:
        openfile = open( eu("~/.visecache") )
    except:
        print "Couldn't open the package cache (%s)" % (eu("~/.visecache"))
        print "Try running: `vise refresh'"
        exit(1)

    for rawline in openfile:
        try:
            line = rawline.split("#")[0].strip()
            if not line: continue

            package_name, version, url = line.split(" ")
            csh_packages.append( ( package_name, version, url ) )

        except:
            print "Error on cache file line: %s" % rawline

    openfile.close()

def writecache():
    global csh_packages

    openfile = open( eu("~/.visecache"), "w" )

    for package_name, version, url in csh_packages:
        openfile.write( "%s %s %s\n" % ( package_name, version, url ) )

    openfile.close()

def readinstalled():
    global inst_installed

    inst_installed = []

    try:
        packages = os.listdir( eu("~/.viseinstalled") )
        inst_installed = [ i[8:] for i in packages if i.startswith("package-") ]
    except:
        print "Couldn't open the installation history directory, %s" % eu("~/.viseinstalled")
        print "Try running: `vise repair', or `vise reset' if this is your first time running Vise."
        exit(1)

    return True

def usage():
    print purple+" Vise"+normal+" v%s" % version
    print "  usage: vise command [argument0, argument1, ...]"
    print
    print "  general commands:"
    print "   refresh                           -- Refreshes the package listing"
    print "   install <package>                 -- Installs the latest version of <package>"
    print "   remove <package>                  -- Uninstalls <package>"
    print "   upgrade <package>                 -- Performs a remove, then an install of <package>"
    #print "   satisfy <package>                 -- Satisfy all the dependencies of <package>, but don't install it"
    print
    print "  information:"
    print "   list                              -- Lists all available packages"
    print "   installed                         -- Lists all installed packages"
    #print "   installed [<package>]             -- Lists all installed packages, or the installed version of <package>"
    #print "   versions <package>                -- Lists the available versions of <package>"
    #print "   depgraph <package>                -- Recursively lists the dependencies of <package>"
    #print "   py-depgraph <package>             -- Draws a graph of all dependencies of a package (Requires Pygame)"
    print
    print "  server related commands:"
    print "   serv-list                         -- Lists the current package servers"
    print "   serv-add <host> [<port>] [<root>] -- Adds <host>:<port> to the list of servers, accessing <root> for data"
    print "   serv-remove <server number>       -- Removes server <number> (Use serv-list to get the server numbers)"
    print
    print "  configuration:"
    print "   reset                             -- Resets the configuration files, ~/.visecfg, ~/.visecache, and ~/.viseinstalled/"
    print "   repair                            -- Like reset, but only recreates the missing ones (non-destructive)"
    print "   vars                              -- List all variables, and their values"
    print "   set <variable> <value>            -- Set <variable> to be <value> (Expands %var% to the value of var automatically)"
    print "   unset <variable>                  -- Removes the definition of <variable>, if it's defined"
    print
    print "  obscure:"
    print "   methods <package>                 -- Lists all the methods of <package>"
    print "   invoke <package> <method>         -- Invokes the <method> of <package>"
    print "                                        (Note: `vise install x' does extra checks that `vise invoke x install' doesn't do)"
    #print "   reverse <package> <method>        -- Reverses the effects of <method> of <package>"
    print
    print "  dangerous commands not to run unless you know what you're doing:"
    print "   pretend-installed <package>       -- Pretends a given package is installed"
    print "   pretend-removed <package>         -- Removes the records of a given package being installed, without actually removing it"
    exit(1)

def complain( reason="Invalid command." ):
    print red+"Error:"+normal, reason
    print " (try: `vise --help')"
    exit(1)

if __name__ == "__main__":

      # Special magical boot-strapping handling!
      # This is to allow the user to `vise reset' and `vise repair' the first time
    if len(sys.argv) == 2 and sys.argv[1] in ("reset", "repair"):
        result = dispatch[ sys.argv[1] ]( sys.argv[2:] )
        if result == False:
            exit(1)
        exit(0)

    success = readconfig()

      # Immediately, test for color preferences
      # If we don't succeed quickly enough, then a colored error message may slip out
    if not check_set("use_color"):
        normal = ""
        grey   = ""
        red    = ""
        green  = ""
        yellow = ""
        blue   = ""
        purple = ""
        teal   = ""

    if not success:
        exit(1)

    success = readinstalled()

    if not success:
        exit(1)

    if len(sys.argv) == 1:
        usage()

    elif sys.argv[1] in ("--help", "help"):
        usage()

    elif sys.argv[1] == "--credits":
        print credits

    elif sys.argv[1] not in valid_commands:
        usage()

    else:

        if sys.argv[1] not in dispatch:
            print red+"This feature not implemented yet!"+normal
            exit(1)

        if not core_get_lock():
            print red+"Error:"+normal+" Locking failed"
            exit(1)

        try:
            result = dispatch[ sys.argv[1] ]( sys.argv[2:] )
            if result == False:
                exit(1)
        finally:
            core_release_lock()

