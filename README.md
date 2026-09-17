# DriveDesk

A Windows desktop file browser for Google Drive remotes already configured in rclone. It provides side-by-side PC and Drive browsing, uploads, downloads, and a **Shared with me** view grouped by file owner.

## Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

On Windows, you can also double-click **Launch DriveDesk.bat**. A packaged executable can be built with:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean DriveDesk.spec
```

The executable will be in `dist/DriveDesk.exe`. Build from the spec file so PyInstaller excludes incompatible ICU DLLs that other software may place on `PATH`.

To build the Windows installer, place the Windows `rclone.exe` binary at
`third_party/rclone.exe`, install Inno Setup, then run:

```powershell
./build.ps1 -Installer
```

The installer will be written to `dist/installer`. Releases are built and
published automatically by `.github/workflows/release.yml` whenever a `v*` tag
is pushed (for example, `git tag v1.0.1; git push origin v1.0.1`). DriveDesk's
**Tools → Check for updates…** menu checks the latest GitHub Release, downloads
the installer asset, and offers to restart into it.

DriveDesk looks for `rclone.exe` on PATH and in common Windows install folders, including Downloads. If it cannot find it, choose the executable from the app.

The app reads your existing rclone configuration; it does not store or display OAuth tokens. Choose **Add Google account** to open Google's sign-in page in your browser. Select the account there; DriveDesk completes rclone configuration in the background without opening a command prompt. Google may require a separate OAuth client ID if rclone's shared client has been retired.

Drag files or folders from the PC pane to the Drive pane to upload, or from Drive to PC to download. Drop onto a folder row to copy into that folder. You can also drag local files from Windows Explorer onto the Drive pane. These actions copy files; they do not remove the originals.

The Transfers table shows each copy's source, destination, transferred size, progress, current speed, ETA, and elapsed time. Use **Cancel** on a running row to stop that transfer. ETA and percentage appear once rclone has reported enough information to calculate them.

Right-click a file or folder for Open, Calculate size, Properties, Upload or Download, Rename, Delete, and New folder. Drive items with a known ID can also open in your browser. Changes inside shared folders require edit access; Google Drive will report a permission error if the account cannot make them. Folder size calculations recurse through contents and can take time on large folders.

Transfers skip files that already exist at the destination by default. Enable **Replace existing** to update them. The app does not delete source or destination files.

The owner groups in **Shared with me** are built from rclone's Google Drive `owner` metadata on items at the shared root. Some items may appear under **Unknown owner** when Google does not provide owner metadata. A shared folder's contents are browsable inside its owner group.

The Drive pane has a navigation tree with **My Drive** and **Shared with me**. Shared items come from the paginated Google Drive API, are grouped by the person who shared them, and shared folders expand on demand. Pages appear as they load; if Google's request quota is reached, the loaded people remain visible and DriveDesk retries later. Shared files and folders use the same API for downloads, uploads into editable folders, and size calculation. If no shared items are returned at all, check that you selected the same Google account that shows them in Drive. The tree reflects items accessible now; it cannot list people whose past shares were removed or revoked.

The account sidebar shows each Google account's display name and email, with its rclone ID in the tooltip. When two configured remotes are verified as the same Google account, DriveDesk can use an existing custom OAuth client for shared operations to avoid the default shared client's request quota.

For a specific shared folder, choose **Open shared link** and paste a `https://drive.google.com/drive/folders/...` URL. DriveDesk uses the folder ID and optional `resourcekey` from the link for browsing, downloading, and uploading with the selected account. Uploading requires edit access to the linked folder. Select files or folders in the PC pane, then choose **Upload to linked folder**.
