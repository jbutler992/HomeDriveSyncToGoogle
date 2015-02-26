import httplib2, pprint, sys, os, subprocess, json
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from datetime import datetime,tzinfo,timedelta

class Zone(tzinfo):
    def __init__(self,offset,isdst,name):
        self.offset = offset
        self.isdst = isdst
        self.name = name
    def utcoffset(self, dt):
        return timedelta(hours=self.offset) + self.dst(dt)
    def dst(self, dt):
        return timedelta(hours=1) if self.isdst else timedelta(0)
    def tzname(self,dt):
        return self.name
UTC = Zone(0,False,'UTC')
EST = Zone(-5,False,'EST')

def googleTimeToLocal(date):
    newDateUTC = datetime.strptime(date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    newDateUTC = newDateUTC.replace(tzinfo=UTC)
    newDateLocal = newDateUTC.astimezone(tz=EST)
    newDateLocal = newDateLocal.replace(tzinfo=None)
    return newDateLocal

def isObjectGoogleDocFileType(service, file_Id):
    file = service.files().get(fileId=file_Id).execute()
    mime_Type = file['mimeType']
    type = mime_Type.split('/')[0]
    if type == "application":
        return True
    else:
        return False

def insert_file(service, title, description, parent_id, mime_type, filename):
    media_body = MediaFileUpload(filename, mimetype=mime_type, resumable=True)
    body = {'title': title,'description': description,'mimeType': mime_type}
    # Set the parent folder.
    if parent_id:
        body['parents'] = [{'id': parent_id}]
    try:
        file = service.files().insert(body=body,media_body=media_body).execute()
        return file
    except errors.HttpError, error:
        print 'An error occured: %s' % error
        return None

def update_file(service, title, description, file_id, mime_type, filePath):
    media_body = MediaFileUpload(filePath, mimetype=mime_type, resumable=True)
    service.files().untrash(fileId=file_id).execute()
    body = {'title': title,'description': description,'mimeType': mime_type}
    try:
        file = service.files().update(fileId=file_id, body=body, media_body=media_body).execute()
        return file
    except errors.HttpError, error:
        print 'An error occured: %s' % error
        return None

def downloadLatest(service, file_id, name, filePath, googleObjects):
    latestMtime = datetime(1900, 12, 25, 12, 00, 00)
    latestMtimeID = 0
    content = ""
    if file_id == '0' or file_id == '':
        for googleObject in googleObjects:
            if googleObject[0] == name:
                if googleObject[4] > latestMtime:
                    latestMtime = googleObject[4]
                    latestMtimeID = googleObject[1]
    else:
        latestMtimeID = file_id
    updatedFile = service.files().get(fileId=latestMtimeID).execute()
    download_url = updatedFile.get('downloadUrl')
    export_links = updatedFile.get('exportLinks')
    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            #print 'Status: %s' % resp
            print "Content Downloaded"
        else:
            print 'An error occurred: %s' % resp
    elif export_links:
        wordLink = export_links.get('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        if wordLink:
            resp, content = service._http.request(wordLink)
            if resp.status == 200:
                #print 'Status: %s' % resp
                filePath = filePath+".docx"
                print "Word Doc Content Downloaded"
            else:
                print 'An error occurred: %s' % resp
        excelLink = export_links.get('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if excelLink:
            resp, content = service._http.request(excelLink)
            if resp.status == 200:
                #print 'Status: %s' % resp
                filePath = filePath+".xlsx"
                print "Excel Content Downloaded"
            else:
                print 'An error occurred: %s' % resp
        powerpointLink = export_links.get('application/vnd.openxmlformats-officedocument.presentationml.presentation')
        if powerpointLink:
            resp, content = service._http.request(powerpointLink)
            if resp.status == 200:
                #print 'Status: %s' % resp
                filePath = filePath+".pptx"
                print "Powerpoint Content Downloaded"
            else:
                print 'An error occurred: %s' % resp
    else:
        failString = "The file doesn't have any content stored on Drive."
        return failString
    w = open(filePath, 'w')
    w.write(content)
    w.close()
    successString = "File Updated Successfully!"
    return successString

def getNamesAndIDs(service):
    names = []
    files = service.files().list().execute()
    for file in files['items']:
        fileObj = [file['title'],file['id']]
        names.append(fileObj)
    return names

def getChildrenInfo(service, folder_Id):
    children = []
    files = service.children().list(folderId=folder_Id).execute()
    for file in files['items']:
        file_Id = file['id']
        fileInfo = service.files().get(fileId=file_Id).execute()
        cDate = googleTimeToLocal(fileInfo['createdDate'])
        mDate = googleTimeToLocal(fileInfo['modifiedDate'])
        fileLabels = fileInfo['labels']
        isTrashed = fileLabels['trashed']
        fileObj = [fileInfo['title'],fileInfo['id'],fileInfo['mimeType'],cDate,mDate, isTrashed]
        children.append(fileObj)
    return children

def getLocalModifiedTime(path):
    stamp = os.path.getmtime(path)
    date = datetime.fromtimestamp(stamp)
    return date