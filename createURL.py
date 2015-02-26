import os

shortcut = open('testURL.url', 'w')
shortcut.write('[InternetShortcut]\n')
shortcut.write('URL=')
shortcut.write('https://google.com')
shortcut.close()