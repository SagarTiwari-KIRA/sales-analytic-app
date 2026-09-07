[app]

# (str) Title of your application
title = Sales Analytics App By SAGAR TIWARI

# (str) Package name
package.name = salesanalytics

# (str) Package domain (needed for android/ios packaging)
package.domain = org.sagar

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db

# (str) Application versioning
version = 0.1

# (list) Application requirements
# kept intentionally lean: only what main.py actually imports.
# sqlite3 ships with Python itself, no separate entry needed.
requirements = python3,kivy==2.3.1,pillow

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# The app writes its sqlite db to the app's own private storage, so no
# storage permission is required.
android.permissions =

# (int) Target Android API, minimum API and NDK API
android.api = 34
android.minapi = 24
android.ndk_api = 24

# (str) Android archive to build - debug apk first, sign a release later
[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
