import httplib2, pprint, sys, os, subprocess, json
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from datetime import datetime,tzinfo,timedelta
import functions

configPath = "config.dat"

def syncAll():
    r = open(configPath, 'r')
    config = json.load(r)
    r.close()
    adminService = functions.createDrive.createDriveService(config['adminEmail'])
    users = []
    functions.updateUserList.updateUserCSV(adminService)
    #updateUserList = subprocess.Popen(['python', 'updateUserList.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    #updateUserList.wait()
    r = open('users.csv', 'r')
    for line in r:
        users.append(line.replace('\n', '').split(","))
    for user in users:
        #add check for existing database file to skip check for existing H Drive
        #This will avoid resyncing the whole folder if user changes folder name
        databaseString = "/home/administrator/drive/userDatabase/"+user[0]
        localDrivePath = "/home/administrator/drive/"+user[1]
        dbPath = "0"
        if os.path.isfile(databaseString):
            dbPath = databaseString
        driveService = functions.createDriveService(user[0], config['serviceAccount'], config['serviceAccountCert'])
        about = driveService.about().get().execute()
        rootId = about['rootFolderId']
        HDriveID = functions.uploadHDrive(user[1], driveService, rootId, dbPath)
        print HDriveID
        now = str(datetime.now()).split('.')
        userData = {'lastsync':now[0], 'HdriveID':HDriveID, 'localRoot':localDrivePath}
        w = open(databaseString, 'w')
        json.dump(userData,w)
        w.close()


syncAll()