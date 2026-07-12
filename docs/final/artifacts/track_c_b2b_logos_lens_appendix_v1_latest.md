# [DRAFT] B2B 매크로 경보 — 부록: 문화·서사 관측 레이어 (Logos)

- **generated_at_utc:** `2026-06-17T09:47:10Z`
- **schema:** `track_c_b2b_logos_lens_appendix_v1`
- **status:** `DRAFT_AUTO` — legal sign-off before external send

**본문 SSOT:** `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md` · `track_c_b2b_macro_alert_offer_onepager_latest.md`  
**본 부록 역할:** 유료 본문 **대체 아님** · `[NON_GATING]` · 아티팩트·스냅샷 근거형만.

---

## 1. 목적·범위

- 엔터프라이즈 매크로·리스크 경보 **본체**는 1차 실물 레짐·운영 게이트·재현 가능 JSON이다.
- 본 부록은 **고난도 텍스트 코퍼스**에서 추출한 **구조화 서사 스냅샷**을 “스트레스 테스트 베드”로만 제공한다.
- **비실행:** 주문·사이징·API 키·임상 판단·Track A 자동 합선에 사용하지 않음.

---

## 2. 이번 호 근거 아티팩트

| 항목 | 상태 |
|------|------|
| 코퍼스 매니페스트 (슬라이스 1) | `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` — present |
| 코퍼스·그래프 번들 (슬라이스 2) | `docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json` — present |
| 벡터 정책·매니페스트 (슬라이스 3) | `docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json` — present · `docs/final/artifacts/logos_vector_index_manifest_v1_latest.json` — present |
| 정책 준비도 (슬라이스 4) | `docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json` — present (`overall_ok` 스냅샷) |
| 딥 퓨전 잡·증류 템플릿 (슬라이스 5) | `docs/final/artifacts/logos_track_b_deep_fusion_job_v1_latest.json` — present · ANN 라이트 `docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json` — present |
| 지휘관 심층 리포트 골격 | `docs/final/artifacts/logos_track_b_commander_deep_report_latest.json` — present · MD `reports/logos_track_b_commander_deep_report_latest.md` |
| 섀도우 인사이트 (Track C 부속) | `docs/final/artifacts/logos_shadow_insight_latest.json` — present |
| 반증 벤치마크 (대조군) | `docs/final/artifacts/logos_falsification_benchmark_latest.json` — present |
| 증류 스냅샷 (latest) | `docs/final/artifacts/logos_deep_research_distill_latest.json` — present |
| 쇼룸 슬라이스 JSON | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_research_slice_v0.json` — present |
| 공개 데모 (스냅샷) | `https://jemaai.cloud/public_showroom_logos_research_v1.html` |
| 메타포 DB | `docs/research/logos_metaphor_db_v1/theme_*.json` (1566 themes) |

---

## 3. 테마 카탈로그 (v0.2.1)

| 테마 | 앵커 구절 | node_id | cross-nodes | 파일 |
|------|-----------|---------|-------------|------|
| 피와 물 (Blood and Water) | 요한복음 19:34 | `ANCHOR_JOHN_19_34` | 4 | `theme_01_blood_and_water.json` |
| 방주 문 폐쇄 (Ark Door Sealed) | 창세기 7:16 | `ANCHOR_GEN_7_16` | 4 | `theme_02_fact_lock_gate.json` |
| 오순절 성령 강림 (Pentecost Unification) | 사도행전 2:4 | `ANCHOR_ACTS_2_4` | 4 | `theme_03_multi_lens_fusion.json` |
| 언약 증언 (Covenant Witness) | 창세기 15:6 | `ANCHOR_GEN_15_6` | 4 | `theme_04_covenant_witness.json` |
| 성소 휘장 찢어짐 (Veil Torn) | 마태복음 27:51 | `ANCHOR_MATT_27_51` | 4 | `theme_05_veil_access.json` |
| 유월절 통과 (Passover Passage) | 출애굽기 12:13 | `ANCHOR_EXOD_12_13` | 4 | `theme_06_exodus_regime_passover.json` |
| 보좌 관측 (Throne Observation) | 요한계시록 4:2 | `ANCHOR_REV_4_2` | 4 | `theme_07_revelation_throne.json` |
| 낙인·표식 (Seal and Mark) | 에스겔 9:4 | `ANCHOR_EZEK_9_4` | 4 | `theme_08_seal_mark.json` |
| 성막·임재 (Tabernacle Presence) | 출애굽기 40:34 | `ANCHOR_EXO_40_34` | 4 | `theme_09_tabernacle_presence.json` |
| Samson Jawbone (Track B) | 시편 119:105 | `ANCHOR_SAMSON_JAWBONE` | 4 | `theme_1000_samson_jawbone.json` |
| Adam Earth (Track B) | 시편 119:105 | `ANCHOR_ADAM_EARTH` | 4 | `theme_1001_adam_earth.json` |
| Dust (Track B) | 시편 119:105 | `ANCHOR_DUST` | 4 | `theme_1002_dust.json` |
| Adam Naming (Track B) | 시편 119:105 | `ANCHOR_ADAM_NAMING` | 4 | `theme_1003_adam_naming.json` |
| Animals (Track B) | 시편 119:105 | `ANCHOR_ANIMALS` | 4 | `theme_1004_animals.json` |
| Ark Raven (Track B) | 시편 119:105 | `ANCHOR_ARK_RAVEN` | 4 | `theme_1005_ark_raven.json` |
| Olive Branch (Track B) | 시편 119:105 | `ANCHOR_OLIVE_BRANCH` | 4 | `theme_1006_olive_branch.json` |
| Babel Languages (Track B) | 시편 119:105 | `ANCHOR_BABEL_LANGUAGES` | 4 | `theme_1007_babel_languages.json` |
| Abraham Tent (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_TENT` | 4 | `theme_1008_abraham_tent.json` |
| Covenant Rainbow (Track B) | 시편 119:105 | `ANCHOR_COVENANT_RAINBOW` | 4 | `theme_1009_covenant_rainbow.json` |
| 마지막 명령 메아리 (Great Commission Echo) | 마태복음 28:20 | `ANCHOR_MAT_28_20` | 4 | `theme_100_great_commission_echo.json` |
| Sarah Laugh (Track B) | 시편 119:105 | `ANCHOR_SARAH_LAUGH` | 4 | `theme_1010_sarah_laugh.json` |
| Hagar Angel (Track B) | 시편 119:105 | `ANCHOR_HAGAR_ANGEL` | 4 | `theme_1011_hagar_angel.json` |
| Lot Veil (Track B) | 시편 119:105 | `ANCHOR_LOT_VEIL` | 4 | `theme_1012_lot_veil.json` |
| Sodom Brimstone (Track B) | 시편 119:105 | `ANCHOR_SODOM_BRIMSTONE` | 4 | `theme_1013_sodom_brimstone.json` |
| Isaac Well (Track B) | 시편 119:105 | `ANCHOR_ISAAC_WELL` | 4 | `theme_1014_isaac_well.json` |
| Rebekah Camels (Track B) | 시편 119:105 | `ANCHOR_REBEKAH_CAMELS` | 4 | `theme_1015_rebekah_camels.json` |
| Jacob Ladder Dream (Track B) | 시편 119:105 | `ANCHOR_JACOB_LADDER_DREAM` | 4 | `theme_1016_jacob_ladder_dream.json` |
| Joseph Dream Coat (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_DREAM_COAT` | 4 | `theme_1017_joseph_dream_coat.json` |
| Benjamin Bowl (Track B) | 시편 119:105 | `ANCHOR_BENJAMIN_BOWL` | 4 | `theme_1018_benjamin_bowl.json` |
| Moses Basket (Track B) | 시편 119:105 | `ANCHOR_MOSES_BASKET` | 4 | `theme_1019_moses_basket.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_101_lazarus_raise.json` |
| Reeds (Track B) | 시편 119:105 | `ANCHOR_REEDS` | 4 | `theme_1020_reeds.json` |
| Plague Darkness (Track B) | 시편 119:105 | `ANCHOR_PLAGUE_DARKNESS` | 4 | `theme_1021_plague_darkness.json` |
| Blood (Track B) | 시편 119:105 | `ANCHOR_BLOOD` | 4 | `theme_1022_blood.json` |
| Lintel (Track B) | 시편 119:105 | `ANCHOR_LINTEL` | 4 | `theme_1023_lintel.json` |
| Pillar Fire Night (Track B) | 시편 119:105 | `ANCHOR_PILLAR_FIRE_NIGHT` | 4 | `theme_1024_pillar_fire_night.json` |
| Calf Worship (Track B) | 시편 119:105 | `ANCHOR_CALF_WORSHIP` | 4 | `theme_1025_calf_worship.json` |
| Tablets Broken (Track B) | 시편 119:105 | `ANCHOR_TABLETS_BROKEN` | 4 | `theme_1026_tablets_broken.json` |
| Covenant Renewed (Track B) | 시편 119:105 | `ANCHOR_COVENANT_RENEWED` | 4 | `theme_1027_covenant_renewed.json` |
| Spies Cluster (Track B) | 시편 119:105 | `ANCHOR_SPIES_CLUSTER` | 4 | `theme_1028_spies_cluster.json` |
| Joshua Horn (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_HORN` | 4 | `theme_1029_joshua_horn.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_102_mary_martha_serve.json` |
| Jericho Shout (Track B) | 시편 119:105 | `ANCHOR_JERICHO_SHOUT` | 4 | `theme_1030_jericho_shout.json` |
| Achan Stolen (Track B) | 시편 119:105 | `ANCHOR_ACHAN_STOLEN` | 4 | `theme_1031_achan_stolen.json` |
| Sun Moon Stood (Track B) | 시편 119:105 | `ANCHOR_SUN_MOON_STOOD` | 4 | `theme_1032_sun_moon_stood.json` |
| Gideon Pitchers (Track B) | 시편 119:105 | `ANCHOR_GIDEON_PITCHERS` | 4 | `theme_1033_gideon_pitchers.json` |
| Jephthah Daughter (Track B) | 시편 119:105 | `ANCHOR_JEPHTHAH_DAUGHTER` | 4 | `theme_1034_jephthah_daughter.json` |
| Samson Gates (Track B) | 시편 119:105 | `ANCHOR_SAMSON_GATES` | 4 | `theme_1035_samson_gates.json` |
| Delilah Scissors (Track B) | 시편 119:105 | `ANCHOR_DELILAH_SCISSORS` | 4 | `theme_1036_delilah_scissors.json` |
| Samuel Voice (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_VOICE` | 4 | `theme_1037_samuel_voice.json` |
| Saul Tall (Track B) | 시편 119:105 | `ANCHOR_SAUL_TALL` | 4 | `theme_1038_saul_tall.json` |
| David Anointed (Track B) | 시편 119:105 | `ANCHOR_DAVID_ANOINTED` | 4 | `theme_1039_david_anointed.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_103_wedding_cana.json` |
| Harp Soothe (Track B) | 시편 119:105 | `ANCHOR_HARP_SOOTHE` | 4 | `theme_1040_harp_soothe.json` |
| Goliath Armor (Track B) | 시편 119:105 | `ANCHOR_GOLIATH_ARMOR` | 4 | `theme_1041_goliath_armor.json` |
| Bathsheba Uriah (Track B) | 시편 119:105 | `ANCHOR_BATHSHEBA_URIAH` | 4 | `theme_1042_bathsheba_uriah.json` |
| Solomon Temple (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_TEMPLE` | 4 | `theme_1043_solomon_temple.json` |
| Ark Glory (Track B) | 시편 119:105 | `ANCHOR_ARK_GLORY` | 4 | `theme_1044_ark_glory.json` |
| Gifts (Track B) | 시편 119:105 | `ANCHOR_GIFTS` | 4 | `theme_1045_gifts.json` |
| Elijah Raven Feed (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_RAVEN_FEED` | 4 | `theme_1046_elijah_raven_feed.json` |
| Jar (Track B) | 시편 119:105 | `ANCHOR_JAR` | 4 | `theme_1047_jar.json` |
| Elisha Shunem Room (Track B) | 시편 119:105 | `ANCHOR_ELISHA_SHUNEM_ROOM` | 4 | `theme_1048_elisha_shunem_room.json` |
| Naaman River (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_RIVER` | 4 | `theme_1049_naaman_river.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_104_cleansing_leper.json` |
| Dip (Track B) | 시편 119:105 | `ANCHOR_DIP` | 4 | `theme_1050_dip.json` |
| Tongue (Track B) | 시편 119:105 | `ANCHOR_TONGUE` | 4 | `theme_1051_tongue.json` |
| Josiah Huldah (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_HULDAH` | 4 | `theme_1052_josiah_huldah.json` |
| Jeremiah Cistern Mud (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_CISTERN_MUD` | 4 | `theme_1053_jeremiah_cistern_mud.json` |
| Ezekiel Bones (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_BONES` | 4 | `theme_1054_ezekiel_bones.json` |
| Breath (Track B) | 시편 119:105 | `ANCHOR_BREATH` | 4 | `theme_1055_breath.json` |
| Daniel Three Friends (Track B) | 시편 119:105 | `ANCHOR_DANIEL_THREE_FRIENDS` | 4 | `theme_1056_daniel_three_friends.json` |
| Furnace (Track B) | 시편 119:105 | `ANCHOR_FURNACE` | 4 | `theme_1057_furnace.json` |
| Belshazzar Mene (Track B) | 시편 119:105 | `ANCHOR_BELSHAZZAR_MENE` | 4 | `theme_1058_belshazzar_mene.json` |
| Ezra Reading (Track B) | 시편 119:105 | `ANCHOR_EZRA_READING` | 4 | `theme_1059_ezra_reading.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_105_sermon_mount.json` |
| Nehemiah Gates (Track B) | 시편 119:105 | `ANCHOR_NEHEMIAH_GATES` | 4 | `theme_1060_nehemiah_gates.json` |
| Job Satan Allowed (Track B) | 시편 119:105 | `ANCHOR_JOB_SATAN_ALLOWED` | 4 | `theme_1061_job_satan_allowed.json` |
| Friends Ashes (Track B) | 시편 119:105 | `ANCHOR_FRIENDS_ASHES` | 4 | `theme_1062_friends_ashes.json` |
| 시편 23 장막 (Psalm 23 Rod) | 시편 23:4 | `ANCHOR_PSALM_23_ROD` | 4 | `theme_1063_psalm_23_rod.json` |
| Proverbs 31 Woman (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_31_WOMAN` | 4 | `theme_1064_proverbs_31_woman.json` |
| Ecclesiastes Seasons (Track B) | 시편 119:105 | `ANCHOR_ECCLESIASTES_SEASONS` | 4 | `theme_1065_ecclesiastes_seasons.json` |
| Song Vineyard (Track B) | 시편 119:105 | `ANCHOR_SONG_VINEYARD` | 4 | `theme_1066_song_vineyard.json` |
| Isaiah 6 Coal (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_6_COAL` | 4 | `theme_1067_isaiah_6_coal.json` |
| Jeremiah 18 Potter (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_18_POTTER` | 4 | `theme_1068_jeremiah_18_potter.json` |
| Ezekiel 37 Army (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_37_ARMY` | 4 | `theme_1069_ezekiel_37_army.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_106_denarius_vineyard.json` |
| Hosea Gomer (Track B) | 시편 119:105 | `ANCHOR_HOSEA_GOMER` | 4 | `theme_1070_hosea_gomer.json` |
| Joel Spirit Pour (Track B) | 시편 119:105 | `ANCHOR_JOEL_SPIRIT_POUR` | 4 | `theme_1071_joel_spirit_pour.json` |
| Amos 5 Justice (Track B) | 시편 119:105 | `ANCHOR_AMOS_5_JUSTICE` | 4 | `theme_1072_amos_5_justice.json` |
| Pride (Track B) | 시편 119:105 | `ANCHOR_PRIDE` | 4 | `theme_1073_pride.json` |
| Jonah Fish (Track B) | 시편 119:105 | `ANCHOR_JONAH_FISH` | 4 | `theme_1074_jonah_fish.json` |
| Micah 4 Mountain (Track B) | 시편 119:105 | `ANCHOR_MICAH_4_MOUNTAIN` | 4 | `theme_1075_micah_4_mountain.json` |
| Nahum Nineveh Fall (Track B) | 시편 119:105 | `ANCHOR_NAHUM_NINEVEH_FALL` | 4 | `theme_1076_nahum_nineveh_fall.json` |
| Habakkuk 2 Write (Track B) | 시편 119:105 | `ANCHOR_HABAKKUK_2_WRITE` | 4 | `theme_1077_habakkuk_2_write.json` |
| Zephaniah Day Wrath (Track B) | 시편 119:105 | `ANCHOR_ZEPHANIAH_DAY_WRATH` | 4 | `theme_1078_zephaniah_day_wrath.json` |
| Haggai Consider (Track B) | 시편 119:105 | `ANCHOR_HAGGAI_CONSIDER` | 4 | `theme_1079_haggai_consider.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_107_wheat_tares.json` |
| Zechariah 4 Lampstand (Track B) | 시편 119:105 | `ANCHOR_ZECHARIAH_4_LAMPSTAND` | 4 | `theme_1080_zechariah_4_lampstand.json` |
| Malachi 3 Rob (Track B) | 시편 119:105 | `ANCHOR_MALACHI_3_ROB` | 4 | `theme_1081_malachi_3_rob.json` |
| Titus Crete (Track B) | 시편 119:105 | `ANCHOR_TITUS_CRETE` | 4 | `theme_1082_titus_crete.json` |
| Matthew Tax Collector (Track B) | 시편 119:105 | `ANCHOR_MATTHEW_TAX_COLLECTOR` | 4 | `theme_1083_matthew_tax_collector.json` |
| Mark Leper Touch (Track B) | 시편 119:105 | `ANCHOR_MARK_LEPER_TOUCH` | 4 | `theme_1084_mark_leper_touch.json` |
| Luke Samaritan (Track B) | 시편 119:105 | `ANCHOR_LUKE_SAMARITAN` | 4 | `theme_1085_luke_samaritan.json` |
| Priest (Track B) | 시편 119:105 | `ANCHOR_PRIEST` | 4 | `theme_1086_priest.json` |
| Levite (Track B) | 시편 119:105 | `ANCHOR_LEVITE` | 4 | `theme_1087_levite.json` |
| John Woman Well (Track B) | 시편 119:105 | `ANCHOR_JOHN_WOMAN_WELL` | 4 | `theme_1088_john_woman_well.json` |
| Acts Lydda Tabitha (Track B) | 시편 119:105 | `ANCHOR_ACTS_LYDDA_TABITHA` | 4 | `theme_1089_acts_lydda_tabitha.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_108_lost_coin.json` |
| Corinth Love Chapter (Track B) | 시편 119:105 | `ANCHOR_CORINTH_LOVE_CHAPTER` | 4 | `theme_1090_corinth_love_chapter.json` |
| Galatians Crucified (Track B) | 시편 119:105 | `ANCHOR_GALATIANS_CRUCIFIED` | 4 | `theme_1091_galatians_crucified.json` |
| Ephesians One Body (Track B) | 시편 119:105 | `ANCHOR_EPHESIANS_ONE_BODY` | 4 | `theme_1092_ephesians_one_body.json` |
| Philippians Christ Mind (Track B) | 시편 119:105 | `ANCHOR_PHILIPPIANS_CHRIST_MIND` | 4 | `theme_1093_philippians_christ_mind.json` |
| Colossians Hidden Treasure (Track B) | 시편 119:105 | `ANCHOR_COLOSSIANS_HIDDEN_TREASURE` | 4 | `theme_1094_colossians_hidden_treasure.json` |
| Thessalonians Day Lord (Track B) | 시편 119:105 | `ANCHOR_THESSALONIANS_DAY_LORD` | 4 | `theme_1095_thessalonians_day_lord.json` |
| Timothy Stir Gift (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_STIR_GIFT` | 4 | `theme_1096_timothy_stir_gift.json` |
| Titus Sound Doctrine (Track B) | 시편 119:105 | `ANCHOR_TITUS_SOUND_DOCTRINE` | 4 | `theme_1097_titus_sound_doctrine.json` |
| Philemon Onesimus (Track B) | 시편 119:105 | `ANCHOR_PHILEMON_ONESIMUS` | 4 | `theme_1098_philemon_onesimus.json` |
| Hebrews 11 Cloud (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_11_CLOUD` | 4 | `theme_1099_hebrews_11_cloud.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_109_prodigal_son.json` |
| 만나·떡 (Manna and Bread) | 출애굽기 16:15 | `ANCHOR_EXO_16_15` | 4 | `theme_10_manna_bread.json` |
| James Visit Orphans (Track B) | 시편 119:105 | `ANCHOR_JAMES_VISIT_ORPHANS` | 4 | `theme_1100_james_visit_orphans.json` |
| Peter Denial Rooster (Track B) | 시편 119:105 | `ANCHOR_PETER_DENIAL_ROOSTER` | 4 | `theme_1101_peter_denial_rooster.json` |
| John Beloved Disciple (Track B) | 시편 119:105 | `ANCHOR_JOHN_BELOVED_DISCIPLE` | 4 | `theme_1102_john_beloved_disciple.json` |
| Faith (Track B) | 시편 119:105 | `ANCHOR_FAITH` | 4 | `theme_1103_faith.json` |
| 보좌 둘러섬 (Revelation 4 Throne) | 요한계시록 4:2 | `ANCHOR_REVELATION_4_THRONE` | 4 | `theme_1104_revelation_4_throne.json` |
| Lamb Book (Track B) | 시편 119:105 | `ANCHOR_LAMB_BOOK` | 4 | `theme_1105_lamb_book.json` |
| 일곱 인 (Seven Seals) | 요한계시록 5:1 | `ANCHOR_SEVEN_SEALS` | 4 | `theme_1106_seven_seals.json` |
| Trumpet Woe (Track B) | 시편 119:105 | `ANCHOR_TRUMPET_WOE` | 4 | `theme_1107_trumpet_woe.json` |
| Bowl Pour (Track B) | 시편 119:105 | `ANCHOR_BOWL_POUR` | 4 | `theme_1108_bowl_pour.json` |
| Harlot Babylon (Track B) | 시편 119:105 | `ANCHOR_HARLOT_BABYLON` | 4 | `theme_1109_harlot_babylon.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_110_cursed_fig_tree.json` |
| Beast Rising (Track B) | 시편 119:105 | `ANCHOR_BEAST_RISING` | 4 | `theme_1110_beast_rising.json` |
| False Prophet (Track B) | 시편 119:105 | `ANCHOR_FALSE_PROPHET` | 4 | `theme_1111_false_prophet.json` |
| Millennium Bind (Track B) | 시편 119:105 | `ANCHOR_MILLENNIUM_BIND` | 4 | `theme_1112_millennium_bind.json` |
| New Earth No Tears (Track B) | 시편 119:105 | `ANCHOR_NEW_EARTH_NO_TEARS` | 4 | `theme_1113_new_earth_no_tears.json` |
| Alpha Omega Begin (Track B) | 시편 119:105 | `ANCHOR_ALPHA_OMEGA_BEGIN` | 4 | `theme_1114_alpha_omega_begin.json` |
| End (Track B) | 시편 119:105 | `ANCHOR_END` | 4 | `theme_1115_end.json` |
| River Life (Track B) | 시편 119:105 | `ANCHOR_RIVER_LIFE` | 4 | `theme_1116_river_life.json` |
| Tree Fruit Month (Track B) | 시편 119:105 | `ANCHOR_TREE_FRUIT_MONTH` | 4 | `theme_1117_tree_fruit_month.json` |
| Golden Candlestick (Track B) | 시편 119:105 | `ANCHOR_GOLDEN_CANDLESTICK` | 4 | `theme_1118_golden_candlestick.json` |
| Abram Call Ur (Track B) | 시편 119:105 | `ANCHOR_ABRAM_CALL_UR` | 4 | `theme_1119_abram_call_ur.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_111_lazarus_raise.json` |
| Lot Plain Choice (Track B) | 시편 119:105 | `ANCHOR_LOT_PLAIN_CHOICE` | 4 | `theme_1120_lot_plain_choice.json` |
| Sodom Angels Visit (Track B) | 시편 119:105 | `ANCHOR_SODOM_ANGELS_VISIT` | 4 | `theme_1121_sodom_angels_visit.json` |
| Abraham Three Visitors (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_THREE_VISITORS` | 4 | `theme_1122_abraham_three_visitors.json` |
| Sarah Cakes Baked (Track B) | 시편 119:105 | `ANCHOR_SARAH_CAKES_BAKED` | 4 | `theme_1123_sarah_cakes_baked.json` |
| Binding Isaac Ram (Track B) | 시편 119:105 | `ANCHOR_BINDING_ISAAC_RAM` | 4 | `theme_1124_binding_isaac_ram.json` |
| Jacob Wrestle Peniel (Track B) | 시편 119:105 | `ANCHOR_JACOB_WRESTLE_PENIEL` | 4 | `theme_1125_jacob_wrestle_peniel.json` |
| Joseph Coat Many (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_COAT_MANY` | 4 | `theme_1126_joseph_coat_many.json` |
| Dreams Sheaf Bow (Track B) | 시편 119:105 | `ANCHOR_DREAMS_SHEAF_BOW` | 4 | `theme_1127_dreams_sheaf_bow.json` |
| Egypt Famine Store (Track B) | 시편 119:105 | `ANCHOR_EGYPT_FAMINE_STORE` | 4 | `theme_1128_egypt_famine_store.json` |
| Moses Red Sea (Track B) | 시편 119:105 | `ANCHOR_MOSES_RED_SEA` | 4 | `theme_1129_moses_red_sea.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_112_mary_martha_serve.json` |
| Bitter Marah Sweet (Track B) | 시편 119:105 | `ANCHOR_BITTER_MARAH_SWEET` | 4 | `theme_1130_bitter_marah_sweet.json` |
| Ten Commandments Sinai (Track B) | 시편 119:105 | `ANCHOR_TEN_COMMANDMENTS_SINAI` | 4 | `theme_1131_ten_commandments_sinai.json` |
| Quail Grumbling Camp (Track B) | 시편 119:105 | `ANCHOR_QUAIL_GRUMBLING_CAMP` | 4 | `theme_1132_quail_grumbling_camp.json` |
| Korah Swallowed Earth (Track B) | 시편 119:105 | `ANCHOR_KORAH_SWALLOWED_EARTH` | 4 | `theme_1133_korah_swallowed_earth.json` |
| Rahab Scarlet Rope (Track B) | 시편 119:105 | `ANCHOR_RAHAB_SCARLET_ROPE` | 4 | `theme_1134_rahab_scarlet_rope.json` |
| Jericho Seven March (Track B) | 시편 119:105 | `ANCHOR_JERICHO_SEVEN_MARCH` | 4 | `theme_1135_jericho_seven_march.json` |
| Achan Hidden Silver (Track B) | 시편 119:105 | `ANCHOR_ACHAN_HIDDEN_SILVER` | 4 | `theme_1136_achan_hidden_silver.json` |
| Gideon Army Three Hundred (Track B) | 시편 119:105 | `ANCHOR_GIDEON_ARMY_THREE_HUNDRED` | 4 | `theme_1137_gideon_army_three_hundred.json` |
| Delilah Hair Shorn (Track B) | 시편 119:105 | `ANCHOR_DELILAH_HAIR_SHORN` | 4 | `theme_1138_delilah_hair_shorn.json` |
| Eli Ark Captured (Track B) | 시편 119:105 | `ANCHOR_ELI_ARK_CAPTURED` | 4 | `theme_1139_eli_ark_captured.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_113_wedding_cana.json` |
| Cave Adullam Hide (Track B) | 시편 119:105 | `ANCHOR_CAVE_ADULLAM_HIDE` | 4 | `theme_1140_cave_adullam_hide.json` |
| Temple Cloud Glory (Track B) | 시편 119:105 | `ANCHOR_TEMPLE_CLOUD_GLORY` | 4 | `theme_1141_temple_cloud_glory.json` |
| Sheba Riddle Tests (Track B) | 시편 119:105 | `ANCHOR_SHEBA_RIDDLE_TESTS` | 4 | `theme_1142_sheba_riddle_tests.json` |
| Elijah Carmel Altar (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_CARMEL_ALTAR` | 4 | `theme_1143_elijah_carmel_altar.json` |
| Elisha Bears Youths (Track B) | 시편 119:105 | `ANCHOR_ELISHA_BEARS_YOUTHS` | 4 | `theme_1144_elisha_bears_youths.json` |
| Naaman Seven Wash (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_SEVEN_WASH` | 4 | `theme_1145_naaman_seven_wash.json` |
| Gehazi Greedy Leprosy (Track B) | 시편 119:105 | `ANCHOR_GEHAZI_GREEDY_LEPROSY` | 4 | `theme_1146_gehazi_greedy_leprosy.json` |
| Hezekiah Fifteen Years (Track B) | 시편 119:105 | `ANCHOR_HEZEKIAH_FIFTEEN_YEARS` | 4 | `theme_1147_hezekiah_fifteen_years.json` |
| Josiah Law Found (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_LAW_FOUND` | 4 | `theme_1148_josiah_law_found.json` |
| Jeremiah Field Buy (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_FIELD_BUY` | 4 | `theme_1149_jeremiah_field_buy.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_114_cleansing_leper.json` |
| Ezekiel Dry Bones Valley (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_DRY_BONES_VALLEY` | 4 | `theme_1150_ezekiel_dry_bones_valley.json` |
| Daniel Statue Dream (Track B) | 시편 119:105 | `ANCHOR_DANIEL_STATUE_DREAM` | 4 | `theme_1151_daniel_statue_dream.json` |
| Three Friends Furnace (Track B) | 시편 119:105 | `ANCHOR_THREE_FRIENDS_FURNACE` | 4 | `theme_1152_three_friends_furnace.json` |
| Belshazzar Feast Hand (Track B) | 시편 119:105 | `ANCHOR_BELSHAZZAR_FEAST_HAND` | 4 | `theme_1153_belshazzar_feast_hand.json` |
| Cyrus Decree Return (Track B) | 시편 119:105 | `ANCHOR_CYRUS_DECREE_RETURN` | 4 | `theme_1154_cyrus_decree_return.json` |
| Ezra Law Reading (Track B) | 시편 119:105 | `ANCHOR_EZRA_LAW_READING` | 4 | `theme_1155_ezra_law_reading.json` |
| Nehemiah Sword And Trowel (Track B) | 시편 119:105 | `ANCHOR_NEHEMIAH_SWORD_AND_TROWEL` | 4 | `theme_1156_nehemiah_sword_and_trowel.json` |
| Job Friends Debate (Track B) | 시편 119:105 | `ANCHOR_JOB_FRIENDS_DEBATE` | 4 | `theme_1157_job_friends_debate.json` |
| Psalm One Tree Streams (Track B) | 시편 119:105 | `ANCHOR_PSALM_ONE_TREE_STREAMS` | 4 | `theme_1158_psalm_one_tree_streams.json` |
| Proverbs Ant Highway (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_ANT_HIGHWAY` | 4 | `theme_1159_proverbs_ant_highway.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_115_sermon_mount.json` |
| Song Garden Locked (Track B) | 시편 119:105 | `ANCHOR_SONG_GARDEN_LOCKED` | 4 | `theme_1160_song_garden_locked.json` |
| Isaiah Servant Songs (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_SERVANT_SONGS` | 4 | `theme_1161_isaiah_servant_songs.json` |
| Jeremiah Weeping Prophet (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_WEEPING_PROPHET` | 4 | `theme_1162_jeremiah_weeping_prophet.json` |
| Lamentations City Fall (Track B) | 시편 119:105 | `ANCHOR_LAMENTATIONS_CITY_FALL` | 4 | `theme_1163_lamentations_city_fall.json` |
| Hosea Buy Back Wife (Track B) | 시편 119:105 | `ANCHOR_HOSEA_BUY_BACK_WIFE` | 4 | `theme_1164_hosea_buy_back_wife.json` |
| Joel Locust Army (Track B) | 시편 119:105 | `ANCHOR_JOEL_LOCUST_ARMY` | 4 | `theme_1165_joel_locust_army.json` |
| Amos Plumb Crooked (Track B) | 시편 119:105 | `ANCHOR_AMOS_PLUMB_CROOKED` | 4 | `theme_1166_amos_plumb_crooked.json` |
| Obadiah Edom Pride (Track B) | 시편 119:105 | `ANCHOR_OBADIAH_EDOM_PRIDE` | 4 | `theme_1167_obadiah_edom_pride.json` |
| Jonah Whale Three (Track B) | 시편 119:105 | `ANCHOR_JONAH_WHALE_THREE` | 4 | `theme_1168_jonah_whale_three.json` |
| Nahum Nineveh Overthrow (Track B) | 시편 119:105 | `ANCHOR_NAHUM_NINEVEH_OVERTHROW` | 4 | `theme_1169_nahum_nineveh_overthrow.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_116_lazarus_raise.json` |
| Zephaniah Silent Day (Track B) | 시편 119:105 | `ANCHOR_ZEPHANIAH_SILENT_DAY` | 4 | `theme_1170_zephaniah_silent_day.json` |
| Haggai Consider Paths (Track B) | 시편 119:105 | `ANCHOR_HAGGAI_CONSIDER_PATHS` | 4 | `theme_1171_haggai_consider_paths.json` |
| Zechariah Branch Temple (Track B) | 시편 119:105 | `ANCHOR_ZECHARIAH_BRANCH_TEMPLE` | 4 | `theme_1172_zechariah_branch_temple.json` |
| Mark Storm Stilled (Track B) | 시편 119:105 | `ANCHOR_MARK_STORM_STILLED` | 4 | `theme_1173_mark_storm_stilled.json` |
| Luke Samaritan Inn (Track B) | 시편 119:105 | `ANCHOR_LUKE_SAMARITAN_INN` | 4 | `theme_1174_luke_samaritan_inn.json` |
| John Vine Branches (Track B) | 시편 119:105 | `ANCHOR_JOHN_VINE_BRANCHES` | 4 | `theme_1175_john_vine_branches.json` |
| Acts Pentecost Wind (Track B) | 시편 119:105 | `ANCHOR_ACTS_PENTECOST_WIND` | 4 | `theme_1176_acts_pentecost_wind.json` |
| Galatians Fruit Spirit List (Track B) | 시편 119:105 | `ANCHOR_GALATIANS_FRUIT_SPIRIT_LIST` | 4 | `theme_1177_galatians_fruit_spirit_list.json` |
| Ephesians Armor Belt (Track B) | 시편 119:105 | `ANCHOR_EPHESIANS_ARMOR_BELT` | 4 | `theme_1178_ephesians_armor_belt.json` |
| Philippians Press Goal (Track B) | 시편 119:105 | `ANCHOR_PHILIPPIANS_PRESS_GOAL` | 4 | `theme_1179_philippians_press_goal.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_117_mary_martha_serve.json` |
| Colossians Supremacy Christ (Track B) | 시편 119:105 | `ANCHOR_COLOSSIANS_SUPREMACY_CHRIST` | 4 | `theme_1180_colossians_supremacy_christ.json` |
| Timothy Good Fight (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_GOOD_FIGHT` | 4 | `theme_1181_timothy_good_fight.json` |
| Titus Crete Island (Track B) | 시편 119:105 | `ANCHOR_TITUS_CRETE_ISLAND` | 4 | `theme_1182_titus_crete_island.json` |
| Philemon Onesimus Plea (Track B) | 시편 119:105 | `ANCHOR_PHILEMON_ONESIMUS_PLEA` | 4 | `theme_1183_philemon_onesimus_plea.json` |
| Hebrews Faith Cloud (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_FAITH_CLOUD` | 4 | `theme_1184_hebrews_faith_cloud.json` |
| James Tongue Rudder (Track B) | 시편 119:105 | `ANCHOR_JAMES_TONGUE_RUDDER` | 4 | `theme_1185_james_tongue_rudder.json` |
| Peter Feed Sheep (Track B) | 시편 119:105 | `ANCHOR_PETER_FEED_SHEEP` | 4 | `theme_1186_peter_feed_sheep.json` |
| John Love Command (Track B) | 시편 119:105 | `ANCHOR_JOHN_LOVE_COMMAND` | 4 | `theme_1187_john_love_command.json` |
| Revelation Lamb Throne (Track B) | 시편 119:105 | `ANCHOR_REVELATION_LAMB_THRONE` | 4 | `theme_1188_revelation_lamb_throne.json` |
| Twenty Four Elders (Track B) | 시편 119:105 | `ANCHOR_TWENTY_FOUR_ELDERS` | 4 | `theme_1189_twenty_four_elders.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_118_wedding_cana.json` |
| Seven Trumpet Woes (Track B) | 시편 119:105 | `ANCHOR_SEVEN_TRUMPET_WOES` | 4 | `theme_1190_seven_trumpet_woes.json` |
| Seven Bowls Wrath (Track B) | 시편 119:105 | `ANCHOR_SEVEN_BOWLS_WRATH` | 4 | `theme_1191_seven_bowls_wrath.json` |
| New Jerusalem Descends (Track B) | 시편 119:105 | `ANCHOR_NEW_JERUSALEM_DESCENDS` | 4 | `theme_1192_new_jerusalem_descends.json` |
| Tree Life Healing Leaves (Track B) | 시편 119:105 | `ANCHOR_TREE_LIFE_HEALING_LEAVES` | 4 | `theme_1193_tree_life_healing_leaves.json` |
| Alpha Omega Amen (Track B) | 시편 119:105 | `ANCHOR_ALPHA_OMEGA_AMEN` | 4 | `theme_1194_alpha_omega_amen.json` |
| Faithful Witness Come (Track B) | 시편 119:105 | `ANCHOR_FAITHFUL_WITNESS_COME` | 4 | `theme_1195_faithful_witness_come.json` |
| Census Bethlehem Travel (Track B) | 시편 119:105 | `ANCHOR_CENSUS_BETHLEHEM_TRAVEL` | 4 | `theme_1196_census_bethlehem_travel.json` |
| Manger Shepherds Angels (Track B) | 시편 119:105 | `ANCHOR_MANGER_SHEPHERDS_ANGELS` | 4 | `theme_1197_manger_shepherds_angels.json` |
| Magi Gold Frankincense (Track B) | 시편 119:105 | `ANCHOR_MAGI_GOLD_FRANKINCENSE` | 4 | `theme_1198_magi_gold_frankincense.json` |
| Flight Egypt Herod (Track B) | 시편 119:105 | `ANCHOR_FLIGHT_EGYPT_HEROD` | 4 | `theme_1199_flight_egypt_herod.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_119_cleansing_leper.json` |
| 물에서 걸음 (Walk on Water) | 마태복음 14:25 | `ANCHOR_MATT_14_25` | 4 | `theme_11_walk_on_water.json` |
| Return Nazareth Child (Track B) | 시편 119:105 | `ANCHOR_RETURN_NAZARETH_CHILD` | 4 | `theme_1200_return_nazareth_child.json` |
| Jordan Baptism Dove (Track B) | 시편 119:105 | `ANCHOR_JORDAN_BAPTISM_DOVE` | 4 | `theme_1201_jordan_baptism_dove.json` |
| Transfiguration White Robes (Track B) | 시편 119:105 | `ANCHOR_TRANSFIGURATION_WHITE_ROBES` | 4 | `theme_1202_transfiguration_white_robes.json` |
| Last Supper Cup (Track B) | 시편 119:105 | `ANCHOR_LAST_SUPPER_CUP` | 4 | `theme_1203_last_supper_cup.json` |
| Gethsemane Bloody Sweat (Track B) | 시편 119:105 | `ANCHOR_GETHSEMANE_BLOODY_SWEAT` | 4 | `theme_1204_gethsemane_bloody_sweat.json` |
| Betrayal Garden Kiss (Track B) | 시편 119:105 | `ANCHOR_BETRAYAL_GARDEN_KISS` | 4 | `theme_1205_betrayal_garden_kiss.json` |
| Pilate Barabbas Vote (Track B) | 시편 119:105 | `ANCHOR_PILATE_BARABBAS_VOTE` | 4 | `theme_1206_pilate_barabbas_vote.json` |
| Crown Thorns Mock (Track B) | 시편 119:105 | `ANCHOR_CROWN_THORNS_MOCK` | 4 | `theme_1207_crown_thorns_mock.json` |
| Crucifixion Noon Dark (Track B) | 시편 119:105 | `ANCHOR_CRUCIFIXION_NOON_DARK` | 4 | `theme_1208_crucifixion_noon_dark.json` |
| Tomb Stone Rolled (Track B) | 시편 119:105 | `ANCHOR_TOMB_STONE_ROLLED` | 4 | `theme_1209_tomb_stone_rolled.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_120_sermon_mount.json` |
| Resurrection Road Emmaus (Track B) | 시편 119:105 | `ANCHOR_RESURRECTION_ROAD_EMMAUS` | 4 | `theme_1210_resurrection_road_emmaus.json` |
| Ascension Olive Cloud (Track B) | 시편 119:105 | `ANCHOR_ASCENSION_OLIVE_CLOUD` | 4 | `theme_1211_ascension_olive_cloud.json` |
| Adam Serpent Curse (Track B) | 시편 119:105 | `ANCHOR_ADAM_SERPENT_CURSE` | 4 | `theme_1212_adam_serpent_curse.json` |
| Eve Mother All Living (Track B) | 시편 119:105 | `ANCHOR_EVE_MOTHER_ALL_LIVING` | 4 | `theme_1213_eve_mother_all_living.json` |
| Cain Abel Offerings (Track B) | 시편 119:105 | `ANCHOR_CAIN_ABEL_OFFERINGS` | 4 | `theme_1214_cain_abel_offerings.json` |
| Enoch Walked With God (Track B) | 시편 119:105 | `ANCHOR_ENOCH_WALKED_WITH_GOD` | 4 | `theme_1215_enoch_walked_with_god.json` |
| Noah Found Grace (Track B) | 시편 119:105 | `ANCHOR_NOAH_FOUND_GRACE` | 4 | `theme_1216_noah_found_grace.json` |
| Abraham Stars Count (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_STARS_COUNT` | 4 | `theme_1217_abraham_stars_count.json` |
| Isaac Wells Dug (Track B) | 시편 119:105 | `ANCHOR_ISAAC_WELLS_DUG` | 4 | `theme_1218_isaac_wells_dug.json` |
| Creation Six Days (Track B) | 시편 119:105 | `ANCHOR_CREATION_SIX_DAYS` | 4 | `theme_1219_creation_six_days.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_121_denarius_vineyard.json` |
| Sabbath Rest Eden (Track B) | 시편 119:105 | `ANCHOR_SABBATH_REST_EDEN` | 4 | `theme_1220_sabbath_rest_eden.json` |
| Garden East Eden (Track B) | 시편 119:105 | `ANCHOR_GARDEN_EAST_EDEN` | 4 | `theme_1221_garden_east_eden.json` |
| Tree Knowledge Good Evil (Track B) | 시편 119:105 | `ANCHOR_TREE_KNOWLEDGE_GOOD_EVIL` | 4 | `theme_1222_tree_knowledge_good_evil.json` |
| Cherubim Flaming Sword (Track B) | 시편 119:105 | `ANCHOR_CHERUBIM_FLAMING_SWORD` | 4 | `theme_1223_cherubim_flaming_sword.json` |
| Noah Covenant Rainbow (Track B) | 시편 119:105 | `ANCHOR_NOAH_COVENANT_RAINBOW` | 4 | `theme_1224_noah_covenant_rainbow.json` |
| Abraham Melchizedek Bread (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_MELCHIZEDEK_BREAD` | 4 | `theme_1225_abraham_melchizedek_bread.json` |
| Circumcision Covenant Sign (Track B) | 시편 119:105 | `ANCHOR_CIRCUMCISION_COVENANT_SIGN` | 4 | `theme_1226_circumcision_covenant_sign.json` |
| Sodom Intercession Prayer (Track B) | 시편 119:105 | `ANCHOR_SODOM_INTERCESSION_PRAYER` | 4 | `theme_1227_sodom_intercession_prayer.json` |
| Isaac Blessing Trick (Track B) | 시편 119:105 | `ANCHOR_ISAAC_BLESSING_TRICK` | 4 | `theme_1228_isaac_blessing_trick.json` |
| Jacob Laban Wages (Track B) | 시편 119:105 | `ANCHOR_JACOB_LABAN_WAGES` | 4 | `theme_1229_jacob_laban_wages.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_122_wheat_tares.json` |
| Joseph Prison Interpreter (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_PRISON_INTERPRETER` | 4 | `theme_1230_joseph_prison_interpreter.json` |
| Moses Leprous Hand (Track B) | 시편 119:105 | `ANCHOR_MOSES_LEPROUS_HAND` | 4 | `theme_1231_moses_leprous_hand.json` |
| Passover Unleavened (Track B) | 시편 119:105 | `ANCHOR_PASSOVER_UNLEAVENED` | 4 | `theme_1232_passover_unleavened.json` |
| Red Sea Song Miriam (Track B) | 시편 119:105 | `ANCHOR_RED_SEA_SONG_MIRIAM` | 4 | `theme_1233_red_sea_song_miriam.json` |
| Marah Tree Sweet (Track B) | 시편 119:105 | `ANCHOR_MARAH_TREE_SWEET` | 4 | `theme_1234_marah_tree_sweet.json` |
| Sinai Smoke Thunder (Track B) | 시편 119:105 | `ANCHOR_SINAI_SMOKE_THUNDER` | 4 | `theme_1235_sinai_smoke_thunder.json` |
| Golden Calf Molten (Track B) | 시편 119:105 | `ANCHOR_GOLDEN_CALF_MOLTEN` | 4 | `theme_1236_golden_calf_molten.json` |
| Tabernacle Blueprint (Track B) | 시편 119:105 | `ANCHOR_TABERNACLE_BLUEPRINT` | 4 | `theme_1237_tabernacle_blueprint.json` |
| Levites Carry Ark (Track B) | 시편 119:105 | `ANCHOR_LEVITES_CARRY_ARK` | 4 | `theme_1238_levites_carry_ark.json` |
| Spies Bad Report (Track B) | 시편 119:105 | `ANCHOR_SPIES_BAD_REPORT` | 4 | `theme_1239_spies_bad_report.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_123_lost_coin.json` |
| Rahab Harlot Saved (Track B) | 시편 119:105 | `ANCHOR_RAHAB_HARLOT_SAVED` | 4 | `theme_1240_rahab_harlot_saved.json` |
| Jordan Stones Memorial (Track B) | 시편 119:105 | `ANCHOR_JORDAN_STONES_MEMORIAL` | 4 | `theme_1241_jordan_stones_memorial.json` |
| Gibeon Sun Stood (Track B) | 시편 119:105 | `ANCHOR_GIBEON_SUN_STOOD` | 4 | `theme_1242_gibeon_sun_stood.json` |
| Deborah Song Victory (Track B) | 시편 119:105 | `ANCHOR_DEBORAH_SONG_VICTORY` | 4 | `theme_1243_deborah_song_victory.json` |
| Midian Camels Jars (Track B) | 시편 119:105 | `ANCHOR_MIDIAN_CAMELS_JARS` | 4 | `theme_1244_midian_camels_jars.json` |
| Samson Gate Carried (Track B) | 시편 119:105 | `ANCHOR_SAMSON_GATE_CARRIED` | 4 | `theme_1245_samson_gate_carried.json` |
| Micah Stolen Idols (Track B) | 시편 119:105 | `ANCHOR_MICAH_STOLEN_IDOLS` | 4 | `theme_1246_micah_stolen_idols.json` |
| Eli Ichabod Glory (Track B) | 시편 119:105 | `ANCHOR_ELI_ICHABOD_GLORY` | 4 | `theme_1247_eli_ichabod_glory.json` |
| Samuel Anoints David (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_ANOINTS_DAVID` | 4 | `theme_1248_samuel_anoints_david.json` |
| David Nabal Abigail (Track B) | 시편 119:105 | `ANCHOR_DAVID_NABAL_ABIGAIL` | 4 | `theme_1249_david_nabal_abigail.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_124_prodigal_son.json` |
| Absalom Hair Caught (Track B) | 시편 119:105 | `ANCHOR_ABSALOM_HAIR_CAUGHT` | 4 | `theme_1250_absalom_hair_caught.json` |
| Solomon Idols Wives (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_IDOLS_WIVES` | 4 | `theme_1251_solomon_idols_wives.json` |
| Elijah Still Small Voice (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_STILL_SMALL_VOICE` | 4 | `theme_1252_elijah_still_small_voice.json` |
| Elisha Axhead Float (Track B) | 시편 119:105 | `ANCHOR_ELISHA_AXHEAD_FLOAT` | 4 | `theme_1253_elisha_axhead_float.json` |
| Naaman Gehazi Greed (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_GEHAZI_GREED` | 4 | `theme_1254_naaman_gehazi_greed.json` |
| Hezekiah Sennacherib Letter (Track B) | 시편 119:105 | `ANCHOR_HEZEKIAH_SENNACHERIB_LETTER` | 4 | `theme_1255_hezekiah_sennacherib_letter.json` |
| Josiah Huldah Prophecy (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_HULDAH_PROPHECY` | 4 | `theme_1256_josiah_huldah_prophecy.json` |
| Jeremiah Rotten Belt (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_ROTTEN_BELT` | 4 | `theme_1257_jeremiah_rotten_belt.json` |
| Ezekiel Scroll Eat (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_SCROLL_EAT` | 4 | `theme_1258_ezekiel_scroll_eat.json` |
| Daniel Vegetables Refuse (Track B) | 시편 119:105 | `ANCHOR_DANIEL_VEGETABLES_REFUSE` | 4 | `theme_1259_daniel_vegetables_refuse.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_125_cursed_fig_tree.json` |
| Fiery Furnace Not Burned (Track B) | 시편 119:105 | `ANCHOR_FIERY_FURNACE_NOT_BURNED` | 4 | `theme_1260_fiery_furnace_not_burned.json` |
| Writing Hand Wall (Track B) | 시편 119:105 | `ANCHOR_WRITING_HAND_WALL` | 4 | `theme_1261_writing_hand_wall.json` |
| Cyrus Ends Captivity (Track B) | 시편 119:105 | `ANCHOR_CYRUS_ENDS_CAPTIVITY` | 4 | `theme_1262_cyrus_ends_captivity.json` |
| Ezra Mixed Marriage (Track B) | 시편 119:105 | `ANCHOR_EZRA_MIXED_MARRIAGE` | 4 | `theme_1263_ezra_mixed_marriage.json` |
| Nehemiah Opposition (Track B) | 시편 119:105 | `ANCHOR_NEHEMIAH_OPPOSITION` | 4 | `theme_1264_nehemiah_opposition.json` |
| Esther Haman Gallows (Track B) | 시편 119:105 | `ANCHOR_ESTHER_HAMAN_GALLOWS` | 4 | `theme_1265_esther_haman_gallows.json` |
| Job Satan Permission (Track B) | 시편 119:105 | `ANCHOR_JOB_SATAN_PERMISSION` | 4 | `theme_1266_job_satan_permission.json` |
| Psalm Twenty Three Valley (Track B) | 시편 119:105 | `ANCHOR_PSALM_TWENTY_THREE_VALLEY` | 4 | `theme_1267_psalm_twenty_three_valley.json` |
| Proverbs Go Ant (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_GO_ANT` | 4 | `theme_1268_proverbs_go_ant.json` |
| Ecclesiastes Chasing Wind (Track B) | 시편 119:105 | `ANCHOR_ECCLESIASTES_CHASING_WIND` | 4 | `theme_1269_ecclesiastes_chasing_wind.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_126_lazarus_raise.json` |
| Song Shulamite Bride (Track B) | 시편 119:105 | `ANCHOR_SONG_SHULAMITE_BRIDE` | 4 | `theme_1270_song_shulamite_bride.json` |
| Isaiah Coal Touched (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_COAL_TOUCHED` | 4 | `theme_1271_isaiah_coal_touched.json` |
| Jeremiah Buy Field Siege (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_BUY_FIELD_SIEGE` | 4 | `theme_1272_jeremiah_buy_field_siege.json` |
| Ezekiel Temple River (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_TEMPLE_RIVER` | 4 | `theme_1273_ezekiel_temple_river.json` |
| Hosea Hosea Redeem (Track B) | 시편 119:105 | `ANCHOR_HOSEA_HOSEA_REDEEM` | 4 | `theme_1274_hosea_hosea_redeem.json` |
| Joel Spirit Poured (Track B) | 시편 119:105 | `ANCHOR_JOEL_SPIRIT_POURED` | 4 | `theme_1275_joel_spirit_poured.json` |
| Obadiah Proud Heart (Track B) | 시편 119:105 | `ANCHOR_OBADIAH_PROUD_HEART` | 4 | `theme_1276_obadiah_proud_heart.json` |
| Jonah Ship Storm (Track B) | 시편 119:105 | `ANCHOR_JONAH_SHIP_STORM` | 4 | `theme_1277_jonah_ship_storm.json` |
| Micah Plow Swords (Track B) | 시편 119:105 | `ANCHOR_MICAH_PLOW_SWORDS` | 4 | `theme_1278_micah_plow_swords.json` |
| Nahum God Vengeance (Track B) | 시편 119:105 | `ANCHOR_NAHUM_GOD_VENGEANCE` | 4 | `theme_1279_nahum_god_vengeance.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_127_mary_martha_serve.json` |
| Habakkuk Rejoice Tribulation (Track B) | 시편 119:105 | `ANCHOR_HABAKKUK_REJOICE_TRIBULATION` | 4 | `theme_1280_habakkuk_rejoice_tribulation.json` |
| Zephaniah Seek Righteousness (Track B) | 시편 119:105 | `ANCHOR_ZEPHANIAH_SEEK_RIGHTEOUSNESS` | 4 | `theme_1281_zephaniah_seek_righteousness.json` |
| Haggai Temple Glory (Track B) | 시편 119:105 | `ANCHOR_HAGGAI_TEMPLE_GLORY` | 4 | `theme_1282_haggai_temple_glory.json` |
| Zechariah Horses Patrol (Track B) | 시편 119:105 | `ANCHOR_ZECHARIAH_HORSES_PATROL` | 4 | `theme_1283_zechariah_horses_patrol.json` |
| Malachi Rob God (Track B) | 시편 119:105 | `ANCHOR_MALACHI_ROB_GOD` | 4 | `theme_1284_malachi_rob_god.json` |
| Matthew Wise Men (Track B) | 시편 119:105 | `ANCHOR_MATTHEW_WISE_MEN` | 4 | `theme_1285_matthew_wise_men.json` |
| Mark Leper Touched (Track B) | 시편 119:105 | `ANCHOR_MARK_LEPER_TOUCHED` | 4 | `theme_1286_mark_leper_touched.json` |
| Luke Prodigal Return (Track B) | 시편 119:105 | `ANCHOR_LUKE_PRODIGAL_RETURN` | 4 | `theme_1287_luke_prodigal_return.json` |
| John Nicodemus Night (Track B) | 시편 119:105 | `ANCHOR_JOHN_NICODEMUS_NIGHT` | 4 | `theme_1288_john_nicodemus_night.json` |
| Romans Abraham Faith (Track B) | 시편 119:105 | `ANCHOR_ROMANS_ABRAHAM_FAITH` | 4 | `theme_1289_romans_abraham_faith.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_128_wedding_cana.json` |
| Galatians Crucified World (Track B) | 시편 119:105 | `ANCHOR_GALATIANS_CRUCIFIED_WORLD` | 4 | `theme_1290_galatians_crucified_world.json` |
| Ephesians One New Man (Track B) | 시편 119:105 | `ANCHOR_EPHESIANS_ONE_NEW_MAN` | 4 | `theme_1291_ephesians_one_new_man.json` |
| Philippians Christ Humility (Track B) | 시편 119:105 | `ANCHOR_PHILIPPIANS_CHRIST_HUMILITY` | 4 | `theme_1292_philippians_christ_humility.json` |
| Colossians Hidden Mystery (Track B) | 시편 119:105 | `ANCHOR_COLOSSIANS_HIDDEN_MYSTERY` | 4 | `theme_1293_colossians_hidden_mystery.json` |
| Thessalonians Asleep Wake (Track B) | 시편 119:105 | `ANCHOR_THESSALONIANS_ASLEEP_WAKE` | 4 | `theme_1294_thessalonians_asleep_wake.json` |
| Timothy Young Pastor (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_YOUNG_PASTOR` | 4 | `theme_1295_timothy_young_pastor.json` |
| Philemon Plea Heart (Track B) | 시편 119:105 | `ANCHOR_PHILEMON_PLEA_HEART` | 4 | `theme_1296_philemon_plea_heart.json` |
| Hebrews Better Covenant (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_BETTER_COVENANT` | 4 | `theme_1297_hebrews_better_covenant.json` |
| James Faith Without Works (Track B) | 시편 119:105 | `ANCHOR_JAMES_FAITH_WITHOUT_WORKS` | 4 | `theme_1298_james_faith_without_works.json` |
| Peter Rooster Crow (Track B) | 시편 119:105 | `ANCHOR_PETER_ROOSTER_CROW` | 4 | `theme_1299_peter_rooster_crow.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_129_cleansing_leper.json` |
| 선지자 불꽃 (Prophet Fire) | 열왕기상 18:38 | `ANCHOR_1KINGS_18_38` | 4 | `theme_12_prophet_fire.json` |
| John Beloved Reclining (Track B) | 시편 119:105 | `ANCHOR_JOHN_BELOVED_RECLINING` | 4 | `theme_1300_john_beloved_reclining.json` |
| Jude Contend Apostasy (Track B) | 시편 119:105 | `ANCHOR_JUDE_CONTEND_APOSTASY` | 4 | `theme_1301_jude_contend_apostasy.json` |
| 일곱 촛대 (Revelation Seven Lampstands) | 요한계시록 1:20 | `ANCHOR_REVELATION_SEVEN_LAMPSTANDS` | 4 | `theme_1302_revelation_seven_lampstands.json` |
| Revelation Four Living (Track B) | 시편 119:105 | `ANCHOR_REVELATION_FOUR_LIVING` | 4 | `theme_1303_revelation_four_living.json` |
| White Horse Rider (Track B) | 시편 119:105 | `ANCHOR_WHITE_HORSE_RIDER` | 4 | `theme_1304_white_horse_rider.json` |
| Red Horse Peace Taken (Track B) | 시편 119:105 | `ANCHOR_RED_HORSE_PEACE_TAKEN` | 4 | `theme_1305_red_horse_peace_taken.json` |
| Black Horse Famine (Track B) | 시편 119:105 | `ANCHOR_BLACK_HORSE_FAMINE` | 4 | `theme_1306_black_horse_famine.json` |
| Pale Horse Death (Track B) | 시편 119:105 | `ANCHOR_PALE_HORSE_DEATH` | 4 | `theme_1307_pale_horse_death.json` |
| Souls Under Altar (Track B) | 시편 119:105 | `ANCHOR_SOULS_UNDER_ALTAR` | 4 | `theme_1308_souls_under_altar.json` |
| 14만4천 인침 (144000 Sealed) | 요한계시록 7:4 | `ANCHOR_144000_SEALED` | 4 | `theme_1309_144000_sealed.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_130_sermon_mount.json` |
| Great Multitude Robes (Track B) | 시편 119:105 | `ANCHOR_GREAT_MULTITUDE_ROBES` | 4 | `theme_1310_great_multitude_robes.json` |
| Two Witnesses Prophesy (Track B) | 시편 119:105 | `ANCHOR_TWO_WITNESSES_PROPHESY` | 4 | `theme_1311_two_witnesses_prophesy.json` |
| Beast From Sea (Track B) | 시편 119:105 | `ANCHOR_BEAST_FROM_SEA` | 4 | `theme_1312_beast_from_sea.json` |
| Beast From Earth (Track B) | 시편 119:105 | `ANCHOR_BEAST_FROM_EARTH` | 4 | `theme_1313_beast_from_earth.json` |
| Mark Of Beast (Track B) | 시편 119:105 | `ANCHOR_MARK_OF_BEAST` | 4 | `theme_1314_mark_of_beast.json` |
| Harvest Earth Reaped (Track B) | 시편 119:105 | `ANCHOR_HARVEST_EARTH_REAPED` | 4 | `theme_1315_harvest_earth_reaped.json` |
| Winepress Wrath Trodden (Track B) | 시편 119:105 | `ANCHOR_WINEPRESS_WRATH_TRODDEN` | 4 | `theme_1316_winepress_wrath_trodden.json` |
| Marriage Supper Lamb (Track B) | 시편 119:105 | `ANCHOR_MARRIAGE_SUPPER_LAMB` | 4 | `theme_1317_marriage_supper_lamb.json` |
| New Jerusalem Bride (Track B) | 시편 119:105 | `ANCHOR_NEW_JERUSALEM_BRIDE` | 4 | `theme_1318_new_jerusalem_bride.json` |
| River Life Clear (Track B) | 시편 119:105 | `ANCHOR_RIVER_LIFE_CLEAR` | 4 | `theme_1319_river_life_clear.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_131_denarius_vineyard.json` |
| Tree Leaves Healing (Track B) | 시편 119:105 | `ANCHOR_TREE_LEAVES_HEALING` | 4 | `theme_1320_tree_leaves_healing.json` |
| No More Tears (Track B) | 시편 119:105 | `ANCHOR_NO_MORE_TEARS` | 4 | `theme_1321_no_more_tears.json` |
| Alpha Omega Beginning End (Track B) | 시편 119:105 | `ANCHOR_ALPHA_OMEGA_BEGINNING_END` | 4 | `theme_1322_alpha_omega_beginning_end.json` |
| Come Lord Amen (Track B) | 시편 119:105 | `ANCHOR_COME_LORD_AMEN` | 4 | `theme_1323_come_lord_amen.json` |
| Nativity Manger (Track B) | 시편 119:105 | `ANCHOR_NATIVITY_MANGER` | 4 | `theme_1324_nativity_manger.json` |
| Shepherds Gloria (Track B) | 시편 119:105 | `ANCHOR_SHEPHERDS_GLORIA` | 4 | `theme_1325_shepherds_gloria.json` |
| Flight Herod Warning (Track B) | 시편 119:105 | `ANCHOR_FLIGHT_HEROD_WARNING` | 4 | `theme_1326_flight_herod_warning.json` |
| Boy Temple Parents (Track B) | 시편 119:105 | `ANCHOR_BOY_TEMPLE_PARENTS` | 4 | `theme_1327_boy_temple_parents.json` |
| Baptism Voice Heaven (Track B) | 시편 119:105 | `ANCHOR_BAPTISM_VOICE_HEAVEN` | 4 | `theme_1328_baptism_voice_heaven.json` |
| Wilderness Temptations (Track B) | 시편 119:105 | `ANCHOR_WILDERNESS_TEMPTATIONS` | 4 | `theme_1329_wilderness_temptations.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_132_wheat_tares.json` |
| Sermon On Mount (Track B) | 시편 119:105 | `ANCHOR_SERMON_ON_MOUNT` | 4 | `theme_1330_sermon_on_mount.json` |
| Calming Sea Faith (Track B) | 시편 119:105 | `ANCHOR_CALMING_SEA_FAITH` | 4 | `theme_1331_calming_sea_faith.json` |
| Walking On Water (Track B) | 시편 119:105 | `ANCHOR_WALKING_ON_WATER` | 4 | `theme_1332_walking_on_water.json` |
| Transfiguration Voice (Track B) | 시편 119:105 | `ANCHOR_TRANSFIGURATION_VOICE` | 4 | `theme_1333_transfiguration_voice.json` |
| Triumphal Entry Hosanna (Track B) | 시편 119:105 | `ANCHOR_TRIUMPHAL_ENTRY_HOSANNA` | 4 | `theme_1334_triumphal_entry_hosanna.json` |
| Last Supper Foot Washing (Track B) | 시편 119:105 | `ANCHOR_LAST_SUPPER_FOOT_WASHING` | 4 | `theme_1335_last_supper_foot_washing.json` |
| 겟세마네 잠 (Gethsemane Watch Sleep) | 마태복음 26:40 | `ANCHOR_GETHSEMANE_WATCH_SLEEP` | 4 | `theme_1336_gethsemane_watch_sleep.json` |
| Noah 600 Years Build (Track B) | 시편 119:105 | `ANCHOR_NOAH_600_YEARS_BUILD` | 4 | `theme_1337_noah_600_years_build.json` |
| Ark Pitch Inside Out (Track B) | 시편 119:105 | `ANCHOR_ARK_PITCH_INSIDE_OUT` | 4 | `theme_1338_ark_pitch_inside_out.json` |
| Rain Forty Days (Track B) | 시편 119:105 | `ANCHOR_RAIN_FORTY_DAYS` | 4 | `theme_1339_rain_forty_days.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_133_lost_coin.json` |
| Rainbow Covenant Sign (Track B) | 시편 119:105 | `ANCHOR_RAINBOW_COVENANT_SIGN` | 4 | `theme_1340_rainbow_covenant_sign.json` |
| Babel One Language (Track B) | 시편 119:105 | `ANCHOR_BABEL_ONE_LANGUAGE` | 4 | `theme_1341_babel_one_language.json` |
| Abram Leave Ur (Track B) | 시편 119:105 | `ANCHOR_ABRAM_LEAVE_UR` | 4 | `theme_1342_abram_leave_ur.json` |
| Lot Pitch Tents Sodom (Track B) | 시편 119:105 | `ANCHOR_LOT_PITCH_TENTS_SODOM` | 4 | `theme_1343_lot_pitch_tents_sodom.json` |
| Isaac Birth Laughter (Track B) | 시편 119:105 | `ANCHOR_ISAAC_BIRTH_LAUGHTER` | 4 | `theme_1344_isaac_birth_laughter.json` |
| Jacob Esau Hairy (Track B) | 시편 119:105 | `ANCHOR_JACOB_ESAU_HAIRY` | 4 | `theme_1345_jacob_esau_hairy.json` |
| Joseph Coat Many Colors (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_COAT_MANY_COLORS` | 4 | `theme_1346_joseph_coat_many_colors.json` |
| Moses Bush Not Consumed (Track B) | 시편 119:105 | `ANCHOR_MOSES_BUSH_NOT_CONSUMED` | 4 | `theme_1347_moses_bush_not_consumed.json` |
| Plagues Frogs Gnats (Track B) | 시편 119:105 | `ANCHOR_PLAGUES_FROGS_GNATS` | 4 | `theme_1348_plagues_frogs_gnats.json` |
| Passover Unleavened Bread (Track B) | 시편 119:105 | `ANCHOR_PASSOVER_UNLEAVENED_BREAD` | 4 | `theme_1349_passover_unleavened_bread.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_134_prodigal_son.json` |
| Pillar Cloud By Day (Track B) | 시편 119:105 | `ANCHOR_PILLAR_CLOUD_BY_DAY` | 4 | `theme_1350_pillar_cloud_by_day.json` |
| Red Sea Wall Water (Track B) | 시편 119:105 | `ANCHOR_RED_SEA_WALL_WATER` | 4 | `theme_1351_red_sea_wall_water.json` |
| Manna Bread Morning (Track B) | 시편 119:105 | `ANCHOR_MANNA_BREAD_MORNING` | 4 | `theme_1352_manna_bread_morning.json` |
| Water Rock Struck (Track B) | 시편 119:105 | `ANCHOR_WATER_ROCK_STRUCK` | 4 | `theme_1353_water_rock_struck.json` |
| Ten Commandments Tablets (Track B) | 시편 119:105 | `ANCHOR_TEN_COMMANDMENTS_TABLETS` | 4 | `theme_1354_ten_commandments_tablets.json` |
| Tabernacle Curtains Blue (Track B) | 시편 119:105 | `ANCHOR_TABERNACLE_CURTAINS_BLUE` | 4 | `theme_1355_tabernacle_curtains_blue.json` |
| Ark Mercy Seat (Track B) | 시편 119:105 | `ANCHOR_ARK_MERCY_SEAT` | 4 | `theme_1356_ark_mercy_seat.json` |
| Spies Cluster Grapes (Track B) | 시편 119:105 | `ANCHOR_SPIES_CLUSTER_GRAPES` | 4 | `theme_1357_spies_cluster_grapes.json` |
| Joshua Sun Moon Still (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_SUN_MOON_STILL` | 4 | `theme_1358_joshua_sun_moon_still.json` |
| Rahab Scarlet Line (Track B) | 시편 119:105 | `ANCHOR_RAHAB_SCARLET_LINE` | 4 | `theme_1359_rahab_scarlet_line.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_135_cursed_fig_tree.json` |
| Gideon Three Hundred (Track B) | 시편 119:105 | `ANCHOR_GIDEON_THREE_HUNDRED` | 4 | `theme_1360_gideon_three_hundred.json` |
| Samson Jawbone Donkey (Track B) | 시편 119:105 | `ANCHOR_SAMSON_JAWBONE_DONKEY` | 4 | `theme_1361_samson_jawbone_donkey.json` |
| Ruth Gleaning Boaz (Track B) | 시편 119:105 | `ANCHOR_RUTH_GLEANING_BOAZ` | 4 | `theme_1362_ruth_gleaning_boaz.json` |
| Eli Ark Philistines (Track B) | 시편 119:105 | `ANCHOR_ELI_ARK_PHILISTINES` | 4 | `theme_1363_eli_ark_philistines.json` |
| Samuel Call Night Lord (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_CALL_NIGHT_LORD` | 4 | `theme_1364_samuel_call_night_lord.json` |
| David Harp Soothes Saul (Track B) | 시편 119:105 | `ANCHOR_DAVID_HARP_SOOTHES_SAUL` | 4 | `theme_1365_david_harp_soothes_saul.json` |
| Goliath Five Stones (Track B) | 시편 119:105 | `ANCHOR_GOLIATH_FIVE_STONES` | 4 | `theme_1366_goliath_five_stones.json` |
| Bathsheba Roof Bath (Track B) | 시편 119:105 | `ANCHOR_BATHSHEBA_ROOF_BATH` | 4 | `theme_1367_bathsheba_roof_bath.json` |
| Nathan Parable Lamb (Track B) | 시편 119:105 | `ANCHOR_NATHAN_PARABLE_LAMB` | 4 | `theme_1368_nathan_parable_lamb.json` |
| Solomon Temple Dedicate (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_TEMPLE_DEDICATE` | 4 | `theme_1369_solomon_temple_dedicate.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_136_lazarus_raise.json` |
| Widow Oil Multiply (Track B) | 시편 119:105 | `ANCHOR_WIDOW_OIL_MULTIPLY` | 4 | `theme_1370_widow_oil_multiply.json` |
| Elisha Shunammite Room (Track B) | 시편 119:105 | `ANCHOR_ELISHA_SHUNAMMITE_ROOM` | 4 | `theme_1371_elisha_shunammite_room.json` |
| Naaman Dip Seven Times (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_DIP_SEVEN_TIMES` | 4 | `theme_1372_naaman_dip_seven_times.json` |
| Josiah Book Law Found (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_BOOK_LAW_FOUND` | 4 | `theme_1373_josiah_book_law_found.json` |
| Jeremiah Potter Clay Wheel (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_POTTER_CLAY_WHEEL` | 4 | `theme_1374_jeremiah_potter_clay_wheel.json` |
| Ezekiel Dry Bones Breath (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_DRY_BONES_BREATH` | 4 | `theme_1375_ezekiel_dry_bones_breath.json` |
| Daniel Lions Mouths Shut (Track B) | 시편 119:105 | `ANCHOR_DANIEL_LIONS_MOUTHS_SHUT` | 4 | `theme_1376_daniel_lions_mouths_shut.json` |
| Fiery Furnace Fourth Man (Track B) | 시편 119:105 | `ANCHOR_FIERY_FURNACE_FOURTH_MAN` | 4 | `theme_1377_fiery_furnace_fourth_man.json` |
| Belshazzar Handwriting Wall (Track B) | 시편 119:105 | `ANCHOR_BELSHAZZAR_HANDWRITING_WALL` | 4 | `theme_1378_belshazzar_handwriting_wall.json` |
| Job Ash Heap Patience (Track B) | 시편 119:105 | `ANCHOR_JOB_ASH_HEAP_PATIENCE` | 4 | `theme_1379_job_ash_heap_patience.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_137_mary_martha_serve.json` |
| Psalm Shepherd Valley (Track B) | 시편 119:105 | `ANCHOR_PSALM_SHEPHERD_VALLEY` | 4 | `theme_1380_psalm_shepherd_valley.json` |
| Proverbs Ant Go Wise (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_ANT_GO_WISE` | 4 | `theme_1381_proverbs_ant_go_wise.json` |
| Ecclesiastes Seasons Turn (Track B) | 시편 119:105 | `ANCHOR_ECCLESIASTES_SEASONS_TURN` | 4 | `theme_1382_ecclesiastes_seasons_turn.json` |
| Song Vineyard Locked (Track B) | 시편 119:105 | `ANCHOR_SONG_VINEYARD_LOCKED` | 4 | `theme_1383_song_vineyard_locked.json` |
| Isaiah Coal Lips (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_COAL_LIPS` | 4 | `theme_1384_isaiah_coal_lips.json` |
| Joel Spirit Poured Out (Track B) | 시편 119:105 | `ANCHOR_JOEL_SPIRIT_POURED_OUT` | 4 | `theme_1385_joel_spirit_poured_out.json` |
| Amos Plumb Line Straight (Track B) | 시편 119:105 | `ANCHOR_AMOS_PLUMB_LINE_STRAIGHT` | 4 | `theme_1386_amos_plumb_line_straight.json` |
| Obadiah Edom Pride Fall (Track B) | 시편 119:105 | `ANCHOR_OBADIAH_EDOM_PRIDE_FALL` | 4 | `theme_1387_obadiah_edom_pride_fall.json` |
| Jonah Fish Three Days (Track B) | 시편 119:105 | `ANCHOR_JONAH_FISH_THREE_DAYS` | 4 | `theme_1388_jonah_fish_three_days.json` |
| Micah Swords Into Plowshares (Track B) | 시편 119:105 | `ANCHOR_MICAH_SWORDS_INTO_PLOWSHARES` | 4 | `theme_1389_micah_swords_into_plowshares.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_138_wedding_cana.json` |
| Habakkuk Faith Wait (Track B) | 시편 119:105 | `ANCHOR_HABAKKUK_FAITH_WAIT` | 4 | `theme_1390_habakkuk_faith_wait.json` |
| Haggai Consider Your Ways (Track B) | 시편 119:105 | `ANCHOR_HAGGAI_CONSIDER_YOUR_WAYS` | 4 | `theme_1391_haggai_consider_your_ways.json` |
| Malachi Storehouse Rob (Track B) | 시편 119:105 | `ANCHOR_MALACHI_STOREHOUSE_ROB` | 4 | `theme_1392_malachi_storehouse_rob.json` |
| Matthew Beatitudes Mourn (Track B) | 시편 119:105 | `ANCHOR_MATTHEW_BEATITUDES_MOURN` | 4 | `theme_1393_matthew_beatitudes_mourn.json` |
| Mark Storm Stilled Faith (Track B) | 시편 119:105 | `ANCHOR_MARK_STORM_STILLED_FAITH` | 4 | `theme_1394_mark_storm_stilled_faith.json` |
| Luke Prodigal Son Return (Track B) | 시편 119:105 | `ANCHOR_LUKE_PRODIGAL_SON_RETURN` | 4 | `theme_1395_luke_prodigal_son_return.json` |
| Acts Pentecost Wind Fire (Track B) | 시편 119:105 | `ANCHOR_ACTS_PENTECOST_WIND_FIRE` | 4 | `theme_1396_acts_pentecost_wind_fire.json` |
| Romans Abraham Faith Counted (Track B) | 시편 119:105 | `ANCHOR_ROMANS_ABRAHAM_FAITH_COUNTED` | 4 | `theme_1397_romans_abraham_faith_counted.json` |
| Ephesians Armor Belt Truth (Track B) | 시편 119:105 | `ANCHOR_EPHESIANS_ARMOR_BELT_TRUTH` | 4 | `theme_1398_ephesians_armor_belt_truth.json` |
| Philippians Press Toward Prize (Track B) | 시편 119:105 | `ANCHOR_PHILIPPIANS_PRESS_TOWARD_PRIZE` | 4 | `theme_1399_philippians_press_toward_prize.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_139_cleansing_leper.json` |
| 포도원·가지 (Vine and Branches) | 요한복음 15:1 | `ANCHOR_JOHN_15_1` | 4 | `theme_13_vine_branches.json` |
| Colossians Christ Supreme (Track B) | 시편 119:105 | `ANCHOR_COLOSSIANS_CHRIST_SUPREME` | 4 | `theme_1400_colossians_christ_supreme.json` |
| Hebrews Faith Cloud Witnesses (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_FAITH_CLOUD_WITNESSES` | 4 | `theme_1401_hebrews_faith_cloud_witnesses.json` |
| James Tongue Rudder Ship (Track B) | 시편 119:105 | `ANCHOR_JAMES_TONGUE_RUDDER_SHIP` | 4 | `theme_1402_james_tongue_rudder_ship.json` |
| Peter Feed My Sheep (Track B) | 시편 119:105 | `ANCHOR_PETER_FEED_MY_SHEEP` | 4 | `theme_1403_peter_feed_my_sheep.json` |
| John Love One Another (Track B) | 시편 119:105 | `ANCHOR_JOHN_LOVE_ONE_ANOTHER` | 4 | `theme_1404_john_love_one_another.json` |
| 어린 양 보좌 중심 (Revelation Lamb Throne Center) | 요한계시록 5:6 | `ANCHOR_REVELATION_LAMB_THRONE_CENTER` | 4 | `theme_1405_revelation_lamb_throne_center.json` |
| Seven Seals Scroll (Track B) | 시편 119:105 | `ANCHOR_SEVEN_SEALS_SCROLL` | 4 | `theme_1406_seven_seals_scroll.json` |
| 네 기수 (Four Horsemen Apocalypse) | 요한계시록 6:2-8 | `ANCHOR_FOUR_HORSEMEN_APOCALYPSE` | 4 | `theme_1407_four_horsemen_apocalypse.json` |
| 새 예루살렘 성전 없음 (New Jerusalem No Temple) | 요한계시록 21:22 | `ANCHOR_NEW_JERUSALEM_NO_TEMPLE` | 4 | `theme_1408_new_jerusalem_no_temple.json` |
| Nativity Manger Shepherds (Track B) | 시편 119:105 | `ANCHOR_NATIVITY_MANGER_SHEPHERDS` | 4 | `theme_1409_nativity_manger_shepherds.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_140_sermon_mount.json` |
| Flight Egypt Herod Warning (Track B) | 시편 119:105 | `ANCHOR_FLIGHT_EGYPT_HEROD_WARNING` | 4 | `theme_1410_flight_egypt_herod_warning.json` |
| Baptism Jordan Dove Voice (Track B) | 시편 119:105 | `ANCHOR_BAPTISM_JORDAN_DOVE_VOICE` | 4 | `theme_1411_baptism_jordan_dove_voice.json` |
| Last Supper Bread Cup (Track B) | 시편 119:105 | `ANCHOR_LAST_SUPPER_BREAD_CUP` | 4 | `theme_1412_last_supper_bread_cup.json` |
| Gethsemane Cup Pass (Track B) | 시편 119:105 | `ANCHOR_GETHSEMANE_CUP_PASS` | 4 | `theme_1413_gethsemane_cup_pass.json` |
| Betrayal Kiss Garden (Track B) | 시편 119:105 | `ANCHOR_BETRAYAL_KISS_GARDEN` | 4 | `theme_1414_betrayal_kiss_garden.json` |
| Pilate Wash Hands (Track B) | 시편 119:105 | `ANCHOR_PILATE_WASH_HANDS` | 4 | `theme_1415_pilate_wash_hands.json` |
| Crown Thorns Mockery (Track B) | 시편 119:105 | `ANCHOR_CROWN_THORNS_MOCKERY` | 4 | `theme_1416_crown_thorns_mockery.json` |
| Darkness Noon Cross (Track B) | 시편 119:105 | `ANCHOR_DARKNESS_NOON_CROSS` | 4 | `theme_1417_darkness_noon_cross.json` |
| Tomb Stone Rolled Away (Track B) | 시편 119:105 | `ANCHOR_TOMB_STONE_ROLLED_AWAY` | 4 | `theme_1418_tomb_stone_rolled_away.json` |
| Emmaus Breaking Bread (Track B) | 시편 119:105 | `ANCHOR_EMMAUS_BREAKING_BREAD` | 4 | `theme_1419_emmaus_breaking_bread.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_141_denarius_vineyard.json` |
| Thomas See Wounds (Track B) | 시편 119:105 | `ANCHOR_THOMAS_SEE_WOUNDS` | 4 | `theme_1420_thomas_see_wounds.json` |
| Pentecost Tongues Flame (Track B) | 시편 119:105 | `ANCHOR_PENTECOST_TONGUES_FLAME` | 4 | `theme_1421_pentecost_tongues_flame.json` |
| Creation Light First Day (Track B) | 시편 119:105 | `ANCHOR_CREATION_LIGHT_FIRST_DAY` | 4 | `theme_1422_creation_light_first_day.json` |
| Sabbath Rest Seventh (Track B) | 시편 119:105 | `ANCHOR_SABBATH_REST_SEVENTH` | 4 | `theme_1423_sabbath_rest_seventh.json` |
| Flood Covenant Rainbow Sign (Track B) | 시편 119:105 | `ANCHOR_FLOOD_COVENANT_RAINBOW_SIGN` | 4 | `theme_1424_flood_covenant_rainbow_sign.json` |
| Abraham Stars Sand Sea (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_STARS_SAND_SEA` | 4 | `theme_1425_abraham_stars_sand_sea.json` |
| Jacob Ladder Angels (Track B) | 시편 119:105 | `ANCHOR_JACOB_LADDER_ANGELS` | 4 | `theme_1426_jacob_ladder_angels.json` |
| Joseph Dreams Interpret (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_DREAMS_INTERPRET` | 4 | `theme_1427_joseph_dreams_interpret.json` |
| Moses Tablets Broken (Track B) | 시편 119:105 | `ANCHOR_MOSES_TABLETS_BROKEN` | 4 | `theme_1428_moses_tablets_broken.json` |
| Balaam Ass Speaks (Track B) | 시편 119:105 | `ANCHOR_BALAAM_ASS_SPEAKS` | 4 | `theme_1429_balaam_ass_speaks.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_142_wheat_tares.json` |
| Jericho Trumpets Shout (Track B) | 시편 119:105 | `ANCHOR_JERICHO_TRUMPETS_SHOUT` | 4 | `theme_1430_jericho_trumpets_shout.json` |
| Samson Delilah Betray (Track B) | 시편 119:105 | `ANCHOR_SAMSON_DELILAH_BETRAY` | 4 | `theme_1431_samson_delilah_betray.json` |
| Elijah Carmel Fire Falls (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_CARMEL_FIRE_FALLS` | 4 | `theme_1432_elijah_carmel_fire_falls.json` |
| Eden River Four Heads (Track B) | 시편 119:105 | `ANCHOR_EDEN_RIVER_FOUR_HEADS` | 4 | `theme_1433_eden_river_four_heads.json` |
| Garden Till Ground (Track B) | 시편 119:105 | `ANCHOR_GARDEN_TILL_GROUND` | 4 | `theme_1434_garden_till_ground.json` |
| Cain Abel Altars (Track B) | 시편 119:105 | `ANCHOR_CAIN_ABEL_ALTARS` | 4 | `theme_1435_cain_abel_altars.json` |
| Seth Enosh Call (Track B) | 시편 119:105 | `ANCHOR_SETH_ENOSH_CALL` | 4 | `theme_1436_seth_enosh_call.json` |
| Enoch Walked God Taken (Track B) | 시편 119:105 | `ANCHOR_ENOCH_WALKED_GOD_TAKEN` | 4 | `theme_1437_enoch_walked_god_taken.json` |
| Adam Formed Dust (Track B) | 시편 119:105 | `ANCHOR_ADAM_FORMED_DUST` | 4 | `theme_1438_adam_formed_dust.json` |
| Eve Rib Bone (Track B) | 시편 119:105 | `ANCHOR_EVE_RIB_BONE` | 4 | `theme_1439_eve_rib_bone.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_143_lost_coin.json` |
| Cain Mark Wanderer (Track B) | 시편 119:105 | `ANCHOR_CAIN_MARK_WANDERER` | 4 | `theme_1440_cain_mark_wanderer.json` |
| Abel Blood Cries (Track B) | 시편 119:105 | `ANCHOR_ABEL_BLOOD_CRIES` | 4 | `theme_1441_abel_blood_cries.json` |
| Enoch Translation Heaven (Track B) | 시편 119:105 | `ANCHOR_ENOCH_TRANSLATION_HEAVEN` | 4 | `theme_1442_enoch_translation_heaven.json` |
| Noah Dove Olive Leaf (Track B) | 시편 119:105 | `ANCHOR_NOAH_DOVE_OLIVE_LEAF` | 4 | `theme_1443_noah_dove_olive_leaf.json` |
| Abraham Tent Oaks (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_TENT_OAKS` | 4 | `theme_1444_abraham_tent_oaks.json` |
| Melchizedek Bread Wine (Track B) | 시편 119:105 | `ANCHOR_MELCHIZEDEK_BREAD_WINE` | 4 | `theme_1445_melchizedek_bread_wine.json` |
| Hagar Well Angel (Track B) | 시편 119:105 | `ANCHOR_HAGAR_WELL_ANGEL` | 4 | `theme_1446_hagar_well_angel.json` |
| Isaac Wells Gerar (Track B) | 시편 119:105 | `ANCHOR_ISAAC_WELLS_GERAR` | 4 | `theme_1447_isaac_wells_gerar.json` |
| Leah Tender Eyes (Track B) | 시편 119:105 | `ANCHOR_LEAH_TENDER_EYES` | 4 | `theme_1448_leah_tender_eyes.json` |
| Judah Lion Whelp (Track B) | 시편 119:105 | `ANCHOR_JUDAH_LION_WHELP` | 4 | `theme_1449_judah_lion_whelp.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_144_prodigal_son.json` |
| Benjamin Wolf Night (Track B) | 시편 119:105 | `ANCHOR_BENJAMIN_WOLF_NIGHT` | 4 | `theme_1450_benjamin_wolf_night.json` |
| Dan Serpent Trail (Track B) | 시편 119:105 | `ANCHOR_DAN_SERPENT_TRAIL` | 4 | `theme_1451_dan_serpent_trail.json` |
| Naphtali Doe Free (Track B) | 시편 119:105 | `ANCHOR_NAPHTALI_DOE_FREE` | 4 | `theme_1452_naphtali_doe_free.json` |
| Issachar Strong Donkey (Track B) | 시편 119:105 | `ANCHOR_ISSACHAR_STRONG_DONKEY` | 4 | `theme_1453_issachar_strong_donkey.json` |
| Zebulun Haven Harbor (Track B) | 시편 119:105 | `ANCHOR_ZEBULUN_HAVEN_HARBOR` | 4 | `theme_1454_zebulun_haven_harbor.json` |
| Asher Bread Kingly (Track B) | 시편 119:105 | `ANCHOR_ASHER_BREAD_KINGLY` | 4 | `theme_1455_asher_bread_kingly.json` |
| Gad Raider Troop (Track B) | 시편 119:105 | `ANCHOR_GAD_RAIDER_TROOP` | 4 | `theme_1456_gad_raider_troop.json` |
| Simeon Sword Violent (Track B) | 시편 119:105 | `ANCHOR_SIMEON_SWORD_VIOLENT` | 4 | `theme_1457_simeon_sword_violent.json` |
| Reuben Unstable Water (Track B) | 시편 119:105 | `ANCHOR_REUBEN_UNSTABLE_WATER` | 4 | `theme_1458_reuben_unstable_water.json` |
| Moses Reed Basket (Track B) | 시편 119:105 | `ANCHOR_MOSES_REED_BASKET` | 4 | `theme_1459_moses_reed_basket.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_145_cursed_fig_tree.json` |
| Aaron Rod Budded (Track B) | 시편 119:105 | `ANCHOR_AARON_ROD_BUDDED` | 4 | `theme_1460_aaron_rod_budded.json` |
| Pharaoh Dreams Cows (Track B) | 시편 119:105 | `ANCHOR_PHARAOH_DREAMS_COWS` | 4 | `theme_1461_pharaoh_dreams_cows.json` |
| Plague Darkness Three Days (Track B) | 시편 119:105 | `ANCHOR_PLAGUE_DARKNESS_THREE_DAYS` | 4 | `theme_1462_plague_darkness_three_days.json` |
| Firstborn Passover Death (Track B) | 시편 119:105 | `ANCHOR_FIRSTBORN_PASSOVER_DEATH` | 4 | `theme_1463_firstborn_passover_death.json` |
| Manna Quail Complaint (Track B) | 시편 119:105 | `ANCHOR_MANNA_QUAIL_COMPLAINT` | 4 | `theme_1464_manna_quail_complaint.json` |
| Calf Worship Dance (Track B) | 시편 119:105 | `ANCHOR_CALF_WORSHIP_DANCE` | 4 | `theme_1465_calf_worship_dance.json` |
| Covenant Tablets Renewed (Track B) | 시편 119:105 | `ANCHOR_COVENANT_TABLETS_RENEWED` | 4 | `theme_1466_covenant_tablets_renewed.json` |
| Spies Bad Report Fear (Track B) | 시편 119:105 | `ANCHOR_SPIES_BAD_REPORT_FEAR` | 4 | `theme_1467_spies_bad_report_fear.json` |
| Sun Stood Gibeon (Track B) | 시편 119:105 | `ANCHOR_SUN_STOOD_GIBEON` | 4 | `theme_1468_sun_stood_gibeon.json` |
| Deborah Palm Judge (Track B) | 시편 119:105 | `ANCHOR_DEBORAH_PALM_JUDGE` | 4 | `theme_1469_deborah_palm_judge.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_146_lazarus_raise.json` |
| Jephthah Vow Daughter (Track B) | 시편 119:105 | `ANCHOR_JEPHTHAH_VOW_DAUGHTER` | 4 | `theme_1470_jephthah_vow_daughter.json` |
| Micah Stolen Silver (Track B) | 시편 119:105 | `ANCHOR_MICAH_STOLEN_SILVER` | 4 | `theme_1471_micah_stolen_silver.json` |
| Eli Ichabod Glory Departed (Track B) | 시편 119:105 | `ANCHOR_ELI_ICHABOD_GLORY_DEPARTED` | 4 | `theme_1472_eli_ichabod_glory_departed.json` |
| Saul Tall Shoulders (Track B) | 시편 119:105 | `ANCHOR_SAUL_TALL_SHOULDERS` | 4 | `theme_1473_saul_tall_shoulders.json` |
| Absalom Hair Oak (Track B) | 시편 119:105 | `ANCHOR_ABSALOM_HAIR_OAK` | 4 | `theme_1474_absalom_hair_oak.json` |
| Gehazi Leprosy Greed (Track B) | 시편 119:105 | `ANCHOR_GEHAZI_LEPROSY_GREED` | 4 | `theme_1475_gehazi_leprosy_greed.json` |
| Manasseh Altar High Places (Track B) | 시편 119:105 | `ANCHOR_MANASSEH_ALTAR_HIGH_PLACES` | 4 | `theme_1476_manasseh_altar_high_places.json` |
| Jeremiah Linen Belt Rot (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_LINEN_BELT_ROT` | 4 | `theme_1477_jeremiah_linen_belt_rot.json` |
| Ezekiel Scroll Eat Sweet (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_SCROLL_EAT_SWEET` | 4 | `theme_1478_ezekiel_scroll_eat_sweet.json` |
| Shadrach Meshach Abednego (Track B) | 시편 119:105 | `ANCHOR_SHADRACH_MESHACH_ABEDNEGO` | 4 | `theme_1479_shadrach_meshach_abednego.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_147_mary_martha_serve.json` |
| Writing Mene Tekel (Track B) | 시편 119:105 | `ANCHOR_WRITING_MENE_TEKEL` | 4 | `theme_1480_writing_mene_tekel.json` |
| Ezra Mixed Marriage Reform (Track B) | 시편 119:105 | `ANCHOR_EZRA_MIXED_MARRIAGE_REFORM` | 4 | `theme_1481_ezra_mixed_marriage_reform.json` |
| Mordecai Gate Sackcloth (Track B) | 시편 119:105 | `ANCHOR_MORDECAI_GATE_SACKCLOTH` | 4 | `theme_1482_mordecai_gate_sackcloth.json` |
| Psalm Twenty Three Rod Staff (Track B) | 시편 119:105 | `ANCHOR_PSALM_TWENTY_THREE_ROD_STAFF` | 4 | `theme_1483_psalm_twenty_three_rod_staff.json` |
| Proverbs Thirty One Woman (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_THIRTY_ONE_WOMAN` | 4 | `theme_1484_proverbs_thirty_one_woman.json` |
| Ecclesiastes Vanity Wind (Track B) | 시편 119:105 | `ANCHOR_ECCLESIASTES_VANITY_WIND` | 4 | `theme_1485_ecclesiastes_vanity_wind.json` |
| Song Beloved Garden (Track B) | 시편 119:105 | `ANCHOR_SONG_BELOVED_GARDEN` | 4 | `theme_1486_song_beloved_garden.json` |
| Isaiah Immanuel Sign (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_IMMANUEL_SIGN` | 4 | `theme_1487_isaiah_immanuel_sign.json` |
| Lamentations City Weeps (Track B) | 시편 119:105 | `ANCHOR_LAMENTATIONS_CITY_WEEPS` | 4 | `theme_1488_lamentations_city_weeps.json` |
| Ezekiel Temple River Flow (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_TEMPLE_RIVER_FLOW` | 4 | `theme_1489_ezekiel_temple_river_flow.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_148_wedding_cana.json` |
| Hosea Gomer Redeemed (Track B) | 시편 119:105 | `ANCHOR_HOSEA_GOMER_REDEEMED` | 4 | `theme_1490_hosea_gomer_redeemed.json` |
| Joel Locust Army Darkness (Track B) | 시편 119:105 | `ANCHOR_JOEL_LOCUST_ARMY_DARKNESS` | 4 | `theme_1491_joel_locust_army_darkness.json` |
| Micah Bethlehem Ruler Small (Track B) | 시편 119:105 | `ANCHOR_MICAH_BETHLEHEM_RULER_SMALL` | 4 | `theme_1492_micah_bethlehem_ruler_small.json` |
| Zephaniah Day Wrath Silence (Track B) | 시편 119:105 | `ANCHOR_ZEPHANIAH_DAY_WRATH_SILENCE` | 4 | `theme_1493_zephaniah_day_wrath_silence.json` |
| Matthew Wise Men Star (Track B) | 시편 119:105 | `ANCHOR_MATTHEW_WISE_MEN_STAR` | 4 | `theme_1494_matthew_wise_men_star.json` |
| Mark Leper Touched Healed (Track B) | 시편 119:105 | `ANCHOR_MARK_LEPER_TOUCHED_HEALED` | 4 | `theme_1495_mark_leper_touched_healed.json` |
| Luke Samaritan Inn Care (Track B) | 시편 119:105 | `ANCHOR_LUKE_SAMARITAN_INN_CARE` | 4 | `theme_1496_luke_samaritan_inn_care.json` |
| John Woman Well Samaria (Track B) | 시편 119:105 | `ANCHOR_JOHN_WOMAN_WELL_SAMARIA` | 4 | `theme_1497_john_woman_well_samaria.json` |
| Acts Lydda Tabitha Raised (Track B) | 시편 119:105 | `ANCHOR_ACTS_LYDDA_TABITHA_RAISED` | 4 | `theme_1498_acts_lydda_tabitha_raised.json` |
| Titus Crete Island Pastor (Track B) | 시편 119:105 | `ANCHOR_TITUS_CRETE_ISLAND_PASTOR` | 4 | `theme_1499_titus_crete_island_pastor.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_149_cleansing_leper.json` |
| 선한 사마리아인 (Good Samaritan) | 누가복음 10:33 | `ANCHOR_LUKE_10_33` | 4 | `theme_14_good_samaritan.json` |
| Jude Contend Apostasy Faith (Track B) | 시편 119:105 | `ANCHOR_JUDE_CONTEND_APOSTASY_FAITH` | 4 | `theme_1500_jude_contend_apostasy_faith.json` |
| Revelation Four Living Creatures (Track B) | 시편 119:105 | `ANCHOR_REVELATION_FOUR_LIVING_CREATURES` | 4 | `theme_1501_revelation_four_living_creatures.json` |
| Twenty Four Elders Thrones (Track B) | 시편 119:105 | `ANCHOR_TWENTY_FOUR_ELDERS_THRONES` | 4 | `theme_1502_twenty_four_elders_thrones.json` |
| White Horse Conqueror (Track B) | 시편 119:105 | `ANCHOR_WHITE_HORSE_CONQUEROR` | 4 | `theme_1503_white_horse_conqueror.json` |
| Red Horse Sword (Track B) | 시편 119:105 | `ANCHOR_RED_HORSE_SWORD` | 4 | `theme_1504_red_horse_sword.json` |
| Black Horse Scales (Track B) | 시편 119:105 | `ANCHOR_BLACK_HORSE_SCALES` | 4 | `theme_1505_black_horse_scales.json` |
| Souls Under Altar Cry (Track B) | 시편 119:105 | `ANCHOR_SOULS_UNDER_ALTAR_CRY` | 4 | `theme_1506_souls_under_altar_cry.json` |
| 144000 Sealed Foreheads (Track B) | 시편 119:105 | `ANCHOR_144000_SEALED_FOREHEADS` | 4 | `theme_1507_144000_sealed_foreheads.json` |
| Great Multitude White Robes (Track B) | 시편 119:105 | `ANCHOR_GREAT_MULTITUDE_WHITE_ROBES` | 4 | `theme_1508_great_multitude_white_robes.json` |
| Beast Sea Ten Horns (Track B) | 시편 119:105 | `ANCHOR_BEAST_SEA_TEN_HORNS` | 4 | `theme_1509_beast_sea_ten_horns.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_150_sermon_mount.json` |
| Beast Earth Lamb Voice (Track B) | 시편 119:105 | `ANCHOR_BEAST_EARTH_LAMB_VOICE` | 4 | `theme_1510_beast_earth_lamb_voice.json` |
| Mark Buy Sell Hand (Track B) | 시편 119:105 | `ANCHOR_MARK_BUY_SELL_HAND` | 4 | `theme_1511_mark_buy_sell_hand.json` |
| Marriage Supper Lamb Invited (Track B) | 시편 119:105 | `ANCHOR_MARRIAGE_SUPPER_LAMB_INVITED` | 4 | `theme_1512_marriage_supper_lamb_invited.json` |
| River Life Clear Crystal (Track B) | 시편 119:105 | `ANCHOR_RIVER_LIFE_CLEAR_CRYSTAL` | 4 | `theme_1513_river_life_clear_crystal.json` |
| Tree Leaves Healing Nations (Track B) | 시편 119:105 | `ANCHOR_TREE_LEAVES_HEALING_NATIONS` | 4 | `theme_1514_tree_leaves_healing_nations.json` |
| No More Tears Death (Track B) | 시편 119:105 | `ANCHOR_NO_MORE_TEARS_DEATH` | 4 | `theme_1515_no_more_tears_death.json` |
| Faithful Witness Amen Come (Track B) | 시편 119:105 | `ANCHOR_FAITHFUL_WITNESS_AMEN_COME` | 4 | `theme_1516_faithful_witness_amen_come.json` |
| Boy Temple Parents Amaze (Track B) | 시편 119:105 | `ANCHOR_BOY_TEMPLE_PARENTS_AMAZE` | 4 | `theme_1517_boy_temple_parents_amaze.json` |
| Wilderness Temptations Three (Track B) | 시편 119:105 | `ANCHOR_WILDERNESS_TEMPTATIONS_THREE` | 4 | `theme_1518_wilderness_temptations_three.json` |
| Sermon On Mount Beatitudes (Track B) | 시편 119:105 | `ANCHOR_SERMON_ON_MOUNT_BEATITUDES` | 4 | `theme_1519_sermon_on_mount_beatitudes.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_151_denarius_vineyard.json` |
| Feeding Five Thousand Loaves (Track B) | 시편 119:105 | `ANCHOR_FEEDING_FIVE_THOUSAND_LOAVES` | 4 | `theme_1520_feeding_five_thousand_loaves.json` |
| Walking On Water Peter (Track B) | 시편 119:105 | `ANCHOR_WALKING_ON_WATER_PETER` | 4 | `theme_1521_walking_on_water_peter.json` |
| Triumphal Entry Palm Branches (Track B) | 시편 119:105 | `ANCHOR_TRIUMPHAL_ENTRY_PALM_BRANCHES` | 4 | `theme_1522_triumphal_entry_palm_branches.json` |
| Foot Washing Upper Room (Track B) | 시편 119:105 | `ANCHOR_FOOT_WASHING_UPPER_ROOM` | 4 | `theme_1523_foot_washing_upper_room.json` |
| Denial Peter Rooster Crow (Track B) | 시편 119:105 | `ANCHOR_DENIAL_PETER_ROOSTER_CROW` | 4 | `theme_1524_denial_peter_rooster_crow.json` |
| Trial Caiaphas Torn Robes (Track B) | 시편 119:105 | `ANCHOR_TRIAL_CAIAPHAS_TORN_ROBES` | 4 | `theme_1525_trial_caiaphas_torn_robes.json` |
| Soldier Pierce Side (Track B) | 시편 119:105 | `ANCHOR_SOLDIER_PIERCE_SIDE` | 4 | `theme_1526_soldier_pierce_side.json` |
| Curtain Temple Torn (Track B) | 시편 119:105 | `ANCHOR_CURTAIN_TEMPLE_TORN` | 4 | `theme_1527_curtain_temple_torn.json` |
| 롯의 아내 소금 기둥 (Lot Wife Pillar Salt) | 창세기 19:26 | `ANCHOR_LOT_WIFE_PILLAR_SALT` | 4 | `theme_1528_lot_wife_pillar_salt.json` |
| Abraham Oath Ceremony (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_OATH_CEREMONY` | 4 | `theme_1529_abraham_oath_ceremony.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_152_wheat_tares.json` |
| Isaac Wells Gerar Dispute (Track B) | 시편 119:105 | `ANCHOR_ISAAC_WELLS_GERAR_DISPUTE` | 4 | `theme_1530_isaac_wells_gerar_dispute.json` |
| Jacob Peeled Rods Streaks (Track B) | 시편 119:105 | `ANCHOR_JACOB_PEELED_RODS_STREAKS` | 4 | `theme_1531_jacob_peeled_rods_streaks.json` |
| Judah Tamar Justice (Track B) | 시편 119:105 | `ANCHOR_JUDAH_TAMAR_JUSTICE` | 4 | `theme_1532_judah_tamar_justice.json` |
| Othniel First Deliverer (Track B) | 시편 119:105 | `ANCHOR_OTHNIEL_FIRST_DELIVERER` | 4 | `theme_1533_othniel_first_deliverer.json` |
| Ehud Left Hand Blade (Track B) | 시편 119:105 | `ANCHOR_EHUD_LEFT_HAND_BLADE` | 4 | `theme_1534_ehud_left_hand_blade.json` |
| Barak Mount Deborah (Track B) | 시편 119:105 | `ANCHOR_BARAK_MOUNT_DEBORAH` | 4 | `theme_1535_barak_mount_deborah.json` |
| Gideon Fleece Dew Test (Track B) | 시편 119:105 | `ANCHOR_GIDEON_FLEECE_DEW_TEST` | 4 | `theme_1536_gideon_fleece_dew_test.json` |
| Samson Riddle Wedding Feast (Track B) | 시편 119:105 | `ANCHOR_SAMSON_RIDDLE_WEDDING_FEAST` | 4 | `theme_1537_samson_riddle_wedding_feast.json` |
| Eli Sons Wicked Judgment (Track B) | 시편 119:105 | `ANCHOR_ELI_SONS_WICKED_JUDGMENT` | 4 | `theme_1538_eli_sons_wicked_judgment.json` |
| David Spares Saul Cave (Track B) | 시편 119:105 | `ANCHOR_DAVID_SPARES_SAUL_CAVE` | 4 | `theme_1539_david_spares_saul_cave.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_153_lost_coin.json` |
| Solomon Wisdom Dream Choice (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_WISDOM_DREAM_CHOICE` | 4 | `theme_1540_solomon_wisdom_dream_choice.json` |
| Queen Sheba Hard Questions (Track B) | 시편 119:105 | `ANCHOR_QUEEN_SHEBA_HARD_QUESTIONS` | 4 | `theme_1541_queen_sheba_hard_questions.json` |
| Elijah Whirlwind Taken Up (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_WHIRLWIND_TAKEN_UP` | 4 | `theme_1542_elijah_whirlwind_taken_up.json` |
| Naaman Gehazi Leprosy (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_GEHAZI_LEPROSY` | 4 | `theme_1543_naaman_gehazi_leprosy.json` |
| Hezekiah Plague Angel (Track B) | 시편 119:105 | `ANCHOR_HEZEKIAH_PLAGUE_ANGEL` | 4 | `theme_1544_hezekiah_plague_angel.json` |
| Josiah Passover Greatest (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_PASSOVER_GREATEST` | 4 | `theme_1545_josiah_passover_greatest.json` |
| Ezekiel Wheels Within Wheels (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_WHEELS_WITHIN_WHEELS` | 4 | `theme_1546_ezekiel_wheels_within_wheels.json` |
| Daniel Writing Wall Mene (Track B) | 시편 119:105 | `ANCHOR_DANIEL_WRITING_WALL_MENE` | 4 | `theme_1547_daniel_writing_wall_mene.json` |
| Esther Haman Gallows Fifty (Track B) | 시편 119:105 | `ANCHOR_ESTHER_HAMAN_GALLOWS_FIFTY` | 4 | `theme_1548_esther_haman_gallows_fifty.json` |
| Job Friends Debate Ashes (Track B) | 시편 119:105 | `ANCHOR_JOB_FRIENDS_DEBATE_ASHES` | 4 | `theme_1549_job_friends_debate_ashes.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_154_prodigal_son.json` |
| Psalm One Delight Law (Track B) | 시편 119:105 | `ANCHOR_PSALM_ONE_DELIGHT_LAW` | 4 | `theme_1550_psalm_one_delight_law.json` |
| Proverbs Woman Excellent Wife (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_WOMAN_EXCELLENT_WIFE` | 4 | `theme_1551_proverbs_woman_excellent_wife.json` |
| Thessalonians Day Lord Thief (Track B) | 시편 119:105 | `ANCHOR_THESSALONIANS_DAY_LORD_THIEF` | 4 | `theme_1552_thessalonians_day_lord_thief.json` |
| Timothy Stir Up Gift (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_STIR_UP_GIFT` | 4 | `theme_1553_timothy_stir_up_gift.json` |
| Smyrna Poverty Rich (Track B) | 시편 119:105 | `ANCHOR_SMYRNA_POVERTY_RICH` | 4 | `theme_1554_smyrna_poverty_rich.json` |
| Laodicea Lukewarm Spit (Track B) | 시편 119:105 | `ANCHOR_LAODICEA_LUKEWARM_SPIT` | 4 | `theme_1555_laodicea_lukewarm_spit.json` |
| Philadelphia Open Door (Track B) | 시편 119:105 | `ANCHOR_PHILADELPHIA_OPEN_DOOR` | 4 | `theme_1556_philadelphia_open_door.json` |
| 생명나무 열매 (Tree Of Life Monthly Fruit) | 요한계시록 22:2 | `ANCHOR_TREE_OF_LIFE_MONTHLY_FRUIT` | 4 | `theme_1557_tree_of_life_monthly_fruit.json` |
| Moses Bronze Serpent Lift (Track B) | 시편 119:105 | `ANCHOR_MOSES_BRONZE_SERPENT_LIFT` | 4 | `theme_1558_moses_bronze_serpent_lift.json` |
| Aaron Rod Swallow Snakes (Track B) | 시편 119:105 | `ANCHOR_AARON_ROD_SWALLOW_SNAKES` | 4 | `theme_1559_aaron_rod_swallow_snakes.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_155_cursed_fig_tree.json` |
| Joshua Circumcision Gilgal (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_CIRCUMCISION_GILGAL` | 4 | `theme_1560_joshua_circumcision_gilgal.json` |
| Ruth Kinsman Redeemer (Track B) | 시편 119:105 | `ANCHOR_RUTH_KINSMAN_REDEEMER` | 4 | `theme_1561_ruth_kinsman_redeemer.json` |
| Boaz Sandal Transaction (Track B) | 시편 119:105 | `ANCHOR_BOAZ_SANDAL_TRANSACTION` | 4 | `theme_1562_boaz_sandal_transaction.json` |
| Hannah Prayed Eli Mistook (Track B) | 시편 119:105 | `ANCHOR_HANNAH_PRAYED_ELI_MISTOOK` | 4 | `theme_1563_hannah_prayed_eli_mistook.json` |
| Saul Prophesying Naked (Track B) | 시편 119:105 | `ANCHOR_SAUL_PROPHESYING_NAKED` | 4 | `theme_1564_saul_prophesying_naked.json` |
| David Danced Ark Return (Track B) | 시편 119:105 | `ANCHOR_DAVID_DANCED_ARK_RETURN` | 4 | `theme_1565_david_danced_ark_return.json` |
| Solomon Two Mothers Sword (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_TWO_MOTHERS_SWORD` | 4 | `theme_1566_solomon_two_mothers_sword.json` |
| 나사로 부활 (Lazarus Raised) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_156_lazarus_raise.json` |
| 마리아와 마르다 (Mary and Martha) | 누가복음 10:42 | `ANCHOR_LUK_10_42` | 4 | `theme_157_mary_martha_serve.json` |
| 가나 혼인 (Wedding at Cana) | 요한복음 2:3 | `ANCHOR_JHN_2_3` | 4 | `theme_158_wedding_cana.json` |
| 문둥병 정결 (Cleansing Leper) | 마가복음 1:41 | `ANCHOR_MRK_1_41` | 4 | `theme_159_cleansing_leper.json` |
| 잃은 양 (Lost Sheep) | 누가복음 15:4 | `ANCHOR_LUKE_15_4` | 4 | `theme_15_lost_sheep.json` |
| 산상수훈 (Sermon on the Mount) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_160_sermon_mount.json` |
| 포도원 하루 품삯 (Denarius Vineyard) | 마태복음 20:13 | `ANCHOR_MAT_20_13` | 4 | `theme_161_denarius_vineyard.json` |
| 밀과 가라지 (Wheat and Tares) | 마태복음 13:30 | `ANCHOR_MAT_13_30` | 4 | `theme_162_wheat_tares.json` |
| 잃은 드라크마 (Lost Coin) | 누가복음 15:9 | `ANCHOR_LUK_15_9` | 4 | `theme_163_lost_coin.json` |
| 탕자 아들 (Prodigal Son) | 누가복음 15:24 | `ANCHOR_LUK_15_24` | 4 | `theme_164_prodigal_son.json` |
| 무화과나무 저주 (Cursed Fig Tree) | 마가복음 11:14 | `ANCHOR_MRK_11_14` | 4 | `theme_165_cursed_fig_tree.json` |
| 삼손 힘 (Samson Strength) | 사사기 16:28 | `ANCHOR_JDG_16_28` | 4 | `theme_166_samson_strength.json` |
| 라합 홍색 줄 (Rahab Scarlet Cord) | 여호수아 2:18 | `ANCHOR_JOS_2_18` | 4 | `theme_167_rahab_scarlet.json` |
| 기드온 양털 (Gideon Fleece) | 사사기 6:37 | `ANCHOR_JDG_6_37` | 4 | `theme_168_gideon_fleece.json` |
| 갈멜 바알 (Elijah Carmel) | 열왕기상 18:39 | `ANCHOR_1KI_18_39` | 4 | `theme_169_elijah_carmel.json` |
| 천국 비유 씨 (Kingdom Seed Parable) | 마태복음 13:3 | `ANCHOR_MATT_13_3` | 4 | `theme_16_kingdom_seed.json` |
| 나아만 담금 (Naaman Dip) | 열왕기하 5:14 | `ANCHOR_2KI_5_14` | 4 | `theme_170_naaman_dip.json` |
| 풀무불 도하 (Fiery Furnace) | 다니엘 3:25 | `ANCHOR_DAN_3_25` | 4 | `theme_171_shadrach_furnace.json` |
| 벨사살 손가락 (Belshazzar Handwriting) | 다니엘 5:25 | `ANCHOR_DAN_5_25` | 4 | `theme_172_belshazzar_hand.json` |
| 요나 박 넝쿨 (Jonah Gourd) | 요나 4:10 | `ANCHOR_JON_4_10` | 4 | `theme_173_jonah_gourd.json` |
| 하박국 망대 (Habakkuk Watch) | 하박국 2:1 | `ANCHOR_HAB_2_1` | 4 | `theme_174_habakkuk_watch.json` |
| 아모스 수평 (Amos Plumb Line) | 아모스 7:8 | `ANCHOR_AMO_7_8` | 4 | `theme_175_amos_plumb_line.json` |
| 호세아 구속 (Hosea Redemption) | 호세아 3:1 | `ANCHOR_HOS_3_1` | 4 | `theme_176_hosea_redemption.json` |
| 스가랴 가지 (Zechariah Branch) | 스가랴 6:12 | `ANCHOR_ZEC_6_12` | 4 | `theme_177_zechariah_branch.json` |
| 말라기 십일조 (Malachi Tithe) | 말라기 3:10 | `ANCHOR_MAL_3_10` | 4 | `theme_178_malachi_tithe.json` |
| 임마누엘 표적 (Immanuel Sign) | 이사야 7:14 | `ANCHOR_ISA_7_14` | 4 | `theme_179_isaiah_virgin_sign.json` |
| 감람산 기도 (Olive Mount Prayer) | 누가복음 22:41 | `ANCHOR_LUKE_22_41` | 4 | `theme_17_olive_mount_prayer.json` |
| 고난받는 종 (Suffering Servant) | 이사야 53:5 | `ANCHOR_ISA_53_5` | 4 | `theme_180_suffering_servant.json` |
| 마른 뼈 골짜기 (Valley Dry Bones) | 에스겔 37:5 | `ANCHOR_EZE_37_5` | 4 | `theme_181_valley_dry_bones.json` |
| 보아스 구속 (Boaz Kinsman) | 룻기 4:9 | `ANCHOR_RUT_4_9` | 4 | `theme_182_boaz_kinsman.json` |
| 에스더 순교 (Esther Purim) | 에스더 4:16 | `ANCHOR_EST_4_16` | 4 | `theme_183_esther_purim.json` |
| 모르드개 망대 (Mordecai Stand) | 에스더 8:2 | `ANCHOR_EST_8_2` | 4 | `theme_184_mordecai_stand.json` |
| 에스라 율법 (Ezra Scroll) | 에스라 7:10 | `ANCHOR_EZR_7_10` | 4 | `theme_185_ezra_scroll.json` |
| 욥 인내 (Job Patience) | 욥기 1:21 | `ANCHOR_JOB_1_21` | 4 | `theme_186_job_patience.json` |
| 발람 나귀 (Balaam Donkey) | 민수기 22:28 | `ANCHOR_NUM_22_28` | 4 | `theme_187_balaam_donkey.json` |
| 놋뱀 표준 (Bronze Serpent) | 민수기 21:9 | `ANCHOR_NUM_21_9` | 4 | `theme_188_bronze_serpent.json` |
| 여호수아 해 (Joshua Sun) | 여호수아 10:13 | `ANCHOR_JOS_10_13` | 4 | `theme_189_joshua_sun.json` |
| 감옥·사슬 (Prison and Chains) | 사도행전 16:26 | `ANCHOR_ACTS_16_26` | 4 | `theme_18_prison_chains.json` |
| 금송아지 (Golden Calf) | 출애굽기 32:4 | `ANCHOR_EXO_32_4` | 4 | `theme_190_golden_calf.json` |
| 유월절 어린양 (Passover Lamb) | 출애굽기 12:13 | `ANCHOR_EXO_12_13` | 4 | `theme_191_passover_lamb.json` |
| 홍해 건넘 (Red Sea Crossing) | 출애굽기 14:21 | `ANCHOR_EXO_14_21` | 4 | `theme_192_red_sea.json` |
| 야곱 사다리 (Jacob Ladder) | 창세기 28:12 | `ANCHOR_GEN_28_12` | 4 | `theme_193_jacob_ladder.json` |
| 에스겔 바퀴 (Ezekiel Wheels) | 에스겔 1:16 | `ANCHOR_EZE_1_16` | 4 | `theme_194_ezekiel_wheel.json` |
| 바벨 탑 (Tower of Babel) | 창세기 11:4 | `ANCHOR_GEN_11_4` | 4 | `theme_195_tower_babel.json` |
| 아벨 피 (Abel Blood) | 창세기 4:10 | `ANCHOR_GEN_4_10` | 4 | `theme_196_abel_blood.json` |
| 가인 표 (Cain Mark) | 창세기 4:15 | `ANCHOR_GEN_4_15` | 4 | `theme_197_cain_mark.json` |
| 에녹 동행 (Enoch Walk) | 창세기 5:24 | `ANCHOR_GEN_5_24` | 4 | `theme_198_enoch_walk.json` |
| 멜기세덱 빵 (Melchizedek Bread) | 창세기 14:18 | `ANCHOR_GEN_14_18` | 4 | `theme_199_melchizedek_bread.json` |
| 부활·첫열매 (Resurrection Firstfruits) | 고린도전서 15:20 | `ANCHOR_1COR_15_20` | 4 | `theme_19_resurrection_firstfruits.json` |
| 아브라함 번제 (Abraham Sacrifice) | 창세기 22:8 | `ANCHOR_GEN_22_8` | 4 | `theme_200_abraham_sacrifice.json` |
| 이삭 우물 (Isaac Wells) | 창세기 26:22 | `ANCHOR_GEN_26_22` | 4 | `theme_201_isaac_wells.json` |
| 바로 완악 (Pharaoh Hardened) | 출애굽기 9:12 | `ANCHOR_EXO_9_12` | 4 | `theme_202_pharaoh_hardened.json` |
| 애굽 재앙 (Plagues of Egypt) | 출애굽기 7:5 | `ANCHOR_EXO_7_5` | 4 | `theme_203_plagues_egypt.json` |
| 구름 기둥 (Pillar Cloud) | 출애굽기 13:21 | `ANCHOR_EXO_13_21` | 4 | `theme_204_pillar_cloud.json` |
| 만나 안식 (Manna Sabbath) | 출애굽기 16:26 | `ANCHOR_EXO_16_26` | 4 | `theme_205_manna_sabbath.json` |
| 고라 반역 (Korah Rebellion) | 민수기 16:32 | `ANCHOR_NUM_16_32` | 4 | `theme_206_korah_rebellion.json` |
| 아론 지팡이 (Aaron Rod) | 민수기 17:8 | `ANCHOR_NUM_17_8` | 4 | `theme_207_aaron_rod.json` |
| 가나안 정탐 (Canaan Spies) | 민수기 13:30 | `ANCHOR_NUM_13_30` | 4 | `theme_208_canaan_spies.json` |
| 언약궤 (Ark of Covenant) | 여호수아 3:13 | `ANCHOR_JOS_3_13` | 4 | `theme_209_ark_covenant.json` |
| 새 예루살렘 (New Jerusalem) | 요한계시록 21:2 | `ANCHOR_REV_21_2` | 4 | `theme_20_new_jerusalem.json` |
| 엘리야 까마귀 (Elijah Raven) | 열왕기상 17:6 | `ANCHOR_1KI_17_6` | 4 | `theme_210_elijah_raven.json` |
| 엘리사 뼈 (Elisha Bones) | 열왕하 13:21 | `ANCHOR_2KI_13_21` | 4 | `theme_211_elisha_bones.json` |
| 히스기야 해시계 (Hezekiah Sundial) | 이사야 38:8 | `ANCHOR_ISA_38_8` | 4 | `theme_212_hezekiah_sundial.json` |
| 요시야 율법책 (Josiah Book) | 열왕하 22:11 | `ANCHOR_2KI_22_11` | 4 | `theme_213_josiah_book.json` |
| 예레미야 토기장 (Jeremiah Potter) | 예레미야 18:6 | `ANCHOR_JER_18_6` | 4 | `theme_214_jeremiah_potter.json` |
| 미가 칼 (Micah Swords) | 미가 4:3 | `ANCHOR_MIC_4_3` | 4 | `theme_215_micah_swords.json` |
| 나훔 니느웨 (Nahum Nineveh) | 나훔 1:8 | `ANCHOR_NAH_1_8` | 4 | `theme_216_nahum_nineveh.json` |
| 스바냐 날 (Zephaniah Day) | 스바냐 1:14 | `ANCHOR_ZEP_1_14` | 4 | `theme_217_zephaniah_day.json` |
| 학개 성전 (Haggai Temple) | 학개 1:8 | `ANCHOR_HAG_1_8` | 4 | `theme_218_haggai_temple.json` |
| 스가랴 말 (Zechariah Horses) | 스가랴 6:5 | `ANCHOR_ZEC_6_5` | 4 | `theme_219_zechariah_horses.json` |
| 요나·폭풍 (Jonah and Storm) | 요나 1:17 | `ANCHOR_JONAH_1_17` | 4 | `theme_21_jonah_storm.json` |
| 세례 요한 (John Baptist) | 마태복음 3:3 | `ANCHOR_MAT_3_3` | 4 | `theme_220_john_baptist.json` |
| 동방 박사 별 (Magi Star) | 마태복음 2:2 | `ANCHOR_MAT_2_2` | 4 | `theme_221_magi_star.json` |
| 애굽 피신 (Flight to Egypt) | 마태복음 2:13 | `ANCHOR_MAT_2_13` | 4 | `theme_222_flight_egypt.json` |
| 광야 시험 (Wilderness Temptation) | 마태복음 4:10 | `ANCHOR_MAT_4_10` | 4 | `theme_223_temptation_wilderness.json` |
| 어리석은 부자 (Rich Fool) | 누가복음 12:20 | `ANCHOR_LUK_12_20` | 4 | `theme_224_rich_fool.json` |
| 나사로 부자 (Lazarus Rich Man) | 누가복음 16:25 | `ANCHOR_LUK_16_25` | 4 | `theme_225_lazarus_rich.json` |
| 포도원 품꾼 (Workers Vineyard) | 마태복음 20:16 | `ANCHOR_MAT_20_16` | 4 | `theme_226_workers_vineyard.json` |
| 악한 농부 (Wicked Tenants) | 마태복음 21:41 | `ANCHOR_MAT_21_41` | 4 | `theme_227_wicked_tenants.json` |
| 감람산 강해 (Olivet Discourse) | 마태복음 24:42 | `ANCHOR_MAT_24_42` | 4 | `theme_228_olivet_discourse.json` |
| 가룟 키스 (Betrayal Kiss) | 마태복음 26:49 | `ANCHOR_MAT_26_49` | 4 | `theme_229_betrayal_kiss.json` |
| 불타는 가시나무 (Burning Bush) | 출애굽기 3:2 | `ANCHOR_EXO_3_2` | 4 | `theme_22_burning_bush.json` |
| 아나니아 삽비라 (Ananias Sapphira) | 사도행전 5:5 | `ANCHOR_ACT_5_5` | 4 | `theme_230_ananias_sapphira.json` |
| 루다 에네아 (Lydda Aeneas) | 사도행전 9:34 | `ANCHOR_ACT_9_34` | 4 | `theme_231_lydda_aeneas.json` |
| 아레오파고 (Mars Hill) | 사도행전 17:23 | `ANCHOR_ACT_17_23` | 4 | `theme_232_mars_hill.json` |
| 오네시모 편지 (Onesimus Letter) | 빌레몬 1:16 | `ANCHOR_PHM_1_16` | 4 | `theme_233_onesimus_letter.json` |
| 사랑 장 (Love Chapter) | 고린도전서 13:8 | `ANCHOR_1CO_13_8` | 4 | `theme_234_love_chapter.json` |
| 성령의 열매 (Fruit of Spirit) | 갈라디아서 5:22 | `ANCHOR_GAL_5_22` | 4 | `theme_235_fruit_spirit.json` |
| 알파와 오메가 (Alpha Omega) | 요한계시록 1:8 | `ANCHOR_REV_1_8` | 4 | `theme_236_revelation_alpha.json` |
| 일곱 교회 (Seven Churches) | 요한계시록 1:11 | `ANCHOR_REV_1_11` | 4 | `theme_237_seven_churches.json` |
| 네 말 (Four Horsemen) | 요한계시록 6:2 | `ANCHOR_REV_6_2` | 4 | `theme_238_four_horsemen.json` |
| 미가엘 전쟁 (Michael War) | 요한계시록 12:7 | `ANCHOR_REV_12_7` | 4 | `theme_239_michael_war.json` |
| 다윗·골리앗 (David and Goliath) | 사무엘상 17:49 | `ANCHOR_1SAM_17_49` | 4 | `theme_23_david_goliath.json` |
| 큰 물고기 (Whale Swallow) | 요나 1:17 | `ANCHOR_JON_1_17` | 4 | `theme_240_whale_swallow.json` |
| 엘리야 회오리 (Elijah Whirlwind) | 열왕기하 2:11 | `ANCHOR_2KI_2_11` | 4 | `theme_241_elijah_whirlwind.json` |
| 게하시 문둥병 (Gehazi Leprosy) | 열왕기하 5:27 | `ANCHOR_2KI_5_27` | 4 | `theme_242_gehazi_leprosy.json` |
| 웃시야 교만 (Uzziah Pride) | 역대하 26:19 | `ANCHOR_2CH_26_19` | 4 | `theme_243_uzziah_pride.json` |
| 솔로몬 우상 (Solomon Idols) | 열왕기상 11:4 | `ANCHOR_1KI_11_4` | 4 | `theme_244_solomon_idols.json` |
| 르호보암 분열 (Rehoboam Split) | 열왕기상 12:16 | `ANCHOR_1KI_12_16` | 4 | `theme_245_rehoboam_split.json` |
| 아합 포도원 (Ahab Vineyard) | 열왕기상 21:19 | `ANCHOR_1KI_21_19` | 4 | `theme_246_ahab_vineyard.json` |
| 이세벨 바알 (Jezebel Baal) | 열왕기상 18:19 | `ANCHOR_1KI_18_19` | 4 | `theme_247_jezebel_baal.json` |
| 외투 전수 (Mantle Pass) | 열왕기하 2:13 | `ANCHOR_2KI_2_13` | 4 | `theme_248_mantle_pass.json` |
| 나아만 종 (Naaman Servant) | 열왕기하 5:13 | `ANCHOR_2KI_5_13` | 4 | `theme_249_naaman_servant.json` |
| 솔로몬 지혜 (Solomon Wisdom) | 열왕기상 3:9 | `ANCHOR_1KINGS_3_9` | 4 | `theme_24_solomon_wisdom.json` |
| 빌라도 씻음 (Pilate Wash) | 마태복음 27:24 | `ANCHOR_MAT_27_24` | 4 | `theme_250_pilate_wash.json` |
| 가시 면류관 (Crown of Thorns) | 마태복음 27:29 | `ANCHOR_MAT_27_29` | 4 | `theme_251_crown_thorns.json` |
| 룻 친족 (Ruth Kinsman) | 룻기 3:9 | `ANCHOR_RUT_3_9` | 4 | `theme_252_ruth_kinsman.json` |
| 기드온 횃불 (Gideon Torches) | 사사기 7:20 | `ANCHOR_JDG_7_20` | 4 | `theme_253_gideon_torches.json` |
| 사울 영 떠남 (Saul Spirit Departed) | 사무엘상 16:14 | `ANCHOR_1SA_16_14` | 4 | `theme_254_saul_spirit_departed.json` |
| 압살롬 머리카락 (Absalom Hair) | 사무엘하 18:9 | `ANCHOR_2SA_18_9` | 4 | `theme_255_absalom_hair.json` |
| 아탈야 왕위 (Athaliah Usurpation) | 열왕기하 11:12 | `ANCHOR_2KI_11_12` | 4 | `theme_256_athaniah_crown.json` |
| 여호야다 왕관 (Jehoiada Crown) | 열왕기하 11:12 | `ANCHOR_2KI_11_12B` | 4 | `theme_257_jehoiada_crown.json` |
| 히스기야 역병 (Hezekiah Plague) | 역대하 32:21 | `ANCHOR_2CH_32_21` | 4 | `theme_258_hezekiah_plague.json` |
| 므낫세 회개 (Manasseh Repentance) | 역대하 33:13 | `ANCHOR_2CH_33_13` | 4 | `theme_259_manasseh_repent.json` |
| 노아 언약 (Noah Covenant) | 창세기 9:13 | `ANCHOR_GEN_9_13` | 4 | `theme_25_noah_covenant.json` |
| 요시야 유월절 (Josiah Passover) | 역대하 35:18 | `ANCHOR_2CH_35_18` | 4 | `theme_260_josiah_passover.json` |
| 벨사살 손가락 글 (Writing on Wall) | 다니엘 5:25 | `ANCHOR_DAN_5_25B` | 4 | `theme_261_daniel_writing_wall.json` |
| 하박국 망대 (Habakkuk Watchtower) | 하박국 2:1 | `ANCHOR_HAB_2_1B` | 4 | `theme_262_habakkuk_watchtower.json` |
| 오바댜 에돔 (Obadiah Edom) | 오바댜 1:15 | `ANCHOR_OBA_1_15` | 4 | `theme_263_obadiah_edom.json` |
| 학개 스룹바벨 (Haggai Zerubbabel) | 학개 2:23 | `ANCHOR_HAG_2_23` | 4 | `theme_264_haggai_zerubbabel.json` |
| 스가랴 촛대 (Zechariah Lampstand) | 스가랴 4:2 | `ANCHOR_ZEC_4_2` | 4 | `theme_265_zechariah_lampstand.json` |
| 말라기 해 (Malachi Sun) | 말라기 4:2 | `ANCHOR_MAL_4_2` | 4 | `theme_266_malachi_sun.json` |
| 발람 신탁 (Balaam Oracle) | 민수기 24:17 | `ANCHOR_NUM_24_17` | 4 | `theme_267_balaam_oracle.json` |
| 고라 땅 삼킴 (Korah Earth) | 민수기 16:32 | `ANCHOR_NUM_16_32` | 4 | `theme_268_korah_earth.json` |
| 아론 지팡이 싹 (Aaron Budding Rod) | 민수기 17:8 | `ANCHOR_NUM_17_8` | 4 | `theme_269_aaron_budding.json` |
| 엘리야 겉옷 (Elijah Mantle) | 열왕기하 2:13 | `ANCHOR_2KINGS_2_13` | 4 | `theme_26_elijah_mantle.json` |
| 여호수아 돌 (Joshua Stones) | 여호수아 4:7 | `ANCHOR_JOS_4_7` | 4 | `theme_270_joshua_stones.json` |
| 바락 드보라 (Barak Deborah) | 사사기 4:14 | `ANCHOR_JDG_4_14` | 4 | `theme_271_barak_deborah.json` |
| 사무엘 기름 (Samuel Anointing) | 사무엘상 16:13 | `ANCHOR_1SA_16_13` | 4 | `theme_272_samuel_anointing.json` |
| 다윗 수금 (David Harp) | 사무엘상 16:23 | `ANCHOR_1SA_16_23` | 4 | `theme_273_david_harp.json` |
| 솔로몬 성전 봉헌 (Solomon Temple Dedication) | 열왕기상 8:10 | `ANCHOR_1KI_8_10` | 4 | `theme_274_solomon_temple_dedic.json` |
| 엘리야 불 (Elijah Fire from Heaven) | 열왕기상 18:38 | `ANCHOR_1KI_18_38B` | 4 | `theme_275_elijah_fire_heaven.json` |
| 나오미 귀환 (Naomi Return) | 룻기 1:16 | `ANCHOR_RUT_1_16` | 4 | `theme_276_naomi_return.json` |
| 에스더 금식 (Esther Fast) | 에스더 4:16 | `ANCHOR_EST_4_16` | 4 | `theme_277_esther_fast.json` |
| 모르드개 문 (Mordecai Gate) | 에스더 2:21 | `ANCHOR_EST_2_21` | 4 | `theme_278_mordecai_gate.json` |
| 느헤미야 술관원 (Nehemiah Cupbearer) | 느헤미야 2:1 | `ANCHOR_NEH_2_1` | 4 | `theme_279_nehemiah_cupbearer.json` |
| 탕자 귀환 (Prodigal Return) | 누가복음 15:20 | `ANCHOR_LUKE_15_20` | 4 | `theme_27_prodigal_return.json` |
| 에스라 금식 (Ezra Fast) | 에스라 8:21 | `ANCHOR_EZR_8_21` | 4 | `theme_280_ezra_fast.json` |
| 욥 친구 (Job Friends) | 욥기 2:11 | `ANCHOR_JOB_2_11` | 4 | `theme_281_job_friends.json` |
| 이사야 숯 (Isaiah Coal) | 이사야 6:6 | `ANCHOR_ISA_6_6` | 4 | `theme_282_isaiah_coal.json` |
| 예레미야 웅덩이 (Jeremiah Cistern) | 예레미야 38:6 | `ANCHOR_JER_38_6` | 4 | `theme_283_jeremiah_cistern.json` |
| 아모스 과일 바구니 (Amos Basket Fruit) | 아모스 8:2 | `ANCHOR_AMO_8_2` | 4 | `theme_284_amos_basket_fruit.json` |
| 미가 베들레헴 (Micah Bethlehem) | 미가 5:2 | `ANCHOR_MIC_5_2` | 4 | `theme_285_micah_bethlehem.json` |
| 나훔 사자 (Nahum Lion) | 나훔 2:11 | `ANCHOR_NAH_2_11` | 4 | `theme_286_nahum_lion.json` |
| 하박국 믿음 (Habakkuk Faith) | 하박국 2:4 | `ANCHOR_HAB_2_4` | 4 | `theme_287_habakkuk_faith.json` |
| 스바냐 노래 (Zephaniah Sing) | 스바냐 3:14 | `ANCHOR_ZEP_3_14` | 4 | `theme_288_zephaniah_sing.json` |
| 야고보 혀 (James Tongue) | 야고보서 3:6 | `ANCHOR_JAS_3_6` | 4 | `theme_289_james_tongue.json` |
| 룻 이삭 줍기 (Ruth Gleaning) | 룻기 2:2 | `ANCHOR_RUTH_2_2` | 4 | `theme_28_ruth_gleaning.json` |
| 유다 투쟁 (Jude Contend) | 유다서 1:3 | `ANCHOR_JUD_1_3` | 4 | `theme_290_jude_contend.json` |
| 계시록 어린양 (Revelation Lamb) | 요한계시록 5:6 | `ANCHOR_REV_5_6` | 4 | `theme_291_revelation_lamb.json` |
| 요나 큰 물고기 (Whale Jonah) | 요나 1:17 | `ANCHOR_JON_1_17B` | 4 | `theme_292_whale_jonah.json` |
| 골리앗 돌 (Goliath Stone) | 사무엘상 17:49 | `ANCHOR_1SA_17_49` | 4 | `theme_293_goliath_stone.json` |
| 보아스 문 (Boaz Gate) | 룻기 4:1 | `ANCHOR_RUT_4_1` | 4 | `theme_294_boaz_gate.json` |
| 엘리야 잔잔한 소리 (Elijah Still Small Voice) | 열왕기상 19:12 | `ANCHOR_1KI_19_12` | 4 | `theme_295_elijah_still_small.json` |
| 모세 불타는 떨기 (Moses Burning Bush) | 출애굽기 3:2 | `ANCHOR_EXO_3_2` | 4 | `theme_296_moses_burning_bush.json` |
| 모세 지팡이 뱀 (Moses Rod Snake) | 출애굽기 4:3 | `ANCHOR_EXO_4_3` | 4 | `theme_297_moses_rod_snake.json` |
| 홍해 건넘 (Red Sea Crossing) | 출애굽기 14:21 | `ANCHOR_EXO_14_21` | 4 | `theme_298_red_sea_cross.json` |
| 바벨 언어 혼잡 (Babel Confusion) | 창세기 11:7 | `ANCHOR_GEN_11_7` | 4 | `theme_299_babel_confusion.json` |
| 에스더 때 (Esther For Such a Time) | 에스더 4:14 | `ANCHOR_ESTH_4_14` | 4 | `theme_29_esther_for_such_time.json` |
| 노아 방주 (Noah Ark) | 창세기 7:1 | `ANCHOR_GEN_7_1` | 4 | `theme_300_noah_ark.json` |
| 노아 무지개 (Noah Rainbow) | 창세기 9:13 | `ANCHOR_GEN_9_13` | 4 | `theme_301_noah_rainbow.json` |
| 아브라함 별 (Abraham Stars) | 창세기 15:5 | `ANCHOR_GEN_15_5` | 4 | `theme_302_abraham_stars.json` |
| 롯 아내 기둥 (Lot Pillar) | 창세기 19:26 | `ANCHOR_GEN_19_26` | 4 | `theme_303_lot_pillar.json` |
| 이삭 축복 (Isaac Blessing) | 창세기 27:27 | `ANCHOR_GEN_27_27` | 4 | `theme_304_isaac_blessing.json` |
| 요셉 옷 (Joseph Coat) | 창세기 37:3 | `ANCHOR_GEN_37_3` | 4 | `theme_305_joseph_coat.json` |
| 만나 메추라기 (Manna Quail) | 출애굽기 16:13 | `ANCHOR_EXO_16_13` | 4 | `theme_306_manna_quail.json` |
| 놋뱀 (Bronze Serpent) | 민수기 21:9 | `ANCHOR_NUM_21_9` | 4 | `theme_307_serpent_bronze.json` |
| 삼손 기둥 (Samson Pillars) | 사사기 16:29 | `ANCHOR_JDG_16_29` | 4 | `theme_308_samson_pillars.json` |
| 엘리사 도끼 뜸 (Elisha Axe Float) | 열왕기하 6:6 | `ANCHOR_2KI_6_6` | 4 | `theme_309_elisha_axe_float.json` |
| 다니엘 사자굴 (Daniel Lions Den) | 다니엘 6:22 | `ANCHOR_DAN_6_22` | 4 | `theme_30_daniel_lions.json` |
| 벨사살 잔치 (Belshazzar Feast) | 다니엘 5:5 | `ANCHOR_DAN_5_5` | 4 | `theme_310_belshazzar_feast.json` |
| 고레스 조서 (Cyrus Decree) | 에스라 1:2 | `ANCHOR_EZR_1_2` | 4 | `theme_311_cyrus_decree.json` |
| 에스더 왕후 (Esther Queen) | 에스더 2:17 | `ANCHOR_EST_2_17` | 4 | `theme_312_esther_queen.json` |
| 하만 나무 (Haman Gallows) | 에스더 7:10 | `ANCHOR_EST_7_10` | 4 | `theme_313_haman_gallows.json` |
| 베드로 물위 걸음 (Peter Walk Water) | 마태복음 14:29 | `ANCHOR_MAT_14_29` | 4 | `theme_314_peter_walk_water.json` |
| 오순절 바람 (Pentecost Wind) | 사도행전 2:2 | `ANCHOR_ACT_2_2` | 4 | `theme_315_pentecost_wind.json` |
| 스데반 돌 (Stephen Stones) | 사도행전 7:59 | `ANCHOR_ACT_7_59` | 4 | `theme_316_stephen_stones.json` |
| 빌립 에티오피아 (Philip Ethiopian) | 사도행전 8:35 | `ANCHOR_ACT_8_35` | 4 | `theme_317_philip_ethiopian.json` |
| 옥중 지진 (Prison Earthquake) | 사도행전 16:26 | `ANCHOR_ACT_16_26` | 4 | `theme_318_prison_earthquake.json` |
| 바울 난파 (Paul Shipwreck) | 사도행전 27:41 | `ANCHOR_ACT_27_41` | 4 | `theme_319_shipwreck_paul.json` |
| 호세아 사랑 (Hosea Loved) | 호세아 11:8 | `ANCHOR_HOS_11_8` | 4 | `theme_31_hosea_loved.json` |
| 바울 가시 (Paul Thorn) | 고린도후서 12:7 | `ANCHOR_2CO_12_7` | 4 | `theme_320_thorn_flesh.json` |
| 하나님의 갑옷 (Armor of God) | 에베소서 6:11 | `ANCHOR_EPH_6_11` | 4 | `theme_321_armor_god.json` |
| 룻 이삭 줍기 (Ruth Glean) | 룻기 2:2 | `ANCHOR_RUT_2_2` | 4 | `theme_322_ruth_glean.json` |
| 한나 기도 (Hannah Prayer) | 사무엘상 1:10 | `ANCHOR_1SA_1_10` | 4 | `theme_323_hannah_prayer.json` |
| 엘리 등불 (Eli Lamp) | 사무엘상 3:3 | `ANCHOR_1SA_3_3` | 4 | `theme_324_eli_lamp.json` |
| 다윗 인구 조사 (David Census) | 역대상 21:1 | `ANCHOR_1CH_21_1` | 4 | `theme_325_census_david.json` |
| 우리아 편지 (Uriah Letter) | 사무엘하 11:15 | `ANCHOR_2SA_11_15` | 4 | `theme_326_uriah_letter.json` |
| 밧세바 지붕 (Bathsheba Roof) | 사무엘하 11:2 | `ANCHOR_2SA_11_2` | 4 | `theme_327_bathsheba_roof.json` |
| 나단 우화 (Nathan Parable) | 사무엘하 12:1 | `ANCHOR_2SA_12_1` | 4 | `theme_328_nathan_parable.json` |
| 시바 여왕 (Queen of Sheba) | 열왕기상 10:2 | `ANCHOR_1KI_10_2` | 4 | `theme_329_queen_sheba.json` |
| 미가 정의 (Micah Justice) | 미가 6:8 | `ANCHOR_MIC_6_8` | 4 | `theme_32_micah_justice.json` |
| 사렙다 과부 (Widow Zarephath) | 열왕기상 17:12 | `ANCHOR_1KI_17_12` | 4 | `theme_330_widow_zarephath.json` |
| 게하시 탐욕 (Gehazi Greed) | 열왕기하 5:27 | `ANCHOR_2KI_5_27` | 4 | `theme_331_gehazi_greed.json` |
| 나사로 무덤 (Lazarus Tomb) | 요한복음 11:43 | `ANCHOR_JHN_11_43` | 4 | `theme_332_lazarus_tomb.json` |
| 엠마오 길 (Road Emmaus) | 누가복음 24:15 | `ANCHOR_LUK_24_15` | 4 | `theme_333_road_emmaus.json` |
| 유다 배반 (Judas Betrayal) | 마태복음 26:48 | `ANCHOR_MAT_26_48` | 4 | `theme_334_judas_betrayal.json` |
| 은 삼십 (Thirty Pieces Silver) | 마태복음 27:3 | `ANCHOR_MAT_27_3` | 4 | `theme_335_thirty_pieces.json` |
| 닭 울음 (Cock Crow) | 마태복음 26:74 | `ANCHOR_MAT_26_74` | 4 | `theme_336_cock_crow.json` |
| 바라바 석방 (Barabbas Release) | 마태복음 27:21 | `ANCHOR_MAT_27_21` | 4 | `theme_337_barabbas_release.json` |
| 휘장 찢김 (Veil Torn) | 마태복음 27:51 | `ANCHOR_MAT_27_51` | 4 | `theme_338_veil_torn.json` |
| 빈 무덤 (Empty Tomb) | 마태복음 28:6 | `ANCHOR_MAT_28_6` | 4 | `theme_339_empty_tomb.json` |
| 아브라함 언약 (Abraham Covenant) | 창세기 15:5 | `ANCHOR_GEN_15_5` | 4 | `theme_33_abraham_covenant.json` |
| 도마 의심 (Doubting Thomas) | 요한복음 20:25 | `ANCHOR_JHN_20_25` | 4 | `theme_340_doubting_thomas.json` |
| 사울 다메섹 길 (Saul Road) | 사도행전 9:3 | `ANCHOR_ACT_9_3` | 4 | `theme_341_saul_road.json` |
| 루스드라 돌 (Lystra Stones) | 사도행전 14:19 | `ANCHOR_ACT_14_19` | 4 | `theme_342_lystra_stones.json` |
| 보아스 구속자 (Boaz Redeemer) | 룻기 4:9 | `ANCHOR_RUT_4_9` | 4 | `theme_343_boaz_redeemer.json` |
| 모세 두 돌판 (Moses Tablets) | 출애굽기 32:19 | `ANCHOR_EXO_32_19` | 4 | `theme_344_moses_tablets.json` |
| 입다 서원 (Jephthah Vow) | 사사기 11:30 | `ANCHOR_JDG_11_30` | 4 | `theme_345_jephthah_vow.json` |
| 에훗 단검 (Ehud Dagger) | 사사기 3:21 | `ANCHOR_JDG_3_21` | 4 | `theme_346_ehud_dagger.json` |
| 드보라 종려나무 (Deborah Palm) | 사사기 4:5 | `ANCHOR_JDG_4_5` | 4 | `theme_347_deborah_palm.json` |
| 베드로 보자기 (Peter Vision Sheet) | 사도행전 10:11 | `ANCHOR_ACT_10_11` | 4 | `theme_348_peter_vision_sheet.json` |
| 초대 교회 나눔 (Acts Church Share) | 사도행전 2:44 | `ANCHOR_ACT_2_44` | 4 | `theme_349_acts_church_share.json` |
| 요셉 꿈 (Joseph Dreams) | 창세기 41:25 | `ANCHOR_GEN_41_25` | 4 | `theme_34_joseph_dreams.json` |
| 디모데 두루마리 (Timothy Scroll) | 디모데후서 3:15 | `ANCHOR_2TI_3_15` | 4 | `theme_350_timothy_scroll.json` |
| 디도 섬 (Titus Island) | 디도서 1:5 | `ANCHOR_TIT_1_5` | 4 | `theme_351_titus_island.json` |
| 베데스다 못 (Healing Pool) | 요한복음 5:2 | `ANCHOR_JHN_5_2` | 4 | `theme_352_healing_pool.json` |
| 베데스다 다섯 포르치 (Pool Bethesda) | 요한복음 5:3 | `ANCHOR_JHN_5_3` | 4 | `theme_353_pool_bethesda.json` |
| 마리아 부음유 (Mary Anointing) | 요한복음 12:3 | `ANCHOR_MARY_ANOINT` | 4 | `theme_354_mary_anoint.json` |
| 유월절 문인방 (Passover Door) | 출애굽기 12:13 | `ANCHOR_PASSOVER_DOOR` | 4 | `theme_355_passover_door.json` |
| 엘리야 까마귀 (Elijah Ravens) | 열왕기상 17:6 | `ANCHOR_ELIJAH_RAVENS` | 4 | `theme_356_elijah_ravens.json` |
| 양과 염소 (Sheep and Goats) | 마태복음 25:32 | `ANCHOR_SHEEP_GOATS` | 4 | `theme_357_sheep_goats.json` |
| 치유 물 (Healing Waters) | 요한복음 5:4 | `ANCHOR_HEALING_WATERS` | 4 | `theme_358_healing_waters.json` |
| 맹인 눈 뜸 (Blind See) | 요한복음 9:7 | `ANCHOR_BLIND_SEE` | 4 | `theme_359_blind_see.json` |
| 모세 율법 (Moses Law Giver) | 출애굽 20:1 | `ANCHOR_EXO_20_1` | 4 | `theme_35_moses_law_giver.json` |
| 귀머거리 들음 (Deaf Hear) | 마가복음 7:35 | `ANCHOR_DEAF_HEAR` | 4 | `theme_360_deaf_hear.json` |
| 앉은뱅이 걸음 (Lame Walk) | 사도행전 3:8 | `ANCHOR_LAME_WALK` | 4 | `theme_361_lame_walk.json` |
| 문둥병 정결 (Leper Cleansed) | 마태복음 8:3 | `ANCHOR_LEPER_CLEANSED` | 4 | `theme_362_leper_cleansed.json` |
| 사천 명 먹이심 (Feeding Four Thousand) | 마가복음 8:9 | `ANCHOR_FEEDING_FOUR_THOUSAND` | 4 | `theme_363_feeding_four_thousand.json` |
| 변화산 구름 (Transfiguration Cloud) | 마태복음 17:5 | `ANCHOR_TRANSFIGURATION_CLOUD` | 4 | `theme_364_transfiguration_cloud.json` |
| 무화과 저주 (Fig Tree Curse) | 마가복음 11:14 | `ANCHOR_FIG_TREE_CURSE` | 4 | `theme_365_fig_tree_curse.json` |
| 혼례 예복 (Wedding Garment) | 마태복음 22:12 | `ANCHOR_WEDDING_GARMENT` | 4 | `theme_366_wedding_garment.json` |
| 달란트 묻음 (Buried Talent) | 마태복음 25:25 | `ANCHOR_TALENT_BURIED` | 4 | `theme_367_talent_buried.json` |
| 포도원 품꾼 (Vineyard Workers) | 마태복음 20:10 | `ANCHOR_VINEYARD_WORKERS` | 4 | `theme_368_vineyard_workers.json` |
| 승천 축복 (Ascension Blessing) | 누가복음 24:51 | `ANCHOR_ASCENSION_BLESSING` | 4 | `theme_369_ascension_blessing.json` |
| 여호수아 성벽 (Joshua Walls) | 여호수아 6:20 | `ANCHOR_JOS_6_20` | 4 | `theme_36_joshua_walls.json` |
| 오순절 방언 (Pentecost Tongues) | 사도행전 2:4 | `ANCHOR_PENTECOST_TONGUES` | 4 | `theme_370_pentecost_tongues.json` |
| 아나니아 거짓 (Ananias Lie) | 사도행전 5:5 | `ANCHOR_ANANIAS_LIE` | 4 | `theme_371_ananias_lie.json` |
| 다비다 기림 (Tabitha Raised) | 사도행전 9:40 | `ANCHOR_TABITHA_RAISE` | 4 | `theme_372_tabitha_raise.json` |
| 고넬료 천사 (Cornelius Angel) | 사도행전 10:3 | `ANCHOR_CORNELIUS_ANGEL` | 4 | `theme_373_cornelius_angel.json` |
| 루디아 침례 (Lydia Baptized) | 사도행전 16:15 | `ANCHOR_LYDIA_BAPTIZED` | 4 | `theme_374_lydia_baptized.json` |
| 아테네 마르스 (Athens Mars Hill) | 사도행전 17:22 | `ANCHOR_ATHENS_MARS` | 4 | `theme_375_athens_mars.json` |
| 고린도 천막 (Corinth Tent) | 사도행전 18:3 | `ANCHOR_CORINTH_TENT` | 4 | `theme_376_corinth_tent.json` |
| 로마 사슬 (Rome Chain) | 사도행전 28:20 | `ANCHOR_ROME_CHAIN` | 4 | `theme_377_rome_chain.json` |
| 몰타 선박 (Ship Malta) | 사도행전 28:1 | `ANCHOR_SHIP_MALTA` | 4 | `theme_378_ship_malta.json` |
| 스데반 순교 (Stephen Martyrdom) | 사도행전 7:60 | `ANCHOR_MARTYRDOM_STEPHEN` | 4 | `theme_379_martyrdom_stephen.json` |
| 사무엘 부르심 (Samuel Call) | 사무엘상 3:10 | `ANCHOR_1SAM_3_10` | 4 | `theme_37_samuel_call.json` |
| 루스드라 치유 (Lystra Healing) | 사도행전 14:10 | `ANCHOR_HEALING_LYSTRA` | 4 | `theme_380_healing_lystra.json` |
| 루다 회개 (Lydda Conversion) | 사도행전 9:35 | `ANCHOR_CONVERSION_LYDDA` | 4 | `theme_381_conversion_lydda.json` |
| 장사 무덤 (Burial Tomb) | 마태복음 27:60 | `ANCHOR_BURIAL_TOMB` | 4 | `theme_382_burial_tomb.json` |
| 십자가 지음 (Cross Carry) | 누가복음 14:27 | `ANCHOR_CROSS_CARRY` | 4 | `theme_383_cross_carry.json` |
| 십자가 어둠 (Crucifixion Darkness) | 마태복음 27:45 | `ANCHOR_CRUCIFIXION_DARKNESS` | 4 | `theme_384_crucifixion_darkness.json` |
| 겟세마네 (Gethsemane Garden) | 마태복음 26:39 | `ANCHOR_GARDEN_GETHSEMANE` | 4 | `theme_385_garden_gethsemane.json` |
| 환전상 (Money Changers) | 마태복음 21:12 | `ANCHOR_MONEY_CHANGERS` | 4 | `theme_386_money_changers.json` |
| 성전 정화 (Temple Cleansing) | 요한복음 2:15 | `ANCHOR_CLEANSING_TEMPLE` | 4 | `theme_387_cleansing_temple.json` |
| 무화과 저주2 (Cursing Fig) | 마태복음 21:19 | `ANCHOR_CURSING_FIG` | 4 | `theme_388_cursing_fig.json` |
| 낙타 바늘귀 (Camel Needle) | 마태복음 19:24 | `ANCHOR_CAMEL_EYE_NEEDLE` | 4 | `theme_389_camel_eye_needle.json` |
| 느헤미야 성벽 (Nehemiah Wall) | 느헤미야 4:6 | `ANCHOR_NEH_4_6` | 4 | `theme_38_nehemiah_wall.json` |
| 부자 관원 (Rich Ruler) | 마가복음 10:22 | `ANCHOR_RICH_RULER_CAMEL` | 4 | `theme_390_rich_ruler_camel.json` |
| 어린이 축복 (Children Blessed) | 마태복음 19:14 | `ANCHOR_CHILDREN_BLESSED` | 4 | `theme_391_children_blessed.json` |
| 바리새인 기도 (Pharisee Prayer) | 누가복음 18:11 | `ANCHOR_PHARISEE_PRAYER` | 4 | `theme_392_pharisee_prayer.json` |
| 과부 끈질김 (Persistent Widow) | 누가복음 18:5 | `ANCHOR_WIDOW_PERSISTENT` | 4 | `theme_393_widow_persistent.json` |
| 백부장 종 (Centurion Servant) | 마태복음 8:8 | `ANCHOR_CENTURION_SERVANT` | 4 | `theme_394_centurion_servant.json` |
| 바다 잔잔 (Calming Sea) | 마가복음 4:39 | `ANCHOR_CALMING_SEA` | 4 | `theme_395_calming_sea.json` |
| 바다 위 걸음 (Walking Sea) | 마태복음 14:25 | `ANCHOR_WALKING_SEA` | 4 | `theme_396_walking_sea.json` |
| 변화산 (Transfiguration Mount) | 누가복음 9:29 | `ANCHOR_TRANSFIGURATION_MOUNT` | 4 | `theme_397_transfiguration_mount.json` |
| 부자 나사로 (Rich Man Lazarus) | 누가복음 16:23 | `ANCHOR_RICH_MAN_LAZARUS` | 4 | `theme_398_rich_man_lazarus.json` |
| 아버지 환영 (Prodigal Father) | 누가복음 15:20 | `ANCHOR_PRODIGAL_FATHER` | 4 | `theme_399_prodigal_father.json` |
| 욥 고난 (Job Suffering) | 욥기 1:21 | `ANCHOR_JOB_1_21` | 4 | `theme_39_job_suffering.json` |
| 맏아들 (Elder Brother) | 누가복음 15:28 | `ANCHOR_ELDER_BROTHER` | 4 | `theme_400_elder_brother.json` |
| 잃은 아들 (Lost Son) | 누가복음 15:24 | `ANCHOR_LOST_SON` | 4 | `theme_401_lost_son.json` |
| 파종자 (Sower Seed) | 마태복음 13:3 | `ANCHOR_SOWER_SEED` | 4 | `theme_402_sower_seed.json` |
| 밭의 가라지 (Weeds Field) | 마태복음 13:30 | `ANCHOR_WEEDS_FIELD` | 4 | `theme_403_weeds_field.json` |
| 겨자 나무 (Mustard Tree) | 마태복음 13:32 | `ANCHOR_MUSTARD_TREE` | 4 | `theme_404_mustard_tree.json` |
| 겨자씨 성장 (Mustard Seed Tree) | 마가복음 4:32 | `ANCHOR_MUSTARD_SEED_TREE` | 4 | `theme_405_mustard_seed_tree.json` |
| 숨은 누룩 (Hidden Yeast) | 마태복음 13:33 | `ANCHOR_YEAST_HIDDEN` | 4 | `theme_406_yeast_hidden.json` |
| 누룩 반죽 (Leaven Meal) | 갈라디아서 5:9 | `ANCHOR_LEAVEN_MEAL` | 4 | `theme_407_leaven_meal.json` |
| 숨은 보물 (Hidden Treasure) | 마태복음 13:44 | `ANCHOR_HIDDEN_TREASURE` | 4 | `theme_408_hidden_treasure.json` |
| 진주 상인 (Pearl Merchant) | 마태복음 13:46 | `ANCHOR_PEARL_MERCHANT` | 4 | `theme_409_pearl_merchant.json` |
| 시편 목자 (Psalm Shepherd) | 시편 23:1 | `ANCHOR_PS_23_1` | 4 | `theme_40_psalm_shepherd.json` |
| 값진 진주 (Costly Pearl) | 마태복음 13:46 | `ANCHOR_COSTLY_PEARL` | 4 | `theme_410_costly_pearl.json` |
| 그물 고기 (Net Fish) | 마태복음 13:47 | `ANCHOR_NET_FISH` | 4 | `theme_411_net_fish.json` |
| 끌어내는 그물 (Dragnet Sea) | 마태복음 13:48 | `ANCHOR_DRAGNET_SEA` | 4 | `theme_412_dragnet_sea.json` |
| 용서 못할 종 (Unforgiving Servant) | 마태복음 18:30 | `ANCHOR_UNFORGIVING_SERVANT` | 4 | `theme_413_unforgiving_servant.json` |
| 자비 없는 빚 (Unmerciful Debtor) | 마태복음 18:34 | `ANCHOR_UNMERCIFUL_DEBTOR` | 4 | `theme_414_unmerciful_debtor.json` |
| 동일 임금 (Equal Pay Workers) | 마태복음 20:12 | `ANCHOR_WORKERS_EQUAL_PAY` | 4 | `theme_415_workers_equal_pay.json` |
| 포도원 세입자 (Vineyard Tenants) | 마태복음 21:38 | `ANCHOR_VINEYARD_TENANTS` | 4 | `theme_416_vineyard_tenants.json` |
| 혼례 잔치 (Wedding Feast) | 마태복음 22:4 | `ANCHOR_WEDDING_FEAST` | 4 | `theme_417_wedding_feast.json` |
| 열 처녀 (Ten Virgins) | 마태복음 25:10 | `ANCHOR_TEN_VIRGINS` | 4 | `theme_418_ten_virgins.json` |
| 달란트 비유 (Talents Parable) | 마태복음 25:21 | `ANCHOR_TALENTS_PARABLE` | 4 | `theme_419_talents_parable.json` |
| 잠언 길 (Proverbs Path) | 잠언 3:5 | `ANCHOR_PROV_3_5` | 4 | `theme_41_proverbs_path.json` |
| 어리석은 부자 (Rich Fool Barn) | 누가복음 12:18 | `ANCHOR_RICH_FOOL_BARN` | 4 | `theme_420_rich_fool_barn.json` |
| 탑 짓는 자 (Tower Builder) | 누가복음 14:28 | `ANCHOR_TOWER_BUILDER` | 4 | `theme_421_tower_builder.json` |
| 비용 계산 (Counting Cost) | 누가복음 14:33 | `ANCHOR_COUNTING_COST` | 4 | `theme_422_counting_cost.json` |
| 소금 맛 잃음 (Salt Lost) | 마태복음 5:13 | `ANCHOR_SALT_LOST` | 4 | `theme_423_salt_lost.json` |
| 등불 가리움 (Light Under Bushel) | 마태복음 5:15 | `ANCHOR_LIGHT_BUSHEL` | 4 | `theme_424_light_bushel.json` |
| 반석 위 집 (House on Rock) | 마태복음 7:24 | `ANCHOR_HOUSE_BUILT_ROCK` | 4 | `theme_425_house_built_rock.json` |
| 모래 위 집 (House on Sand) | 마태복음 7:26 | `ANCHOR_HOUSE_BUILT_SAND` | 4 | `theme_426_house_built_sand.json` |
| 지혜로운 건축 (Wise Builder) | 누가복음 6:48 | `ANCHOR_WISE_BUILDER` | 4 | `theme_427_wise_builder.json` |
| 겨자 믿음 (Mustard Faith) | 마태복음 17:20 | `ANCHOR_FAITH_MUSTARD` | 4 | `theme_428_faith_mustard.json` |
| 무화과 마름 (Fig Wither) | 마태복음 21:20 | `ANCHOR_FIG_TREE_WITHER` | 4 | `theme_429_fig_tree_wither.json` |
| 전도서 헛됨 (Ecclesiastes Vanity) | 전도서 1:2 | `ANCHOR_ECCL_1_2` | 4 | `theme_42_ecclesiastes_vanity.json` |
| 천국 열쇠 (Keys of Kingdom) | 마태복음 16:19 | `ANCHOR_KEYS_KINGDOM` | 4 | `theme_430_keys_kingdom.json` |
| 베드로 열쇠 (Peter Keys) | 마태복음 16:18 | `ANCHOR_PETER_KEYS` | 4 | `theme_431_peter_keys.json` |
| 부활 나타남 (Resurrection Appear) | 요한복음 20:19 | `ANCHOR_RESURRECTION_APPEAR` | 4 | `theme_432_resurrection_appear.json` |
| 나인 과부 (Widow Nain) | 누가복음 7:14 | `ANCHOR_WIDOW_NAIN` | 4 | `theme_433_widow_nain.json` |
| 과부 동전 (Widow Mite) | 마가복음 12:42 | `ANCHOR_WIDOWS_MITE` | 4 | `theme_434_widows_mite.json` |
| 양 염소 심판 (Sheep Goats Judgment) | 마태복음 25:46 | `ANCHOR_SHEEP_GOATS_JUDGMENT` | 4 | `theme_435_sheep_goats_judgment.json` |
| 삼손 머리 (Samson Hair) | 사사기 16:17 | `ANCHOR_SAMSON_HAIR` | 4 | `theme_436_samson_hair.json` |
| 마리아 기름 (Mary Anointing Oil) | 마가복음 14:8 | `ANCHOR_MARY_ANOINTING` | 4 | `theme_437_mary_anointing.json` |
| 창조 빛 (Creation Light) | 창세기 1:3 | `ANCHOR_CREATION_LIGHT` | 4 | `theme_438_creation_light.json` |
| 에덴 동산 (Eden Garden) | 창세기 2:8 | `ANCHOR_EDEN_GARDEN` | 4 | `theme_439_eden_garden.json` |
| 이사야 종 (Isaiah Servant) | 이사야 53:5 | `ANCHOR_ISA_53_5` | 4 | `theme_43_isaiah_servant.json` |
| Cain Abel (Track B) | 시편 119:105 | `ANCHOR_CAIN_ABEL` | 4 | `theme_440_cain_abel.json` |
| Enoch Taken (Track B) | 시편 119:105 | `ANCHOR_ENOCH_TAKEN` | 4 | `theme_441_enoch_taken.json` |
| Noah Dove (Track B) | 시편 119:105 | `ANCHOR_NOAH_DOVE` | 4 | `theme_442_noah_dove.json` |
| Abe Isaac Ram (Track B) | 시편 119:105 | `ANCHOR_ABE_ISAAC_RAM` | 4 | `theme_443_abe_isaac_ram.json` |
| Jacob Wrestle (Track B) | 시편 119:105 | `ANCHOR_JACOB_WRESTLE` | 4 | `theme_444_jacob_wrestle.json` |
| Jacob Stairway (Track B) | 시편 119:105 | `ANCHOR_JACOB_STAIRWAY` | 4 | `theme_445_jacob_stairway.json` |
| Leah Rachel (Track B) | 시편 119:105 | `ANCHOR_LEAH_RACHEL` | 4 | `theme_446_leah_rachel.json` |
| Dinah Shame (Track B) | 시편 119:105 | `ANCHOR_DINAH_SHAME` | 4 | `theme_447_dinah_shame.json` |
| Judah Tamar (Track B) | 시편 119:105 | `ANCHOR_JUDAH_TAMAR` | 4 | `theme_448_judah_tamar.json` |
| Potiphar Wife (Track B) | 시편 119:105 | `ANCHOR_POTIPHAR_WIFE` | 4 | `theme_449_potiphar_wife.json` |
| 예레미야 새언약 (Jeremiah New Covenant) | 예레미야 31:31 | `ANCHOR_JER_31_31` | 4 | `theme_44_jeremiah_covenant.json` |
| Famine Egypt (Track B) | 시편 119:105 | `ANCHOR_FAMINE_EGYPT` | 4 | `theme_450_famine_egypt.json` |
| Benjamin Cup (Track B) | 시편 119:105 | `ANCHOR_BENJAMIN_CUP` | 4 | `theme_451_benjamin_cup.json` |
| Exodus Passover (Track B) | 시편 119:105 | `ANCHOR_EXODUS_PASSOVER` | 4 | `theme_452_exodus_passover.json` |
| Pharaoh Army (Track B) | 시편 119:105 | `ANCHOR_PHARAOH_ARMY` | 4 | `theme_453_pharaoh_army.json` |
| Marah Bitter (Track B) | 시편 119:105 | `ANCHOR_MARAH_BITTER` | 4 | `theme_454_marah_bitter.json` |
| Marah Sweet (Track B) | 시편 119:105 | `ANCHOR_MARAH_SWEET` | 4 | `theme_455_marah_sweet.json` |
| Quail Graves (Track B) | 시편 119:105 | `ANCHOR_QUAIL_GRAVES` | 4 | `theme_456_quail_graves.json` |
| Korah Swallowed (Track B) | 시편 119:105 | `ANCHOR_KORAH_SWALLOWED` | 4 | `theme_457_korah_swallowed.json` |
| 여리고 함뿌 (Joshua Jericho) | 여호수아 6:20 | `ANCHOR_JOSHUA_JERICHO` | 4 | `theme_458_joshua_jericho.json` |
| Rahab Rope (Track B) | 시편 119:105 | `ANCHOR_RAHAB_ROPE` | 4 | `theme_459_rahab_rope.json` |
| 에스겔 마른 뼈 (Ezekiel Dry Bones) | 에스겔 37:10 | `ANCHOR_EZE_37_10` | 4 | `theme_45_ezekiel_dry_bones.json` |
| 기브온 해 멈춤 (Gibeon Sun) | 여호수아 10:13 | `ANCHOR_GIBEON_SUN` | 4 | `theme_460_gibeon_sun.json` |
| Samuel Birth (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_BIRTH` | 4 | `theme_461_samuel_birth.json` |
| Eli Sons (Track B) | 시편 119:105 | `ANCHOR_ELI_SONS` | 4 | `theme_462_eli_sons.json` |
| Saul Jonathan (Track B) | 시편 119:105 | `ANCHOR_SAUL_JONATHAN` | 4 | `theme_463_saul_jonathan.json` |
| Jonathan Bow (Track B) | 시편 119:105 | `ANCHOR_JONATHAN_BOW` | 4 | `theme_464_jonathan_bow.json` |
| David Spare Saul (Track B) | 시편 119:105 | `ANCHOR_DAVID_SPARE_SAUL` | 4 | `theme_465_david_spare_saul.json` |
| Absalom Oak (Track B) | 시편 119:105 | `ANCHOR_ABSALOM_OAK` | 4 | `theme_466_absalom_oak.json` |
| Solomon Dream (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_DREAM` | 4 | `theme_467_solomon_dream.json` |
| Solomon Two Mothers (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_TWO_MOTHERS` | 4 | `theme_468_solomon_two_mothers.json` |
| Elijah Brook (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_BROOK` | 4 | `theme_469_elijah_brook.json` |
| 말라기 사자 (Malachi Messenger) | 말라기 3:1 | `ANCHOR_MAL_3_1` | 4 | `theme_46_malachi_messenger.json` |
| Jezebel Threat (Track B) | 시편 119:105 | `ANCHOR_JEZEBEL_THREAT` | 4 | `theme_470_jezebel_threat.json` |
| Naaman Seven (Track B) | 시편 119:105 | `ANCHOR_NAAMAN_SEVEN` | 4 | `theme_471_naaman_seven.json` |
| Hezekiah Sennacherib (Track B) | 시편 119:105 | `ANCHOR_HEZEKIAH_SENNACHERIB` | 4 | `theme_472_hezekiah_sennacherib.json` |
| Manasseh Idols (Track B) | 시편 119:105 | `ANCHOR_MANASSEH_IDOLS` | 4 | `theme_473_manasseh_idols.json` |
| Josiah Law (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_LAW` | 4 | `theme_474_josiah_law.json` |
| Jeremiah Linen (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_LINEN` | 4 | `theme_475_jeremiah_linen.json` |
| Ezekiel Valley (Track B) | 시편 119:105 | `ANCHOR_EZEKIEL_VALLEY` | 4 | `theme_476_ezekiel_valley.json` |
| Daniel Dream (Track B) | 시편 119:105 | `ANCHOR_DANIEL_DREAM` | 4 | `theme_477_daniel_dream.json` |
| 풀무불 (Fiery Furnace) | 다니엘 3:25 | `ANCHOR_FIERY_FURNACE` | 4 | `theme_478_fiery_furnace.json` |
| Writing Wall (Track B) | 시편 119:105 | `ANCHOR_WRITING_WALL` | 4 | `theme_479_writing_wall.json` |
| 팔복 (Beatitudes) | 마태복음 5:3 | `ANCHOR_MAT_5_3` | 4 | `theme_47_beatitudes.json` |
| John Baptist Camel (Track B) | 시편 119:105 | `ANCHOR_JOHN_BAPTIST_CAMEL` | 4 | `theme_480_john_baptist_camel.json` |
| Herod Birth (Track B) | 시편 119:105 | `ANCHOR_HEROD_BIRTH` | 4 | `theme_481_herod_birth.json` |
| Magi Gifts (Track B) | 시편 119:105 | `ANCHOR_MAGI_GIFTS` | 4 | `theme_482_magi_gifts.json` |
| Slaughter Innocents (Track B) | 시편 119:105 | `ANCHOR_SLAUGHTER_INNOCENTS` | 4 | `theme_483_slaughter_innocents.json` |
| Temptation Stones (Track B) | 시편 119:105 | `ANCHOR_TEMPTATION_STONES` | 4 | `theme_484_temptation_stones.json` |
| Sermon Beatitudes (Track B) | 시편 119:105 | `ANCHOR_SERMON_BEATITUDES` | 4 | `theme_485_sermon_beatitudes.json` |
| Lord Prayer (Track B) | 시편 119:105 | `ANCHOR_LORD_PRAYER` | 4 | `theme_486_lord_prayer.json` |
| Beatitudes Mourn (Track B) | 시편 119:105 | `ANCHOR_BEATITUDES_MOURN` | 4 | `theme_487_beatitudes_mourn.json` |
| Salt Earth (Track B) | 시편 119:105 | `ANCHOR_SALT_EARTH` | 4 | `theme_488_salt_earth.json` |
| City Hill (Track B) | 시편 119:105 | `ANCHOR_CITY_HILL` | 4 | `theme_489_city_hill.json` |
| 주기도문 (Lords Prayer) | 마태복음 6:10 | `ANCHOR_MAT_6_10` | 4 | `theme_48_lords_prayer.json` |
| Log In Eye (Track B) | 시편 119:105 | `ANCHOR_LOG_IN_EYE` | 4 | `theme_490_log_in_eye.json` |
| Pearls Swine (Track B) | 시편 119:105 | `ANCHOR_PEARLS_SWINE` | 4 | `theme_491_pearls_swine.json` |
| Ask Seek Knock (Track B) | 시편 119:105 | `ANCHOR_ASK_SEEK_KNOCK` | 4 | `theme_492_ask_seek_knock.json` |
| Narrow Gate (Track B) | 시편 119:105 | `ANCHOR_NARROW_GATE` | 4 | `theme_493_narrow_gate.json` |
| Fruit Known (Track B) | 시편 119:105 | `ANCHOR_FRUIT_KNOWN` | 4 | `theme_494_fruit_known.json` |
| House Divide (Track B) | 시편 119:105 | `ANCHOR_HOUSE_DIVIDE` | 4 | `theme_495_house_divide.json` |
| Sign Jonah (Track B) | 시편 119:105 | `ANCHOR_SIGN_JONAH` | 4 | `theme_496_sign_jonah.json` |
| Leaven Pharisees (Track B) | 시편 119:105 | `ANCHOR_LEAVEN_PHARISEES` | 4 | `theme_497_leaven_pharisees.json` |
| Rich Man Gate (Track B) | 시편 119:105 | `ANCHOR_RICH_MAN_GATE` | 4 | `theme_498_rich_man_gate.json` |
| Zaccheus Short (Track B) | 시편 119:105 | `ANCHOR_ZACCHEUS_SHORT` | 4 | `theme_499_zaccheus_short.json` |
| 대위임 (Great Commission) | 마태복음 28:19 | `ANCHOR_MAT_28_19` | 4 | `theme_49_great_commission.json` |
| Money Table (Track B) | 시편 119:105 | `ANCHOR_MONEY_TABLE` | 4 | `theme_500_money_table.json` |
| Withered Hand (Track B) | 시편 119:105 | `ANCHOR_WITHERED_HAND` | 4 | `theme_501_withered_hand.json` |
| Sabbath Grain (Track B) | 시편 119:105 | `ANCHOR_SABBATH_GRAIN` | 4 | `theme_502_sabbath_grain.json` |
| Beelzebub (Track B) | 시편 119:105 | `ANCHOR_BEELZEBUB` | 4 | `theme_503_beelzebub.json` |
| Unpardonable Sin (Track B) | 시편 119:105 | `ANCHOR_UNPARDONABLE_SIN` | 4 | `theme_504_unpardonable_sin.json` |
| Sign Resurrection (Track B) | 시편 119:105 | `ANCHOR_SIGN_RESURRECTION` | 4 | `theme_505_sign_resurrection.json` |
| Greatest Command (Track B) | 시편 119:105 | `ANCHOR_GREATEST_COMMAND` | 4 | `theme_506_greatest_command.json` |
| Woes Pharisees (Track B) | 시편 119:105 | `ANCHOR_WOES_PHARISEES` | 4 | `theme_507_woes_pharisees.json` |
| Lament Jerusalem (Track B) | 시편 119:105 | `ANCHOR_LAMENT_JERUSALEM` | 4 | `theme_508_lament_jerusalem.json` |
| Olivet Signs (Track B) | 시편 119:105 | `ANCHOR_OLIVET_SIGNS` | 4 | `theme_509_olivet_signs.json` |
| 오순절 성령 (Pentecost Spirit) | 사도행전 2:4 | `ANCHOR_ACT_2_4` | 4 | `theme_50_pentecost_spirit.json` |
| Watchful Servants (Track B) | 시편 119:105 | `ANCHOR_WATCHFUL_SERVANTS` | 4 | `theme_510_watchful_servants.json` |
| Ten Minas (Track B) | 시편 119:105 | `ANCHOR_TEN_MINAS` | 4 | `theme_511_ten_minas.json` |
| Sheep Fold (Track B) | 시편 119:105 | `ANCHOR_SHEEP_FOLD` | 4 | `theme_512_sheep_fold.json` |
| Comforter Spirit (Track B) | 시편 119:105 | `ANCHOR_COMFORTER_SPIRIT` | 4 | `theme_513_comforter_spirit.json` |
| Upper Room Wash (Track B) | 시편 119:105 | `ANCHOR_UPPER_ROOM_WASH` | 4 | `theme_514_upper_room_wash.json` |
| Gethsemane Sleep (Track B) | 시편 119:105 | `ANCHOR_GETHSEMANE_SLEEP` | 4 | `theme_515_gethsemane_sleep.json` |
| Kiss Judas (Track B) | 시편 119:105 | `ANCHOR_KISS_JUDAS` | 4 | `theme_516_kiss_judas.json` |
| Pilate Truth (Track B) | 시편 119:105 | `ANCHOR_PILATE_TRUTH` | 4 | `theme_517_pilate_truth.json` |
| Crucified Thieves (Track B) | 시편 119:105 | `ANCHOR_CRUCIFIED_THIEVES` | 4 | `theme_518_crucified_thieves.json` |
| Darkness Noon (Track B) | 시편 119:105 | `ANCHOR_DARKNESS_NOON` | 4 | `theme_519_darkness_noon.json` |
| 변화산 (Transfiguration) | 마태복음 17:2 | `ANCHOR_MAT_17_2` | 4 | `theme_51_transfiguration.json` |
| Soldier Pierce (Track B) | 시편 119:105 | `ANCHOR_SOLDIER_PIERCE` | 4 | `theme_520_soldier_pierce.json` |
| Nicodemus Burial (Track B) | 시편 119:105 | `ANCHOR_NICODEMUS_BURIAL` | 4 | `theme_521_nicodemus_burial.json` |
| Women Tomb (Track B) | 시편 119:105 | `ANCHOR_WOMEN_TOMB` | 4 | `theme_522_women_tomb.json` |
| Fish Breakfast (Track B) | 시편 119:105 | `ANCHOR_FISH_BREAKFAST` | 4 | `theme_523_fish_breakfast.json` |
| Peter Restore (Track B) | 시편 119:105 | `ANCHOR_PETER_RESTORE` | 4 | `theme_524_peter_restore.json` |
| Ascend Olive (Track B) | 시편 119:105 | `ANCHOR_ASCEND_OLIVE` | 4 | `theme_525_ascend_olive.json` |
| Lottery Matthias (Track B) | 시편 119:105 | `ANCHOR_LOTTERY_MATTHIAS` | 4 | `theme_526_lottery_matthias.json` |
| Tongues Pentecost (Track B) | 시편 119:105 | `ANCHOR_TONGUES_PENTECOST` | 4 | `theme_527_tongues_pentecost.json` |
| Shared All (Track B) | 시편 119:105 | `ANCHOR_SHARED_ALL` | 4 | `theme_528_shared_all.json` |
| Paul Blind (Track B) | 시편 119:105 | `ANCHOR_PAUL_BLIND` | 4 | `theme_529_paul_blind.json` |
| 겟세마네 (Gethsemane Watch) | 마태복음 26:39 | `ANCHOR_MAT_26_39` | 4 | `theme_52_gethsemane_watch.json` |
| Derbe Lystra (Track B) | 시편 119:105 | `ANCHOR_DERBE_LYSTRA` | 4 | `theme_530_derbe_lystra.json` |
| 빌립보 간수 (Philippi Jailer) | 사도행전 16:30 | `ANCHOR_PHILIPPI_JAILER` | 4 | `theme_531_philippi_jailer.json` |
| Thessalonica Riot (Track B) | 시편 119:105 | `ANCHOR_THESSALONICA_RIOT` | 4 | `theme_532_thessalonica_riot.json` |
| Athens Unknown (Track B) | 시편 119:105 | `ANCHOR_ATHENS_UNKNOWN` | 4 | `theme_533_athens_unknown.json` |
| Corinth Aquila (Track B) | 시편 119:105 | `ANCHOR_CORINTH_AQUILA` | 4 | `theme_534_corinth_aquila.json` |
| Epaphroditus Sick (Track B) | 시편 119:105 | `ANCHOR_EPAPHRODITUS_SICK` | 4 | `theme_535_epaphroditus_sick.json` |
| Onesimus Return (Track B) | 시편 119:105 | `ANCHOR_ONESIMUS_RETURN` | 4 | `theme_536_onesimus_return.json` |
| Timothy Gifts (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_GIFTS` | 4 | `theme_537_timothy_gifts.json` |
| Armor Belt (Track B) | 시편 119:105 | `ANCHOR_ARMOR_BELT` | 4 | `theme_538_armor_belt.json` |
| Shield Faith (Track B) | 시편 119:105 | `ANCHOR_SHIELD_FAITH` | 4 | `theme_539_shield_faith.json` |
| 승천 (Ascension Cloud) | 사도행전 1:9 | `ANCHOR_ACT_1_9` | 4 | `theme_53_ascension_cloud.json` |
| Helmet Salvation (Track B) | 시편 119:105 | `ANCHOR_HELMET_SALVATION` | 4 | `theme_540_helmet_salvation.json` |
| Sword Spirit (Track B) | 시편 119:105 | `ANCHOR_SWORD_SPIRIT` | 4 | `theme_541_sword_spirit.json` |
| Running Race (Track B) | 시편 119:105 | `ANCHOR_RUNNING_RACE` | 4 | `theme_542_running_race.json` |
| Cloud Witnesses (Track B) | 시편 119:105 | `ANCHOR_CLOUD_WITNESSES` | 4 | `theme_543_cloud_witnesses.json` |
| Hebrews Rest (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_REST` | 4 | `theme_544_hebrews_rest.json` |
| James Faith Works (Track B) | 시편 119:105 | `ANCHOR_JAMES_FAITH_WORKS` | 4 | `theme_545_james_faith_works.json` |
| Peter Rooster (Track B) | 시편 119:105 | `ANCHOR_PETER_ROOSTER` | 4 | `theme_546_peter_rooster.json` |
| Jude Apostates (Track B) | 시편 119:105 | `ANCHOR_JUDE_APOSTATES` | 4 | `theme_547_jude_apostates.json` |
| Revelation Seven (Track B) | 시편 119:105 | `ANCHOR_REVELATION_SEVEN` | 4 | `theme_548_revelation_seven.json` |
| Lampstands Seven (Track B) | 시편 119:105 | `ANCHOR_LAMPSTANDS_SEVEN` | 4 | `theme_549_lampstands_seven.json` |
| 하나님의 전신갑주 (Armor of God) | 에베소서 6:11 | `ANCHOR_EPH_6_11` | 4 | `theme_54_armor_of_god.json` |
| White Stone (Track B) | 시편 119:105 | `ANCHOR_WHITE_STONE` | 4 | `theme_550_white_stone.json` |
| Open Door (Track B) | 시편 119:105 | `ANCHOR_OPEN_DOOR` | 4 | `theme_551_open_door.json` |
| 라오디게아 미지근 (Lukewarm Laodicea) | 요한계시록 3:16 | `ANCHOR_LUKEWARM_LAODICEA` | 4 | `theme_552_lukewarm_laodicea.json` |
| Tree Life (Track B) | 시편 119:105 | `ANCHOR_TREE_LIFE` | 4 | `theme_553_tree_life.json` |
| Beast Mark (Track B) | 시편 119:105 | `ANCHOR_BEAST_MARK` | 4 | `theme_554_beast_mark.json` |
| Harvest Earth (Track B) | 시편 119:105 | `ANCHOR_HARVEST_EARTH` | 4 | `theme_555_harvest_earth.json` |
| Alpha Omega Throne (Track B) | 시편 119:105 | `ANCHOR_ALPHA_OMEGA_THRONE` | 4 | `theme_556_alpha_omega_throne.json` |
| Amos Basket (Track B) | 시편 119:105 | `ANCHOR_AMOS_BASKET` | 4 | `theme_557_amos_basket.json` |
| 바벨론 패망 (Babylon Fallen) | 요한계시록 18:2 | `ANCHOR_BABYLON_FALLEN` | 4 | `theme_558_babylon_fallen.json` |
| Beast Sea (Track B) | 시편 119:105 | `ANCHOR_BEAST_SEA` | 4 | `theme_559_beast_sea.json` |
| 최후 만찬 (Last Supper) | 누가복음 22:20 | `ANCHOR_LUK_22_20` | 4 | `theme_55_last_supper.json` |
| Dragon Cast (Track B) | 시편 119:105 | `ANCHOR_DRAGON_CAST` | 4 | `theme_560_dragon_cast.json` |
| Joshua Sun Stand (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_SUN_STAND` | 4 | `theme_561_joshua_sun_stand.json` |
| Lost Coin Parable (Track B) | 시편 119:105 | `ANCHOR_LOST_COIN_PARABLE` | 4 | `theme_562_lost_coin_parable.json` |
| Lost Sheep Parable (Track B) | 시편 119:105 | `ANCHOR_LOST_SHEEP_PARABLE` | 4 | `theme_563_lost_sheep_parable.json` |
| Marriage Supper (Track B) | 시편 119:105 | `ANCHOR_MARRIAGE_SUPPER` | 4 | `theme_564_marriage_supper.json` |
| New Jerusalem Gate (Track B) | 시편 119:105 | `ANCHOR_NEW_JERUSALEM_GATE` | 4 | `theme_565_new_jerusalem_gate.json` |
| Seal Forehead (Track B) | 시편 119:105 | `ANCHOR_SEAL_FOREHEAD` | 4 | `theme_566_seal_forehead.json` |
| Throne White (Track B) | 시편 119:105 | `ANCHOR_THRONE_WHITE` | 4 | `theme_567_throne_white.json` |
| Two Witnesses (Track B) | 시편 119:105 | `ANCHOR_TWO_WITNESSES` | 4 | `theme_568_two_witnesses.json` |
| Woman Clothed (Track B) | 시편 119:105 | `ANCHOR_WOMAN_CLOTHED` | 4 | `theme_569_woman_clothed.json` |
| 십자가 완료 (Cross Finished) | 요한복음 19:30 | `ANCHOR_JHN_19_30` | 4 | `theme_56_cross_finished.json` |
| Ark Noah Raven (Track B) | 시편 119:105 | `ANCHOR_ARK_NOAH_RAVEN` | 4 | `theme_570_ark_noah_raven.json` |
| Babel Gate (Track B) | 시편 119:105 | `ANCHOR_BABEL_GATE` | 4 | `theme_571_babel_gate.json` |
| Birth Esau (Track B) | 시편 119:105 | `ANCHOR_BIRTH_ESAU` | 4 | `theme_572_birth_esau.json` |
| Birth Jacob (Track B) | 시편 119:105 | `ANCHOR_BIRTH_JACOB` | 4 | `theme_573_birth_jacob.json` |
| Blessing Jacob (Track B) | 시편 119:105 | `ANCHOR_BLESSING_JACOB` | 4 | `theme_574_blessing_jacob.json` |
| Blessing Joseph (Track B) | 시편 119:105 | `ANCHOR_BLESSING_JOSEPH` | 4 | `theme_575_blessing_joseph.json` |
| Blood Passover (Track B) | 시편 119:105 | `ANCHOR_BLOOD_PASSOVER` | 4 | `theme_576_blood_passover.json` |
| Bondservant Paul (Track B) | 시편 119:105 | `ANCHOR_BONDSERVANT_PAUL` | 4 | `theme_577_bondservant_paul.json` |
| 생명책 (Book Life) | 요한계시록 20:12 | `ANCHOR_BOOK_LIFE` | 4 | `theme_578_book_life.json` |
| Bow Rainbow (Track B) | 시편 119:105 | `ANCHOR_BOW_RAINBOW` | 4 | `theme_579_bow_rainbow.json` |
| 엠마오 길 (Emmaus Road) | 누가복음 24:31 | `ANCHOR_LUK_24_31` | 4 | `theme_57_emmaus_road.json` |
| Branch Jesse (Track B) | 시편 119:105 | `ANCHOR_BRANCH_JESSE` | 4 | `theme_580_branch_jesse.json` |
| Bread Melchizedek (Track B) | 시편 119:105 | `ANCHOR_BREAD_MELCHIZEDEK` | 4 | `theme_581_bread_melchizedek.json` |
| Burning Sulfur (Track B) | 시편 119:105 | `ANCHOR_BURNING_SULFUR` | 4 | `theme_582_burning_sulfur.json` |
| Calf Gold (Track B) | 시편 119:105 | `ANCHOR_CALF_GOLD` | 4 | `theme_583_calf_gold.json` |
| Call Abraham (Track B) | 시편 119:105 | `ANCHOR_CALL_ABRAHAM` | 4 | `theme_584_call_abraham.json` |
| Call Moses (Track B) | 시편 119:105 | `ANCHOR_CALL_MOSES` | 4 | `theme_585_call_moses.json` |
| Call Samuel (Track B) | 시편 119:105 | `ANCHOR_CALL_SAMUEL` | 4 | `theme_586_call_samuel.json` |
| Census Moses (Track B) | 시편 119:105 | `ANCHOR_CENSUS_MOSES` | 4 | `theme_587_census_moses.json` |
| Chains Paul (Track B) | 시편 119:105 | `ANCHOR_CHAINS_PAUL` | 4 | `theme_588_chains_paul.json` |
| Chariot Fire (Track B) | 시편 119:105 | `ANCHOR_CHARIOT_FIRE` | 4 | `theme_589_chariot_fire.json` |
| 바울 회심 (Paul Conversion) | 사도행전 9:6 | `ANCHOR_ACT_9_6` | 4 | `theme_58_paul_conversion.json` |
| Child Laugh (Track B) | 시편 119:105 | `ANCHOR_CHILD_LAUGH` | 4 | `theme_590_child_laugh.json` |
| Chosen David (Track B) | 시편 119:105 | `ANCHOR_CHOSEN_DAVID` | 4 | `theme_591_chosen_david.json` |
| Cloud Glory (Track B) | 시편 119:105 | `ANCHOR_CLOUD_GLORY` | 4 | `theme_592_cloud_glory.json` |
| Coal Altar (Track B) | 시편 119:105 | `ANCHOR_COAL_ALTAR` | 4 | `theme_593_coal_altar.json` |
| Covenant Abraham (Track B) | 시편 119:105 | `ANCHOR_COVENANT_ABRAHAM` | 4 | `theme_594_covenant_abraham.json` |
| Covenant David (Track B) | 시편 119:105 | `ANCHOR_COVENANT_DAVID` | 4 | `theme_595_covenant_david.json` |
| Covenant Noah (Track B) | 시편 119:105 | `ANCHOR_COVENANT_NOAH` | 4 | `theme_596_covenant_noah.json` |
| Creation Man (Track B) | 시편 119:105 | `ANCHOR_CREATION_MAN` | 4 | `theme_597_creation_man.json` |
| Curse Ground (Track B) | 시편 119:105 | `ANCHOR_CURSE_GROUND` | 4 | `theme_598_curse_ground.json` |
| Day Atonement (Track B) | 시편 119:105 | `ANCHOR_DAY_ATONEMENT` | 4 | `theme_599_day_atonement.json` |
| 난파와 소망 (Shipwreck Hope) | 사도행전 27:25 | `ANCHOR_ACT_27_25` | 4 | `theme_59_shipwreck_hope.json` |
| Death Absalom (Track B) | 시편 119:105 | `ANCHOR_DEATH_ABSALOM` | 4 | `theme_600_death_absalom.json` |
| Denial Peter (Track B) | 시편 119:105 | `ANCHOR_DENIAL_PETER` | 4 | `theme_601_denial_peter.json` |
| Desert Elijah (Track B) | 시편 119:105 | `ANCHOR_DESERT_ELIJAH` | 4 | `theme_602_desert_elijah.json` |
| Dove Spirit (Track B) | 시편 119:105 | `ANCHOR_DOVE_SPIRIT` | 4 | `theme_603_dove_spirit.json` |
| Dream Joseph (Track B) | 시편 119:105 | `ANCHOR_DREAM_JOSEPH` | 4 | `theme_604_dream_joseph.json` |
| 마른 뼈 (Dry Bones) | 에스겔 37:7 | `ANCHOR_DRY_BONES` | 4 | `theme_605_dry_bones.json` |
| Eagle Wings (Track B) | 시편 119:105 | `ANCHOR_EAGLE_WINGS` | 4 | `theme_606_eagle_wings.json` |
| Eden Expelled (Track B) | 시편 119:105 | `ANCHOR_EDEN_EXPELLED` | 4 | `theme_607_eden_expelled.json` |
| Elisha Double (Track B) | 시편 119:105 | `ANCHOR_ELISHA_DOUBLE` | 4 | `theme_608_elisha_double.json` |
| Endurance Job (Track B) | 시편 119:105 | `ANCHOR_ENDURANCE_JOB` | 4 | `theme_609_endurance_job.json` |
| 빌립보 감옥 (Philippi Jail) | 사도행전 16:26 | `ANCHOR_ACT_16_26` | 4 | `theme_60_philippi_jail.json` |
| Esau Soup (Track B) | 시편 119:105 | `ANCHOR_ESAU_SOUP` | 4 | `theme_610_esau_soup.json` |
| Eve Fruit (Track B) | 시편 119:105 | `ANCHOR_EVE_FRUIT` | 4 | `theme_611_eve_fruit.json` |
| Exile Return (Track B) | 시편 119:105 | `ANCHOR_EXILE_RETURN` | 4 | `theme_612_exile_return.json` |
| Faith Abraham (Track B) | 시편 119:105 | `ANCHOR_FAITH_ABRAHAM` | 4 | `theme_613_faith_abraham.json` |
| Fall Tower (Track B) | 시편 119:105 | `ANCHOR_FALL_TOWER` | 4 | `theme_614_fall_tower.json` |
| Famine World (Track B) | 시편 119:105 | `ANCHOR_FAMINE_WORLD` | 4 | `theme_615_famine_world.json` |
| Fast Esther (Track B) | 시편 119:105 | `ANCHOR_FAST_ESTHER` | 4 | `theme_616_fast_esther.json` |
| Fear Not (Track B) | 시편 119:105 | `ANCHOR_FEAR_NOT` | 4 | `theme_617_fear_not.json` |
| Field Harvest (Track B) | 시편 119:105 | `ANCHOR_FIELD_HARVEST` | 4 | `theme_618_field_harvest.json` |
| Fire Pentecost (Track B) | 시편 119:105 | `ANCHOR_FIRE_PENTECOST` | 4 | `theme_619_fire_pentecost.json` |
| 도마 의심 (Thomas Doubt) | 요한복음 20:29 | `ANCHOR_JHN_20_29` | 4 | `theme_61_thomas_doubt.json` |
| Firstborn Death (Track B) | 시편 119:105 | `ANCHOR_FIRSTBORN_DEATH` | 4 | `theme_620_firstborn_death.json` |
| Flood Noah (Track B) | 시편 119:105 | `ANCHOR_FLOOD_NOAH` | 4 | `theme_621_flood_noah.json` |
| Forgive Seventy (Track B) | 시편 119:105 | `ANCHOR_FORGIVE_SEVENTY` | 4 | `theme_622_forgive_seventy.json` |
| Fountain Life (Track B) | 시편 119:105 | `ANCHOR_FOUNTAIN_LIFE` | 4 | `theme_623_fountain_life.json` |
| Four Winds (Track B) | 시편 119:105 | `ANCHOR_FOUR_WINDS` | 4 | `theme_624_four_winds.json` |
| Garment Salvation (Track B) | 시편 119:105 | `ANCHOR_GARMENT_SALVATION` | 4 | `theme_625_garment_salvation.json` |
| Gentiles Grafted (Track B) | 시편 119:105 | `ANCHOR_GENTILES_GRAFTED` | 4 | `theme_626_gentiles_grafted.json` |
| Giant Goliath (Track B) | 시편 119:105 | `ANCHOR_GIANT_GOLIATH` | 4 | `theme_627_giant_goliath.json` |
| Glory Tabernacle (Track B) | 시편 119:105 | `ANCHOR_GLORY_TABERNACLE` | 4 | `theme_628_glory_tabernacle.json` |
| God Provides (Track B) | 시편 119:105 | `ANCHOR_GOD_PROVIDES` | 4 | `theme_629_god_provides.json` |
| 루디아 보라 (Lydia Purple) | 사도행전 16:14 | `ANCHOR_ACT_16_14` | 4 | `theme_62_lydia_purple.json` |
| Golden Incense (Track B) | 시편 119:105 | `ANCHOR_GOLDEN_INCENSE` | 4 | `theme_630_golden_incense.json` |
| Good Cheer (Track B) | 시편 119:105 | `ANCHOR_GOOD_CHEER` | 4 | `theme_631_good_cheer.json` |
| Gospel Preach (Track B) | 시편 119:105 | `ANCHOR_GOSPEL_PREACH` | 4 | `theme_632_gospel_preach.json` |
| Grace Sufficient (Track B) | 시편 119:105 | `ANCHOR_GRACE_SUFFICIENT` | 4 | `theme_633_grace_sufficient.json` |
| Grapes Wild (Track B) | 시편 119:105 | `ANCHOR_GRAPES_WILD` | 4 | `theme_634_grapes_wild.json` |
| Handwriting Wall (Track B) | 시편 119:105 | `ANCHOR_HANDWRITING_WALL` | 4 | `theme_635_handwriting_wall.json` |
| Healing Nations (Track B) | 시편 119:105 | `ANCHOR_HEALING_NATIONS` | 4 | `theme_636_healing_nations.json` |
| Heart Circumcise (Track B) | 시편 119:105 | `ANCHOR_HEART_CIRCUMCISE` | 4 | `theme_637_heart_circumcise.json` |
| Heaven Opened (Track B) | 시편 119:105 | `ANCHOR_HEAVEN_OPENED` | 4 | `theme_638_heaven_opened.json` |
| Hell Gehenna (Track B) | 시편 119:105 | `ANCHOR_HELL_GEHENNA` | 4 | `theme_639_hell_gehenna.json` |
| 고넬료 환상 (Cornelius Vision) | 사도행전 10:3 | `ANCHOR_ACT_10_3` | 4 | `theme_63_cornelius_vision.json` |
| Holy Spirit (Track B) | 시편 119:105 | `ANCHOR_HOLY_SPIRIT` | 4 | `theme_640_holy_spirit.json` |
| Hope Anchor (Track B) | 시편 119:105 | `ANCHOR_HOPE_ANCHOR` | 4 | `theme_641_hope_anchor.json` |
| Horn Salvation (Track B) | 시편 119:105 | `ANCHOR_HORN_SALVATION` | 4 | `theme_642_horn_salvation.json` |
| Hosanna Cry (Track B) | 시편 119:105 | `ANCHOR_HOSANNA_CRY` | 4 | `theme_643_hosanna_cry.json` |
| Image Daniel (Track B) | 시편 119:105 | `ANCHOR_IMAGE_DANIEL` | 4 | `theme_644_image_daniel.json` |
| Incense Prayer (Track B) | 시편 119:105 | `ANCHOR_INCENSE_PRAYER` | 4 | `theme_645_incense_prayer.json` |
| Inheritance Lot (Track B) | 시편 119:105 | `ANCHOR_INHERITANCE_LOT` | 4 | `theme_646_inheritance_lot.json` |
| Israel Stiff (Track B) | 시편 119:105 | `ANCHOR_ISRAEL_STIFF` | 4 | `theme_647_israel_stiff.json` |
| Jordan Cross (Track B) | 시편 119:105 | `ANCHOR_JORDAN_CROSS` | 4 | `theme_648_jordan_cross.json` |
| Joy Salvation (Track B) | 시편 119:105 | `ANCHOR_JOY_SALVATION` | 4 | `theme_649_joy_salvation.json` |
| 스데반 증언 (Stephen Witness) | 사도행전 7:59 | `ANCHOR_ACT_7_59` | 4 | `theme_64_stephen_witness.json` |
| Judgment Seat (Track B) | 시편 119:105 | `ANCHOR_JUDGMENT_SEAT` | 4 | `theme_650_judgment_seat.json` |
| Kingdom Parables (Track B) | 시편 119:105 | `ANCHOR_KINGDOM_PARABLES` | 4 | `theme_651_kingdom_parables.json` |
| Lamb Passover (Track B) | 시편 119:105 | `ANCHOR_LAMB_PASSOVER` | 4 | `theme_652_lamb_passover.json` |
| Lamp Oil (Track B) | 시편 119:105 | `ANCHOR_LAMP_OIL` | 4 | `theme_653_lamp_oil.json` |
| Law Grace (Track B) | 시편 119:105 | `ANCHOR_LAW_GRACE` | 4 | `theme_654_law_grace.json` |
| Leaven Sins (Track B) | 시편 119:105 | `ANCHOR_LEAVEN_SINS` | 4 | `theme_655_leaven_sins.json` |
| Light World (Track B) | 시편 119:105 | `ANCHOR_LIGHT_WORLD` | 4 | `theme_656_light_world.json` |
| Lion Judah (Track B) | 시편 119:105 | `ANCHOR_LION_JUDAH` | 4 | `theme_657_lion_judah.json` |
| Living Stone (Track B) | 시편 119:105 | `ANCHOR_LIVING_STONE` | 4 | `theme_658_living_stone.json` |
| Loaves Fishes (Track B) | 시편 119:105 | `ANCHOR_LOAVES_FISHES` | 4 | `theme_659_loaves_fishes.json` |
| 디모데 젊음 (Timothy Youth) | 디모데전서 4:12 | `ANCHOR_1TI_4_12` | 4 | `theme_65_timothy_youth.json` |
| Love Enemies (Track B) | 시편 119:105 | `ANCHOR_LOVE_ENEMIES` | 4 | `theme_660_love_enemies.json` |
| Man Sower (Track B) | 시편 119:105 | `ANCHOR_MAN_SOWER` | 4 | `theme_661_man_sower.json` |
| Manna Heaven (Track B) | 시편 119:105 | `ANCHOR_MANNA_HEAVEN` | 4 | `theme_662_manna_heaven.json` |
| Mark Cain (Track B) | 시편 119:105 | `ANCHOR_MARK_CAIN` | 4 | `theme_663_mark_cain.json` |
| Marriage King (Track B) | 시편 119:105 | `ANCHOR_MARRIAGE_KING` | 4 | `theme_664_marriage_king.json` |
| Mercy Seat (Track B) | 시편 119:105 | `ANCHOR_MERCY_SEAT` | 4 | `theme_665_mercy_seat.json` |
| Messiah Anointed (Track B) | 시편 119:105 | `ANCHOR_MESSIAH_ANOINTED` | 4 | `theme_666_messiah_anointed.json` |
| Millstone Neck (Track B) | 시편 119:105 | `ANCHOR_MILLSTONE_NECK` | 4 | `theme_667_millstone_neck.json` |
| Miracle Sign (Track B) | 시편 119:105 | `ANCHOR_MIRACLE_SIGN` | 4 | `theme_668_miracle_sign.json` |
| Miry Clay (Track B) | 시편 119:105 | `ANCHOR_MIRY_CLAY` | 4 | `theme_669_miry_clay.json` |
| 바나바 권면 (Barnabas Encourage) | 사도행전 11:23 | `ANCHOR_ACT_11_23` | 4 | `theme_66_barnabas_encourage.json` |
| Mount Olives (Track B) | 시편 119:105 | `ANCHOR_MOUNT_OLIVES` | 4 | `theme_670_mount_olives.json` |
| Mountain Zion (Track B) | 시편 119:105 | `ANCHOR_MOUNTAIN_ZION` | 4 | `theme_671_mountain_zion.json` |
| Mustard Faith (Track B) | 시편 119:105 | `ANCHOR_MUSTARD_FAITH` | 4 | `theme_672_mustard_faith.json` |
| Name Jesus (Track B) | 시편 119:105 | `ANCHOR_NAME_JESUS` | 4 | `theme_673_name_jesus.json` |
| New Wine (Track B) | 시편 119:105 | `ANCHOR_NEW_WINE` | 4 | `theme_674_new_wine.json` |
| Night Watch (Track B) | 시편 119:105 | `ANCHOR_NIGHT_WATCH` | 4 | `theme_675_night_watch.json` |
| Oil Anoint (Track B) | 시편 119:105 | `ANCHOR_OIL_ANOINT` | 4 | `theme_676_oil_anoint.json` |
| Olive Tree (Track B) | 시편 119:105 | `ANCHOR_OLIVE_TREE` | 4 | `theme_677_olive_tree.json` |
| Open Grave (Track B) | 시편 119:105 | `ANCHOR_OPEN_GRAVE` | 4 | `theme_678_open_grave.json` |
| Oracle Balaam (Track B) | 시편 119:105 | `ANCHOR_ORACLE_BALAAM` | 4 | `theme_679_oracle_balaam.json` |
| 알파와 오메가 (Alpha Omega) | 요한계시록 22:13 | `ANCHOR_REV_22_13` | 4 | `theme_67_alpha_omega.json` |
| Overcomer Crown (Track B) | 시편 119:105 | `ANCHOR_OVERCOMER_CROWN` | 4 | `theme_680_overcomer_crown.json` |
| Patience Job (Track B) | 시편 119:105 | `ANCHOR_PATIENCE_JOB` | 4 | `theme_681_patience_job.json` |
| Peace Prince (Track B) | 시편 119:105 | `ANCHOR_PEACE_PRINCE` | 4 | `theme_682_peace_prince.json` |
| Pentecost Flame (Track B) | 시편 119:105 | `ANCHOR_PENTECOST_FLAME` | 4 | `theme_683_pentecost_flame.json` |
| Persecution Blessed (Track B) | 시편 119:105 | `ANCHOR_PERSECUTION_BLESSED` | 4 | `theme_684_persecution_blessed.json` |
| Pharaoh Dreams (Track B) | 시편 119:105 | `ANCHOR_PHARAOH_DREAMS` | 4 | `theme_685_pharaoh_dreams.json` |
| Pillar Fire (Track B) | 시편 119:105 | `ANCHOR_PILLAR_FIRE` | 4 | `theme_686_pillar_fire.json` |
| Plague Locusts (Track B) | 시편 119:105 | `ANCHOR_PLAGUE_LOCUSTS` | 4 | `theme_687_plague_locusts.json` |
| 토기장이 진흙 (Potter Clay) | 예레미야 18:6 | `ANCHOR_POTTER_CLAY` | 4 | `theme_688_potter_clay.json` |
| Power Spirit (Track B) | 시편 119:105 | `ANCHOR_POWER_SPIRIT` | 4 | `theme_689_power_spirit.json` |
| 겨자씨 믿음 (Mustard Seed Faith) | 마태복음 17:20 | `ANCHOR_MAT_17_20` | 4 | `theme_68_mustard_seed_faith.json` |
| Praise Temple (Track B) | 시편 119:105 | `ANCHOR_PRAISE_TEMPLE` | 4 | `theme_690_praise_temple.json` |
| Prayer Fervent (Track B) | 시편 119:105 | `ANCHOR_PRAYER_FERVENT` | 4 | `theme_691_prayer_fervent.json` |
| Priest Melchizedek (Track B) | 시편 119:105 | `ANCHOR_PRIEST_MELCHIZEDEK` | 4 | `theme_692_priest_melchizedek.json` |
| Promise Land (Track B) | 시편 119:105 | `ANCHOR_PROMISE_LAND` | 4 | `theme_693_promise_land.json` |
| Prophecy Fulfill (Track B) | 시편 119:105 | `ANCHOR_PROPHECY_FULFILL` | 4 | `theme_694_prophecy_fulfill.json` |
| Providence God (Track B) | 시편 119:105 | `ANCHOR_PROVIDENCE_GOD` | 4 | `theme_695_providence_god.json` |
| Pure Heart (Track B) | 시편 119:105 | `ANCHOR_PURE_HEART` | 4 | `theme_696_pure_heart.json` |
| Rain Latter (Track B) | 시편 119:105 | `ANCHOR_RAIN_LATTER` | 4 | `theme_697_rain_latter.json` |
| Redeemer Boaz (Track B) | 시편 119:105 | `ANCHOR_REDEEMER_BOAZ` | 4 | `theme_698_redeemer_boaz.json` |
| Refiner Fire (Track B) | 시편 119:105 | `ANCHOR_REFINER_FIRE` | 4 | `theme_699_refiner_fire.json` |
| 선한 싸움 (Good Fight) | 디모데전서 6:12 | `ANCHOR_1TI_6_12` | 4 | `theme_69_good_fight.json` |
| Repent Baptize (Track B) | 시편 119:105 | `ANCHOR_REPENT_BAPTIZE` | 4 | `theme_700_repent_baptize.json` |
| Rest Sabbath (Track B) | 시편 119:105 | `ANCHOR_REST_SABBATH` | 4 | `theme_701_rest_sabbath.json` |
| Resurrection Body (Track B) | 시편 119:105 | `ANCHOR_RESURRECTION_BODY` | 4 | `theme_702_resurrection_body.json` |
| Righteous Lot (Track B) | 시편 119:105 | `ANCHOR_RIGHTEOUS_LOT` | 4 | `theme_703_righteous_lot.json` |
| River Eden (Track B) | 시편 119:105 | `ANCHOR_RIVER_EDEN` | 4 | `theme_704_river_eden.json` |
| Rock Moses (Track B) | 시편 119:105 | `ANCHOR_ROCK_MOSES` | 4 | `theme_705_rock_moses.json` |
| Rod Iron (Track B) | 시편 119:105 | `ANCHOR_ROD_IRON` | 4 | `theme_706_rod_iron.json` |
| Root Jesse (Track B) | 시편 119:105 | `ANCHOR_ROOT_JESSE` | 4 | `theme_707_root_jesse.json` |
| Sabbath Rest (Track B) | 시편 119:105 | `ANCHOR_SABBATH_REST` | 4 | `theme_708_sabbath_rest.json` |
| Sacrifice Praise (Track B) | 시편 119:105 | `ANCHOR_SACRIFICE_PRAISE` | 4 | `theme_709_sacrifice_praise.json` |
| 과부 헌금 (Widow Mite) | 마가복음 12:43 | `ANCHOR_MRK_12_43` | 4 | `theme_70_widow_mite.json` |
| Salt Covenant (Track B) | 시편 119:105 | `ANCHOR_SALT_COVENANT` | 4 | `theme_710_salt_covenant.json` |
| Sanctuary God (Track B) | 시편 119:105 | `ANCHOR_SANCTUARY_GOD` | 4 | `theme_711_sanctuary_god.json` |
| Scroll Ezekiel (Track B) | 시편 119:105 | `ANCHOR_SCROLL_EZEKIEL` | 4 | `theme_712_scroll_ezekiel.json` |
| Second Death (Track B) | 시편 119:105 | `ANCHOR_SECOND_DEATH` | 4 | `theme_713_second_death.json` |
| Seed Word (Track B) | 시편 119:105 | `ANCHOR_SEED_WORD` | 4 | `theme_714_seed_word.json` |
| Servant Moses (Track B) | 시편 119:105 | `ANCHOR_SERVANT_MOSES` | 4 | `theme_715_servant_moses.json` |
| Seven Spirits (Track B) | 시편 119:105 | `ANCHOR_SEVEN_SPIRITS` | 4 | `theme_716_seven_spirits.json` |
| Shepherd King (Track B) | 시편 119:105 | `ANCHOR_SHEPHERD_KING` | 4 | `theme_717_shepherd_king.json` |
| Sign Covenant (Track B) | 시편 119:105 | `ANCHOR_SIGN_COVENANT` | 4 | `theme_718_sign_covenant.json` |
| Sin Scapegoat (Track B) | 시편 119:105 | `ANCHOR_SIN_SCAPEGOAT` | 4 | `theme_719_sin_scapegoat.json` |
| 촛대 교회 (Lampstand Church) | 요한계시록 2:5 | `ANCHOR_REV_2_5` | 4 | `theme_71_lampstand_church.json` |
| Sower Word (Track B) | 시편 119:105 | `ANCHOR_SOWER_WORD` | 4 | `theme_720_sower_word.json` |
| Spirit Truth (Track B) | 시편 119:105 | `ANCHOR_SPIRIT_TRUTH` | 4 | `theme_721_spirit_truth.json` |
| Star Bethlehem (Track B) | 시편 119:105 | `ANCHOR_STAR_BETHLEHEM` | 4 | `theme_722_star_bethlehem.json` |
| Stone Rolled (Track B) | 시편 119:105 | `ANCHOR_STONE_ROLLED` | 4 | `theme_723_stone_rolled.json` |
| Storm Calmed (Track B) | 시편 119:105 | `ANCHOR_STORM_CALMED` | 4 | `theme_724_storm_calmed.json` |
| Strong Delusion (Track B) | 시편 119:105 | `ANCHOR_STRONG_DELUSION` | 4 | `theme_725_strong_delusion.json` |
| Suffering Christ (Track B) | 시편 119:105 | `ANCHOR_SUFFERING_CHRIST` | 4 | `theme_726_suffering_christ.json` |
| Tabernacle God (Track B) | 시편 119:105 | `ANCHOR_TABERNACLE_GOD` | 4 | `theme_727_tabernacle_god.json` |
| Temple Body (Track B) | 시편 119:105 | `ANCHOR_TEMPLE_BODY` | 4 | `theme_728_temple_body.json` |
| Tent Meeting (Track B) | 시편 119:105 | `ANCHOR_TENT_MEETING` | 4 | `theme_729_tent_meeting.json` |
| 생수 (Living Water) | 요한복음 4:14 | `ANCHOR_JHN_4_14` | 4 | `theme_72_living_water.json` |
| Test Abraham (Track B) | 시편 119:105 | `ANCHOR_TEST_ABRAHAM` | 4 | `theme_730_test_abraham.json` |
| Thorn Crown (Track B) | 시편 119:105 | `ANCHOR_THORN_CROWN` | 4 | `theme_731_thorn_crown.json` |
| Three Hebrews (Track B) | 시편 119:105 | `ANCHOR_THREE_HEBREWS` | 4 | `theme_732_three_hebrews.json` |
| Threshing Floor (Track B) | 시편 119:105 | `ANCHOR_THRESHING_FLOOR` | 4 | `theme_733_threshing_floor.json` |
| Tithe Melchizedek (Track B) | 시편 119:105 | `ANCHOR_TITHE_MELCHIZEDEK` | 4 | `theme_734_tithe_melchizedek.json` |
| Tongue Control (Track B) | 시편 119:105 | `ANCHOR_TONGUE_CONTROL` | 4 | `theme_735_tongue_control.json` |
| Tower Siloam (Track B) | 시편 119:105 | `ANCHOR_TOWER_SILOAM` | 4 | `theme_736_tower_siloam.json` |
| Tree Planted (Track B) | 시편 119:105 | `ANCHOR_TREE_PLANTED` | 4 | `theme_737_tree_planted.json` |
| Tribulation Saints (Track B) | 시편 119:105 | `ANCHOR_TRIBULATION_SAINTS` | 4 | `theme_738_tribulation_saints.json` |
| Trumpet Judgment (Track B) | 시편 119:105 | `ANCHOR_TRUMPET_JUDGMENT` | 4 | `theme_739_trumpet_judgment.json` |
| 생명의 떡 (Bread of Life) | 요한복음 6:35 | `ANCHOR_JHN_6_35` | 4 | `theme_73_bread_of_life.json` |
| Truth Sets Free (Track B) | 시편 119:105 | `ANCHOR_TRUTH_SETS_FREE` | 4 | `theme_740_truth_sets_free.json` |
| Unity Spirit (Track B) | 시편 119:105 | `ANCHOR_UNITY_SPIRIT` | 4 | `theme_741_unity_spirit.json` |
| Valley Decision (Track B) | 시편 119:105 | `ANCHOR_VALLEY_DECISION` | 4 | `theme_742_valley_decision.json` |
| Vine True (Track B) | 시편 119:105 | `ANCHOR_VINE_TRUE` | 4 | `theme_743_vine_true.json` |
| Voice Lamb (Track B) | 시편 119:105 | `ANCHOR_VOICE_LAMB` | 4 | `theme_744_voice_lamb.json` |
| Walk Emmaus (Track B) | 시편 119:105 | `ANCHOR_WALK_EMMAUS` | 4 | `theme_745_walk_emmaus.json` |
| 여리고 성벽 (Wall Jericho) | 여호수아 6:20 | `ANCHOR_WALL_JERICHO` | 4 | `theme_746_wall_jericho.json` |
| War Heaven (Track B) | 시편 119:105 | `ANCHOR_WAR_HEAVEN` | 4 | `theme_747_war_heaven.json` |
| Watchman Wall (Track B) | 시편 119:105 | `ANCHOR_WATCHMAN_WALL` | 4 | `theme_748_watchman_wall.json` |
| Water Baptism (Track B) | 시편 119:105 | `ANCHOR_WATER_BAPTISM` | 4 | `theme_749_water_baptism.json` |
| 선한 목자 문 (Good Shepherd Gate) | 요한복음 10:9 | `ANCHOR_JHN_10_9` | 4 | `theme_74_good_shepherd_gate.json` |
| 길 진리 생명 (Way Truth Life) | 요한복음 14:6 | `ANCHOR_WAY_TRUTH_LIFE` | 4 | `theme_750_way_truth_life.json` |
| Wheat Harvest (Track B) | 시편 119:105 | `ANCHOR_WHEAT_HARVEST` | 4 | `theme_751_wheat_harvest.json` |
| Whirlwind God (Track B) | 시편 119:105 | `ANCHOR_WHIRLWIND_GOD` | 4 | `theme_752_whirlwind_god.json` |
| Widow Oil (Track B) | 시편 119:105 | `ANCHOR_WIDOW_OIL` | 4 | `theme_753_widow_oil.json` |
| Wilderness Test (Track B) | 시편 119:105 | `ANCHOR_WILDERNESS_TEST` | 4 | `theme_754_wilderness_test.json` |
| Wine Blood (Track B) | 시편 119:105 | `ANCHOR_WINE_BLOOD` | 4 | `theme_755_wine_blood.json` |
| Wisdom Solomon (Track B) | 시편 119:105 | `ANCHOR_WISDOM_SOLOMON` | 4 | `theme_756_wisdom_solomon.json` |
| Witness Cloud (Track B) | 시편 119:105 | `ANCHOR_WITNESS_CLOUD` | 4 | `theme_757_witness_cloud.json` |
| Woman Wisdom (Track B) | 시편 119:105 | `ANCHOR_WOMAN_WISDOM` | 4 | `theme_758_woman_wisdom.json` |
| Word Incarnate (Track B) | 시편 119:105 | `ANCHOR_WORD_INCARNATE` | 4 | `theme_759_word_incarnate.json` |
| 귀한 진주 (Pearl of Great Price) | 마태복음 13:45 | `ANCHOR_MAT_13_45` | 4 | `theme_75_pearl_great_price.json` |
| Wrath Lamb (Track B) | 시편 119:105 | `ANCHOR_WRATH_LAMB` | 4 | `theme_760_wrath_lamb.json` |
| Yoke Easy (Track B) | 시편 119:105 | `ANCHOR_YOKE_EASY` | 4 | `theme_761_yoke_easy.json` |
| Zeal House (Track B) | 시편 119:105 | `ANCHOR_ZEAL_HOUSE` | 4 | `theme_762_zeal_house.json` |
| Zion Hill (Track B) | 시편 119:105 | `ANCHOR_ZION_HILL` | 4 | `theme_763_zion_hill.json` |
| Creation Sabbath (Track B) | 시편 119:105 | `ANCHOR_CREATION_SABBATH` | 4 | `theme_764_creation_sabbath.json` |
| Sabbath Creator (Track B) | 시편 119:105 | `ANCHOR_SABBATH_CREATOR` | 4 | `theme_765_sabbath_creator.json` |
| Abraham Oath (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_OATH` | 4 | `theme_766_abraham_oath.json` |
| Isaac Wells Dig (Track B) | 시편 119:105 | `ANCHOR_ISAAC_WELLS_DIG` | 4 | `theme_767_isaac_wells_dig.json` |
| Jacob Peeled Rods (Track B) | 시편 119:105 | `ANCHOR_JACOB_PEELED_RODS` | 4 | `theme_768_jacob_peeled_rods.json` |
| Leah Weak Eyes (Track B) | 시편 119:105 | `ANCHOR_LEAH_WEAK_EYES` | 4 | `theme_769_leah_weak_eyes.json` |
| 달란트 청지기 (Talents Stewardship) | 마태복음 25:21 | `ANCHOR_MAT_25_21` | 4 | `theme_76_talents_stewardship.json` |
| Rachel Beautiful (Track B) | 시편 119:105 | `ANCHOR_RACHEL_BEAUTIFUL` | 4 | `theme_770_rachel_beautiful.json` |
| Benjamin Wolf (Track B) | 시편 119:105 | `ANCHOR_BENJAMIN_WOLF` | 4 | `theme_771_benjamin_wolf.json` |
| Dan Serpent (Track B) | 시편 119:105 | `ANCHOR_DAN_SERPENT` | 4 | `theme_772_dan_serpent.json` |
| Naphtali Deer (Track B) | 시편 119:105 | `ANCHOR_NAPHTALI_DEER` | 4 | `theme_773_naphtali_deer.json` |
| Issachar Donkey (Track B) | 시편 119:105 | `ANCHOR_ISSACHAR_DONKEY` | 4 | `theme_774_issachar_donkey.json` |
| Zebulun Haven (Track B) | 시편 119:105 | `ANCHOR_ZEBULUN_HAVEN` | 4 | `theme_775_zebulun_haven.json` |
| Asher Bread (Track B) | 시편 119:105 | `ANCHOR_ASHER_BREAD` | 4 | `theme_776_asher_bread.json` |
| Gad Troop (Track B) | 시편 119:105 | `ANCHOR_GAD_TROOP` | 4 | `theme_777_gad_troop.json` |
| Manasseh Vine (Track B) | 시편 119:105 | `ANCHOR_MANASSEH_VINE` | 4 | `theme_778_manasseh_vine.json` |
| Ephraim Fruit (Track B) | 시편 119:105 | `ANCHOR_EPHRAIM_FRUIT` | 4 | `theme_779_ephraim_fruit.json` |
| 지혜로운 처녀 (Wise Virgins) | 마태복음 25:10 | `ANCHOR_MAT_25_10` | 4 | `theme_77_wise_virgins.json` |
| Simeon Sword (Track B) | 시편 119:105 | `ANCHOR_SIMEON_SWORD` | 4 | `theme_780_simeon_sword.json` |
| Reuben Water (Track B) | 시편 119:105 | `ANCHOR_REUBEN_WATER` | 4 | `theme_781_reuben_water.json` |
| Judah Lion Cub (Track B) | 시편 119:105 | `ANCHOR_JUDAH_LION_CUB` | 4 | `theme_782_judah_lion_cub.json` |
| Moses Mechuzoth (Track B) | 시편 119:105 | `ANCHOR_MOSES_MECHUZOTH` | 4 | `theme_783_moses_mechuzoth.json` |
| Aaron Budding Rod (Track B) | 시편 119:105 | `ANCHOR_AARON_BUDDING_ROD` | 4 | `theme_784_aaron_budding_rod.json` |
| Korah Incense (Track B) | 시편 119:105 | `ANCHOR_KORAH_INCENSE` | 4 | `theme_785_korah_incense.json` |
| Aaron Rod Bud (Track B) | 시편 119:105 | `ANCHOR_AARON_ROD_BUD` | 4 | `theme_786_aaron_rod_bud.json` |
| Serpent Fiery (Track B) | 시편 119:105 | `ANCHOR_SERPENT_FIERY` | 4 | `theme_787_serpent_fiery.json` |
| Balak Balaam (Track B) | 시편 119:105 | `ANCHOR_BALAK_BALAAM` | 4 | `theme_788_balak_balaam.json` |
| Moab Seduction (Track B) | 시편 119:105 | `ANCHOR_MOAB_SEDUCTION` | 4 | `theme_789_moab_seduction.json` |
| 백부장 믿음 (Centurion Faith) | 마태복음 8:10 | `ANCHOR_MAT_8_10` | 4 | `theme_78_centurion_faith.json` |
| Phinehas Zeal (Track B) | 시편 119:105 | `ANCHOR_PHINEHAS_ZEAL` | 4 | `theme_790_phinehas_zeal.json` |
| Joshua Caleb (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_CALEB` | 4 | `theme_791_joshua_caleb.json` |
| Othniel Captor (Track B) | 시편 119:105 | `ANCHOR_OTHNIEL_CAPTOR` | 4 | `theme_792_othniel_captor.json` |
| Gideon Fleece Dew (Track B) | 시편 119:105 | `ANCHOR_GIDEON_FLEECE_DEW` | 4 | `theme_793_gideon_fleece_dew.json` |
| Samson Riddle (Track B) | 시편 119:105 | `ANCHOR_SAMSON_RIDDLE` | 4 | `theme_794_samson_riddle.json` |
| Samson Delilah (Track B) | 시편 119:105 | `ANCHOR_SAMSON_DELILAH` | 4 | `theme_795_samson_delilah.json` |
| Ruth Boaz Field (Track B) | 시편 119:105 | `ANCHOR_RUTH_BOAZ_FIELD` | 4 | `theme_796_ruth_boaz_field.json` |
| Eli Ark Taken (Track B) | 시편 119:105 | `ANCHOR_ELI_ARK_TAKEN` | 4 | `theme_797_eli_ark_taken.json` |
| Samuel Anoints Saul (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_ANOINTS_SAUL` | 4 | `theme_798_samuel_anoints_saul.json` |
| David Nabal (Track B) | 시편 119:105 | `ANCHOR_DAVID_NABAL` | 4 | `theme_799_david_nabal.json` |
| 삭개오 나무 (Zacchaeus Tree) | 누가복음 19:5 | `ANCHOR_LUK_19_5` | 4 | `theme_79_zacchaeus_tree.json` |
| Abigail Peacemaker (Track B) | 시편 119:105 | `ANCHOR_ABIGAIL_PEACEMAKER` | 4 | `theme_800_abigail_peacemaker.json` |
| Absalom Oak Hair (Track B) | 시편 119:105 | `ANCHOR_ABSALOM_OAK_HAIR` | 4 | `theme_801_absalom_oak_hair.json` |
| Solomon Proverbs (Track B) | 시편 119:105 | `ANCHOR_SOLOMON_PROVERBS` | 4 | `theme_802_solomon_proverbs.json` |
| Queen Sheba Riddles (Track B) | 시편 119:105 | `ANCHOR_QUEEN_SHEBA_RIDDLES` | 4 | `theme_803_queen_sheba_riddles.json` |
| Elijah Mount Carmel (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_MOUNT_CARMEL` | 4 | `theme_804_elijah_mount_carmel.json` |
| Ahab Naboth (Track B) | 시편 119:105 | `ANCHOR_AHAB_NABOTH` | 4 | `theme_805_ahab_naboth.json` |
| Jehu Furious (Track B) | 시편 119:105 | `ANCHOR_JEHU_FURIOUS` | 4 | `theme_806_jehu_furious.json` |
| Joash Crown (Track B) | 시편 119:105 | `ANCHOR_JOASH_CROWN` | 4 | `theme_807_joash_crown.json` |
| Hezekiah Sundial Back (Track B) | 시편 119:105 | `ANCHOR_HEZEKIAH_SUNDIAL_BACK` | 4 | `theme_808_hezekiah_sundial_back.json` |
| Manasseh Altar (Track B) | 시편 119:105 | `ANCHOR_MANASSEH_ALTAR` | 4 | `theme_809_manasseh_altar.json` |
| 씨 뿌리는 자 (Sower Soils) | 마태복음 13:8 | `ANCHOR_MAT_13_8` | 4 | `theme_80_sower_soils.json` |
| Josiah Book Found (Track B) | 시편 119:105 | `ANCHOR_JOSIAH_BOOK_FOUND` | 4 | `theme_810_josiah_book_found.json` |
| Jeremiah Linen Belt (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_LINEN_BELT` | 4 | `theme_811_jeremiah_linen_belt.json` |
| 에스겔 바퀴 (Ezekiel Wheels) | 에스겔 1:16 | `ANCHOR_EZEKIEL_WHEELS` | 4 | `theme_812_ezekiel_wheels.json` |
| Daniel Stone (Track B) | 시편 119:105 | `ANCHOR_DANIEL_STONE` | 4 | `theme_813_daniel_stone.json` |
| Cyrus Issued (Track B) | 시편 119:105 | `ANCHOR_CYRUS_ISSUED` | 4 | `theme_814_cyrus_issued.json` |
| Ezra Scribe (Track B) | 시편 119:105 | `ANCHOR_EZRA_SCRIBE` | 4 | `theme_815_ezra_scribe.json` |
| Nehemiah Governor (Track B) | 시편 119:105 | `ANCHOR_NEHEMIAH_GOVERNOR` | 4 | `theme_816_nehemiah_governor.json` |
| Esther Courage (Track B) | 시편 119:105 | `ANCHOR_ESTHER_COURAGE` | 4 | `theme_817_esther_courage.json` |
| Job Ash Heap (Track B) | 시편 119:105 | `ANCHOR_JOB_ASH_HEAP` | 4 | `theme_818_job_ash_heap.json` |
| Proverbs Woman (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_WOMAN` | 4 | `theme_819_proverbs_woman.json` |
| 니고데모 밤 (Nicodemus Night) | 요한복음 3:3 | `ANCHOR_JHN_3_3` | 4 | `theme_81_nicodemus_night.json` |
| Song Beloved (Track B) | 시편 119:105 | `ANCHOR_SONG_BELOVED` | 4 | `theme_820_song_beloved.json` |
| Isaiah Virgin (Track B) | 시편 119:105 | `ANCHOR_ISAIAH_VIRGIN` | 4 | `theme_821_isaiah_virgin.json` |
| Jeremiah Potter Clay (Track B) | 시편 119:105 | `ANCHOR_JEREMIAH_POTTER_CLAY` | 4 | `theme_822_jeremiah_potter_clay.json` |
| Lamentations City (Track B) | 시편 119:105 | `ANCHOR_LAMENTATIONS_CITY` | 4 | `theme_823_lamentations_city.json` |
| Ezechiel Dry (Track B) | 시편 119:105 | `ANCHOR_EZECHIEL_DRY` | 4 | `theme_824_ezechiel_dry.json` |
| 다니엘 사자굴 (Daniel Lions Den) | 다니엘 6:22 | `ANCHOR_DANIEL_LIONS_DEN` | 4 | `theme_825_daniel_lions_den.json` |
| Hosea Unfaithful (Track B) | 시편 119:105 | `ANCHOR_HOSEA_UNFAITHFUL` | 4 | `theme_826_hosea_unfaithful.json` |
| Joel Locusts (Track B) | 시편 119:105 | `ANCHOR_JOEL_LOCUSTS` | 4 | `theme_827_joel_locusts.json` |
| Amos Plumbline (Track B) | 시편 119:105 | `ANCHOR_AMOS_PLUMBLINE` | 4 | `theme_828_amos_plumbline.json` |
| Obadiah Proud (Track B) | 시편 119:105 | `ANCHOR_OBADIAH_PROUD` | 4 | `theme_829_obadiah_proud.json` |
| 사마리아 우물 (Woman at the Well) | 요한복음 4:14 | `ANCHOR_JHN_4_14_WELL` | 4 | `theme_82_woman_well_samaria.json` |
| Jonah Gourd Shade (Track B) | 시편 119:105 | `ANCHOR_JONAH_GOURD_SHADE` | 4 | `theme_830_jonah_gourd_shade.json` |
| Micah Swords Beat (Track B) | 시편 119:105 | `ANCHOR_MICAH_SWORDS_BEAT` | 4 | `theme_831_micah_swords_beat.json` |
| Nahum Runner (Track B) | 시편 119:105 | `ANCHOR_NAHUM_RUNNER` | 4 | `theme_832_nahum_runner.json` |
| Zephaniah Day Silent (Track B) | 시편 119:105 | `ANCHOR_ZEPHANIAH_DAY_SILENT` | 4 | `theme_833_zephaniah_day_silent.json` |
| Haggai Temple Rebuild (Track B) | 시편 119:105 | `ANCHOR_HAGGAI_TEMPLE_REBUILD` | 4 | `theme_834_haggai_temple_rebuild.json` |
| Malachi Sun Healing (Track B) | 시편 119:105 | `ANCHOR_MALACHI_SUN_HEALING` | 4 | `theme_835_malachi_sun_healing.json` |
| Matthew Genealogy (Track B) | 시편 119:105 | `ANCHOR_MATTHEW_GENEALOGY` | 4 | `theme_836_matthew_genealogy.json` |
| Mark Urgency (Track B) | 시편 119:105 | `ANCHOR_MARK_URGENCY` | 4 | `theme_837_mark_urgency.json` |
| Luke Compassion (Track B) | 시편 119:105 | `ANCHOR_LUKE_COMPASSION` | 4 | `theme_838_luke_compassion.json` |
| John Light (Track B) | 시편 119:105 | `ANCHOR_JOHN_LIGHT` | 4 | `theme_839_john_light.json` |
| 가이사 동전 (Caesar Coin) | 마태복음 22:21 | `ANCHOR_MAT_22_21` | 4 | `theme_83_caesar_coin.json` |
| Acts Spread (Track B) | 시편 119:105 | `ANCHOR_ACTS_SPREAD` | 4 | `theme_840_acts_spread.json` |
| Romans Gospel (Track B) | 시편 119:105 | `ANCHOR_ROMANS_GOSPEL` | 4 | `theme_841_romans_gospel.json` |
| Corinthians Body (Track B) | 시편 119:105 | `ANCHOR_CORINTHIANS_BODY` | 4 | `theme_842_corinthians_body.json` |
| Galatians Freedom (Track B) | 시편 119:105 | `ANCHOR_GALATIANS_FREEDOM` | 4 | `theme_843_galatians_freedom.json` |
| 에베소 갑옷 (Ephesians Armor) | 에베소서 6:11 | `ANCHOR_EPHESIANS_ARMOR` | 4 | `theme_844_ephesians_armor.json` |
| Philippians Joy (Track B) | 시편 119:105 | `ANCHOR_PHILIPPIANS_JOY` | 4 | `theme_845_philippians_joy.json` |
| Colossians Head (Track B) | 시편 119:105 | `ANCHOR_COLOSSIANS_HEAD` | 4 | `theme_846_colossians_head.json` |
| Thessalonians Wait (Track B) | 시편 119:105 | `ANCHOR_THESSALONIANS_WAIT` | 4 | `theme_847_thessalonians_wait.json` |
| Timothy Young (Track B) | 시편 119:105 | `ANCHOR_TIMOTHY_YOUNG` | 4 | `theme_848_timothy_young.json` |
| Titus Island Pastor (Track B) | 시편 119:105 | `ANCHOR_TITUS_ISLAND_PASTOR` | 4 | `theme_849_titus_island_pastor.json` |
| 바리새인과 세리 (Pharisee and Publican) | 누가복음 18:14 | `ANCHOR_LUK_18_14` | 4 | `theme_84_pharisee_publican.json` |
| Philemon Slave (Track B) | 시편 119:105 | `ANCHOR_PHILEMON_SLAVE` | 4 | `theme_850_philemon_slave.json` |
| Hebrews Rest Promised (Track B) | 시편 119:105 | `ANCHOR_HEBREWS_REST_PROMISED` | 4 | `theme_851_hebrews_rest_promised.json` |
| James Tongue Fire (Track B) | 시편 119:105 | `ANCHOR_JAMES_TONGUE_FIRE` | 4 | `theme_852_james_tongue_fire.json` |
| Peter Rock (Track B) | 시편 119:105 | `ANCHOR_PETER_ROCK` | 4 | `theme_853_peter_rock.json` |
| John Love (Track B) | 시편 119:105 | `ANCHOR_JOHN_LOVE` | 4 | `theme_854_john_love.json` |
| Jude Contend Faith (Track B) | 시편 119:105 | `ANCHOR_JUDE_CONTEND_FAITH` | 4 | `theme_855_jude_contend_faith.json` |
| 어린 양 (Revelation Lamb Slain) | 요한계시록 5:6 | `ANCHOR_REVELATION_LAMB_SLAIN` | 4 | `theme_856_revelation_lamb_slain.json` |
| Genesis Beginning (Track B) | 시편 119:105 | `ANCHOR_GENESIS_BEGINNING` | 4 | `theme_857_genesis_beginning.json` |
| Exodus Deliverance (Track B) | 시편 119:105 | `ANCHOR_EXODUS_DELIVERANCE` | 4 | `theme_858_exodus_deliverance.json` |
| Leviticus Holiness (Track B) | 시편 119:105 | `ANCHOR_LEVITICUS_HOLINESS` | 4 | `theme_859_leviticus_holiness.json` |
| 풍파 잠잠 (Calming Storm) | 마가복음 4:39 | `ANCHOR_MRK_4_39` | 4 | `theme_85_calming_storm.json` |
| Numbers Wilderness (Track B) | 시편 119:105 | `ANCHOR_NUMBERS_WILDERNESS` | 4 | `theme_860_numbers_wilderness.json` |
| Deuteronomy Law Repeat (Track B) | 시편 119:105 | `ANCHOR_DEUTERONOMY_LAW_REPEAT` | 4 | `theme_861_deuteronomy_law_repeat.json` |
| Joshua Promised Land (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_PROMISED_LAND` | 4 | `theme_862_joshua_promised_land.json` |
| Judges Cycle (Track B) | 시편 119:105 | `ANCHOR_JUDGES_CYCLE` | 4 | `theme_863_judges_cycle.json` |
| Ruth Loyalty (Track B) | 시편 119:105 | `ANCHOR_RUTH_LOYALTY` | 4 | `theme_864_ruth_loyalty.json` |
| Samuel Transition (Track B) | 시편 119:105 | `ANCHOR_SAMUEL_TRANSITION` | 4 | `theme_865_samuel_transition.json` |
| Kings Divided (Track B) | 시편 119:105 | `ANCHOR_KINGS_DIVIDED` | 4 | `theme_866_kings_divided.json` |
| Chronicles Retell (Track B) | 시편 119:105 | `ANCHOR_CHRONICLES_RETELL` | 4 | `theme_867_chronicles_retell.json` |
| Ezra Restoration (Track B) | 시편 119:105 | `ANCHOR_EZRA_RESTORATION` | 4 | `theme_868_ezra_restoration.json` |
| Nehemiah Wall Build (Track B) | 시편 119:105 | `ANCHOR_NEHEMIAH_WALL_BUILD` | 4 | `theme_869_nehemiah_wall_build.json` |
| 오천 명 떡 (Feeding Five Thousand) | 요한복음 6:11 | `ANCHOR_JHN_6_11` | 4 | `theme_86_feeding_five_thousand.json` |
| Esther Providence (Track B) | 시편 119:105 | `ANCHOR_ESTHER_PROVIDENCE` | 4 | `theme_870_esther_providence.json` |
| Job Suffering Wisdom (Track B) | 시편 119:105 | `ANCHOR_JOB_SUFFERING_WISDOM` | 4 | `theme_871_job_suffering_wisdom.json` |
| Psalms Worship (Track B) | 시편 119:105 | `ANCHOR_PSALMS_WORSHIP` | 4 | `theme_872_psalms_worship.json` |
| Proverbs Wisdom Daily (Track B) | 시편 119:105 | `ANCHOR_PROVERBS_WISDOM_DAILY` | 4 | `theme_873_proverbs_wisdom_daily.json` |
| Ecclesiastes Meaning (Track B) | 시편 119:105 | `ANCHOR_ECCLESIASTES_MEANING` | 4 | `theme_874_ecclesiastes_meaning.json` |
| Song Union (Track B) | 시편 119:105 | `ANCHOR_SONG_UNION` | 4 | `theme_875_song_union.json` |
| Major Prophets (Track B) | 시편 119:105 | `ANCHOR_MAJOR_PROPHETS` | 4 | `theme_876_major_prophets.json` |
| Minor Prophets Twelve (Track B) | 시편 119:105 | `ANCHOR_MINOR_PROPHETS_TWELVE` | 4 | `theme_877_minor_prophets_twelve.json` |
| Gospel Fourfold (Track B) | 시편 119:105 | `ANCHOR_GOSPEL_FOURFOLD` | 4 | `theme_878_gospel_fourfold.json` |
| Epistles Pauline (Track B) | 시편 119:105 | `ANCHOR_EPISTLES_PAULINE` | 4 | `theme_879_epistles_pauline.json` |
| 열 문둥병자 (Ten Lepers) | 누가복음 17:17 | `ANCHOR_LUK_17_17` | 4 | `theme_87_ten_lepers.json` |
| Pastoral Epistles (Track B) | 시편 119:105 | `ANCHOR_PASTORAL_EPISTLES` | 4 | `theme_880_pastoral_epistles.json` |
| General Epistles (Track B) | 시편 119:105 | `ANCHOR_GENERAL_EPISTLES` | 4 | `theme_881_general_epistles.json` |
| 요한 계시 (Apocalypse Unveiling) | 요한계시록 1:1 | `ANCHOR_APOCALYPSE_UNVEILING` | 4 | `theme_882_apocalypse_unveiling.json` |
| Abel Firstling (Track B) | 시편 119:105 | `ANCHOR_ABEL_FIRSTLING` | 4 | `theme_883_abel_firstling.json` |
| Adam Rib (Track B) | 시편 119:105 | `ANCHOR_ADAM_RIB` | 4 | `theme_884_adam_rib.json` |
| Ark Dove (Track B) | 시편 119:105 | `ANCHOR_ARK_DOVE` | 4 | `theme_885_ark_dove.json` |
| Balaam Star (Track B) | 시편 119:105 | `ANCHOR_BALAAM_STAR` | 4 | `theme_886_balaam_star.json` |
| Barnabas Land (Track B) | 시편 119:105 | `ANCHOR_BARNABAS_LAND` | 4 | `theme_887_barnabas_land.json` |
| Beersheba Oath (Track B) | 시편 119:105 | `ANCHOR_BEERSHEBA_OATH` | 4 | `theme_888_beersheba_oath.json` |
| Bethlehem Star (Track B) | 시편 119:105 | `ANCHOR_BETHLEHEM_STAR` | 4 | `theme_889_bethlehem_star.json` |
| 소경 바디매오 (Blind Bartimaeus) | 마가복음 10:52 | `ANCHOR_MRK_10_52` | 4 | `theme_88_blind_bartimaeus.json` |
| Bread Wine Last (Track B) | 시편 119:105 | `ANCHOR_BREAD_WINE_LAST` | 4 | `theme_890_bread_wine_last.json` |
| 불타지 않는 떨기나무 (Burning Bush Unburnt) | 출애굽기 3:2 | `ANCHOR_BURNING_BUSH_UNBURNT` | 4 | `theme_891_burning_bush_unburnt.json` |
| Cain Abel Offer (Track B) | 시편 119:105 | `ANCHOR_CAIN_ABEL_OFFER` | 4 | `theme_892_cain_abel_offer.json` |
| Cana Wedding (Track B) | 시편 119:105 | `ANCHOR_CANA_WEDDING` | 4 | `theme_893_cana_wedding.json` |
| Cloud Pillar Night (Track B) | 시편 119:105 | `ANCHOR_CLOUD_PILLAR_NIGHT` | 4 | `theme_894_cloud_pillar_night.json` |
| Cornelius Peter (Track B) | 시편 119:105 | `ANCHOR_CORNELIUS_PETER` | 4 | `theme_895_cornelius_peter.json` |
| Creation Light Day (Track B) | 시편 119:105 | `ANCHOR_CREATION_LIGHT_DAY` | 4 | `theme_896_creation_light_day.json` |
| Curse Babel (Track B) | 시편 119:105 | `ANCHOR_CURSE_BABEL` | 4 | `theme_897_curse_babel.json` |
| Daniel Prayer Open (Track B) | 시편 119:105 | `ANCHOR_DANIEL_PRAYER_OPEN` | 4 | `theme_898_daniel_prayer_open.json` |
| David Bethlehem (Track B) | 시편 119:105 | `ANCHOR_DAVID_BETHLEHEM` | 4 | `theme_899_david_bethlehem.json` |
| 물을 포도주로 (Water to Wine) | 요한복음 2:9 | `ANCHOR_JHN_2_9` | 4 | `theme_89_water_to_wine.json` |
| David Cave Adullam (Track B) | 시편 119:105 | `ANCHOR_DAVID_CAVE_ADULLAM` | 4 | `theme_900_david_cave_adullam.json` |
| Denarius Workers (Track B) | 시편 119:105 | `ANCHOR_DENARIUS_WORKERS` | 4 | `theme_901_denarius_workers.json` |
| Drought Elijah (Track B) | 시편 119:105 | `ANCHOR_DROUGHT_ELIJAH` | 4 | `theme_902_drought_elijah.json` |
| Eden Guardian (Track B) | 시편 119:105 | `ANCHOR_EDEN_GUARDIAN` | 4 | `theme_903_eden_guardian.json` |
| Elisha Shunammite (Track B) | 시편 119:105 | `ANCHOR_ELISHA_SHUNAMMITE` | 4 | `theme_904_elisha_shunammite.json` |
| Elijah Ravens Brook (Track B) | 시편 119:105 | `ANCHOR_ELIJAH_RAVENS_BROOK` | 4 | `theme_905_elijah_ravens_brook.json` |
| Enoch Translation (Track B) | 시편 119:105 | `ANCHOR_ENOCH_TRANSLATION` | 4 | `theme_906_enoch_translation.json` |
| Esau Hairy (Track B) | 시편 119:105 | `ANCHOR_ESAU_HAIRY` | 4 | `theme_907_esau_hairy.json` |
| Eve Seed (Track B) | 시편 119:105 | `ANCHOR_EVE_SEED` | 4 | `theme_908_eve_seed.json` |
| Exodus Manna (Track B) | 시편 119:105 | `ANCHOR_EXODUS_MANNA` | 4 | `theme_909_exodus_manna.json` |
| 혈루증 여인 (Woman Bleeding) | 마가복음 5:34 | `ANCHOR_MRK_5_34` | 4 | `theme_90_woman_bleeding.json` |
| Faithful Servant (Track B) | 시편 119:105 | `ANCHOR_FAITHFUL_SERVANT` | 4 | `theme_910_faithful_servant.json` |
| Fig Tree Cursed (Track B) | 시편 119:105 | `ANCHOR_FIG_TREE_CURSED` | 4 | `theme_911_fig_tree_cursed.json` |
| Fire Sodom (Track B) | 시편 119:105 | `ANCHOR_FIRE_SODOM` | 4 | `theme_912_fire_sodom.json` |
| Five Loaves (Track B) | 시편 119:105 | `ANCHOR_FIVE_LOAVES` | 4 | `theme_913_five_loaves.json` |
| Flood Rainbow Sign (Track B) | 시편 119:105 | `ANCHOR_FLOOD_RAINBOW_SIGN` | 4 | `theme_914_flood_rainbow_sign.json` |
| Gad Seer (Track B) | 시편 119:105 | `ANCHOR_GAD_SEER` | 4 | `theme_915_gad_seer.json` |
| Gentile Centurion (Track B) | 시편 119:105 | `ANCHOR_GENTILE_CENTURION` | 4 | `theme_916_gentile_centurion.json` |
| Gideon Trumpets (Track B) | 시편 119:105 | `ANCHOR_GIDEON_TRUMPETS` | 4 | `theme_917_gideon_trumpets.json` |
| Golden Rule (Track B) | 시편 119:105 | `ANCHOR_GOLDEN_RULE` | 4 | `theme_918_golden_rule.json` |
| Good Seed Weeds (Track B) | 시편 119:105 | `ANCHOR_GOOD_SEED_WEEDS` | 4 | `theme_919_good_seed_weeds.json` |
| 무화과나무 믿음 (Fig Tree Faith) | 마가복음 11:23 | `ANCHOR_MRK_11_23` | 4 | `theme_91_fig_tree_faith.json` |
| Healing Pool Bethesda (Track B) | 시편 119:105 | `ANCHOR_HEALING_POOL_BETHESDA` | 4 | `theme_920_healing_pool_bethesda.json` |
| Heavenly Host (Track B) | 시편 119:105 | `ANCHOR_HEAVENLY_HOST` | 4 | `theme_921_heavenly_host.json` |
| Herod Fox (Track B) | 시편 119:105 | `ANCHOR_HEROD_FOX` | 4 | `theme_922_herod_fox.json` |
| Holy Ground Shoes (Track B) | 시편 119:105 | `ANCHOR_HOLY_GROUND_SHOES` | 4 | `theme_923_holy_ground_shoes.json` |
| Holy Of Holies (Track B) | 시편 119:105 | `ANCHOR_HOLY_OF_HOLIES` | 4 | `theme_924_holy_of_holies.json` |
| Holy Spirit Dove (Track B) | 시편 119:105 | `ANCHOR_HOLY_SPIRIT_DOVE` | 4 | `theme_925_holy_spirit_dove.json` |
| Isaac Blessing Jacob (Track B) | 시편 119:105 | `ANCHOR_ISAAC_BLESSING_JACOB` | 4 | `theme_926_isaac_blessing_jacob.json` |
| Isaac Marriage (Track B) | 시편 119:105 | `ANCHOR_ISAAC_MARRIAGE` | 4 | `theme_927_isaac_marriage.json` |
| Jairus Daughter Raise (Track B) | 시편 119:105 | `ANCHOR_JAIRUS_DAUGHTER_RAISE` | 4 | `theme_928_jairus_daughter_raise.json` |
| Jericho March (Track B) | 시편 119:105 | `ANCHOR_JERICHO_MARCH` | 4 | `theme_929_jericho_march.json` |
| 부자 청년 (Rich Young Ruler) | 마가복음 10:21 | `ANCHOR_MRK_10_21` | 4 | `theme_92_rich_young_ruler.json` |
| Jesus Temptation (Track B) | 시편 119:105 | `ANCHOR_JESUS_TEMPTATION` | 4 | `theme_930_jesus_temptation.json` |
| Jochebed Basket (Track B) | 시편 119:105 | `ANCHOR_JOCHEBED_BASKET` | 4 | `theme_931_jochebed_basket.json` |
| John Baptist Behead (Track B) | 시편 119:105 | `ANCHOR_JOHN_BAPTIST_BEHEAD` | 4 | `theme_932_john_baptist_behead.json` |
| Jonah Three Days (Track B) | 시편 119:105 | `ANCHOR_JONAH_THREE_DAYS` | 4 | `theme_933_jonah_three_days.json` |
| Joseph Prison Dream (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_PRISON_DREAM` | 4 | `theme_934_joseph_prison_dream.json` |
| Joshua Commander (Track B) | 시편 119:105 | `ANCHOR_JOSHUA_COMMANDER` | 4 | `theme_935_joshua_commander.json` |
| Judas Silver (Track B) | 시편 119:105 | `ANCHOR_JUDAS_SILVER` | 4 | `theme_936_judas_silver.json` |
| 나사로 사흘 (Lazarus Four Days) | 요한복음 11:39 | `ANCHOR_LAZARUS_FOUR_DAYS` | 4 | `theme_937_lazarus_four_days.json` |
| Light Under Bushel (Track B) | 시편 119:105 | `ANCHOR_LIGHT_UNDER_BUSHEL` | 4 | `theme_938_light_under_bushel.json` |
| 말씀 로고스 (Logos Word) | 요한복음 1:1 | `ANCHOR_LOGOS_WORD` | 4 | `theme_939_logos_word.json` |
| 종려주일 입성 (Triumphal Entry) | 마태복음 21:9 | `ANCHOR_MAT_21_9` | 4 | `theme_93_triumphal_entry.json` |
| Lot Salt (Track B) | 시편 119:105 | `ANCHOR_LOT_SALT` | 4 | `theme_940_lot_salt.json` |
| Loaves Blessing (Track B) | 시편 119:105 | `ANCHOR_LOAVES_BLESSING` | 4 | `theme_941_loaves_blessing.json` |
| Manna Corruption (Track B) | 시편 119:105 | `ANCHOR_MANNA_CORRUPTION` | 4 | `theme_942_manna_corruption.json` |
| Martha Mary (Track B) | 시편 119:105 | `ANCHOR_MARTHA_MARY` | 4 | `theme_943_martha_mary.json` |
| Melchizedek King (Track B) | 시편 119:105 | `ANCHOR_MELCHIZEDEK_KING` | 4 | `theme_944_melchizedek_king.json` |
| Mercy Good Samaritan (Track B) | 시편 119:105 | `ANCHOR_MERCY_GOOD_SAMARITAN` | 4 | `theme_945_mercy_good_samaritan.json` |
| Micaiah True (Track B) | 시편 119:105 | `ANCHOR_MICAIAH_TRUE` | 4 | `theme_946_micaiah_true.json` |
| Miracle Cana (Track B) | 시편 119:105 | `ANCHOR_MIRACLE_CANA` | 4 | `theme_947_miracle_cana.json` |
| Mustard Seed Kingdom (Track B) | 시편 119:105 | `ANCHOR_MUSTARD_SEED_KINGDOM` | 4 | `theme_948_mustard_seed_kingdom.json` |
| Naomi Bitterness (Track B) | 시편 119:105 | `ANCHOR_NAOMI_BITTERNESS` | 4 | `theme_949_naomi_bitterness.json` |
| 성전 정화 (Temple Cleansing) | 요한복음 2:15 | `ANCHOR_JHN_2_15` | 4 | `theme_94_temple_cleansing.json` |
| New Wine Skins (Track B) | 시편 119:105 | `ANCHOR_NEW_WINE_SKINS` | 4 | `theme_950_new_wine_skins.json` |
| Noah Ark Window (Track B) | 시편 119:105 | `ANCHOR_NOAH_ARK_WINDOW` | 4 | `theme_951_noah_ark_window.json` |
| Olive Mount Ascend (Track B) | 시편 119:105 | `ANCHOR_OLIVE_MOUNT_ASCEND` | 4 | `theme_952_olive_mount_ascend.json` |
| Paul Shipwreck (Track B) | 시편 119:105 | `ANCHOR_PAUL_SHIPWRECK` | 4 | `theme_953_paul_shipwreck.json` |
| Pharaoh Dream Cows (Track B) | 시편 119:105 | `ANCHOR_PHARAOH_DREAM_COWS` | 4 | `theme_954_pharaoh_dream_cows.json` |
| Pilate Barabbas (Track B) | 시편 119:105 | `ANCHOR_PILATE_BARABBAS` | 4 | `theme_955_pilate_barabbas.json` |
| Pool Siloam (Track B) | 시편 119:105 | `ANCHOR_POOL_SILOAM` | 4 | `theme_956_pool_siloam.json` |
| Prophet Without Honor (Track B) | 시편 119:105 | `ANCHOR_PROPHET_WITHOUT_HONOR` | 4 | `theme_957_prophet_without_honor.json` |
| Rebecca Well (Track B) | 시편 119:105 | `ANCHOR_REBECCA_WELL` | 4 | `theme_958_rebecca_well.json` |
| 다메섹 도상 (Road Damascus) | 사도행전 9:3 | `ANCHOR_ROAD_DAMASCUS` | 4 | `theme_959_road_damascus.json` |
| 다락방 (Upper Room) | 사도행전 1:13 | `ANCHOR_ACT_1_13` | 4 | `theme_95_upper_room.json` |
| Rock Christ (Track B) | 시편 119:105 | `ANCHOR_ROCK_CHRIST` | 4 | `theme_960_rock_christ.json` |
| Rod Staff Comfort (Track B) | 시편 119:105 | `ANCHOR_ROD_STAFF_COMFORT` | 4 | `theme_961_rod_staff_comfort.json` |
| Roman Centurion (Track B) | 시편 119:105 | `ANCHOR_ROMAN_CENTURION` | 4 | `theme_962_roman_centurion.json` |
| Sabbath Manborn (Track B) | 시편 119:105 | `ANCHOR_SABBATH_MANBORN` | 4 | `theme_963_sabbath_manborn.json` |
| Samaria Woman (Track B) | 시편 119:105 | `ANCHOR_SAMARIA_WOMAN` | 4 | `theme_964_samaria_woman.json` |
| Samaritan Lepers (Track B) | 시편 119:105 | `ANCHOR_SAMARITAN_LEPERS` | 4 | `theme_965_samaritan_lepers.json` |
| Saul Damascus (Track B) | 시편 119:105 | `ANCHOR_SAUL_DAMASCUS` | 4 | `theme_966_saul_damascus.json` |
| Seven Deacons (Track B) | 시편 119:105 | `ANCHOR_SEVEN_DEACONS` | 4 | `theme_967_seven_deacons.json` |
| Siloam Tower (Track B) | 시편 119:105 | `ANCHOR_SILOAM_TOWER` | 4 | `theme_968_siloam_tower.json` |
| Sinai Thunder (Track B) | 시편 119:105 | `ANCHOR_SINAI_THUNDER` | 4 | `theme_969_sinai_thunder.json` |
| 베드로 부인 (Peter Denial) | 누가복음 22:61 | `ANCHOR_LUK_22_61` | 4 | `theme_96_peter_denial.json` |
| 씨 뿌리는 자 (Sower Four Soils) | 마태복음 13:8 | `ANCHOR_SOWER_FOUR_SOILS` | 4 | `theme_970_sower_four_soils.json` |
| Spirit Helper (Track B) | 시편 119:105 | `ANCHOR_SPIRIT_HELPER` | 4 | `theme_971_spirit_helper.json` |
| Storm Stilled (Track B) | 시편 119:105 | `ANCHOR_STORM_STILLED` | 4 | `theme_972_storm_stilled.json` |
| Temple Tax Coin (Track B) | 시편 119:105 | `ANCHOR_TEMPLE_TAX_COIN` | 4 | `theme_973_temple_tax_coin.json` |
| Thief Cross (Track B) | 시편 119:105 | `ANCHOR_THIEF_CROSS` | 4 | `theme_974_thief_cross.json` |
| Three Temptations (Track B) | 시편 119:105 | `ANCHOR_THREE_TEMPTATIONS` | 4 | `theme_975_three_temptations.json` |
| 변화산 영광 (Transfiguration Glory) | 마태복음 17:2 | `ANCHOR_TRANSFIGURATION_GLORY` | 4 | `theme_976_transfiguration_glory.json` |
| Tree Known Fruit (Track B) | 시편 119:105 | `ANCHOR_TREE_KNOWN_FRUIT` | 4 | `theme_977_tree_known_fruit.json` |
| Triumphal Palm (Track B) | 시편 119:105 | `ANCHOR_TRIUMPHAL_PALM` | 4 | `theme_978_triumphal_palm.json` |
| Twelve Stones (Track B) | 시편 119:105 | `ANCHOR_TWELVE_STONES` | 4 | `theme_979_twelve_stones.json` |
| 어부 부르심 (Fishers Call) | 마태복음 4:19 | `ANCHOR_MAT_4_19` | 4 | `theme_97_fishers_call.json` |
| Upper Room Prayer (Track B) | 시편 119:105 | `ANCHOR_UPPER_ROOM_PRAYER` | 4 | `theme_980_upper_room_prayer.json` |
| Water Rock Strike (Track B) | 시편 119:105 | `ANCHOR_WATER_ROCK_STRIKE` | 4 | `theme_981_water_rock_strike.json` |
| Winepress Wrath (Track B) | 시편 119:105 | `ANCHOR_WINEPRESS_WRATH` | 4 | `theme_982_winepress_wrath.json` |
| Whitened Harvest (Track B) | 시편 119:105 | `ANCHOR_WHITENED_HARVEST` | 4 | `theme_983_whitened_harvest.json` |
| Woman Issue Blood (Track B) | 시편 119:105 | `ANCHOR_WOMAN_ISSUE_BLOOD` | 4 | `theme_984_woman_issue_blood.json` |
| Zealots Sword (Track B) | 시편 119:105 | `ANCHOR_ZEALOTS_SWORD` | 4 | `theme_985_zealots_sword.json` |
| Zaccheus Restitution (Track B) | 시편 119:105 | `ANCHOR_ZACCHEUS_RESTITUTION` | 4 | `theme_986_zaccheus_restitution.json` |
| Abraham Intercedes (Track B) | 시편 119:105 | `ANCHOR_ABRAHAM_INTERCEDES` | 4 | `theme_987_abraham_intercedes.json` |
| Lot Angels (Track B) | 시편 119:105 | `ANCHOR_LOT_ANGELS` | 4 | `theme_988_lot_angels.json` |
| Hagar Well (Track B) | 시편 119:105 | `ANCHOR_HAGAR_WELL` | 4 | `theme_989_hagar_well.json` |
| 야이로 딸 (Jairus Daughter) | 마가복음 5:41 | `ANCHOR_MRK_5_41` | 4 | `theme_98_jairus_daughter.json` |
| Ishmael Bow (Track B) | 시편 119:105 | `ANCHOR_ISHMAEL_BOW` | 4 | `theme_990_ishmael_bow.json` |
| Isaac Altar (Track B) | 시편 119:105 | `ANCHOR_ISAAC_ALTAR` | 4 | `theme_991_isaac_altar.json` |
| Jacob Stone Pillow (Track B) | 시편 119:105 | `ANCHOR_JACOB_STONE_PILLOW` | 4 | `theme_992_jacob_stone_pillow.json` |
| Leah Mandrakes (Track B) | 시편 119:105 | `ANCHOR_LEAH_MANDRAKES` | 4 | `theme_993_leah_mandrakes.json` |
| Joseph Storehouse (Track B) | 시편 119:105 | `ANCHOR_JOSEPH_STOREHOUSE` | 4 | `theme_994_joseph_storehouse.json` |
| Moses Brass Snake (Track B) | 시편 119:105 | `ANCHOR_MOSES_BRASS_SNAKE` | 4 | `theme_995_moses_brass_snake.json` |
| Aaron Golden Calf (Track B) | 시편 119:105 | `ANCHOR_AARON_GOLDEN_CALF` | 4 | `theme_996_aaron_golden_calf.json` |
| Spies Grapes (Track B) | 시편 119:105 | `ANCHOR_SPIES_GRAPES` | 4 | `theme_997_spies_grapes.json` |
| Rahab House (Track B) | 시편 119:105 | `ANCHOR_RAHAB_HOUSE` | 4 | `theme_998_rahab_house.json` |
| Gideon Army (Track B) | 시편 119:105 | `ANCHOR_GIDEON_ARMY` | 4 | `theme_999_gideon_army.json` |
| 큰 고기 잡음 (Great Fish Catch) | 요한복음 21:11 | `ANCHOR_JHN_21_11` | 4 | `theme_99_great_fish_catch.json` |

**예시 요약 (피와 물 (Blood and Water)):** 앵커 요한복음 19:34 — cross-node 4개. `research_metaphor_*` 필드는 교육용 은유이며 운영 `NO_GO`·`LOCKED_MODE`와 **동일하지 않음**.

---

## 4. 한계·면책

- `[HYPO]` · `hypo_research_only` · 종교적 정답·투자 확정·실시간 무지연 주장 없음
- 지연 스냅샷; 실시간 트레이딩 피드 아님
- Phase N(주석·사본학·2차 문헌 스택)은 RQ-015 백로그 — 본 부록 범위 밖
- Not investment advice. No buy/sell instructions. Logos layer `[NON_GATING]`. Core formulas not disclosed (§9A).

---

## 5. 문의·확장

- 전체 테마 JSON·주간 스냅샷: **엔터프라이즈 부록·API** 별도 계약
- PoC: LG/가전 등 — **본선 매크로 PoC와 범위 분리** 명시

---

## Regenerate

```powershell
py scripts/build_logos_b2b_appendix_v1.py
py scripts/build_showroom_logos_research_slice_v1.py
```

## Disclaimers (canonical · document tail)

> Not investment advice. No buy/sell instructions. Logos layer `[NON_GATING]`. Core formulas not disclosed (§9A).
