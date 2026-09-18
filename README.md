# DriveDesk

A desktop file manager with side-by-side local and cloud browsing. Google Drive is the first native provider: Google sign-in, My Drive and Shared with me browsing, file operations, transfers, and previewable folder sync use Google's API directly. Other configured cloud providers and Windows Mount remain available through optional legacy rclone support. This is not an Air Explorer clone or a measured speed improvement; transfer speed still depends on Google, the network, and the files involved.

## Install and sign in

Install the Windows installer or macOS DMG from the [Releases page](https://github.com/YuvrajxGarg/DriveDesk/releases), or run from source:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Choose **Add Google account**. DriveDesk opens Google's consent page in your browser and receives the response on a temporary local loopback port. It requests offline Drive access so it can refresh your session. Refresh tokens are stored in the operating system's credential store through `keyring`, not in the app settings. The Desktop OAuth client ID can be changed under **Tools → Google sign-in settings**. A client secret is not required or stored.

Google's broad Drive scope is classified as restricted. The OAuth consent screen and test-user or verification configuration for the supplied client ID must be correctly set up in Google Cloud before sign-in will work for other people. Existing rclone accounts are still listed separately; the new native Google account is not an automatic migration of an old rclone remote.

Browse **My Drive** in the cloud pane. Open the **Shared with me** toggle only when you want to browse shared items; selecting an account and showing the Folders tree no longer scan them in the background. Shared entries are grouped by owner where Google provides owner metadata. Use Refresh to reload the shared listing. Double-click folders to navigate. Drag files between panes or use the context menu for upload, download, rename, delete, and new folder. A transfer copies by default; it does not remove the source. Google-native deletions use Drive Trash. You can paste a Google Drive folder link using **Open shared link** if your account has access.

## Native Google folder sync

Select a Google account and browse to the destination folder, then open **Sync and backup**. The app compares local and cloud trees and shows a preview before making changes. Available modes are copy/update, mirror, move, and two-way update. Mirror and move can delete from the source or destination; Google items go to Drive Trash and local items go to the OS recycle bin/trash. Review the preview carefully, especially for large or shared folders. Include/exclude filters are in **Tools → Sync filters**.

Google-native documents and shortcuts cannot yet be transferred by folder sync. They are skipped in copy/update and two-way mode; mirror and move refuse to run when these items are present. Duplicate case-insensitive names and ambiguous two-way conflicts also stop the sync. Two-way update does not propagate deletions. This is not a continuous background sync service.

## Legacy providers and Mount

For existing non-native accounts or Mount, install or select `rclone` via the legacy Tools menu. Mount on Windows also needs WinFsp. The Windows installer and macOS DMG still bundle rclone to preserve those features, but a native Google account does not require rclone for browsing, transfers, or sync.

## Build

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m unittest discover -q
python -m PyInstaller --noconfirm --clean DriveDesk.spec
dist\DriveDesk.exe --smoke-test
```

The Windows executable is `dist/DriveDesk.exe`. To make the Windows installer, put the Windows rclone binary at `third_party/rclone.exe`, install Inno Setup, and run `./build.ps1 -Installer`. Inno Setup writes to `dist/installer`. The release workflow builds installers on version tags; local builds are not published automatically.

On macOS, use the platform DMG from Releases, drag DriveDesk into Applications, and launch it normally. Mount is Windows-only. For a source build on macOS, use the macOS spec and a macOS Python environment.
