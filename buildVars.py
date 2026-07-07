from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries
from site_scons.site_tools.NVDATool.utils import _
# Add-on information variables
addon_info = AddonInfo(
	addon_name="instantAccess",
	addon_summary=_("instant Access"),
	addon_description=_("""A powerful productivity tool to launch websites, files, folders, and programs quickly using a dedicated layer.
	Features include background execution, verbosity levels, command line arguments, and settings import/export."""),
	addon_version="2026.4",
	addon_changelog=_("""
- Version 2026.4:
  - New Feature: Keystrokes macro simulation (allows advanced screen reader users to execute keyboard shortcut sequences with custom delays).
  - Code Quality: Refactored core modules to improve maintainability and clean up code duplication.
  - Documentation: Updated the documentation to detail the new Keystrokes feature and format.
- Version 2026.3: Official release update.
  - Add-on Loading Fix: Resolved a critical issue that prevented the add-on from loading correctly in certain NVDA environments.
  - Documentation Updates: Fully updated the Arabic user guide to provide clearer instructions and information.
  - General Stability: Internal refinements and cleanup to ensure smoother performance."""),
	addon_author="Kamal Yaser <kamalyaser31@gmail.com>",
	addon_url="https://github.com/kamalyaser31/instantAccess",
	addon_sourceURL="https://github.com/kamalyaser31/instantAccess",
	addon_docFileName="readme.html",
	addon_minimumNVDAVersion="2024.1.0",
	addon_lastTestedNVDAVersion="2026.1",
	addon_updateChannel=None,
	addon_license="GPL v2",
	addon_licenseURL=None,
)
pythonSources = ["addon/**/*.py"]
i18nSources: list[str] = pythonSources + ["buildVars.py"]
excludedFiles: list[str] = []
baseLanguage: str = "en"
markdownExtensions: list[str] = []
brailleTables: BrailleTables = {}
symbolDictionaries: SymbolDictionaries = {}
