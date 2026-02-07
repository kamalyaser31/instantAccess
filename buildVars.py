# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries
from site_scons.site_tools.NVDATool.utils import _

# Add-on information variables
addon_info = AddonInfo(
	# الاسم البرمجي للإضافة (بدون مسافات)
	addon_name="instantAccess",
	
	# العنوان الظاهر للمستخدم
	addon_summary=_("instant Access"),
	
	# الوصف الكامل
	addon_description=_("""A powerful productivity tool to launch websites, files, folders, and programs quickly using a dedicated layer.
Features include background execution, verbosity levels, command line arguments, and settings import/export."""),
	
	# رقم الإصدار
	addon_version="2026.1",
	
	# سجل التغييرات
	addon_changelog=_("""- New: first releace."""),
	
	# اسم المؤلف وبريده
	addon_author="Kamal Yaser <kamalyaser31@gmail.com>",
	
	# روابط (غيرها برابط مستودعك الحقيقي)
	addon_url="https://github.com/kamalyaser31/instantAccess",
	addon_sourceURL="https://github.com/kamalyaser31/qinstantAccess",
	
	# اسم ملف التوثيق
	addon_docFileName="readme.md",
	
	# أقل إصدار NVDA مدعوم
	addon_minimumNVDAVersion="2019.3.0",
	
	# آخر إصدار تم اختباره عليه
	addon_lastTestedNVDAVersion="2026.1",
	
	addon_updateChannel=None,
	addon_license=None,
	addon_licenseURL=None,
)

# تحديد ملفات بايثون (مهم جداً لنجاح البناء)
pythonSources: list[str] = ["addon/globalPlugins/instantAccess.py"]

# ملفات الترجمة
i18nSources: list[str] = pythonSources + ["buildVars.py"]

# ملفات مستبعدة
excludedFiles: list[str] = []

# اللغة الأساسية
baseLanguage: str = "en"

# إضافات Markdown
markdownExtensions: list[str] = []

brailleTables: BrailleTables = {}
symbolDictionaries: SymbolDictionaries = {}
