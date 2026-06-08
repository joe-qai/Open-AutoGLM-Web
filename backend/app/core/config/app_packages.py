"""App name to package name mapping for supported applications.

Contains mappings for Android, HarmonyOS, and iOS platforms.
"""

APP_PACKAGES: dict[str, str] = {
    # Social & Messaging
    "微信": "com.tencent.mm",
    "WeChat": "com.tencent.mm",
    "wechat": "com.tencent.mm",
    "QQ": "com.tencent.mobileqq",
    "微博": "com.sina.weibo",
    "Twitter": "com.twitter.android",
    "twitter": "com.twitter.android",
    "X": "com.twitter.android",
    "Telegram": "org.telegram.messenger",
    "WhatsApp": "com.whatsapp",
    "Whatsapp": "com.whatsapp",
    # E-commerce
    "淘宝": "com.taobao.taobao",
    "京东": "com.jingdong.app.mall",
    "拼多多": "com.xunmeng.pinduoduo",
    "淘宝闪购": "com.taobao.taobao",
    "京东秒送": "com.jingdong.app.mall",
    "天猫": "com.tmall.wphlient",
    "唯品会": "com.achievo.vipshop",
    # Lifestyle & Social
    "小红书": "com.xingin.xhs",
    "豆瓣": "com.douban.frodo",
    "知乎": "com.zhihu.android",
    "抖音": "com.ss.android.ugc.aweme",
    "TikTok": "com.zhiliaoapp.musically",
    "tiktok": "com.zhiliaoapp.musically",
    "快手": "com.smile.gifmaker",
    # Maps & Navigation
    "高德地图": "com.autonavi.minimap",
    "百度地图": "com.baidu.BaiduMap",
    "腾讯地图": "com.tencent.map",
    # Food & Services
    "美团": "com.sankuai.meituan",
    "大众点评": "com.dianping.v1",
    "饿了么": "me.ele",
    "肯德基": "com.yek.android.kfc.activitys",
    "麦当劳": "com.mcdonalds.app",
    # Travel
    "携程": "ctrip.android.view",
    "铁路12306": "com.MobileTicket",
    "12306": "com.MobileTicket",
    "去哪儿": "com.Qunar",
    "去哪儿旅行": "com.Qunar",
    "滴滴出行": "com.sdu.didi.psnger",
    # Video & Entertainment
    "bilibili": "tv.danmaku.bili",
    "B站": "tv.danmaku.bili",
    "腾讯视频": "com.tencent.qqlive",
    "爱奇艺": "com.qiyi.video",
    "优酷视频": "com.youku.phone",
    "芒果TV": "com.hunantv.imgo.activity",
    "红果短剧": "com.phoenix.read",
    "Netflix": "com.netflix.mediaclient",
    "YouTube": "com.google.android.youtube",
    # Music & Audio
    "网易云音乐": "com.netease.cloudmusic",
    "QQ音乐": "com.tencent.qqmusic",
    "汽水音乐": "com.luna.music",
    "喜马拉雅": "com.ximalaya.ting.android",
    "Spotify": "com.spotify.music",
    # Reading
    "番茄小说": "com.dragon.read",
    "番茄免费小说": "com.dragon.read",
    "七猫免费小说": "com.kmxs.reader",
    "起点读书": "com.qidian.QDReader",
    # Productivity
    "飞书": "com.ss.android.lark",
    "钉钉": "com.alibaba.android.rimet",
    "微信读书": "com.tencent.weread",
    "QQ邮箱": "com.tencent.androidqqmail",
    "邮箱": "com.android.email",
    # AI & Tools
    "豆包": "com.larus.nova",
    "文心一言": "com.baidu.ditu.protectplus",
    "ChatGPT": "com.openai.chatgpt",
    "Gemini": "com.google.android.apps.bard",
    # Smart Home
    "鹿客管家": "com.lockin.smart",
    # Health & Fitness
    "Keep": "com.gotokeep.keep",
    "keep": "com.gotokeep.keep",
    "美柚": "com.lingan.seeyou",
    "薄荷健康": "com.boohee.health",
    # News & Information
    "腾讯新闻": "com.tencent.news",
    "今日头条": "com.ss.android.article.news",
    "今日头条": "com.ss.android.article.news",
    "澎湃新闻": "com.thepaper",
    # Real Estate
    "贝壳找房": "com.lianjia.beike",
    "安居客": "com.anjuke.android.app",
    "链家": "com.homelink.rental",
    # Finance
    "同花顺": "com.hexin.plat.android",
    "支付宝": "com.eg.android.AlipayGphone",
    "微信支付": "com.tencent.mm",
    "股票": "com.tencent.stocks",
    # Games
    "王者荣耀": "com.tencent.tmgp.sgame",
    "原神": "com.miHoYo.OVSeBird",
    "星穹铁道": "com.miHoYo.hkrpg",
    "崩坏：星穹铁道": "com.miHoYo.hkrpg",
    "恋与深空": "com.papegames.lysk.cn",
    "蛋仔派对": "com.netease.eggyolk",
    "金铲铲之战": "com.tencent.autochess",
    # System
    "设置": "com.android.settings",
    "AndroidSettings": "com.android.settings",
    "Settings": "com.android.settings",
    "浏览器": "com.android.browser",
    "Chrome": "com.android.chrome",
    "chrome": "com.android.chrome",
    "Google Chrome": "com.android.chrome",
    "相机": "com.android.camera2",
    "Camera": "com.android.camera2",
    "相册": "com.google.android.apps.photos",
    "Photos": "com.google.android.apps.photos",
    "文件管理器": "com.android.fileexplorer",
    "Files": "com.android.fileexplorer",
    "电话": "com.android.contacts",
    "通讯录": "com.android.contacts",
    "短信": "com.android.mms",
    "日历": "com.android.calendar",
    "Calendar": "com.android.calendar",
    "计算器": "com.android.calculator2",
    "Calculator": "com.android.calculator2",
    "时钟": "com.android.deskclock",
    "Clock": "com.android.deskclock",
    "音乐": "com.google.android.apps.youtube.music",
    "Music": "com.google.android.apps.youtube.music",
    # Utilities
    "录音机": "com.android.soundrecorder",
    "AudioRecorder": "com.android.soundreccer",
    "备忘录": "com.google.android.keep",
    "Keep": "com.google.android.keep",
    "Temu": "com.einnovation.temu",
    "temu": "com.einnovation.temu",
    "Duolingo": "com.duolingo",
    "duolingo": "com.duolingo",
    "Reddit": "com.reddit.frontpage",
    "reddit": "com.reddit.frontpage",
    "鹿客管家": "com.lockin.loock"
}


def get_package_name(app_name: str) -> str | None:
    """
    Get the package name for an app name.

    Args:
        app_name: The display name of the app.

    Returns:
        The Android package name, or None if not found.
    """
    if not app_name:
        return None

    # Direct match
    if app_name in APP_PACKAGES:
        return APP_PACKAGES[app_name]

    # Case-insensitive match
    for name, package in APP_PACKAGES.items():
        if name.lower() == app_name.lower():
            return package

    # If input looks like a package name already, return it
    if '.' in app_name and ' ' not in app_name:
        return app_name

    return None


def get_app_name(package_name: str) -> str | None:
    """
    Get the app name from a package name.

    Args:
        package_name: The Android package name.

    Returns:
        The display name of the app, or None if not found.
    """
    for name, package in APP_PACKAGES.items():
        if package == package_name:
            return name
    return None


def list_supported_apps() -> list[str]:
    """
    Get a list of all supported app names.

    Returns:
        List of app names.
    """
    return list(APP_PACKAGES.keys())


def get_supported_apps_text(platform: str = "android") -> str:
    """
    Get a formatted string of all supported app names and their package names.
    Used for LLM prompt context.

    Args:
        platform: Platform to get apps for ("android", "harmonyos", "ios").

    Returns:
        Formatted string of app names and packages.
    """
    packages_map = _get_packages_map(platform)
    lines = [f"支持的应用列表（名称 -> 包名） [{platform}]:"]
    for name, package in sorted(packages_map.items()):
        lines.append(f"  {name} -> {package}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# HarmonyOS App Mappings
# ──────────────────────────────────────────────────────────────

# Custom ability names for apps that don't use the default "EntryAbility"
APP_ABILITIES: dict[str, str] = {
    "cn.wps.mobileoffice.hap": "DocumentAbility",
    "com.ccb.mobilebank.hm": "CcbMainAbility",
    "com.dewu.hos": "HomeAbility",
    "com.larus.nova.hm": "MainAbility",
    "com.luna.hm.music": "MainAbility",
    "com.meitu.meitupic": "MainAbility",
    "com.ss.hm.article.news": "MainAbility",
    "com.ss.hm.ugc.aweme": "MainAbility",
    "com.taobao.taobao4hmos": "Taobao_mainAbility",
    "com.tencent.videohm": "AppAbility",
    "com.ximalaya.ting.xmharmony": "MainBundleAbility",
    "com.zhihu.hmos": "PhoneAbility",
    "com.huawei.hmos.browser": "MainAbility",
    "com.huawei.hmos.calculator": "com.huawei.hmos.calculator.CalculatorAbility",
    "com.huawei.hmos.calendar": "MainAbility",
    "com.huawei.hmos.camera": "com.huawei.hmos.camera.MainAbility",
    "com.huawei.hmos.clock": "com.huawei.hmos.clock.phone",
    "com.huawei.hmos.clouddrive": "MainAbility",
    "com.huawei.hmos.email": "ApplicationAbility",
    "com.huawei.hmos.filemanager": "MainAbility",
    "com.huawei.hmos.health": "Activity_card_entryAbility",
    "com.huawei.hmos.notepad": "MainAbility",
    "com.huawei.hmos.photos": "MainAbility",
    "com.huawei.hmos.screenrecorder": "com.huawei.hmos.screenrecorder.ServiceExtAbility",
    "com.huawei.hmos.screenshot": "com.huawei.hmos.screenshot.ServiceExtAbility",
    "com.huawei.hmos.settings": "com.huawei.hmos.settings.MainAbility",
    "com.huawei.hmos.soundrecorder": "MainAbility",
    "com.huawei.hmos.vassistant": "AiCaptionServiceExtAbility",
    "com.huawei.hmos.wallet": "MainAbility",
    "com.huawei.hmsapp.appgallery": "MainAbility",
    "com.huawei.hmsapp.books": "MainAbility",
    "com.huawei.hmsapp.himovie": "MainAbility",
    "com.huawei.hmsapp.hisearch": "MainAbility",
    "com.huawei.hmsapp.music": "MainAbility",
    "com.huawei.hmsapp.thememanager": "MainAbility",
    "com.huawei.hmsapp.totemweather": "com.huawei.hmsapp.totemweather.MainAbility",
    "com.ohos.callui": "com.ohos.callui.ServiceAbility",
    "com.ohos.contacts": "com.ohos.contacts.MainAbility",
    "com.ohos.mms": "com.ohos.mms.MainAbility",
}

APP_PACKAGES_HARMONYOS: dict[str, str] = {
    # Social & Messaging
    "微信": "com.tencent.wechat",
    "QQ": "com.tencent.mqq",
    "微博": "com.sina.weibo.stage",
    # E-commerce
    "淘宝": "com.taobao.taobao4hmos",
    "京东": "com.jd.hm.mall",
    "拼多多": "com.xunmeng.pinduoduo.hos",
    "淘宝闪购": "com.taobao.taobao4hmos",
    "京东秒送": "com.jd.hm.mall",
    # Lifestyle & Social
    "小红书": "com.xingin.xhs_hos",
    "知乎": "com.zhihu.hmos",
    # Maps & Navigation
    "高德地图": "com.amap.hmapp",
    "百度地图": "com.baidu.hmmap",
    # Food & Services
    "美团": "com.sankuai.hmeituan",
    "美团外卖": "com.meituan.takeaway",
    "大众点评": "com.sankuai.dianping",
    # Travel
    "铁路12306": "com.chinarailway.ticketingHM",
    "12306": "com.chinarailway.ticketingHM",
    "滴滴出行": "com.sdu.didi.hmos.psnger",
    # Video & Entertainment
    "bilibili": "yylx.danmaku.bili",
    "抖音": "com.ss.hm.ugc.aweme",
    "快手": "com.kuaishou.hmapp",
    "腾讯视频": "com.tencent.videohm",
    "爱奇艺": "com.qiyi.video.hmy",
    "芒果TV": "com.mgtv.phone",
    # Music & Audio
    "QQ音乐": "com.tencent.hm.qqmusic",
    "汽水音乐": "com.luna.hm.music",
    "喜马拉雅": "com.ximalaya.ting.xmharmony",
    # Productivity
    "飞书": "com.ss.feishu",
    # AI & Tools
    "豆包": "com.larus.nova.hm",
    # News & Information
    "今日头条": "com.ss.hm.article.news",
    # HarmonyOS 第三方应用
    "百度": "com.baidu.baiduapp",
    "阿里巴巴": "com.alibaba.wireless_hmos",
    "WPS": "cn.wps.mobileoffice.hap",
    "企业微信": "com.tencent.wework.hmos",
    "同程": "com.tongcheng.hmos",
    "同程旅行": "com.tongcheng.hmos",
    "唯品会": "com.vip.hosapp",
    "支付宝": "com.alipay.mobile.client",
    "UC浏览器": "com.uc.mobile",
    "闲鱼": "com.taobao.idlefish4ohos",
    "转转": "com.zhuanzhuan.hmoszz",
    "迅雷": "com.xunlei.thunder",
    "搜狗输入法": "com.sogou.input",
    "扫描全能王": "com.intsig.camscanner.hap",
    "美图秀秀": "com.meitu.meitupic",
    "58同城": "com.wuba.life",
    "得物": "com.dewu.hos",
    "海底捞": "com.haidilao.haros",
    "中国移动": "com.droi.tong",
    "中国联通": "com.sinovatech.unicom.ha",
    "国家税务总局": "cn.gov.chinatax.gt4.hm",
    "建设银行": "com.ccb.mobilebank.hm",
    "快手极速版": "com.kuaishou.hmnebula",
    # HarmonyOS 系统应用 - 工具类
    "浏览器": "com.huawei.hmos.browser",
    "计算器": "com.huawei.hmos.calculator",
    "日历": "com.huawei.hmos.calendar",
    "相机": "com.huawei.hmos.camera",
    "时钟": "com.huawei.hmos.clock",
    "云盘": "com.huawei.hmos.clouddrive",
    "云空间": "com.huawei.hmos.clouddrive",
    "邮件": "com.huawei.hmos.email",
    "文件管理器": "com.huawei.hmos.filemanager",
    "文件": "com.huawei.hmos.files",
    "查找设备": "com.huawei.hmos.finddevice",
    "查找手机": "com.huawei.hmos.finddevice",
    "录音机": "com.huawei.hmos.soundrecorder",
    "录音": "com.huawei.hmos.soundrecorder",
    "录屏": "com.huawei.hmos.screenrecorder",
    "截屏": "com.huawei.hmos.screenshot",
    "笔记": "com.huawei.hmos.notepad",
    "备忘录": "com.huawei.hmos.notepad",
    # HarmonyOS 系统应用 - 媒体类
    "相册": "com.huawei.hmos.photos",
    "图库": "com.huawei.hmos.photos",
    # HarmonyOS 系统应用 - 通讯类
    "联系人": "com.ohos.contacts",
    "通讯录": "com.ohos.contacts",
    "短信": "com.ohos.mms",
    "信息": "com.ohos.mms",
    "电话": "com.ohos.callui",
    "拨号": "com.ohos.callui",
    # HarmonyOS 系统应用 - 设置类
    "设置": "com.huawei.hmos.settings",
    "系统设置": "com.huawei.hmos.settings",
    "AndroidSystemSettings": "com.huawei.hmos.settings",
    "Android System Settings": "com.huawei.hmos.settings",
    "Settings": "com.huawei.hmos.settings",
    # HarmonyOS 系统应用 - 生活服务
    "健康": "com.huawei.hmos.health",
    "运动健康": "com.huawei.hmos.health",
    "地图": "com.huawei.hmos.maps.app",
    "华为地图": "com.huawei.hmos.maps.app",
    "钱包": "com.huawei.hmos.wallet",
    "华为钱包": "com.huawei.hmos.wallet",
    "智慧生活": "com.huawei.hmos.ailife",
    "智能助手": "com.huawei.hmos.vassistant",
    "小艺": "com.huawei.hmos.vassistant",
    # HarmonyOS 服务
    "应用市场": "com.huawei.hmsapp.appgallery",
    "华为应用市场": "com.huawei.hmsapp.appgallery",
    "音乐": "com.huawei.hmsapp.music",
    "华为音乐": "com.huawei.hmsapp.music",
    "主题": "com.huawei.hmsapp.thememanager",
    "主题管理": "com.huawei.hmsapp.thememanager",
    "天气": "com.huawei.hmsapp.totemweather",
    "华为天气": "com.huawei.hmsapp.totemweather",
    "视频": "com.huawei.hmsapp.himovie",
    "华为视频": "com.huawei.hmsapp.himovie",
    "阅读": "com.huawei.hmsapp.books",
    "华为阅读": "com.huawei.hmsapp.books",
    "游戏中心": "com.huawei.hmsapp.gamecenter",
    "华为游戏中心": "com.huawei.hmsapp.gamecenter",
    "搜索": "com.huawei.hmsapp.hisearch",
    "华为搜索": "com.huawei.hmsapp.hisearch",
    "指南针": "com.huawei.hmsapp.compass",
    "会员中心": "com.huawei.hmos.myhuawei",
    "我的华为": "com.huawei.hmos.myhuawei",
    "华为会员": "com.huawei.hmos.myhuawei",
}


# ──────────────────────────────────────────────────────────────
# iOS App Mappings
# ──────────────────────────────────────────────────────────────

APP_PACKAGES_IOS: dict[str, str] = {
    # Tencent Apps (腾讯系)
    "微信": "com.tencent.xin",
    "企业微信": "com.tencent.ww",
    "微信读书": "com.tencent.weread",
    "微信听书": "com.tencent.wehear",
    "QQ": "com.tencent.mqq",
    "QQ音乐": "com.tencent.QQMusic",
    "QQ阅读": "com.tencent.qqreaderiphone",
    "QQ邮箱": "com.tencent.qqmail",
    "QQ浏览器": "com.tencent.mttlite",
    "TIM": "com.tencent.tim",
    "腾讯新闻": "com.tencent.info",
    "腾讯视频": "com.tencent.live4iphone",
    # Alibaba Apps (阿里系)
    "支付宝": "com.alipay.iphoneclient",
    "钉钉": "com.laiwang.DingTalk",
    "闲鱼": "com.taobao.fleamarket",
    "淘宝": "com.taobao.taobao4iphone",
    "天猫": "com.taobao.tmall",
    "饿了么": "me.ele.ios.eleme",
    "高德地图": "com.autonavi.amap",
    "优酷": "com.youku.YouKu",
    # ByteDance Apps (字节系)
    "抖音": "com.ss.iphone.ugc.Aweme",
    "Tiktok": "com.zhiliaoapp.musically",
    "飞书": "com.bytedance.ee.lark",
    "今日头条": "com.ss.iphone.article.News",
    # Meituan Apps (美团系)
    "美团": "com.meituan.imeituan",
    "美团外卖": "com.meituan.itakeaway",
    "大众点评": "com.dianping.dpscope",
    # JD Apps (京东系)
    "京东": "com.360buy.jdmobile",
    # NetEase Apps (网易系)
    "网易新闻": "com.netease.news",
    "网易云音乐": "com.netease.cloudmusic",
    "网易邮箱大师": "com.netease.macmail",
    # Baidu Apps (百度系)
    "百度": "com.baidu.BaiduMobile",
    "百度网盘": "com.baidu.netdisk",
    "百度贴吧": "com.baidu.tieba",
    "百度地图": "com.baidu.map",
    "百度翻译": "com.baidu.translate",
    # Kuaishou Apps (快手系)
    "快手": "com.jiangjia.gif",
    "快手极速版": "com.kuaishou.nebula",
    # Other Popular Apps
    "哔哩哔哩": "tv.danmaku.bilianime",
    "芒果TV": "com.hunantv.imgotv",
    "微博": "com.sina.weibo",
    "豆瓣": "com.douban.frodo",
    "知乎": "com.zhihu.ios",
    "小红书": "com.xingin.discover",
    "喜马拉雅": "com.gemd.iting",
    "得物": "com.siwuai.duapp",
    "起点读书": "m.qidian.QDReaderAppStore",
    "番茄小说": "com.dragon.read",
    "拼多多": "com.xunmeng.pinduoduo",
    "爱奇艺视频": "com.qiyi.iphone",
    "携程": "ctrip.com",
    "去哪儿旅行": "com.qunar.iphoneclient8",
    # International Apps
    "Google Chrome": "com.google.chrome.ios",
    "Gmail": "com.google.Gmail",
    "Facebook": "com.facebook.Facebook",
    "Instagram": "com.burbn.instagram",
    "Youtube": "com.google.ios.youtube",
    "Spotify": "com.spotify.client",
    "Netflix": "com.netflix.Netflix",
    "Twitter": "com.atebits.Tweetie2",
    "WhatsApp": "net.whatsapp.WhatsApp",
    # Apple Native Apps
    "Safari": "com.apple.mobilesafari",
    "App Store": "com.apple.AppStore",
    "设置": "com.apple.Preferences",
    "相机": "com.apple.camera",
    "照片": "com.apple.mobileslideshow",
    "时钟": "com.apple.mobiletimer",
    "备忘录": "com.apple.mobilenotes",
    "提醒事项": "com.apple.reminders",
    "天气": "com.apple.weather",
    "日历": "com.apple.mobilecal",
    "地图": "com.apple.Maps",
    "电话": "com.apple.mobilephone",
    "通讯录": "com.apple.MobileAddressBook",
    "信息": "com.apple.MobileSMS",
    "计算器": "com.apple.calculator",
    "钱包": "com.apple.Passbook",
    "邮件": "com.apple.mobilemail",
    "音乐": "com.apple.Music",
}


# ──────────────────────────────────────────────────────────────
# Platform-aware helper functions
# ──────────────────────────────────────────────────────────────

def _get_packages_map(platform: str) -> dict[str, str]:
    """Get the appropriate packages dict for a platform."""
    if platform == "harmonyos":
        return APP_PACKAGES_HARMONYOS
    elif platform == "ios":
        return APP_PACKAGES_IOS
    return APP_PACKAGES


def get_package_name_harmonyos(app_name: str) -> str | None:
    """Get the HarmonyOS bundle name for an app name."""
    if not app_name:
        return None
    if app_name in APP_PACKAGES_HARMONYOS:
        return APP_PACKAGES_HARMONYOS[app_name]
    for name, package in APP_PACKAGES_HARMONYOS.items():
        if name.lower() == app_name.lower():
            return package
    if '.' in app_name and ' ' not in app_name:
        return app_name
    return None


def get_package_name_ios(app_name: str) -> str | None:
    """Get the iOS bundle ID for an app name."""
    if not app_name:
        return None
    if app_name in APP_PACKAGES_IOS:
        return APP_PACKAGES_IOS[app_name]
    for name, package in APP_PACKAGES_IOS.items():
        if name.lower() == app_name.lower():
            return package
    if '.' in app_name and ' ' not in app_name:
        return app_name
    return None


def get_package_name_for_platform(platform: str, app_name: str) -> str | None:
    """
    Get the package/bundle name for an app across any platform.

    Args:
        platform: "android", "harmonyos", or "ios"
        app_name: The display name of the app.

    Returns:
        The platform-specific package/bundle ID, or None if not found.
    """
    if platform == "harmonyos":
        return get_package_name_harmonyos(app_name)
    elif platform == "ios":
        return get_package_name_ios(app_name)
    return get_package_name(app_name)


def get_harmonyos_ability(bundle_name: str) -> str:
    """
    Get the HarmonyOS ability name for a bundle.

    Args:
        bundle_name: The HarmonyOS bundle name.

    Returns:
        The ability name, defaults to "EntryAbility" if not found.
    """
    return APP_ABILITIES.get(bundle_name, "EntryAbility")
