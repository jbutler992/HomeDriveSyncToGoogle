import httplib2, pprint, sys, os, subprocess, json
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from datetime import datetime,tzinfo,timedelta
import fileOperations
import updateUserList

def createDriveService(user_email, serviceAccountEmail, certPath):
    f = file(certPath, 'rb')
    key = f.read()
    f.close()
    credentials = SignedJwtAssertionCredentials(serviceAccountEmail, key, scope='https://www.googleapis.com/auth/drive', sub=user_email)
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build('drive', 'v2', http=http)

def syncFolder(service, name, folderID, localLocation, lastsync):
    contents = fileOperations.getChildrenInfo(service, folderID)
    localContents = os.listdir(localLocation)
    #syncing from Google Drive to Local
    for object in contents:
        if object[5]:
            print object[0]+" is in Trash - last modified time = "+str(object[4])
            continue
        
        found = 0
        if object[2] == "application/vnd.google-apps.folder":
            newFolderPath = localLocation+"/"+object[0]
            if not os.path.isdir(newFolderPath):
                os.mkdir(newFolderPath)
            syncFolder(service, name, object[1], newFolderPath, lastsync)
            
        
        for localObj in localContents:
            if localObj == object[0]:
                found = 1
                locPath = localLocation+"/"+localObj
                locMTime = fileOperations.getLocalModifiedTime(locPath)
                #print "Local Copy of "+localObj+" modified Time = "+str(locMTime)
                if object[4] > locMTime:
                    timedif = object[4] - locMTime
                    if timedif.seconds > 60:
                        if not os.path.isdir(locPath):
                            print "Newer version of "+localObj+" on Google Drive please download"
                            print fileOperations.downloadLatest(service, '0', localObj, locPath, contents)
        
        if found == 0 and object[3] > lastsync:
            print object[0]+" creation time :"+str(object[3])+" - Last sync Time "+str(lastsync)
            #How can we find if this was deleted from the local drive?
            #Answer - Was it created before last sync time!
            print "Google drive file "+object[0]+" not found in Local files"
            createPath = localLocation+"/"+object[0]
            print fileOperations.downloadLatest(service, object[1], object[0], createPath, contents)

        elif found == 0:
            #Assuming file was removed from Local Drive, thus is should be removed from Google Drive
            service.files().trash(fileId=object[1]).execute()
            print "Trashed "+object[0]
        
        #print "Google Drive Name = "+object[0]+" modified Time = "+str(object[4])

    for localObject in localContents:
        found = 0
        localPath = localLocation+"/"+localObject
        localMTime = fileOperations.getLocalModifiedTime(localPath)
        for googleObject in contents:
            if localObject == googleObject[0]:
                found = 1
                if localMTime > googleObject[4] and not os.path.isdir(localPath):
                    timedif = localMTime - googleObject[4]
                    if timedif.seconds > 60:
                        print "Updating "+googleObject[0]
                        fileOperations.update_file(service, localObject, localObject, googleObject[1], '', localPath)
                
                if googleObject[4] > lastsync and googleObject[5] and not fileOperations.isObjectGoogleDocFileType(service, googleObject[1]):
                    print localObject+" is in Google Drive Trash, deleting from local directory"
                    os.remove(localPath)
                if googleObject[4] > lastsync and googleObject[5] and googleObject[2] == "application/vnd.google-apps.folder":
                    print localObject+" directory is in Google Drive Teash, removing from local directory"
                    folderContents = os.listdir(localPath)
                    for lObject in folderContents:
                        lPath = localPath+"/"+lObject
                        os.remove(lPath)
                    print "Directory Emptied, Removing folder"
                    os.rmdir(localPath)

        if found == 0 and not os.path.isdir(localPath):
            print localObject+" Does not exist in Google Drive"
            fileOperations.insert_file(service, localObject, localObject, folderID, '', localPath)
        elif found == 0 and os.path.isdir(localPath):
            print localObject+" is a folder and does not exist in Google Drive"
            uploadFolder(localPath, folderID, service)

def uploadHDrive(name, service, rootId, dbPath):
    hExists = 0
    folderID = ""
    if dbPath != "0":
        r = open(dbPath, 'r')
        userInfo = json.load(r)
        r.close()
        folderID = userInfo['HdriveID']
        print "dbPath passed to upload Method"
        #print "Last sync = "+userInfo['lastsync']
        #print "H drive ID = "+userInfo['HdriveID']
        date = datetime.strptime(userInfo['lastsync'], "%Y-%m-%d %H:%M:%S")
        localFolderLocation = userInfo['localRoot']
        syncFolder(service, name, folderID, localFolderLocation, date)
    else:
        existing = fileOperations.getChildrenInfo(service, rootId)
        for files in existing:
            if files[0] == "HDrive":
                hExists = 1
                folderID = files[1]
                #FIX THIS CALL!
                syncFolder(service, name, folderID, "", "0")
        if hExists == 0:
            folderBody = {
                'title': "HDrive",
                'mimeType': "application/vnd.google-apps.folder"
            }
            folder = service.files().insert(body=folderBody).execute()
            folderID = folder['id']
            uploadFolder("/home/administrator/drive/"+name, folderID, service)
    return folderID

def uploadFolder(path, parentId, service):
    folderContents = os.listdir(path)
    for item in folderContents:
        newPath = path+"/"+item
        if os.path.isdir(newPath):
            folderBody = {
                'title': item,
                'mimeType': "application/vnd.google-apps.folder",
                'parents': [{"id":parentId}]
            }
            folder = service.files().insert(body=folderBody).execute()
            uploadFolder(newPath, folder['id'], service)
        else:
            fileOperations.insert_file(service, item, item, parentId, '', newPath)
