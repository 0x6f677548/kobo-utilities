# kobo-utilities
Some utilities for the kobo eReader.

## change_user.py
This script will help you change the user on your kobo eReader. When changing the user in a kobo device, you loose all your book status (read, unread, bookmarks, etc). This script will help you keep your book status and annotations.

This is especially useful when you need to setup a new trial, and you want to keep your book status and annotations.

### Usage
```
    python change_user.py <kobo_mount_point> <backup_destionation>
```

#### mounting kobo
Make sure you have your kobo drive mounted. 
If you are using wsl, you can mount your kobo with the following command:
```
    sudo mount -t drvfs <kobo_drive_letter> <kobo_mount_point>
```
Make sure you have your kobo mount point directory created. If you are using wsl, you can create it with the following command:
```
    sudo mkdir <kobo_mount_point>
```
Example:
```
    sudo mount -t drvfs e: /mnt/e
```
```
    sudo mkdir /mnt/e
```

#### running the script
```
    python change_user.py /mnt/e /mnt/c/Users/username/Desktop/kobo_backup
```
