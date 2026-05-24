"""App name to package name mapping for supported applications."""

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


def get_supported_apps_text() -> str:
    """
    Get a formatted string of all supported app names and their package names.
    Used for LLM prompt context.

    Returns:
        Formatted string of app names and packages.
    """
    lines = ["支持的应用列表（名称 -> 包名）:"]
    for name, package in sorted(APP_PACKAGES.items()):
        lines.append(f"  {name} -> {package}")
    return "\n".join(lines)
