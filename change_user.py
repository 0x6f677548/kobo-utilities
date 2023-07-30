#allows you to change the user account in a Kobo device without losing the books and annotations
#it basically does the following:
#1. backs up the Kobo device to a backup destination
#2. truncates the user table in the KoboReader.sqlite database in the Kobo device (this will force the Kobo device to ask for the user account again)
#3. restores the backup to the Kobo device
#4. merges the backup of the KoboReader.sqlite database with the new user account
#5. restores the merged KoboReader.sqlite database to the Kobo device
# author: 0x6f677548


import argparse
import os
import datetime
import os
import sqlite3
import fnmatch
import subprocess

#region copy helper functions

def _copy_file(src, dst):
    '''
    Copies a file from src to dst
    it uses the platform specific copy command, to avoid copying file permissions
    '''
    if os.name == "posix":  # Unix-based system (Linux, macOS)
        subprocess.run(["cp", src, dst])
    elif os.name == "nt":  # Windows
        subprocess.run(["copy", src, dst], shell=True)
    else:
        raise Exception("Platform not supported. Unable to copy the file.")


def _copy_tree(src, dest, ignore=None, symlink=False, force=False):

    #  expand special characters in path
    source_path = os.path.abspath(os.path.expanduser(src))
    destination_path = os.path.abspath(os.path.expanduser(dest))

    # Create destination path if it does not exists
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)

    # Get lists of all files and dirs in source path
    source_items = os.listdir(source_path)

    # Call ignore function and get the items to ignore
    if ignore is not None:
        ignored_names = ignore(source_path, source_items)
    else:
        ignored_names = set()


    for item in source_items:

        #filter ignored items
        if item in ignored_names:
            continue

        source_item = os.path.join(source_path, item)
        destination_item = os.path.join(destination_path, item)

        # handle symlinks
        if os.path.islink(source_item):
            if symlink:
                if os.path.lexists(destination_item):
                    os.remove(destination_item)
                os.symlink(os.readlink(source_item), destination_item)

        # If source item is a directory, recursivly copy
        elif os.path.isdir(source_item):
            _copy_tree(source_item, destination_item, ignore, symlink, force)

        # Skip if the file exists in the destination and force is False
        elif os.path.isfile(destination_item):
            if force:
                print('Overwriting destination: {}'.format(repr(destination_item)))
                _copy_file(source_item, destination_item)

        # Copy other files
        else:
            print('Copying: {}'.format(repr(source_item)))
            _copy_file(source_item, destination_item)

def _ignore_patterns(*patterns):
    """
    List of patterns to ignore

    :param args patterns: Defines a sequence of glob-style patterns
                          to specify what files to ignore.
    """
    def __ignore_patterns(path, names):  # pylint: disable=unused-argument
        "returns ignore list"

        ignored_item = []
        for pattern in patterns:
            ignored_item.extend(fnmatch.filter(names, pattern))
        return set(ignored_item)

    return __ignore_patterns


#endregion

def _backup(args):
    print("Backing up the Kobo device to the backup destination.. (this may take a while)")    

    
    # Ensure the Kobo mount point exists
    if not os.path.exists(args.kobo_mount_point):
        print(f"Error: Kobo mount point {args.kobo_mount_point} does not exist.")
        exit(1)

    # Ensure the backup destination does not exist and create it
    if os.path.exists(args.backup_destination):
        print(f"Error: Backup destination {args.backup_destination} exists. Please specify a backup destination that does not exist.")
        exit(1)

    _copy_tree(args.kobo_mount_point, args.backup_destination)
    print(f"Backup complete. Files copied to {args.backup_destination}.")

def _truncate_users_table(kobo_mount_point):
    print("We will now truncate the user table in the KoboReader.sqlite database")
    print("This will force the Kobo device to ask for the user account again")
    #ask the user to confirm
    print("Are you sure you want to continue? (y/n)")
    answer = input()
    if answer != "y":
        print("Aborting...")
        exit(0)
    

    #open the KoboReader.sqlite database in the device
    db = sqlite3.connect(kobo_mount_point + "/.kobo/KoboReader.sqlite")
    cursor = db.cursor()

    print("Deleting all the rows in the user table")

    #delete all the rows in the user table
    cursor.execute("DELETE FROM user")

    #commit the changes
    db.commit()
    db.close()

def _restore_backup(args):
    print("Restoring the backup to the Kobo device... (this may take a while)")

    #copy all the files from the backup device to the Kobo device except the .kobo folder
    _copy_tree(args.backup_destination, args.kobo_mount_point, 
                    force=True,
                    ignore=_ignore_patterns('.kobo'))

    input("Restored. Press Enter to continue...")

def _create_temp_db(args):
    timestamp_str = str(datetime.datetime.now().timestamp())

    # filename of the backup of the KoboReader.sqlite database that is currently in the device (which has the new user account)
    db_device_backup_filename = "KoboReader.sqlite" + ".device-backup-" + timestamp_str

    # filename of the temporary sqlite db file that will be used to merge of the backup of the KoboReader.sqlite database with the new user account
    db_temp_filename = "KoboReader.sqlite" + ".temp-" + timestamp_str

    print("Doing a backup of the current device's KoboReader.sqlite database with the name " + db_device_backup_filename)
    _copy_file(args.kobo_mount_point + "/.kobo/KoboReader.sqlite", args.backup_destination + "/.kobo/" + db_device_backup_filename)

    print("Creating a temporary sqlite db file based on backup to manipulate the user table with the name " + db_temp_filename)
    _copy_file(args.backup_destination + "/.kobo/KoboReader.sqlite", args.backup_destination + "/.kobo/" + db_temp_filename)

    print("Press Enter to continue...")


    #now let's merge the backup of the KoboReader.sqlite database with the new user account
    #temp_db is the temporary sqlite db file that we will use to manipulate the user table
    temp_db = sqlite3.connect(args.backup_destination + "/.kobo/" + db_temp_filename)
    dest_cursor = temp_db.cursor()

    print("Deleting all the rows in the user table in the temp db")
    dest_cursor.execute("DELETE FROM user")

    # get the column names and types from the source table
    dest_cursor.execute('PRAGMA table_info(user)')
    columns = [column[1] for column in dest_cursor.fetchall()]
    
    #connect to the db that was in the device
    backup_db = sqlite3.connect(args.backup_destination + "/.kobo/" + db_device_backup_filename)
    backup_cursor = backup_db.cursor()

    print("Copying the rows from the backup database to the temp db")
    backup_cursor.execute("SELECT * FROM user")
    rows = backup_cursor.fetchall()

    dest_cursor.executemany(f"INSERT INTO user VALUES ({', '.join('?' for _ in columns)})", rows)

    
    #commit the changes
    temp_db.commit()
    temp_db.close()
    backup_db.close()
    return db_temp_filename

    

if __name__ == "__main__":

    # Create an argument parser to accept command line arguments
    parser = argparse.ArgumentParser(description='Backup files from Kobo to a backup destination.')
    parser.add_argument('kobo_mount_point', type=str, help='Path to Kobo mount point.')
    parser.add_argument('backup_destination', type=str, help='Path to backup destination.')
    args = parser.parse_args()

    #print the arguments
    print("kobo_mount_point: " + args.kobo_mount_point)
    print("backup_destination: " + args.backup_destination)

    print("This script will backup the files from your Kobo device to a backup destination and then delete the user account from the Kobo device. " + 
            "This will force the Kobo device to ask for the user account again and you can sign in with a different account. " +
            "It will then restore the backup to the Kobo device.")

    _backup(args)
    _truncate_users_table(args.kobo_mount_point)

    print ("Disconnect your Kobo device and sign in with the new account")
    print("Then reconnect your Kobo device and press Enter to continue...")
    input()

    #test if the kobo mount point is valid
    if not os.path.isdir(args.kobo_mount_point):
        print("The Kobo mount point is not valid. Trying to mount it...")
        os.system("mount " + args.kobo_mount_point)
        if not os.path.isdir(args.kobo_mount_point):
            
            
            #trying to infer the mount point from the mount point directory
            # this is done by checking if the mount directory is a single letter drive and trying to find the drive letter
            # ex: if the mount point is something like /mnt/k the drive will be k:
            _mount_point_drive_letter = args.kobo_mount_point[-1] + ":"
            _mount_command = "sudo mount -t drvfs " + _mount_point_drive_letter + " " + args.kobo_mount_point

            print("The Kobo mount point is still not valid. If you are in a WSL environment, I can try to " + 
                  "mount the drive with the following command: ")
            print(_mount_command)
            print("Does this makes sense at all to you? Do you want me to proceed? (y/n)")
            _answer = input()
            if _answer == "y":
                os.system(_mount_command)
            else:
                exit()   
            
            if not os.path.isdir(args.kobo_mount_point):
                print("The Kobo mount point is still not valid. Exiting...")
                exit()
            else:
                print("The Kobo mount point is valid. Proceeding...")
                print("Press Enter to continue...")
                input()



    _restore_backup(args)
    db_temp_filename = _create_temp_db(args)

    #now let's copy the temp db to the device to replace the KoboReader.sqlite database that has the new user account
    print("Copying the temp db to the device")
    _copy_file(args.backup_destination + "/.kobo/" + db_temp_filename, args.kobo_mount_point + "/.kobo/KoboReader.sqlite")

    print("Done. You can now disconnect your Kobo device")









    









