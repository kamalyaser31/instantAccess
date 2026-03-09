from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries
from site_scons.site_tools.NVDATool.utils import _
# Add-on information variables
addon_info = AddonInfo(
	addon_name="instantAccess",
	addon_summary=_("instant Access"),
	addon_description=_("""A powerful productivity tool to launch websites, files, folders, and programs quickly using a dedicated layer.
	Features include background execution, verbosity levels, command line arguments, and settings import/export."""),
	addon_version="2026.2",
	addon_changelog=_("""- New: Text snippets.
	- New: NVDA commands."""),
	addon_author="Kamal Yaser <kamalyaser31@gmail.com>",
	addon_url="https://github.com/kamalyaser31/instantAccess",
	addon_sourceURL="https://github.com/kamalyaser31/instantAccess",
	addon_docFileName="readme.html",
	addon_minimumNVDAVersion="2024.1.0",
	addon_lastTestedNVDAVersion="2025.3.3",
	addon_updateChannel=None,
	addon_license="GPL v2",
	addon_licenseURL=None,
)
pythonSources = ["addon/globalPlugins/*.py"]
i18nSources: list[str] = pythonSources + ["buildVars.py"]
excludedFiles: list[str] = []
baseLanguage: str = "en"
markdownExtensions: list[str] = []
brailleTables: BrailleTables = {}
symbolDictionaries: SymbolDictionaries = {}
