import httplib2, pprint, sys, os
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from datetime import datetime
import createDrive
import fileOperations

def updateUserCSV(service):
    r = open('userListID.txt', 'r')
    userListID = r.readline()
    r.close()
    file = service.files().get(fileId=userListID).execute()
    export_url = file.get('exportLinks').get('text/csv')
    if export_url:
        resp, content = service._http.request(export_url)
        if resp.status == 200:
            #print 'Status: %s' % resp
            w = open('users.csv', 'w')
            w.write(content)
            w.close()
            return content
        else:
            print 'An error occurred: %s' % resp
            return None
    else:
        # The file doesn't have any content stored on Drive.
        return None

def updateSpreadsheetId(service, spreadsheet):
    w = open('userListID.txt', 'w')
    w.write(spreadsheet['id'])
    w.close()

testDrive = createDrive.createDriveService('adminEmailHere!')
spreadsheet = fileOperations.insert_file(testDrive, 'UsersSpreadSheet', 'UsersToSyncWithDrive', 'application/vnd.google-apps.spreadsheet')
updateSpreadsheetId(testDrive, spreadsheet)
updateUserCSV(testDrive)