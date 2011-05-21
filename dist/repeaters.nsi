; Script generated by the HM NIS Edit Script Wizard.

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "NZ Repeaters"
!define PRODUCT_VERSION "0.1"
!define PRODUCT_PUBLISHER "Rob Wallace"
!define PRODUCT_WEB_SITE "http://projects.wallace.gen.nz/projects/nzrepeaters"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\rpt.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"
!define PRODUCT_STARTMENU_REGVAL "NSIS:StartMenuDir"

SetCompressor lzma

!include "EnvVarUpdate.nsh"

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "..\COPYING"
; Components page
!insertmacro MUI_PAGE_COMPONENTS
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Start menu page
var ICONS_GROUP
!define MUI_STARTMENUPAGE_NODISABLE
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "NZ Repeaters"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "${PRODUCT_UNINST_ROOT_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${PRODUCT_UNINST_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "${PRODUCT_STARTMENU_REGVAL}"
!insertmacro MUI_PAGE_STARTMENU Application $ICONS_GROUP
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
;!define MUI_FINISHPAGE_RUN "$INSTDIR\repeaters.exe"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; Reserve files
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Setup-NZ_Repeaters_0.1.exe"
InstallDir "$PROGRAMFILES\NZ Repeaters"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Section "Application" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "bz2.pyd"
  File "library.zip"
  File "python26.dll"
  File "rpt.exe"
  File "select.pyd"
  File "sqlite3.dll"
  File "unicodedata.pyd"
  File "w9xpopen.exe"
  File "_sqlite3.pyd"
  File "..\README.txt"
  File "..\COPYING"

  ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"

; Shortcuts
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
  CreateDirectory "$SMPROGRAMS\$ICONS_GROUP"
  CreateShortCut "$SMPROGRAMS\$ICONS_GROUP\README.lnk" "$INSTDIR\README.txt"
;  CreateShortCut "$SMPROGRAMS\$ICONS_GROUP\NZ Repeaters.lnk" "$INSTDIR\rpt.exe"
;  CreateShortCut "$DESKTOP\NZ Repeaters.lnk" "$INSTDIR\repeaters.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section "Data" SEC02
  SetOutPath "$INSTDIR\data"
  SetOverwrite try
  File "..\repeaters\data\callsigns.csv"
  File "..\repeaters\data\ctcss.csv"
  File "..\repeaters\data\info.csv"
  File "..\repeaters\data\prism.sqlite"
  File "..\repeaters\data\skip.csv"
  File "..\repeaters\data\update_db.sh"

; Shortcuts
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section -AdditionalIcons
  SetOutPath $INSTDIR
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\$ICONS_GROUP\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\$ICONS_GROUP\Uninstall.lnk" "$INSTDIR\uninst.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\repeaters.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\repeaters.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "App"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Data for "
!insertmacro MUI_FUNCTION_DESCRIPTION_END


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  !insertmacro MUI_STARTMENU_GETFOLDER "Application" $ICONS_GROUP
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\data\update_db.sh"
  Delete "$INSTDIR\data\skip.csv"
  Delete "$INSTDIR\data\prism.sqlite"
  Delete "$INSTDIR\data\info.csv"
  Delete "$INSTDIR\data\ctcss.csv"
  Delete "$INSTDIR\data\callsigns.csv"
  Delete "$INSTDIR\COPYING"
  Delete "$INSTDIR\README.txt"
  Delete "$INSTDIR\_sqlite3.pyd"
  Delete "$INSTDIR\w9xpopen.exe"
  Delete "$INSTDIR\unicodedata.pyd"
  Delete "$INSTDIR\sqlite3.dll"
  Delete "$INSTDIR\select.pyd"
  Delete "$INSTDIR\rpt.exe"
  Delete "$INSTDIR\python26.dll"
  Delete "$INSTDIR\library.zip"
  Delete "$INSTDIR\bz2.pyd"

  Delete "$SMPROGRAMS\$ICONS_GROUP\Uninstall.lnk"
  Delete "$SMPROGRAMS\$ICONS_GROUP\Website.lnk"
  Delete "$DESKTOP\NZ Repeaters.lnk"
  Delete "$SMPROGRAMS\$ICONS_GROUP\NZ Repeaters.lnk"

  RMDir "$SMPROGRAMS\$ICONS_GROUP"
  RMDir "$INSTDIR\data"
  RMDir "$INSTDIR"

  ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd