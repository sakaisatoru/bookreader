#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  bunko.py
#
#  Copyright 2015 sakaisatoru <endeavor2wako@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

""" NDC (日本十進分類法）
"""

"""
    ウィキペディア　フリー百科事典　日本十進分類法より　引用

    総記（0類）

        000 総記
            001
            002 知識、学問、学術
            003
            004
            005
            006
            007 情報科学
            008
            009

        010 図書館、図書館学
            011 図書館政策、図書館行財政
            012 図書館建築、図書館設備
            013 図書館管理
            014 資料の収集、資料の整理、資料の保管
            015 図書館奉仕、図書館活動
            016 各種の図書館
                017 学校図書館
                018 専門図書館
            019 読書、読書法

        020 図書、書誌学
            021 著作、編集
            022 写本、刊本、造本
            023 出版
            024 図書の販売
            025 一般書誌、全国書誌
            026 稀書目録、善本目録
            027 特種目録
            028 選定図書目録、参考図書目録
            029 蔵書目録、総合目録

        030 百科事典
            031 日本語
            032 中国語
            033 英語
            034 ドイツ語
            035 フランス語
            036 スペイン語
            037 イタリア語
            038 ロシア語

        039 用語索引＜一般＞

        040 一般論文集、一般講演集
            041 日本語
            042 中国語
            043 英語
            044 ドイツ語
            045 フランス語
            046 スペイン語
            047 イタリア語
            048 ロシア語

        049 雑著

        050 逐次刊行物
            051 日本の雑誌
            052 中国語
            053 英語
            054 ドイツ語
            055 フランス語
            056 スペイン語
            057 イタリア語
            058 ロシア語
        059 一般年鑑

        060 団体
            061 学術・研究機関
            062
            063 文化交流機関
            064
            065 親睦団体、その他の団体
            066
            067
            068
        069 博物館

        070 ジャーナリズム、新聞
            071 日本
            072 アジア
            073 ヨーロッパ
            074 アフリカ
            075 北アメリカ
            076 南アメリカ
            077 オセアニア、両極地方
            078
            079

        080 叢書、全集、選集
            081 日本語
            082 中国語
            083 英語
            084 ドイツ語
            085 フランス語
            086 スペイン語
            087 イタリア語
            088 ロシア語
            089 その他の諸言語

        090 貴重書、郷土資料、その他の特別コレクション
            091
            092
            093
            094
            095
            096
            097
            098
            099

    哲学（1類）

        100 哲学
            101 哲学理論
            102 哲学史
            103 参考図書（レファレンスブック）
            104 論文集、評論集、講演集
            105 逐次刊行物
            106 団体
            107 研究法、指導法、哲学教育
            108 叢書、全集、選集
            109

        110 哲学各論
            111 形而上学、存在論
            112 自然哲学、宇宙論
            113 人生観、世界観
            114 人間学
            115 認識論
            116 論理学、弁証法（弁証法的論理学）、方法論
            117 価値哲学
            118 文化哲学、技術哲学
            [119] 美学 → 701.1

        120 東洋思想
            121 日本思想
            122 中国思想、中国哲学
                123 経書
                124 先秦思想、諸子百家
                125 中世思想、近代思想
            126 インド哲学、バラモン教
            127
            128
            129 その他のアジア・アラブ哲学

        130 西洋哲学
            131 古代哲学
            132 中世哲学
            133 近代哲学
                134 ドイツ・オーストリア哲学
                135 フランス・オランダ哲学
                136 スペイン・ポルトガル哲学
                137 イタリア哲学
                138 ロシア哲学
                139 その他の哲学

        140 心理学
            141 普通心理学、心理各論
            142
            143 発達心理学
            144
            145 異常心理学
            146 臨床心理学、精神分析学
            147 超心理学、心霊研究
            148 相法、易占
            [149] 応用心理学

        150 倫理学、道徳
            151 倫理各論
            152 家庭倫理、性倫理
            153 職業倫理
            154 社会倫理（社会道徳）
            155 国体論、詔勅
            156 武士道
            157 報徳教、石門心学
            158 その他の特定主題
            159 人生訓、教訓

        160 宗教
            161 宗教学、宗教思想
            162 宗教史・事情
            163 原始宗教、宗教民族学
            164 神話、神話学
            165 比較宗教
            166 道教
            167 イスラム
            168 ヒンズー教、ジャイナ教
            169 その他の宗教、新興宗教

        170 神道
            171 神道思想、神道説
            172 神祇・神道史
            173 神典
            174 信仰録、説教集
            175 神社、神職
            176 祭祀
            177 布教、伝道
            178 各教派、教派神道
            179

        180 仏教
            181 仏教教理、仏教哲学
            182 仏教史
            183 経典
            184 法話・説教集
            185 寺院、僧職
            186 仏会
            187 布教、伝道
            188 各宗
            189

        190 キリスト教
            191 教義、キリスト教神学
            192 キリスト教史、迫害史
            193 聖書
            194 信仰録、説教集
            195 教会、聖職
            196 典礼、祭式、礼拝
            197 布教、伝道
            198 各教派、教会史
        199 ユダヤ教

    歴史（2類）

    伝記のうち、280 - 287には3人以上の伝記を、289（個人伝記）には1人または2人の伝記を納める。ただし、「特定主題の3人以上の伝記」や、哲学者・宗教家・芸術家・スポーツマン・諸芸に携わる者・文学者（すなわち1類・7類・9類。ただし文学研究者は除く）に該当する1人または2人の伝記は、それぞれの主題の下に納める。

        200 歴史
            201 歴史学
            202 歴史補助学
            203 参考図書（レファレンスブック）
            204 論文集、評論集、講演集
            205 逐次刊行物
            206 団体
            207 研究法、指導法、歴史教育
            208 叢書、全集、選集
        209 世界史、文化史

        210 日本史
            211 北海道地方
            212 東北地方
            213 関東地方
            214 北陸地方
            215 中部地方
            216 近畿地方
            217 中国地方
            218 四国地方
            219 九州地方

        220 アジア史、東洋史
            221 朝鮮
            222 中国
            223 東南アジア
                224 インドネシア
            225 インド
            [226] 西南アジア、中東（近東） → 227
            227 西南アジア、中東（近東）
            [228] アラブ諸国 → 227
            229 アジア・ロシア

        230 ヨーロッパ史、西洋史
            231 古代ギリシア
            232 古代ローマ
            233 イギリス、英国
            234 ドイツ、中欧
            235 フランス
            236 スペイン（イスパニア）
            237 イタリア
            238 ロシア（ソビエト連邦、独立国家共同体）
            239 バルカン諸国

        240 アフリカ史
            241 北アフリカ
                242 エジプト
                243 バーバリ諸国
            244 西アフリカ
            245 東アフリカ
            246
            247
            248 南アフリカ
            249 インド洋のアフリカ諸島

        250 北アメリカ史
            251 カナダ
            252
            253 アメリカ合衆国
            254
            255 ラテン・アメリカ（中南米）
                256 メキシコ
                257 中央アメリカ（中米諸国）
                258
                259 西インド諸島

        260 南アメリカ史
            261 北部諸国（カリブ沿海諸国）
            262 ブラジル
            263 パラグアイ
            264 ウルグアイ
            265 アルゼンチン
            266 チリ
            267 ボリビア
            268 ペルー
            269

        270 オセアニア史、両極地方史
            271 オーストラリア
            272 ニュージーランド
            273 メラネシア
            274 ミクロネシア
            275 ポリネシア
            276 ハワイ
            277 両極地方
                278 北極、北極地方
                279 南極、南極地方

        280 伝記
            281 日本
            282 アジア
            283 ヨーロッパ
            284 アフリカ
            285 北アメリカ
            286 南アメリカ
            287 オセアニア、両極地方
            288 系譜、家史、皇室
            289 個人伝記

        290 地理、地誌、紀行
            291 日本
            292 アジア
            293 ヨーロッパ
            294 アフリカ
            295 北アメリカ
            296 南アメリカ
            297 オセアニア、両極地方
            298
            299 海洋

    社会科学（3類）

        300 社会科学
            301 理論、方法論
            302 政治・経済・社会・文化事情
            303 参考図書（レファレンスブック）
            304 論文集、評論集、講演集
            305 逐次刊行物
            306 団体
            307 研究法、指導法、社会科学教育
            308 叢書、全集、選集
            309 社会思想

        310 政治
            311 政治学、政治思想
            312 政治史・事情
            313 国家の形態、政治体制
            314 議会
            315 政党、政治結社
            316 国家と個人・宗教・民族
            317 行政
            318 地方自治、地方行政
            319 外交、国際問題

        320 法律
            321 法学
            322 法制史
            323 憲法
            324 民法
            325 商法
            326 刑法、刑事法
            327 司法、訴訟手続法
            [328] 諸法
            329 国際法

        330 経済
            331 経済学、経済思想
            332 経済史・事情、経済体制
            333 経済政策、国際経済
            334 人口、土地、資源
            335 企業、経営
                336 経営管理
            337 貨幣、通貨
            338 金融、銀行、信託
            339 保険

        340 財政
            341 財政学、財政思想
            342 財政史・事情
            343 財政政策、財務行政
            344 予算、決算
            345 租税
            346
            347 公債、国債
            348 専売、国有財産
            349 地方財政

        350 統計
            351 日本
            352 アジア
            353 ヨーロッパ
            354 アフリカ
            355 北アメリカ
            356 南アメリカ
            357 オセアニア、両極地方
            358 人口統計、国勢調査
            [359] 各種の統計書

        360 社会
            361 社会学
            362 社会史、社会体制
            363
            364 社会保障
            365 生活・消費者問題
            366 労働経済、労働問題
            367 家族問題、男性・女性問題、老人問題
            368 社会病理
            369 社会福祉

        370 教育
            371 教育学、教育思想
            372 教育史・事情
            373 教育政策、教育制度、教育行財政
            374 学校経営・管理、学校保健
            375 教育課程、学習指導、教科別教育
            376 幼児・初等・中等教育
            377 大学、高等・専門教育、学術行政
            378 障害児教育
            379 社会教育

        380 風俗習慣、民俗学、民族学
            381
            382 風俗史、民俗誌、民族誌
            383 衣食住の習俗
            384 社会・家庭生活の習俗
            385 通過儀礼、冠婚葬祭
            386 年中行事、祭礼
            387 民間信仰、迷信（俗信）
            388 伝説、民話（昔話）
            389 民族学、文化人類学

        390 国防、軍事
            391 戦争、戦略、戦術
            392 国防史・事情、軍事史・事情
            393 国防政策・行政・法令
            394 軍事医学、兵食
            395 軍事施設、軍需品
            396 陸軍
            397 海軍
            398 空軍
            399 古代兵法、軍学

    自然科学（4類）

        400 自然科学
            401 科学理論、科学哲学
            402 科学史・事情
            403 参考図書（レファレンスブック）
            404 論文集、評論集、講演集
            405 逐次刊行物
            406 団体
            407 研究法、指導法、科学教育
            408 叢書、全集、選集
            409 科学技術政策、科学技術行政

        410 数学
            411 代数学
            412 数論（整数論）
            413 解析学
            414 幾何学
            415 位相数学
            416
            417 確率論、数理統計学
            418 計算法
            419 和算、中国算法

        420 物理学
            421 理論物理学
            422
            423 力学
            424 振動学、音響学
            425 光学
            426 熱学
            427 電磁気学
            428 物性物理学
            429 原子物理学

        430 化学
            431 物理化学、理論化学
            432 実験化学（化学実験法）
            433 分析化学（化学分析）
            434 合成化学（化学合成）
            435 無機化学
                436 金属元素とその化合物
            437 有機化学
                438 環式化合物の化学
                439 天然物質の化学

        440 天文学、宇宙科学
            441 理論天文学、数理天文学
            442 実地天文学、天体観測法
            443 恒星、恒星天文学
            444 太陽、太陽物理学
            445 惑星、衛星
            446 月
            447 彗星、流星
            448 地球、天文地理学
            449 時法、暦学

        450 地球科学、地学
            451 気象学
            452 海洋学
            453 地震学
            454 地形学
            455 地質学
            456 地史学、層位学
            457 古生物学、化石
            458 岩石学
            459 鉱物学

        460 生物科学、一般生物学
            461 理論生物学、生命論
            462 生物地理、生物誌
            463 細胞学
            464 生化学
            465 微生物学
            466
            467 遺伝学
            468 生態学
            469 人類学

        470 植物学
            471 一般植物学
            472 植物地理、植物誌
            473 葉状植物
                474 藻類、菌類
                475 コケ植物（蘚苔類）
                476 シダ植物
            477 種子植物
                478 裸子植物
                479 被子植物

        480 動物学
            481 一般動物学
            482 動物地理、動物誌
            483 無脊椎動物
                484 軟体動物、貝類学
                485 節足動物
                    486 昆虫類
            487 脊椎動物
                488 鳥類
                489 哺乳類

        490 医学
            491 基礎医学
            492 臨床医学、診断・治療
            493 内科学
            494 外科学
            495 婦人科学、産科学
            496 眼科学、耳鼻咽喉科学
            497 歯科学
            498 衛生学、公衆衛生、予防医学
        499 薬学

    技術（5類）

        500 技術、工学
            501 工業基礎学
            502 技術史、工学史
            503 参考図書（レファレンスブック）
            504 論文集、評論集、講演集
            505 逐次刊行物
            506 団体
            507 研究法、指導法、技術教育
            508 叢書、全集、選集
            509 工業、工業経済

        510 建設工学、土木工学
            511 土木力学、建設材料
            512 測量
            513 土木設計・施工法
            514 道路工学
            515 橋梁工学
            516 鉄道工学
            517 河海工学、河川工学
            518 衛生工学、都市工学
            519 公害、環境工学

        520 建築学
            521 日本の建築
            522 東洋の建築、アジアの建築
            523 西洋の建築、その他の様式の建築
            524 建築構造
            525 建築計画・施工
            526 各種の建築
                527 住宅建築
            528 建築設備、設備工学
            529 建築意匠・装飾

        530 機械工学
            531 機械力学・材料・設計
            532 機械工作、工作機械
            533 熱機関、熱工学
            534 流体機械、流体工学
            535 精密機器、光学機器
            536 運輸工学、車輌、運搬機械
            537 自動車工学
            538 航空宇宙工学
        539 原子力工学

        540 電気工学
            541 電気回路・計測・材料
            542 電気機器
            543 発電
            544 送電、変電、配電
            545 電灯、照明、電熱
            546 電気鉄道
            547 通信工学、電気通信
            548 情報工学
            549 電子工学

        550 海洋工学、船舶工学
            551 理論造船学
            552 船体構造・材料・施工
            553 船体艤装、船舶設備
            554 舶用機関（造機）
            555 船舶修理、保守
            556 各種の船舶・艦艇
            557 航海、航海学
            558 海洋開発
        559 兵器、軍事工学

        560 金属工学、鉱山工学
            561 採鉱、選鉱
            562 各種の金属鉱床・採掘
            563 冶金、合金
                564 鉄鋼
                565 非鉄金属
                566 金属加工、製造冶金
            567 石炭
            568 石油
            569 非金属鉱物、土石採取業

        570 化学工業
            571 化学工学、化学機器
            572 電気化学工業
            573 セラミックス、窯業、珪酸塩化学工業
            574 化学薬品
            575 燃料、爆発物
            576 油脂類
            577 染料
            578 高分子化学工業
            579 その他の化学工業

        580 製造工業
            581 金属製品
            582 事務機器、家庭機器、楽器
            583 木工業、木製品
            584 皮革工業、皮革製品
            585 パルプ・製紙工業
            586 繊維工学
            587 染色加工、染色業
            588 食品工業
            589 その他の雑工業

        590 家政学、生活科学
            591 家庭経済・経営
            592 家庭理工学
            593 衣服、裁縫
            594 手芸
            595 理容、美容
            596 食品、料理
            597 住居、家具調度
            598 家庭衛生
            599 育児

    産業（6類）

        600 産業
            601 産業政策・行政、総合開発
            602 産業史・事情、物産誌
            603 参考図書（レファレンスブック）
            604 論文集、評論集、講演集
            605 逐次刊行物
            606 団体
            607 研究法、指導法、産業教育
            608 叢書、全集、選集
            609 度量衡、計量法

        610 農業
            611 農業経済
            612 農業史・事情
            613 農業基礎学
            614 農業工学
            615 作物栽培、作物学
                616 食用作物
                617 工芸作物
                618 繊維作物
            619 農産物製造・加工

        620 園芸
            621 園芸経済・行政・経営
            622 園芸史・事情
            623 園芸植物学、病虫害
            624 温室、温床、園芸用具
            625 果樹園芸
            626 蔬菜園芸
            627 花卉園芸（草花）
            628 園芸利用
        629 造園

        630 蚕糸業
            631 蚕糸経済・行政・経営
            632 蚕糸業史・事情
            633 蚕学、蚕業基礎学
            634 蚕種
            635 飼育法
            636 くわ、栽桑
            637 蚕室、蚕具
            638 まゆ
            639 製糸、生糸、蚕糸利用

        640 畜産業
            641 畜産経済・行政・経営
            642 畜産史・事情
            643 家畜の繁殖、家畜飼料
            644 家畜の管理、畜舎、用具
            645 家畜・畜産動物各論
            646 家禽各論、飼鳥
            [647] みつばち、昆虫 → 646.9
            648 畜産製造、畜産物
            649 獣医学、比較医学

        650 林業
            651 林業経済・行政・経営
            652 森林史、林業史・事情
            653 森林立地、造林
            654 森林保護
            655 森林施業
            656 森林工学
            657 森林利用、林産物、木材学
            658 林産製造
        659 狩猟

        660 水産業
            661 水産経済・行政・経営
            662 水産業および漁業史・事情
            663 水産基礎学
            664 漁労、漁業各論
            665 漁船、漁具
            666 水産増殖、養殖業
            667 水産製造、水産食品
            668 水産物利用、水産利用工業
            669 製塩、塩業

        670 商業
            671 商業政策・行政
            672 商業史・事情
            673 商業経営、商店
            674 広告、宣伝
            675 マーケティング
            676 取引所
            677
            678 貿易
            679

        680 運輸、交通
            681 交通政策・行政・経営
            682 交通史・事情
            683 海運
            684 内水・運河交通
            685 陸運、自動車運送
            686 鉄道
            687 航空運送
            688 倉庫業
        689 観光事業

        690 通信事業
            691 通信政策・行政・法令
            692 通信事業史・事情
            693 郵便、郵政事業
            694 電気通信事業
            695
            696
            697
            698
            699 放送事業

    芸術（7類）

        700 芸術、美術
            701 芸術理論、美学
            702 芸術史、美術史
            703 参考図書（レファレンスブック）
            704 論文集、評論集、講演集
            705 逐次刊行物
            706 団体
            707 研究法、指導法、芸術教育
            708 叢書、全集、選集
            709 芸術政策、文化財

        710 彫刻
            711 彫塑材料・技法
            712 彫刻史、各国の彫刻
            713 木彫
            714 石彫
            715 金属彫刻、鋳造
            716
            717 粘土彫刻、塑造
            718 仏像
        719 オブジェ

        720 絵画
            721 日本画
            722 東洋画
            723 洋画
            724 絵画材料・技法
                725 素描、描画
            726 漫画、挿絵、童画
            727 グラフィックデザイン、図案
        728 書、書道
        729

        730 版画
            731 版画材料・技法
            732 版画史、各国の版画
            733 木版画
            734 石版画
            735 銅版画、鋼版画
            736 リノリウム版画、ゴム版画
            737 写真版画、孔版画
            738
        739 印章、篆刻、印譜

        740 写真
            741
            742 写真器械・材料
            743 撮影技術
            744 現像、印画
            745 複写技術
            746 特殊写真
            747 写真の応用
            748 写真集
        749 印刷

        750 工芸
            751 陶磁工芸
            752 漆工芸
            753 染織工芸
            754 木竹工芸
            755 宝石・牙角・皮革工芸
            756 金工芸
            757 デザイン、装飾美術
            758 美術家具
            759 人形、玩具

        760 音楽
            761 音楽の一般理論、音楽学
            762 音楽史、各国の音楽
            763 楽器、器楽
            764 器楽合奏
            765 宗教音楽、聖楽
            766 劇音楽
            767 声楽
            768 邦楽
        769 舞踊、バレエ

        770 演劇
            771 劇場、演出、演技
            772 演劇史、各国の演劇
            773 能楽、狂言
            774 歌舞伎
            775 各種の演劇
            776
            777 人形劇
        778 映画
        779 大衆演芸

        780 スポーツ、体育
            781 体操、遊戯
            782 陸上競技
            783 球技
            784 冬季競技
            785 水上競技
            786 戸外レクリエーション
            787 釣魚、遊猟
            788 相撲、拳闘、競馬
            789 武術

        790 諸芸、娯楽
            791 茶道
            792 香道
            793 花道
            794 撞球
            795 囲碁
            796 将棋
            797 射倖ゲーム
            798 室内娯楽
            799 ダンス

    言語（8類）

        800 言語
            801 言語学
            802 言語史・事情、言語政策
            803 参考図書（レファレンスブック）
            804 論文集、評論集、講演集
            805 逐次刊行物
            806 団体
            807 研究法、指導法、言語教育
            808 叢書、全集、選集
            809 言語生活

        810 日本語
            811 音声、音韻、文字
            812 語源、意味
            813 辞典
            814 語彙
            815 文法、語法
            816 文章、文体、作文
            817 読本、解釈、会話
            818 方言、訛語
            819

        820 中国語
            821 音声、音韻、文字
            822 語源、意味
            823 辞典
            824 語彙
            825 文法、語法
            826 文章、文体、作文
            827 読本、解釈、会話
            828 方言、訛語
        829 その他の東洋の諸言語

        830 英語
            831 音声、音韻、文字
            832 語源、意味
            833 辞典
            834 語彙
            835 文法、語法
            836 文章、文体、作文
            837 読本、解釈、会話
            838 方言、訛語
            839

        840 ドイツ語
            841 音声、音韻、文字
            842 語源、意味
            843 辞典
            844 語彙
            845 文法、語法
            846 文章、文体、作文
            847 読本、解釈、会話
            848 方言、訛語
        849 その他のゲルマン諸語

        850 フランス語
            851 音声、音韻、文字
            852 語源、意味
            853 辞典
            854 語彙
            855 文法、語法
            856 文章、文体、作文
            857 読本、解釈、会話
            858 方言、訛語
        859 プロヴァンス語

        860 スペイン語
            861 音声、音韻、文字
            862 語源、意味
            863 辞典
            864 語彙
            865 文法、語法
            866 文章、文体、作文
            867 読本、解釈、会話
            868 方言、訛語
        869 ポルトガル語

        870 イタリア語
            871 音声、音韻、文字
            872 語源、意味
            873 辞典
            874 語彙
            875 文法、語法
            876 文章、文体、作文
            877 読本、解釈、会話
            878 方言、訛語
        879 その他のロマンス諸語

        880 ロシア語
            881 音声、音韻、文字
            882 語源、意味
            883 辞典
            884 語彙
            885 文法、語法
            886 文章、文体、作文
            887 読本、解釈、会話
            888 方言、訛語
        889 その他のスラヴ諸語

        890 その他の諸言語
            891 ギリシア語
            892 ラテン語
            893 その他のヨーロッパの諸言語
            894 アフリカの諸言語
            895 アメリカの諸言語
            896
            897 オーストラリアの諸言語
            898
            899 国際語（人工語）

    文学（9類）

    原書が書かれた言語によって区分する。叢書、全集、選集 (908) には原書の言語も作品の形式も特定できないものを納める。作品集（918など）には（原書が特定の言語で書かれているが）作品の形式は特定できないものを納める。

        900 文学
            901 文学理論・作法
            902 文学史、文学思想史
            903 参考図書（レファレンスブック）
            904 論文集、評論集、講演集
            905 逐次刊行物
            906 団体
            907 研究法、指導法、文学教育
            908 叢書、全集、選集
            909 児童文学研究

        910 日本文学
            911 詩歌
            912 戯曲
            913 小説、物語
            914 評論、エッセイ、随筆
            915 日記、書簡、紀行
            916 記録、手記、ルポルタージュ
            917 箴言、アフォリズム、寸言
            918 作品集
            919 漢詩文、日本漢文学

        920 中国文学
            921 詩歌、韻文、詩文
            922 戯曲
            923 小説、物語
            924 評論、エッセイ、随筆
            925 日記、書簡、紀行
            926 記録、手記、ルポルタージュ
            927 箴言、アフォリズム、寸言
            928 作品集
        929 その他の東洋文学

        930 英米文学
            931 詩
            932 戯曲
            933 小説、物語
            934 評論、エッセイ、随筆
            935 日記、書簡、紀行
            936 記録、手記、ルポルタージュ
            937 箴言、アフォリズム、寸言
            938 作品集
            [939] アメリカ文学 → 930 / 938

        940 ドイツ文学
            941 詩
            942 戯曲
            943 小説、物語
            944 評論、エッセイ、随筆
            945 日記、書簡、紀行
            946 記録、手記、ルポルタージュ
            947 箴言、アフォリズム、寸言
            948 作品集
        949 その他のゲルマン文学

        950 フランス文学
            951 詩
            952 戯曲
            953 小説、物語
            954 評論、エッセイ、随筆
            955 日記、書簡、紀行
            956 記録、手記、ルポルタージュ
            957 箴言、アフォリズム、寸言
            958 作品集
        959 プロヴァンス文学

        960 スペイン文学
            961 詩
            962 戯曲
            963 小説、物語
            964 評論、エッセイ、随筆
            965 日記、書簡、紀行
            966 記録、手記、ルポルタージュ
            967 箴言、アフォリズム、寸言
            968 作品集
        969 ポルトガル文学

        970 イタリア文学
            971 詩
            972 戯曲
            973 小説、物語
            974 評論、エッセイ、随筆
            975 日記、書簡、紀行
            976 記録、手記、ルポルタージュ
            977 箴言、アフォリズム、寸言
            978 作品集
        979 その他のロマンス文学

        980 ロシア・ソビエト文学
            981 詩
            982 戯曲
            983 小説、物語
            984 評論、エッセイ、随筆
            985 日記、書簡、紀行
            986 記録、手記、ルポルタージュ
            987 箴言、アフォリズム、寸言
            988 作品集
        989 その他のスラヴ文学

        990 その他の諸文学
            991 ギリシア文学
            992 ラテン文学
            993 その他のヨーロッパ文学
            994 アフリカ文学
            995 アメリカ先住民語の文学
            996
            997 オーストラリア先住民語の文学
            998
            999 国際語による文学
"""

class NDC(object):

    """ 類
    """
    rui = [u'0 総記',u'1 哲学',u'2 歴史',u'3 社会科学',u'4 自然科学',u'5 技術',u'6 産業',u'7 芸術',u'8 言語',u'9 文学']

    """ 目（要目、綱を兼ねる）
    """
    moku =[[[u'000 総記',u'001',u'002 知識、学問、学術',u'003',u'004',u'005',u'006',u'007 情報科学',u'008',u'009'],
            [u'010 図書館、図書館学',u'011 図書館政策、図書館行財政',u'012 図書館建築、図書館設備',u'013 図書館管理',u'014 資料の収集、資料の整理、資料の保管',u'015 図書館奉仕、図書館活動',u'016 各種の図書館',u'017 学校図書館',u'018 専門図書館',u'019 読書、読書法'],
            [u'020 図書、書誌学',u'021 著作、編集',u'022 写本、刊本、造本',u'023 出版',u'024 図書の販売',u'025 一般書誌、全国書誌',u'026 稀書目録、善本目録',u'027 特種目録',u'028 選定図書目録、参考図書目録',u'029 蔵書目録、総合目録'],
            [u'030 百科事典',u'031 日本語',u'032 中国語',u'033 英語',u'034 ドイツ語',u'035 フランス語',u'036 スペイン語',u'037 イタリア語',u'038 ロシア語',u'039 用語索引＜一般＞'],
            [u'040 一般論文集、一般講演集',u'041 日本語',u'042 中国語',u'043 英語',u'044 ドイツ語',u'045 フランス語',u'046 スペイン語',u'047 イタリア語',u'048 ロシア語',u'049 雑著'],
            [u'050 逐次刊行物',u'051 日本の雑誌',u'052 中国語',u'053 英語',u'054 ドイツ語',u'055 フランス語',u'056 スペイン語',u'057 イタリア語',u'058 ロシア語',u'059 一般年鑑'],
            [u'060 団体',u'061 学術・研究機関',u'062',u'063 文化交流機関',u'064',u'065 親睦団体、その他の団体',u'066',u'067',u'068',u'069 博物館'],
            [u'070 ジャーナリズム、新聞',u'071 日本',u'072 アジア',u'073 ヨーロッパ',u'074 アフリカ',u'075 北アメリカ',u'076 南アメリカ',u'077 オセアニア、両極地方',u'078',u'079'],
            [u'080 叢書、全集、選集',u'081 日本語',u'082 中国語',u'083 英語',u'084 ドイツ語',u'085 フランス語',u'086 スペイン語',u'087 イタリア語',u'088 ロシア語',u'089 その他の諸言語'],
            [u'090 貴重書、郷土資料、その他の特別コレクション',u'091',u'092',u'093',u'094',u'095',u'096',u'097',u'098',u'099']],

           [[u'100 哲学',u'101 哲学理論',u'102 哲学史',u'103 参考図書（レファレンスブック）',u'104 論文集、評論集、講演集',u'105 逐次刊行物',u'106 団体',u'107 研究法、指導法、哲学教育',u'108 叢書、全集、選集',u'109'],
            [u'110 哲学各論',u'111 形而上学、存在論',u'112 自然哲学、宇宙論',u'113 人生観、世界観',u'114 人間学',u'115 認識論',u'116 論理学、弁証法（弁証法的論理学）、方法論',u'117 価値哲学',u'118 文化哲学、技術哲学',u'119'],
            [u'120 東洋思想',u'121 日本思想',u'122 中国思想、中国哲学',u'123 経書',u'124 先秦思想、諸子百家',u'125 中世思想、近代思想',u'126 インド哲学、バラモン教',u'127',u'128',u'129 その他のアジア・アラブ哲学'],
            [u'130 西洋哲学',u'131 古代哲学',u'132 中世哲学',u'133 近代哲学',u'134 ドイツ・オーストリア哲学',u'135 フランス・オランダ哲学',u'136 スペイン・ポルトガル哲学',u'137 イタリア哲学',u'138 ロシア哲学',u'139 その他の哲学'],
            [u'140 心理学',u'141 普通心理学、心理各論',u'142',u'143 発達心理学',u'144',u'145 異常心理学',u'146 臨床心理学、精神分析学',u'147 超心理学、心霊研究',u'148 相法、易占',u'149'],
            [u'150 倫理学、道徳',u'151 倫理各論',u'152 家庭倫理、性倫理',u'153 職業倫理',u'154 社会倫理（社会道徳）',u'155 国体論、詔勅',u'156 武士道',u'157 報徳教、石門心学',u'158 その他の特定主題',u'159 人生訓、教訓'],
            [u'160 宗教',u'161 宗教学、宗教思想',u'162 宗教史・事情',u'163 原始宗教、宗教民族学',u'164 神話、神話学',u'165 比較宗教',u'166 道教',u'167 イスラム',u'168 ヒンズー教、ジャイナ教',u'169 その他の宗教、新興宗教'],
            [u'170 神道',u'171 神道思想、神道説',u'172 神祇・神道史',u'173 神典',u'174 信仰録、説教集',u'175 神社、神職',u'176 祭祀',u'177 布教、伝道',u'178 各教派、教派神道',u'179'],
            [u'180 仏教',u'181 仏教教理、仏教哲学',u'182 仏教史',u'183 経典',u'184 法話・説教集',u'185 寺院、僧職',u'186 仏会',u'187 布教、伝道',u'188 各宗',u'189'],
            [u'190 キリスト教',u'191 教義、キリスト教神学',u'192 キリスト教史、迫害史',u'193 聖書',u'194 信仰録、説教集',u'195 教会、聖職',u'196 典礼、祭式、礼拝',u'197 布教、伝道',u'198 各教派、教会史',u'199 ユダヤ教']],

           [[u'200 歴史',u'201 歴史学',u'202 歴史補助学',u'203 参考図書（レファレンスブック）',u'204 論文集、評論集、講演集',u'205 逐次刊行物',u'206 団体',u'207 研究法、指導法、歴史教育',u'208 叢書、全集、選集',u'209 世界史、文化史'],
            [u'210 日本史',u'211 北海道地方',u'212 東北地方',u'213 関東地方',u'214 北陸地方',u'215 中部地方',u'216 近畿地方',u'217 中国地方',u'218 四国地方',u'219 九州地方'],
            [u'220 アジア史、東洋史',u'221 朝鮮',u'222 中国',u'223 東南アジア',u'224 インドネシア',u'225 インド',u'226',u'227 西南アジア、中東（近東）',u'228',u'229 アジア・ロシア'],
            [u'230 ヨーロッパ史、西洋史',u'231 古代ギリシア',u'232 古代ローマ',u'233 イギリス、英国',u'234 ドイツ、中欧',u'235 フランス',u'236 スペイン（イスパニア）',u'237 イタリア',u'238 ロシア（ソビエト連邦、独立国家共同体）',u'239 バルカン諸国'],
            [u'240 アフリカ史',u'241 北アフリカ',u'242 エジプト',u'243 バーバリ諸国',u'244 西アフリカ',u'245 東アフリカ',u'246',u'247',u'248 南アフリカ',u'249 インド洋のアフリカ諸島'],
            [u'250 北アメリカ史',u'251 カナダ',u'252',u'253 アメリカ合衆国',u'254',u'255 ラテン・アメリカ（中南米）',u'256 メキシコ',u'257 中央アメリカ（中米諸国）',u'258',u'259 西インド諸島'],
            [u'260 南アメリカ史',u'261 北部諸国（カリブ沿海諸国）',u'262 ブラジル',u'263 パラグアイ',u'264 ウルグアイ',u'265 アルゼンチン',u'266 チリ',u'267 ボリビア',u'268 ペルー',u'269'],
            [u'270 オセアニア史、両極地方史',u'271 オーストラリア',u'272 ニュージーランド',u'273 メラネシア',u'274 ミクロネシア',u'275 ポリネシア',u'276 ハワイ',u'277 両極地方',u'278 北極、北極地方',u'279 南極、南極地方'],
            [u'280 伝記',u'281 日本',u'282 アジア',u'283 ヨーロッパ',u'284 アフリカ',u'285 北アメリカ',u'286 南アメリカ',u'287 オセアニア、両極地方',u'288 系譜、家史、皇室',u'289 個人伝記'],
            [u'290 地理、地誌、紀行',u'291 日本',u'292 アジア',u'293 ヨーロッパ',u'294 アフリカ',u'295 北アメリカ',u'296 南アメリカ',u'297 オセアニア、両極地方',u'298',u'299 海洋']],

           [[u'300 社会科学',u'301 理論、方法論',u'302 政治・経済・社会・文化事情',u'303 参考図書（レファレンスブック）',u'304 論文集、評論集、講演集',u'305 逐次刊行物',u'306 団体',u'307 研究法、指導法、社会科学教育',u'308 叢書、全集、選集',u'309 社会思想'],
            [u'310 政治',u'311 政治学、政治思想',u'312 政治史・事情',u'313 国家の形態、政治体制',u'314 議会',u'315 政党、政治結社',u'316 国家と個人・宗教・民族',u'317 行政',u'318 地方自治、地方行政',u'319 外交、国際問題'],
            [u'320 法律',u'321 法学',u'322 法制史',u'323 憲法',u'324 民法',u'325 商法',u'326 刑法、刑事法',u'327 司法、訴訟手続法',u'328',u'329 国際法'],
            [u'330 経済',u'331 経済学、経済思想',u'332 経済史・事情、経済体制',u'333 経済政策、国際経済',u'334 人口、土地、資源',u'335 企業、経営',u'336 経営管理',u'337 貨幣、通貨',u'338 金融、銀行、信託',u'339 保険'],
            [u'340 財政',u'341 財政学、財政思想',u'342 財政史・事情',u'343 財政政策、財務行政',u'344 予算、決算',u'345 租税',u'346',u'347 公債、国債',u'348 専売、国有財産',u'349 地方財政'],
            [u'350 統計',u'351 日本',u'352 アジア',u'353 ヨーロッパ',u'354 アフリカ',u'355 北アメリカ',u'356 南アメリカ',u'357 オセアニア、両極地方',u'358 人口統計、国勢調査',u'359'],
            [u'360 社会',u'361 社会学',u'362 社会史、社会体制',u'363',u'364 社会保障',u'365 生活・消費者問題',u'366 労働経済、労働問題',u'367 家族問題、男性・女性問題、老人問題',u'368 社会病理',u'369 社会福祉'],
            [u'370 教育',u'371 教育学、教育思想',u'372 教育史・事情',u'373 教育政策、教育制度、教育行財政',u'374 学校経営・管理、学校保健',u'375 教育課程、学習指導、教科別教育',u'376 幼児・初等・中等教育',u'377 大学、高等・専門教育、学術行政',u'378 障害児教育',u'379 社会教育'],
            [u'380 風俗習慣、民俗学、民族学',u'381',u'382 風俗史、民俗誌、民族誌',u'383 衣食住の習俗',u'384 社会・家庭生活の習俗',u'385 通過儀礼、冠婚葬祭',u'386 年中行事、祭礼',u'387 民間信仰、迷信（俗信）',u'388 伝説、民話（昔話）',u'389 民族学、文化人類学'],
            [u'390 国防、軍事',u'391 戦争、戦略、戦術',u'392 国防史・事情、軍事史・事情',u'393 国防政策・行政・法令',u'394 軍事医学、兵食',u'395 軍事施設、軍需品',u'396 陸軍',u'397 海軍',u'398 空軍',u'399 古代兵法、軍学']],

           [[u'400 自然科学',u'401 科学理論、科学哲学',u'402 科学史・事情',u'403 参考図書（レファレンスブック）',u'404 論文集、評論集、講演集',u'405 逐次刊行物',u'406 団体',u'407 研究法、指導法、科学教育',u'408 叢書、全集、選集',u'409 科学技術政策、科学技術行政'],
            [u'410 数学',u'411 代数学',u'412 数論（整数論）',u'413 解析学',u'414 幾何学',u'415 位相数学',u'416',u'417 確率論、数理統計学',u'418 計算法',u'419 和算、中国算法'],
            [u'420 物理学',u'421 理論物理学',u'422',u'423 力学',u'424 振動学、音響学',u'425 光学',u'426 熱学',u'427 電磁気学',u'428 物性物理学',u'429 原子物理学'],
            [u'430 化学',u'431 物理化学、理論化学',u'432 実験化学（化学実験法）',u'433 分析化学（化学分析）',u'434 合成化学（化学合成）',u'435 無機化学',u'436 金属元素とその化合物',u'437 有機化学',u'438 環式化合物の化学',u'439 天然物質の化学'],
            [u'440 天文学、宇宙科学',u'441 理論天文学、数理天文学',u'442 実地天文学、天体観測法',u'443 恒星、恒星天文学',u'444 太陽、太陽物理学',u'445 惑星、衛星',u'446 月',u'447 彗星、流星',u'448 地球、天文地理学',u'449 時法、暦学'],
            [u'450 地球科学、地学',u'451 気象学',u'452 海洋学',u'453 地震学',u'454 地形学',u'455 地質学',u'456 地史学、層位学',u'457 古生物学、化石',u'458 岩石学',u'459 鉱物学'],
            [u'460 生物科学、一般生物学',u'461 理論生物学、生命論',u'462 生物地理、生物誌',u'463 細胞学',u'464 生化学',u'465 微生物学',u'466',u'467 遺伝学',u'468 生態学',u'469 人類学'],
            [u'470 植物学',u'471 一般植物学',u'472 植物地理、植物誌',u'473 葉状植物',u'474 藻類、菌類',u'475 コケ植物（蘚苔類）',u'476 シダ植物',u'477 種子植物',u'478 裸子植物',u'479 被子植物'],
            [u'480 動物学',u'481 一般動物学',u'482 動物地理、動物誌',u'483 無脊椎動物',u'484 軟体動物、貝類学',u'485 節足動物',u'486 昆虫類',u'487 脊椎動物',u'488 鳥類',u'489 哺乳類'],
            [u'490 医学',u'491 基礎医学',u'492 臨床医学、診断・治療',u'493 内科学',u'494 外科学',u'495 婦人科学、産科学',u'496 眼科学、耳鼻咽喉科学',u'497 歯科学',u'498 衛生学、公衆衛生、予防医学',u'499 薬学']],

           [[u'500 技術、工学',u'501 工業基礎学',u'502 技術史、工学史',u'503 参考図書（レファレンスブック）',u'504 論文集、評論集、講演集',u'505 逐次刊行物',u'506 団体',u'507 研究法、指導法、技術教育',u'508 叢書、全集、選集',u'509 工業、工業経済'],
            [u'510 建設工学、土木工学',u'511 土木力学、建設材料',u'512 測量',u'513 土木設計・施工法',u'514 道路工学',u'515 橋梁工学',u'516 鉄道工学',u'517 河海工学、河川工学',u'518 衛生工学、都市工学',u'519 公害、環境工学'],
            [u'520 建築学',u'521 日本の建築',u'522 東洋の建築、アジアの建築',u'523 西洋の建築、その他の様式の建築',u'524 建築構造',u'525 建築計画・施工',u'526 各種の建築',u'527 住宅建築',u'528 建築設備、設備工学',u'529 建築意匠・装飾'],
            [u'530 機械工学',u'531 機械力学・材料・設計',u'532 機械工作、工作機械',u'533 熱機関、熱工学',u'534 流体機械、流体工学',u'535 精密機器、光学機器',u'536 運輸工学、車輌、運搬機械',u'537 自動車工学',u'538 航空宇宙工学',u'539 原子力工学'],
            [u'540 電気工学',u'541 電気回路・計測・材料',u'542 電気機器',u'543 発電',u'544 送電、変電、配電',u'545 電灯、照明、電熱',u'546 電気鉄道',u'547 通信工学、電気通信',u'548 情報工学',u'549 電子工学'],
            [u'550 海洋工学、船舶工学',u'551 理論造船学',u'552 船体構造・材料・施工',u'553 船体艤装、船舶設備',u'554 舶用機関（造機）',u'555 船舶修理、保守',u'556 各種の船舶・艦艇',u'557 航海、航海学',u'558 海洋開発',u'559 兵器、軍事工学'],
            [u'560 金属工学、鉱山工学',u'561 採鉱、選鉱',u'562 各種の金属鉱床・採掘',u'563 冶金、合金',u'564 鉄鋼',u'565 非鉄金属',u'566 金属加工、製造冶金',u'567 石炭',u'568 石油',u'569 非金属鉱物、土石採取業'],
            [u'570 化学工業',u'571 化学工学、化学機器',u'572 電気化学工業',u'573 セラミックス、窯業、珪酸塩化学工業',u'574 化学薬品',u'575 燃料、爆発物',u'576 油脂類',u'577 染料',u'578 高分子化学工業',u'579 その他の化学工業'],
            [u'580 製造工業',u'581 金属製品',u'582 事務機器、家庭機器、楽器',u'583 木工業、木製品',u'584 皮革工業、皮革製品',u'585 パルプ・製紙工業',u'586 繊維工学',u'587 染色加工、染色業',u'588 食品工業',u'589 その他の雑工業'],
            [u'590 家政学、生活科学',u'591 家庭経済・経営',u'592 家庭理工学',u'593 衣服、裁縫',u'594 手芸',u'595 理容、美容',u'596 食品、料理',u'597 住居、家具調度',u'598 家庭衛生',u'599 育児']],

           [[u'600 産業',u'601 産業政策・行政、総合開発',u'602 産業史・事情、物産誌',u'603 参考図書（レファレンスブック）',u'604 論文集、評論集、講演集',u'605 逐次刊行物',u'606 団体',u'607 研究法、指導法、産業教育',u'608 叢書、全集、選集',u'609 度量衡、計量法'],
            [u'610 農業',u'611 農業経済',u'612 農業史・事情',u'613 農業基礎学',u'614 農業工学',u'615 作物栽培、作物学',u'616 食用作物',u'617 工芸作物',u'618 繊維作物',u'619 農産物製造・加工'],
            [u'620 園芸',u'621 園芸経済・行政・経営',u'622 園芸史・事情',u'623 園芸植物学、病虫害',u'624 温室、温床、園芸用具',u'625 果樹園芸',u'626 蔬菜園芸',u'627 花卉園芸（草花）',u'628 園芸利用',u'629 造園'],
            [u'630 蚕糸業',u'631 蚕糸経済・行政・経営',u'632 蚕糸業史・事情',u'633 蚕学、蚕業基礎学',u'634 蚕種',u'635 飼育法',u'636 くわ、栽桑',u'637 蚕室、蚕具',u'638 まゆ',u'639 製糸、生糸、蚕糸利用'],
            [u'640 畜産業',u'641 畜産経済・行政・経営',u'642 畜産史・事情',u'643 家畜の繁殖、家畜飼料',u'644 家畜の管理、畜舎、用具',u'645 家畜・畜産動物各論',u'646 家禽各論、飼鳥',u'647',u'648 畜産製造、畜産物',u'649 獣医学、比較医学'],
            [u'650 林業',u'651 林業経済・行政・経営',u'652 森林史、林業史・事情',u'653 森林立地、造林',u'654 森林保護',u'655 森林施業',u'656 森林工学',u'657 森林利用、林産物、木材学',u'658 林産製造',u'659 狩猟'],
            [u'660 水産業',u'661 水産経済・行政・経営',u'662 水産業および漁業史・事情',u'663 水産基礎学',u'664 漁労、漁業各論',u'665 漁船、漁具',u'666 水産増殖、養殖業',u'667 水産製造、水産食品',u'668 水産物利用、水産利用工業',u'669 製塩、塩業'],
            [u'670 商業',u'671 商業政策・行政',u'672 商業史・事情',u'673 商業経営、商店',u'674 広告、宣伝',u'675 マーケティング',u'676 取引所',u'677',u'678 貿易',u'679'],
            [u'680 運輸、交通',u'681 交通政策・行政・経営',u'682 交通史・事情',u'683 海運',u'684 内水・運河交通',u'685 陸運、自動車運送',u'686 鉄道',u'687 航空運送',u'688 倉庫業',u'689 観光事業'],
            [u'690 通信事業',u'691 通信政策・行政・法令',u'692 通信事業史・事情',u'693 郵便、郵政事業',u'694 電気通信事業',u'695',u'696',u'697',u'698',u'699 放送事業']],

           [[u'700 芸術、美術',u'701 芸術理論、美学',u'702 芸術史、美術史',u'703 参考図書（レファレンスブック）',u'704 論文集、評論集、講演集',u'705 逐次刊行物',u'706 団体',u'707 研究法、指導法、芸術教育',u'708 叢書、全集、選集',u'709 芸術政策、文化財'],
            [u'710 彫刻',u'711 彫塑材料・技法',u'712 彫刻史、各国の彫刻',u'713 木彫',u'714 石彫',u'715 金属彫刻、鋳造',u'716',u'717 粘土彫刻、塑造',u'718 仏像',u'719 オブジェ'],
            [u'720 絵画',u'721 日本画',u'722 東洋画',u'723 洋画',u'724 絵画材料・技法',u'725 素描、描画',u'726 漫画、挿絵、童画',u'727 グラフィックデザイン、図案',u'728 書、書道',u'729'],
            [u'730 版画',u'731 版画材料・技法',u'732 版画史、各国の版画',u'733 木版画',u'734 石版画',u'735 銅版画、鋼版画',u'736 リノリウム版画、ゴム版画',u'737 写真版画、孔版画',u'738',u'739 印章、篆刻、印譜'],
            [u'740 写真',u'741',u'742 写真器械・材料',u'743 撮影技術',u'744 現像、印画',u'745 複写技術',u'746 特殊写真',u'747 写真の応用',u'748 写真集',u'749 印刷'],
            [u'750 工芸',u'751 陶磁工芸',u'752 漆工芸',u'753 染織工芸',u'754 木竹工芸',u'755 宝石・牙角・皮革工芸',u'756 金工芸',u'757 デザイン、装飾美術',u'758 美術家具',u'759 人形、玩具'],
            [u'760 音楽',u'761 音楽の一般理論、音楽学',u'762 音楽史、各国の音楽',u'763 楽器、器楽',u'764 器楽合奏',u'765 宗教音楽、聖楽',u'766 劇音楽',u'767 声楽',u'768 邦楽',u'769 舞踊、バレエ'],
            [u'770 演劇',u'771 劇場、演出、演技',u'772 演劇史、各国の演劇',u'773 能楽、狂言',u'774 歌舞伎',u'775 各種の演劇',u'776',u'777 人形劇',u'778 映画',u'779 大衆演芸'],
            [u'780 スポーツ、体育',u'781 体操、遊戯',u'782 陸上競技',u'783 球技',u'784 冬季競技',u'785 水上競技',u'786 戸外レクリエーション',u'787 釣魚、遊猟',u'788 相撲、拳闘、競馬',u'789 武術'],
            [u'790 諸芸、娯楽',u'791 茶道',u'792 香道',u'793 花道',u'794 撞球',u'795 囲碁',u'796 将棋',u'797 射倖ゲーム',u'798 室内娯楽',u'799 ダンス']],

           [[u'800 言語',u'801 言語学',u'802 言語史・事情、言語政策',u'803 参考図書（レファレンスブック）',u'804 論文集、評論集、講演集',u'805 逐次刊行物',u'806 団体',u'807 研究法、指導法、言語教育',u'808 叢書、全集、選集',u'809 言語生活'],
            [u'810 日本語',u'811 音声、音韻、文字',u'812 語源、意味',u'813 辞典',u'814 語彙',u'815 文法、語法',u'816 文章、文体、作文',u'817 読本、解釈、会話',u'818 方言、訛語',u'819'],
            [u'820 中国語',u'821 音声、音韻、文字',u'822 語源、意味',u'823 辞典',u'824 語彙',u'825 文法、語法',u'826 文章、文体、作文',u'827 読本、解釈、会話',u'828 方言、訛語',u'829 その他の東洋の諸言語'],
            [u'830 英語',u'831 音声、音韻、文字',u'832 語源、意味',u'833 辞典',u'834 語彙',u'835 文法、語法',u'836 文章、文体、作文',u'837 読本、解釈、会話',u'838 方言、訛語',u'839'],
            [u'840 ドイツ語',u'841 音声、音韻、文字',u'842 語源、意味',u'843 辞典',u'844 語彙',u'845 文法、語法',u'846 文章、文体、作文',u'847 読本、解釈、会話',u'848 方言、訛語',u'849 その他のゲルマン諸語'],
            [u'850 フランス語',u'851 音声、音韻、文字',u'852 語源、意味',u'853 辞典',u'854 語彙',u'855 文法、語法',u'856 文章、文体、作文',u'857 読本、解釈、会話',u'858 方言、訛語',u'859 プロヴァンス語'],
            [u'860 スペイン語',u'861 音声、音韻、文字',u'862 語源、意味',u'863 辞典',u'864 語彙',u'865 文法、語法',u'866 文章、文体、作文',u'867 読本、解釈、会話',u'868 方言、訛語',u'869 ポルトガル語'],
            [u'870 イタリア語',u'871 音声、音韻、文字',u'872 語源、意味',u'873 辞典',u'874 語彙',u'875 文法、語法',u'876 文章、文体、作文',u'877 読本、解釈、会話',u'878 方言、訛語',u'879 その他のロマンス諸語'],
            [u'880 ロシア語',u'881 音声、音韻、文字',u'882 語源、意味',u'883 辞典',u'884 語彙',u'885 文法、語法',u'886 文章、文体、作文',u'887 読本、解釈、会話',u'888 方言、訛語',u'889 その他のスラヴ諸語'],
            [u'890 その他の諸言語',u'891 ギリシア語',u'892 ラテン語',u'893 その他のヨーロッパの諸言語',u'894 アフリカの諸言語',u'895 アメリカの諸言語',u'896',u'897 オーストラリアの諸言語',u'898',u'899 国際語（人工語）']],

           [[u'900 文学',u'901 文学理論・作法',u'902 文学史、文学思想史',u'903 参考図書（レファレンスブック）',u'904 論文集、評論集、講演集',u'905 逐次刊行物',u'906 団体',u'907 研究法、指導法、文学教育',u'908 叢書、全集、選集',u'909 児童文学研究'],
            [u'910 日本文学',u'911 詩歌',u'912 戯曲',u'913 小説、物語',u'914 評論、エッセイ、随筆',u'915 日記、書簡、紀行',u'916 記録、手記、ルポルタージュ',u'917 箴言、アフォリズム、寸言',u'918 作品集',u'919 漢詩文、日本漢文学'],
            [u'920 中国文学',u'921 詩歌、韻文、詩文',u'922 戯曲',u'923 小説、物語',u'924 評論、エッセイ、随筆',u'925 日記、書簡、紀行',u'926 記録、手記、ルポルタージュ',u'927 箴言、アフォリズム、寸言',u'928 作品集',u'929 その他の東洋文学'],
            [u'930 英米文学',u'931 詩',u'932 戯曲',u'933 小説、物語',u'934 評論、エッセイ、随筆',u'935 日記、書簡、紀行',u'936 記録、手記、ルポルタージュ',u'937 箴言、アフォリズム、寸言',u'938 作品集',u'939'],
            [u'940 ドイツ文学',u'941 詩',u'942 戯曲',u'943 小説、物語',u'944 評論、エッセイ、随筆',u'945 日記、書簡、紀行',u'946 記録、手記、ルポルタージュ',u'947 箴言、アフォリズム、寸言',u'948 作品集',u'949 その他のゲルマン文学'],
            [u'950 フランス文学',u'951 詩',u'952 戯曲',u'953 小説、物語',u'954 評論、エッセイ、随筆',u'955 日記、書簡、紀行',u'956 記録、手記、ルポルタージュ',u'957 箴言、アフォリズム、寸言',u'958 作品集',u'959 プロヴァンス文学'],
            [u'960 スペイン文学',u'961 詩',u'962 戯曲',u'963 小説、物語',u'964 評論、エッセイ、随筆',u'965 日記、書簡、紀行',u'966 記録、手記、ルポルタージュ',u'967 箴言、アフォリズム、寸言',u'968 作品集',u'969 ポルトガル文学'],
            [u'970 イタリア文学',u'971 詩',u'972 戯曲',u'973 小説、物語',u'974 評論、エッセイ、随筆',u'975 日記、書簡、紀行',u'976 記録、手記、ルポルタージュ',u'977 箴言、アフォリズム、寸言',u'978 作品集',u'979 その他のロマンス文学'],
            [u'980 ロシア・ソビエト文学',u'981 詩',u'982 戯曲',u'983 小説、物語',u'984 評論、エッセイ、随筆',u'985 日記、書簡、紀行',u'986 記録、手記、ルポルタージュ',u'987 箴言、アフォリズム、寸言',u'988 作品集',u'989 その他のスラヴ文学'],
            [u'990 その他の諸文学',u'991 ギリシア文学',u'992 ラテン文学',u'993 その他のヨーロッパ文学',u'994 アフリカ文学',u'995 アメリカ先住民語の文学',u'996',u'997 オーストラリア先住民語の文学',u'998',u'999 国際語による文学']]]

    def __init__(self):
        pass

    def rui_itre(self):
        """ 類をイテレータで返す
        """
        for i in NDC.rui:
            yield i

    def moku_itre(self, rui, kou):
        """ 要目をイテレータで返す
            kou に -1 を渡すと、綱目を返す
        """
        if kou == -1:
            """ 綱目を返す
            """
            for i in NDC.moku[rui]:
                yield i[0]
        else:
            """ 要目を返す
            """
            for i in NDC.moku[rui][kou]:
                yield i

    def get_moku(self, n):
        """ 分類コードを渡して名前を得る
        """
        z = int(n[0])
        y = int(n[1])
        x = int(n[2])
        return NDC.moku[z][y][x]
