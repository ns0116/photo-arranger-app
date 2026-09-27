import math

# Lightweight offline city database (city_en, city_ja, country_en, country_ja, lat, lon)
# Covers all 47 prefectural capitals and major sightseeing spots in Japan,
# as well as top international travel destinations and world capitals.
CITIES = [
    # --- 日本: 北海道・東北 ---
    ("Sapporo", "札幌", "Japan", "日本", 43.0618, 141.3545),
    ("Hakodate", "函館", "Japan", "日本", 41.7687, 140.7290),
    ("Asahikawa", "旭川", "Japan", "日本", 43.7706, 142.3649),
    ("Otaru", "小樽", "Japan", "日本", 43.1907, 140.9947),
    ("Furano", "富良野", "Japan", "日本", 43.3421, 142.3832),
    ("Aomori", "青森", "Japan", "日本", 40.8244, 140.7400),
    ("Hirosaki", "弘前", "Japan", "日本", 40.6031, 140.4639),
    ("Morioka", "盛岡", "Japan", "日本", 39.7036, 141.1527),
    ("Sendai", "仙台", "Japan", "日本", 38.2682, 140.8694),
    ("Akita", "秋田", "Japan", "日本", 39.7186, 140.1024),
    ("Yamagata", "山形", "Japan", "日本", 38.2404, 140.3633),
    ("Fukushima", "福島", "Japan", "日本", 37.7503, 140.4678),
    ("Aizuwakamatsu", "会津若松", "Japan", "日本", 37.4948, 139.9298),
    # --- 日本: 関東 ---
    ("Mito", "水戸", "Japan", "日本", 36.3418, 140.4468),
    ("Tsukuba", "つくば", "Japan", "日本", 36.0835, 140.0764),
    ("Utsunomiya", "宇都宮", "Japan", "日本", 36.5658, 139.8836),
    ("Nikko", "日光", "Japan", "日本", 36.7199, 139.6983),
    ("Maebashi", "前橋", "Japan", "日本", 36.3911, 139.0608),
    ("Takasaki", "高崎", "Japan", "日本", 36.3223, 139.0127),
    ("Kusatsu", "草津", "Japan", "日本", 36.6206, 138.5960),
    ("Saitama", "さいたま", "Japan", "日本", 35.8569, 139.6489),
    ("Kawagoe", "川越", "Japan", "日本", 35.9251, 139.4858),
    ("Chichibu", "秩父", "Japan", "日本", 35.9922, 139.0853),
    ("Chiba", "千葉", "Japan", "日本", 35.6074, 140.1065),
    ("Urayasu", "浦安", "Japan", "日本", 35.6531, 139.8984),
    ("Narita", "成田", "Japan", "日本", 35.7767, 140.3188),
    ("Tokyo", "東京", "Japan", "日本", 35.6895, 139.6917),
    ("Hachioji", "八王子", "Japan", "日本", 35.6558, 139.3239),
    ("Yokohama", "横浜", "Japan", "日本", 35.4437, 139.6380),
    ("Kawasaki", "川崎", "Japan", "日本", 35.5308, 139.7029),
    ("Kamakura", "鎌倉", "Japan", "日本", 35.3192, 139.5467),
    ("Hakone", "箱根", "Japan", "日本", 35.2323, 139.1069),
    # --- 日本: 中部・北陸 ---
    ("Niigata", "新潟", "Japan", "日本", 37.9022, 139.0232),
    ("Nagaoka", "長岡", "Japan", "日本", 37.4475, 138.8514),
    ("Toyama", "富山", "Japan", "日本", 36.6953, 137.2113),
    ("Kanazawa", "金沢", "Japan", "日本", 36.5947, 136.6256),
    ("Fukui", "福井", "Japan", "日本", 36.0652, 136.2219),
    ("Kofu", "甲府", "Japan", "日本", 35.6639, 138.5684),
    ("Fujiyoshida", "富士吉田", "Japan", "日本", 35.4876, 138.7953),
    ("Nagano", "長野", "Japan", "日本", 36.6513, 138.1810),
    ("Matsumoto", "松本", "Japan", "日本", 36.2380, 137.9720),
    ("Karuizawa", "軽井沢", "Japan", "日本", 36.3488, 138.6358),
    ("Gifu", "岐阜", "Japan", "日本", 35.3912, 136.7223),
    ("Takayama", "高山", "Japan", "日本", 36.1460, 137.2522),
    ("Shirakawa", "白川郷", "Japan", "日本", 36.2562, 136.9067),
    ("Shizuoka", "静岡", "Japan", "日本", 34.9756, 138.3828),
    ("Hamamatsu", "浜松", "Japan", "日本", 34.7108, 137.7261),
    ("Atami", "熱海", "Japan", "日本", 35.0963, 139.0717),
    ("Nagoya", "名古屋", "Japan", "日本", 35.1815, 136.9066),
    ("Toyota", "豊田", "Japan", "日本", 35.0848, 137.1559),
    # --- 日本: 近畿 ---
    ("Tsu", "津", "Japan", "日本", 34.7303, 136.5086),
    ("Ise", "伊勢", "Japan", "日本", 34.4875, 136.7093),
    ("Otsu", "大津", "Japan", "日本", 35.0045, 135.8686),
    ("Hikone", "彦根", "Japan", "日本", 35.2744, 136.2597),
    ("Kyoto", "京都", "Japan", "日本", 35.0116, 135.7681),
    ("Uji", "宇治", "Japan", "日本", 34.8893, 135.8005),
    ("Osaka", "大阪", "Japan", "日本", 34.6937, 135.5023),
    ("Sakai", "堺", "Japan", "日本", 34.5733, 135.4830),
    ("Kobe", "神戸", "Japan", "日本", 34.6901, 135.1955),
    ("Himeji", "姫路", "Japan", "日本", 34.8152, 134.6853),
    ("Nara", "奈良", "Japan", "日本", 34.6851, 135.8048),
    ("Wakayama", "和歌山", "Japan", "日本", 34.2260, 135.1675),
    ("Shirahama", "白浜", "Japan", "日本", 33.6822, 135.3436),
    # --- 日本: 中国・四国 ---
    ("Tottori", "鳥取", "Japan", "日本", 35.5011, 134.2351),
    ("Yonago", "米子", "Japan", "日本", 35.4281, 133.3308),
    ("Matsue", "松江", "Japan", "日本", 35.4723, 133.0505),
    ("Izumo", "出雲", "Japan", "日本", 35.3669, 132.7554),
    ("Okayama", "岡山", "Japan", "日本", 34.6618, 133.9350),
    ("Kurashiki", "倉敷", "Japan", "日本", 34.5850, 133.7719),
    ("Hiroshima", "広島", "Japan", "日本", 34.3853, 132.4553),
    ("Onomichi", "尾道", "Japan", "日本", 34.4088, 133.1950),
    ("Miyajima", "宮島", "Japan", "日本", 34.2980, 132.3195),
    ("Yamaguchi", "山口", "Japan", "日本", 34.1859, 131.4714),
    ("Shimonoseki", "下関", "Japan", "日本", 33.9578, 130.9415),
    ("Tokushima", "徳島", "Japan", "日本", 34.0657, 134.5594),
    ("Naruto", "鳴門", "Japan", "日本", 34.1795, 134.6085),
    ("Takamatsu", "高松", "Japan", "日本", 34.3402, 134.0433),
    ("Matsuyama", "松山", "Japan", "日本", 33.8417, 132.7661),
    ("Kochi", "高知", "Japan", "日本", 33.5597, 133.5311),
    # --- 日本: 九州・沖縄 ---
    ("Fukuoka", "福岡", "Japan", "日本", 33.5904, 130.4017),
    ("Kitakyushu", "北九州", "Japan", "日本", 33.8835, 130.8752),
    ("Dazaifu", "太宰府", "Japan", "日本", 33.5135, 130.5239),
    ("Saga", "佐賀", "Japan", "日本", 33.2494, 130.2988),
    ("Nagasaki", "長崎", "Japan", "日本", 32.7448, 129.8737),
    ("Sasebo", "佐世保", "Japan", "日本", 33.1599, 129.7237),
    ("Kumamoto", "熊本", "Japan", "日本", 32.7898, 130.7417),
    ("Aso", "阿蘇", "Japan", "日本", 32.9377, 131.1217),
    ("Oita", "大分", "Japan", "日本", 33.2382, 131.6126),
    ("Beppu", "別府", "Japan", "日本", 33.2846, 131.4912),
    ("Yufuin", "湯布院", "Japan", "日本", 33.2652, 131.3553),
    ("Miyazaki", "宮崎", "Japan", "日本", 31.9111, 131.4239),
    ("Kagoshima", "鹿児島", "Japan", "日本", 31.5602, 130.5581),
    ("Yakushima", "屋久島", "Japan", "日本", 30.3444, 130.5186),
    ("Amami", "奄美", "Japan", "日本", 28.3775, 129.4950),
    ("Naha", "那覇", "Japan", "日本", 26.2124, 127.6809),
    ("Nago", "名護", "Japan", "日本", 26.5916, 127.9774),
    ("Ishigaki", "石垣島", "Japan", "日本", 24.3448, 124.1572),
    ("Miyakojima", "宮古島", "Japan", "日本", 24.8055, 125.2811),
    # --- アジア ---
    ("Seoul", "ソウル", "South Korea", "韓国", 37.5665, 126.9780),
    ("Busan", "釜山", "South Korea", "韓国", 35.1796, 129.0756),
    ("Jeju", "済州", "South Korea", "韓国", 33.4996, 126.5312),
    ("Incheon", "仁川", "South Korea", "韓国", 37.4563, 126.7052),
    ("Taipei", "台北", "Taiwan", "台湾", 25.0330, 121.5654),
    ("Kaohsiung", "高雄", "Taiwan", "台湾", 22.6273, 120.3014),
    ("Tainan", "台南", "Taiwan", "台湾", 22.9997, 120.2270),
    ("Taichung", "台中", "Taiwan", "台湾", 24.1477, 120.6736),
    ("Beijing", "北京", "China", "中国", 39.9042, 116.4074),
    ("Shanghai", "上海", "China", "中国", 31.2304, 121.4737),
    ("Guangzhou", "広州", "China", "中国", 23.1291, 113.2644),
    ("Shenzhen", "深圳", "China", "中国", 22.5431, 114.0579),
    ("Chengdu", "成都", "China", "中国", 30.5728, 104.0668),
    ("Xi'an", "西安", "China", "中国", 34.3416, 108.9398),
    ("Hong Kong", "香港", "Hong Kong", "香港", 22.3193, 114.1694),
    ("Macau", "マカオ", "Macau", "マカオ", 22.1987, 113.5439),
    ("Bangkok", "バンコク", "Thailand", "タイ", 13.7563, 100.5018),
    ("Phuket", "プーケット", "Thailand", "タイ", 7.8804, 98.3923),
    ("Chiang Mai", "チェンマイ", "Thailand", "タイ", 18.7883, 98.9853),
    ("Pattaya", "パタヤ", "Thailand", "タイ", 12.9276, 100.8771),
    ("Singapore", "シンガポール", "Singapore", "シンガポール", 1.3521, 103.8198),
    ("Hanoi", "ハノイ", "Vietnam", "ベトナム", 21.0285, 105.8542),
    ("Ho Chi Minh City", "ホーチミン", "Vietnam", "ベトナム", 10.8231, 106.6297),
    ("Da Nang", "ダナン", "Vietnam", "ベトナム", 16.0544, 108.2022),
    ("Hoi An", "ホイアン", "Vietnam", "ベトナム", 15.8801, 108.3380),
    ("Kuala Lumpur", "クアラルンプール", "Malaysia", "マレーシア", 3.1390, 101.6869),
    ("Penang", "ペナン", "Malaysia", "マレーシア", 5.4141, 100.3288),
    ("Kota Kinabalu", "コタキナバル", "Malaysia", "マレーシア", 5.9804, 116.0735),
    ("Jakarta", "ジャカルタ", "Indonesia", "インドネシア", -6.2088, 106.8456),
    ("Bali", "バリ", "Indonesia", "インドネシア", -8.4095, 115.1889),
    ("Manila", "マニラ", "Philippines", "フィリピン", 14.5995, 120.9842),
    ("Cebu", "セブ", "Philippines", "フィリピン", 10.3157, 123.8854),
    ("Boracay", "ボラカイ", "Philippines", "フィリピン", 11.9674, 121.9248),
    ("Delhi", "デリー", "India", "インド", 28.6139, 77.2090),
    ("Mumbai", "ムンバイ", "India", "インド", 19.0760, 72.8777),
    ("Agra", "アーグラ", "India", "インド", 27.1767, 78.0081),
    ("Dubai", "ドバイ", "UAE", "UAE", 25.2048, 55.2708),
    ("Abu Dhabi", "アブダビ", "UAE", "UAE", 24.4539, 54.3773),
    ("Istanbul", "イスタンブール", "Turkey", "トルコ", 41.0082, 28.9784),
    ("Cappadocia", "カッパドキア", "Turkey", "トルコ", 38.6431, 34.8289),
    # --- 北米・ハワイ ---
    ("Honolulu", "ホノルル", "USA", "アメリカ", 21.3069, -157.8583),
    ("Maui", "マウイ", "USA", "アメリカ", 20.7984, -156.3319),
    ("Kauai", "カウアイ", "USA", "アメリカ", 22.0964, -159.5261),
    ("New York", "ニューヨーク", "USA", "アメリカ", 40.7128, -74.0060),
    ("Los Angeles", "ロサンゼルス", "USA", "アメリカ", 34.0522, -118.2437),
    ("San Francisco", "サンフランシスコ", "USA", "アメリカ", 37.7749, -122.4194),
    ("Las Vegas", "ラスベガス", "USA", "アメリカ", 36.1699, -115.1398),
    ("Seattle", "シアトル", "USA", "アメリカ", 47.6062, -122.3321),
    ("Chicago", "シカゴ", "USA", "アメリカ", 41.8781, -87.6298),
    ("Boston", "ボストン", "USA", "アメリカ", 42.3601, -71.0589),
    ("Washington DC", "ワシントンDC", "USA", "アメリカ", 38.9072, -77.0369),
    ("Orlando", "オーランド", "USA", "アメリカ", 28.5383, -81.3792),
    ("Miami", "マイアミ", "USA", "アメリカ", 25.7617, -80.1918),
    ("San Diego", "サンディエゴ", "USA", "アメリカ", 32.7157, -117.1611),
    ("Portland", "ポートランド", "USA", "アメリカ", 45.5152, -122.6784),
    ("Grand Canyon", "グランドキャニオン", "USA", "アメリカ", 36.0544, -112.1401),
    ("Vancouver", "バンクーバー", "Canada", "カナダ", 49.2827, -123.1207),
    ("Toronto", "トロント", "Canada", "カナダ", 43.6532, -79.3832),
    ("Montreal", "モントリオール", "Canada", "カナダ", 45.5017, -73.5673),
    ("Banff", "バンフ", "Canada", "カナダ", 51.1784, -115.5708),
    ("Mexico City", "メキシコシティ", "Mexico", "メキシコ", 19.4326, -99.1332),
    ("Cancun", "カンクン", "Mexico", "メキシコ", 21.1619, -86.8515),
    # --- ヨーロッパ ---
    ("London", "ロンドン", "UK", "イギリス", 51.5074, -0.1278),
    ("Edinburgh", "エディンバラ", "UK", "イギリス", 55.9533, -3.1883),
    ("Paris", "パリ", "France", "フランス", 48.8566, 2.3522),
    ("Nice", "ニース", "France", "フランス", 43.7102, 7.2620),
    ("Lyon", "リヨン", "France", "フランス", 45.7640, 4.8357),
    ("Marseille", "マルセイユ", "France", "フランス", 43.2965, 5.3698),
    ("Rome", "ローマ", "Italy", "イタリア", 41.9028, 12.4964),
    ("Milan", "ミラノ", "Italy", "イタリア", 45.4642, 9.1900),
    ("Florence", "フィレンツェ", "Italy", "イタリア", 43.7696, 11.2558),
    ("Venice", "ベネチア", "Italy", "イタリア", 45.4408, 12.3155),
    ("Naples", "ナポリ", "Italy", "イタリア", 40.8518, 14.2681),
    ("Madrid", "マドリード", "Spain", "スペイン", 40.4168, -3.7038),
    ("Barcelona", "バルセロナ", "Spain", "スペイン", 41.3851, 2.1734),
    ("Seville", "セビリア", "Spain", "スペイン", 37.3891, -5.9845),
    ("Berlin", "ベルリン", "Germany", "ドイツ", 52.5200, 13.4050),
    ("Munich", "ミュンヘン", "Germany", "ドイツ", 48.1351, 11.5820),
    ("Frankfurt", "フランクフルト", "Germany", "ドイツ", 50.1109, 8.6821),
    ("Amsterdam", "アムステルダム", "Netherlands", "オランダ", 52.3676, 4.9041),
    ("Brussels", "ブリュッセル", "Belgium", "ベルギー", 50.8503, 4.3517),
    ("Zurich", "チューリッヒ", "Switzerland", "スイス", 47.3769, 8.5417),
    ("Geneva", "ジュネーブ", "Switzerland", "スイス", 46.2044, 6.1432),
    ("Vienna", "ウィーン", "Austria", "オーストリア", 48.2082, 16.3738),
    ("Salzburg", "ザルツブルク", "Austria", "オーストリア", 47.8095, 13.0550),
    ("Prague", "プラハ", "Czech Republic", "チェコ", 50.0755, 14.4378),
    ("Budapest", "ブダペスト", "Hungary", "ハンガリー", 47.4979, 19.0402),
    ("Athens", "アテネ", "Greece", "ギリシャ", 37.9838, 23.7275),
    ("Santorini", "サントリーニ", "Greece", "ギリシャ", 36.3932, 25.4615),
    ("Lisbon", "リスボン", "Portugal", "ポルトガル", 38.7223, -9.1393),
    ("Dublin", "ダブリン", "Ireland", "アイルランド", 53.3498, -6.2603),
    ("Copenhagen", "コペンハーゲン", "Denmark", "デンマーク", 55.6761, 12.5683),
    ("Stockholm", "ストックホルム", "Sweden", "スウェーデン", 59.3293, 18.0686),
    ("Oslo", "オスロ", "Norway", "ノルウェー", 59.9139, 10.7522),
    ("Helsinki", "ヘルシンキ", "Finland", "フィンランド", 60.1699, 24.9384),
    ("Reykjavik", "レイキャビク", "Iceland", "アイスランド", 64.1466, -21.9426),
    # --- オセアニア・リゾート ---
    ("Sydney", "シドニー", "Australia", "オーストラリア", -33.8688, 151.2093),
    ("Melbourne", "メルボルン", "Australia", "オーストラリア", -37.8136, 144.9631),
    ("Brisbane", "ブリスベン", "Australia", "オーストラリア", -27.4698, 153.0251),
    (
        "Gold Coast",
        "ゴールドコースト",
        "Australia",
        "オーストラリア",
        -28.0167,
        153.4000,
    ),
    ("Cairns", "ケアンズ", "Australia", "オーストラリア", -16.9186, 145.7781),
    ("Perth", "パース", "Australia", "オーストラリア", -31.9505, 115.8605),
    ("Auckland", "オークランド", "New Zealand", "ニュージーランド", -36.8485, 174.7633),
    (
        "Christchurch",
        "クライストチャーチ",
        "New Zealand",
        "ニュージーランド",
        -43.5321,
        172.6362,
    ),
    (
        "Queenstown",
        "クイーンズタウン",
        "New Zealand",
        "ニュージーランド",
        -45.0312,
        168.6626,
    ),
    ("Guam", "グアム", "Guam", "グアム", 13.4443, 144.7937),
    ("Saipan", "サイパン", "Northern Mariana Islands", "サイパン", 15.1833, 145.7500),
    ("Fiji", "フィジー", "Fiji", "フィジー", -17.7134, 178.0650),
    ("Tahiti", "タヒチ", "French Polynesia", "タヒチ", -17.6509, -149.4260),
    ("Maldives", "モルディブ", "Maldives", "モルディブ", 4.1755, 73.5093),
    # --- 中南米・アフリカ ---
    ("Rio de Janeiro", "リオデジャネイロ", "Brazil", "ブラジル", -22.9068, -43.1729),
    ("Sao Paulo", "サンパウロ", "Brazil", "ブラジル", -23.5505, -46.6333),
    (
        "Buenos Aires",
        "ブエノスアイレス",
        "Argentina",
        "アルゼンチン",
        -34.6037,
        -58.3816,
    ),
    ("Cusco", "クスコ", "Peru", "ペルー", -13.5319, -71.9675),
    ("Lima", "リマ", "Peru", "ペルー", -12.0464, -77.0428),
    ("Cairo", "カイロ", "Egypt", "エジプト", 30.0444, 31.2357),
    ("Cape Town", "ケープタウン", "South Africa", "南アフリカ", -33.9249, 18.4241),
]


def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points in km."""
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def reverse_geocode(lat, lon, max_distance_km=None):
    """Performs offline reverse geocoding to find the nearest city and country.

    Args:
        lat (float or None): Latitude in decimal degrees.
        lon (float or None): Longitude in decimal degrees.
        max_distance_km (float, optional): Maximum distance threshold in km.

    Returns:
        dict: Geocoded location information containing:
            - city: str (English city name or 'No_Location')
            - city_ja: str (Japanese city name or '位置情報なし')
            - country: str (English country name or 'No_Location')
            - country_ja: str (Japanese country name or '位置情報なし')
            - distance_km: float or None
            - lat: float or None
            - lon: float or None
    """
    if lat is None or lon is None:
        return {
            "has_gps": False,
            "city": "No_Location",
            "city_ja": "位置情報なし",
            "country": "No_Location",
            "country_ja": "位置情報なし",
            "distance_km": None,
            "lat": None,
            "lon": None,
        }

    rad = math.pi / 180.0
    lat_r = lat * rad
    lon_r = lon * rad

    best_dist_sq = float("inf")
    best_entry = None

    # Equirectangular approximation for rapid search
    for city_en, city_ja, country_en, country_ja, c_lat, c_lon in CITIES:
        c_lat_r = c_lat * rad
        c_lon_r = c_lon * rad
        x = (c_lon_r - lon_r) * math.cos((lat_r + c_lat_r) / 2.0)
        y = c_lat_r - lat_r
        d2 = x * x + y * y
        if d2 < best_dist_sq:
            best_dist_sq = d2
            best_entry = (city_en, city_ja, country_en, country_ja, c_lat, c_lon)

    if best_entry is None:
        return {
            "has_gps": True,
            "city": "Unknown_City",
            "city_ja": "不明な都市",
            "country": "Unknown_Country",
            "country_ja": "不明な国",
            "distance_km": None,
            "lat": lat,
            "lon": lon,
        }

    city_en, city_ja, country_en, country_ja, c_lat, c_lon = best_entry
    exact_km = round(haversine_distance_km(lat, lon, c_lat, c_lon), 1)

    if max_distance_km is not None and exact_km > max_distance_km:
        return {
            "has_gps": True,
            "city": "Unknown_City",
            "city_ja": "不明な都市",
            "country": country_en,
            "country_ja": country_ja,
            "distance_km": exact_km,
            "lat": lat,
            "lon": lon,
        }

    return {
        "has_gps": True,
        "city": city_en,
        "city_ja": city_ja,
        "country": country_en,
        "country_ja": country_ja,
        "distance_km": exact_km,
        "lat": lat,
        "lon": lon,
    }


def format_gps_string(lat, lon):
    """Formats decimal coordinates into a clean folder/tag string like '35.69N_139.69E'.

    Returns 'No_GPS' if coordinates are missing.
    """
    if lat is None or lon is None:
        return "No_GPS"

    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.2f}{lat_dir}_{abs(lon):.2f}{lon_dir}"
