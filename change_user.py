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
import shutil
import datetime
import os
import sqlite3



def _backup(args):
    
    # Ensure the Kobo mount point exists
    if not os.path.exists(args.kobo_mount_point):
        print(f"Error: Kobo mount point {args.kobo_mount_point} does not exist.")
        exit(1)

    # Ensure the backup destination does not exist and create it
    if os.path.exists(args.backup_destination):
        print(f"Error: Backup destination {args.backup_destination} exists. Please specify a backup destination that does not exist.")
        exit(1)

    shutil.copytree(args.kobo_mount_point, args.backup_destination)
    print(f"Backup complete. Files copied to {args.backup_destination}.")

def _truncate_users_table(kobo_mount_point):
    print("We will now truncate the user table in the KoboReader.sqlite database")
    print("This will force the Kobo device to ask for the user account again")
    input("Press Enter to continue...")


    #open the KoboReader.sqlite database in the device
    #and delete all the rows in the user table
    #this will force the Kobo device to ask for the user account again

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
    print("Restoring the backup to the Kobo device..")

    #copy all the files from the backup device to the Kobo device except the .kobo folder
    shutil.copytree(args.backup_destination, args.kobo_mount_point, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.kobo'))
    #os.system("rsync -av --delete --exclude=.kobo " + backup_mount_point + "/ " + kobo_mount_point + "/")

    input("Restored. Press Enter to continue...")

def _create_temp_db(args):
    timestamp_str = str(datetime.datetime.now().timestamp())

    # filename of the backup of the KoboReader.sqlite database that is currently in the device (which has the new user account)
    db_device_backup_filename = "KoboReader.sqlite" + ".device-backup-" + timestamp_str

    # filename of the temporary sqlite db file that will be used to merge of the backup of the KoboReader.sqlite database with the new user account
    db_temp_filename = "KoboReader.sqlite" + ".temp-" + timestamp_str

    print("Doing a backup of the current device's KoboReader.sqlite database with the name " + db_device_backup_filename)

    #use shutil.copy instead of os.system("cp") because os.system("cp") does not work on Windows
    shutil.copy(args.kobo_mount_point + "/.kobo/KoboReader.sqlite", args.backup_destination + "/.kobo/" + db_device_backup_filename)
    #os.system("cp " + args.kobo_mount_point + "/.kobo/KoboReader.sqlite " + args.backup_destination + "/.kobo/" + db_device_backup_filename)

    print("Creating a temporary sqlite db file based on backup to manipulate the user table with the name " + db_temp_filename)
    shutil.copy(args.backup_destination + "/.kobo/KoboReader.sqlite", args.backup_destination + "/.kobo/" + db_temp_filename)
    #os.system("cp " + args.backup_destination + "/.kobo/KoboReader.sqlite " + args.backup_destination + "/.kobo/" + db_temp_filename)

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

    _backup(args.kobo_mount_point, args.backup_destination)
    _truncate_users_table(args.kobo_mount_point)

    print ("Disconnect your Kobo device and sign in with the new account")
    print("Then reconnect your Kobo device and press Enter to continue...")
    input()

    _restore_backup(args)
    db_temp_filename = _create_temp_db(args)

    #now let's copy the temp db to the device to replace the KoboReader.sqlite database that has the new user account
    print("Copying the temp db to the device")
    shutil.copy(args.backup_destination + "/.kobo/" + db_temp_filename, args.kobo_mount_point + "/.kobo/KoboReader.sqlite")
    #os.system("cp " + args.backup_destination + "/.kobo/" + db_temp_filename + " " + args.kobo_mount_point + "/.kobo/KoboReader.sqlite")


    print("Done. You can now disconnect your Kobo device")









    









