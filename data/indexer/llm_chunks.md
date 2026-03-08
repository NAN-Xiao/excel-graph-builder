# Schema Graph LLM Export
# 206 tables, 3461 relations

## 表: achievement [other]
- 文件: achievement.xlsx | sheet: achievement
- 行数: 33 | 列数: 7 | 主键: id
- 列: id(int), 成就类型(int), 任务索引(int)→task.任务id, 奖励(str)→reward.ID, 成就名称(str), 成就名称.1(str), 成就图片(str)
- 关联: → task(任务索引→任务id @0.95), → reward(奖励→ID @0.71), ← rank_rank_reward(奖励id→奖励 @0.98), ← alliance_buff_attribute(类型→任务索引 @0.76)

## 表: achievement_achievementGroup [other]
- 文件: achievement.xlsx | sheet: achievementGroup
- 行数: 9 | 列数: 2 | 主键: id
- 列: id(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 成就(str)
- 关联: → shop_shop_item(id→商店id @0.8), → item(id→道具分类排序 @0.66), → pve_pve_level(id→关卡显示等级 @0.62), → pve_pve_level(id→PVE关卡文件ID @0.61), → city_node_type_cityNodeTypeConf(id→节点类型  参考CityNodeType @0.61)

## 表: activity [other]
- 文件: activity.xlsx | sheet: activity
- 行数: 33 | 列数: 33 | 主键: ID
- 列: ID(int), 活动名称(str), #策划备注1(str), 活动图标(str), 选择tab图标(str), 宣传图(str), 敬请期待_宣传图(str), 宣传图标题(str), 宣传图文字(str), 副标题(str), 活动说明(str), 是否在活动日历显示(int), 是否在预览中显示(int), 活动分组(int), 活动入口(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 包含其他活动(str), 显示优先级(int)→worldMonster.部队配置ID, 活动奖励显示(int)→city_area_grid.绑定事件id gridEvent 
事件ideventTYpe, 界面名称(str), 预览界面名称(str), 类型(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 是否开启(int), 合服是否开启(int), 跨服数据同步限制(int), 玩家限制条件(str), ...+8列
- 关联: → item(活动入口→道具分类排序 @0.94), → shop_shop_item(活动入口→商店id @0.92), → pve_pve_level(活动参数→PVE关卡文件ID @0.89), → pve_pve_level(类型→关卡显示等级 @0.85), → hero(活动额外参数→英雄主动技能ID @0.82), → rank(活动额外参数→排行榜奖励 @0.82), → baseLevel(活动参数→大本等级 @0.81), → rank_rank_reward(活动额外参数→排名组 @0.81), → city_node_type_cityNodeTypeConf(类型→节点类型  参考CityNodeType @0.8), → skill_condition(活动入口→值参数对比条件 @0.79), ...+52条出向, ← recharge(关联活动Id→ID @0.95), ← building(等级→活动参数 @0.94), ← worldScene_monsterLevel(等级上限→活动参数 @0.9), ← item(物品类型→活动参数 @0.89), ← building(缩放时隐藏次序，越大越不会被隐藏→活动参数 @0.89), ← recharge(优先级→活动参数 @0.88), ← buff_attribute_buff_client(排序，小的在前→活动参数 @0.88), ← recharge_rechargeShow(宣传图→宣传图 @0.88), ← army(优先级→活动参数 @0.85), ← science(显示层级【只需配置第1级】→活动参数 @0.85), ...+86条入向

## 表: activity_activity_extra_param [config]
- 文件: activity.xlsx | sheet: activity_extra_param
- 行数: 6 | 列数: 6 | 主键: ID
- 列: ID(int)→rank_rank_reward.排名组, 整型参数1(str), #备注(str), 整型参数2(str), #备注.1(str), 字符串参数(str)
- 关联: → hero(ID→英雄主动技能ID @0.67), → rank(ID→排行榜奖励 @0.62), → rank_rank_reward(ID→排名组 @0.61), ← alliance_buff_attribute(类型→ID @0.65), ← activity(活动额外参数→ID @0.6)

## 表: activity_activity_param [config]
- 文件: activity.xlsx | sheet: activity_param
- 行数: 31 | 列数: 12 | 主键: ID
- 列: ID(int)→pve_pve_level.PVE关卡文件ID, #备注(str), 任务组(float)→task.任务id, 兑换组(int), 活动怪物组(int), 关排行榜(str), 排行榜奖励发放(str), 奖励邮件ID(int)→mail.索引, 活动结束后删除道具(int), 活动计数重置(int), 副本组(float), 活动开启/关闭/预告邮件ID(str)
- 关联: → mail(奖励邮件ID→索引 @0.95), → task(任务组→分组 @0.85), → pve_pve_level(ID→PVE关卡文件ID @0.74), → task(任务组→任务id @0.65), → baseLevel(ID→大本等级 @0.61), ← client_rank_alliance_rank(排行榜类型→排行榜奖励发放 @0.9), ← default_sth_defaultSth(id→排行榜奖励发放 @0.87), ← sceneManager(场景LOD配置ID→排行榜奖励发放 @0.8), ← world_building_worldBuilding(区分地图→排行榜奖励发放 @0.8), ← worldScene_monsterLevel(等级上限→ID @0.7), ← client_rank_alliance_rank(自增id→排行榜奖励发放 @0.7), ← item(物品类型→ID @0.69), ← building(缩放时隐藏次序，越大越不会被隐藏→ID @0.69), ← buff_attribute_buff_client(排序，小的在前→ID @0.68), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→ID @0.68), ...+13条入向

## 表: ai_scheme_aiScheme [other]
- 文件: ai_scheme.xlsx | sheet: aiScheme
- 行数: 6 | 列数: 13 | 主键: 键值
- 列: 键值(int), #策划备注(str), 环境限定(int), 主体类型(int), 是否群体AI(int), 初始状态(int), 接触战斗距离(float), 开始追击移动距离(float), 停止追击移动距离(float), 脱战距离(float), 游荡距离(float), AI行为组ID(int), AI行为组权重(int)
- 关联: 无

## 表: alliance_alliance_permission [quest]
- 文件: alliance.xlsx | sheet: alliance_permission
- 行数: 30 | 列数: 10 | 主键: 索引
- 列: 索引(int)→pve_pve_level.PVE关卡文件ID, #策划备注列(str), 权限名称(str), R1权限(str), R2权限(str), R3权限(str), R4权限(str), R4.5权限(官员)(str), R5权限(str), 是否显示(str)
- 关联: → pve_pve_level(索引→PVE关卡文件ID @0.73), ← pve_pve_level(关卡显示等级→索引 @0.63)

## 表: alliance_buff_attribute [skill]
- 文件: alliance_buff_attribute.xlsx | sheet: alliance_buff_attribute
- 行数: 3 | 列数: 4 | 主键: 编号
- 列: 编号(int), #buff名称(str), 类型(int)→guide_config.主键, 数值类型(int)
- 关联: → activity(类型→活动额外参数 @0.85), → video_gift_videoGift(类型→奖励 @0.78), → achievement(类型→任务索引 @0.76), → hero(类型→英雄主动技能ID @0.76), → mail(类型→奖励 @0.76), → rank(类型→排行榜奖励 @0.76), → rank_rank_reward(类型→排名组 @0.76), → buff_attribute(类型→类型 @0.72), → monsterTroop(类型→主键 @0.71), → rank(类型→排行数据源类型 @0.71), ...+6条出向

## 表: alliance_building [building]
- 文件: alliance_building.xlsx | sheet: alliance_building
- 行数: 17 | 列数: 26 | 主键: id=10000*type+n
- 列: id=10000*type+n(int), 名称(str), 详细描述，建筑描述，key_new.xlsx(str), 建筑类型(int)→key_new.facial, 图标(str), 模型资源名(str), 大地图标志ICON(str), 建筑半径【客户端用】(float), 排序数量(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 解锁条件-成员数量(int), 解锁条件-联盟战力(int), 解锁条件-旗帜数量(int), 消耗资源(str), 说明(str), 建筑值(int), 容纳士兵上限(int)→hero_hero_level.升下一级需要经验值, 领地范围(int), 资源田容量(int)→point_transform_pointTransform.积分, 采集速度(int)→pve_skill.检索距离，即技能释放距离【float，米】, 建筑城防值(int), 建筑完成后存活时间（H)(int), 燃烧速度/持续时间(str), 宝石CD(int), 联盟积分CD(int), 恢复速度/每满几秒(str), ...+1列
- 关联: → shop_shop_item(排序数量→商店id @0.95), → item(建筑类型→道具分类排序 @0.91), → shop_shop_item(建筑类型→商店id @0.89), → skill_condition(建筑类型→值参数对比条件 @0.88), → item(排序数量→道具分类排序 @0.86), → client_show_client_bullet(采集速度→飞行速度
默认15m/s @0.85), → pve_pve_level(排序数量→关卡显示等级 @0.82), → pve_pve_level(建筑类型→关卡显示等级 @0.8), → pve_skill(采集速度→检索距离，即技能释放距离【float，米】 @0.8), → activity(排序数量→活动参数 @0.79), ...+64条出向, ← activity(活动入口→排序数量 @0.77), ← baseLevel(时代→排序数量 @0.77), ← kvkSeason(报名赛季标识组→排序数量 @0.77), ← alliance_shop_alliance_shopItem(排序→排序数量 @0.77), ← zombie_survivor(兵种等级→排序数量 @0.77), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→建筑类型 @0.76), ← equip(装备位置→排序数量 @0.73), ← kvkSeason(默认投票结果→排序数量 @0.73), ← recharge(档位(真实付费)→排序数量 @0.73), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→排序数量 @0.73), ...+14条入向

## 表: alliance_constant [alliance]
- 文件: alliance_constant.xlsx | sheet: alliance_constant
- 行数: 17 | 列数: 4 | 主键: 键值
- 列: 键值(str), 值(float), @类型(str)→data_constant.@类型, #策划备注(str)
- 关联: → data_constant(@类型→@类型 @0.8), ← soldier_consumption(重伤比例→值 @0.76), ← monsterTroop_monsterHero(英雄等级→值 @0.76)

## 表: alliance_flag [alliance]
- 文件: alliance_flag.xlsx | sheet: alliance_flag
- 行数: 4 | 列数: 3 | 主键: 索引
- 列: 索引(int), #策划备注列(str), 配置的数组值，图片直接填写图片名，颜色填写颜色值（如红色:#ff0000ff, 最后两位是透明度）(str)
- 关联: ← matchingEntityRule_matchingAllianceRule(联盟匹配规则ID→索引 @0.95)

## 表: alliance_gift [alliance]
- 文件: alliance_gift.xlsx | sheet: alliance_gift
- 行数: 6 | 列数: 12 | 主键: id
- 列: id(int)→mail.模板, 触发类型(int), 触发条件(int), 礼物类型(int), 礼物名称(str), 礼物图片(str), 礼物说明(str), 礼物来源说明(str), 礼物点数(int), 钥匙点数(int)→data_constant.常量值, 奖励(int)→guide_config.主键, 倒计时(小时)(int)→building.参数1
- 关联: → activity(倒计时(小时)→活动参数 @0.76), → pve_pve_level(倒计时(小时)→PVE关卡文件ID @0.74), → monsterTroop(倒计时(小时)→主键 @0.72), → building(倒计时(小时)→参数1 @0.72), → data_constant(钥匙点数→常量值 @0.72), → world_building_worldBuilding(奖励→id @0.71), → guide_config(奖励→主键 @0.71), → item(倒计时(小时)→参数1 @0.71), → reward(奖励→ID @0.7), → task(奖励→任务id @0.7), ...+1条出向

## 表: alliance_gift_box [alliance]
- 文件: alliance_gift_box.xlsx | sheet: alliance_gift_box
- 行数: 6 | 列数: 8 | 主键: id
- 列: id(int), #礼物等级(int), 所需经验(int)→lord_exp_lordExp.经验值, #水晶等级(int), 水晶外形(str), 所需钥匙(int)→building.参数2, 对应奖励(int)→reward.ID, 宝箱名称(str)
- 关联: → lord_exp_lordExp(所需经验→经验值 @0.75), → lord_exp_lordExp(所需钥匙→经验值 @0.75), → building(所需钥匙→参数2 @0.71), → reward(对应奖励→ID @0.7), ← resource_Resinfo(生成速度→所需经验 @0.85), ← weapon(攻击速度（普攻技能CD，复写pve_skill字段）→所需经验 @0.85)

## 表: alliance_science [alliance]
- 文件: alliance_science.xlsx | sheet: alliance_science
- 行数: 321 | 列数: 21 | 主键: ID,约定
group*1000+level
 
- 列: ID,约定
group*1000+level
 (int), #备注名称

(str), 

页签(int), 组名(int)→item.编号, 等级(int)→key_new.facial, 最高等级(int), 名称
【只需配置第1级】(str), 说明
【只需配置第1级】(str), 显示X轴，横坐标
【只需配置第1级】(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
(int)→key_new.facial, 需要前置科技
(str), 作用效果(str), 联盟作用效果(str), 解锁技能(str), 捐献资源类型(int), 捐献资源数量(int), 捐献获得id(int), 集满所需科技点数(int)→monsterTroop.主键, 研究消耗联盟资源(str), 研究时间消耗（s）(int), 加成属性名【客户端】(str)
- 关联: → shop_shop_item(显示X轴，横坐标
【只需配置第1级】→商店id @0.95), → item(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→道具分类排序 @0.91), → shop_shop_item(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→商店id @0.89), → skill_condition(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→值参数对比条件 @0.88), → item(显示X轴，横坐标
【只需配置第1级】→道具分类排序 @0.86), → pve_pve_level(等级→关卡显示等级 @0.85), → pve_pve_level(显示X轴，横坐标
【只需配置第1级】→关卡显示等级 @0.82), → pve_pve_level(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→关卡显示等级 @0.8), → activity(显示X轴，横坐标
【只需配置第1级】→活动参数 @0.79), → activity(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→活动参数 @0.77), ...+50条出向, ← alliance_science_alliance_skill(发动消耗联盟资源→研究消耗联盟资源 @0.8), ← activity(活动入口→显示X轴，横坐标
【只需配置第1级】 @0.77), ← baseLevel(时代→显示X轴，横坐标
【只需配置第1级】 @0.77), ← equip(穿戴等级→等级 @0.77), ← kvkSeason(报名赛季标识组→显示X轴，横坐标
【只需配置第1级】 @0.77), ← alliance_shop_alliance_shopItem(排序→显示X轴，横坐标
【只需配置第1级】 @0.77), ← zombie_survivor(兵种等级→显示X轴，横坐标
【只需配置第1级】 @0.77), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
 @0.76), ← draw_card_discount(折扣组→等级 @0.75), ← worldScene_monsterFresh(基础刷新等级→等级 @0.75), ...+32条入向

## 表: alliance_science_alliance_donate [alliance]
- 文件: alliance_science.xlsx | sheet: alliance_donate
- 行数: 1 | 列数: 5 | 主键: 编号
- 列: 编号(int), 捐献获得科技点/充能点(int), 捐献获得个人积分(int), 捐献获得联盟积分(int), 捐献获得贡献值(int)
- 关联: 无

## 表: alliance_science_alliance_skill [skill]
- 文件: alliance_science.xlsx | sheet: alliance_skill
- 行数: 45 | 列数: 17 | 主键: ID，约定
group*1000+level
 
- 列: ID，约定
group*1000+level
 (int), #备注名称

(str), 组名(int)→key_new.facial, 等级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 最高等级(int), 名称(str), 说明(str), 显示位置
【只需配置第1级】(int), 作用效果(str), 持续时间(小时)(int), 冷却时间（小时）(int)→item.参数1, 捐献资源类型(int), 捐献资源数量(int), 捐献获得id(int), 集满所需充能点数(int), 发动消耗联盟资源(str)→alliance_science.研究消耗联盟资源, 加成属性名【客户端】(str)
- 关联: → shop_shop_item(等级→商店id @0.87), → pve_pve_level(等级→关卡显示等级 @0.84), → activity(等级→活动参数 @0.8), → alliance_science(发动消耗联盟资源→研究消耗联盟资源 @0.8), → city_node_type_cityNodeTypeConf(等级→节点类型  参考CityNodeType @0.78), → activity(等级→类型 @0.77), → pve_pve_level(等级→PVE关卡文件ID @0.76), → hud_config_bookmark_config(等级→关键值【唯一】，暂时没有使用 @0.73), → zombie_survivor(等级→战斗力，显示值 @0.73), → building(等级→参数1 @0.73), ...+16条出向, ← draw_card_discount(折扣组→等级 @0.77), ← worldScene_monsterFresh(基础刷新等级→等级 @0.77), ← alliance_building(排序数量→等级 @0.77), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→等级 @0.77), ← activity(活动入口→等级 @0.74), ← baseLevel(时代→等级 @0.74), ← kvkSeason(报名赛季标识组→等级 @0.74), ← zombie_survivor(兵种等级→等级 @0.74), ← equip(装备位置→等级 @0.71), ← kvkSeason(默认投票结果→等级 @0.71), ...+12条入向

## 表: alliance_shop_alliance_shopItem [item]
- 文件: alliance_shop.xlsx | sheet: alliance_shopItem
- 行数: 18 | 列数: 7 | 主键: ID
- 列: ID(int), #道具说明(str), 出售道具(int)→item.编号, 补货价格(int), 出售价格(int), 道具分类(int), 排序(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType
- 关联: → item(排序→道具分类排序 @0.94), → shop_shop_item(排序→商店id @0.92), → pve_pve_level(排序→关卡显示等级 @0.81), → skill_condition(排序→值参数对比条件 @0.79), → activity(排序→活动参数 @0.78), → draw_card_discount(排序→折扣组 @0.77), → worldScene_monsterFresh(排序→基础刷新等级 @0.77), → alliance_building(排序→排序数量 @0.77), → alliance_science(排序→显示X轴，横坐标
【只需配置第1级】 @0.77), → pve_pve_level(排序→PVE关卡文件ID @0.75), ...+19条出向, ← equip(装备位置→排序 @0.76), ← kvkSeason(默认投票结果→排序 @0.76), ← recharge(档位(真实付费)→排序 @0.76), ← alliance_building(建筑类型→排序 @0.76), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→排序 @0.76), ← hud_config(显示权重，越大显示越前面→排序 @0.76), ← task(任务类型→排序 @0.76), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→排序 @0.73), ← zombie_bt_ai(范围内不会跟随主将距离→排序 @0.69), ← resource_ResRules(联盟资源田数量→排序 @0.65), ...+1条入向

## 表: area_area_config [world]
- 文件: area.xlsx | sheet: area_config
- 行数: 8 | 列数: 5 | 主键: 主键
- 列: 主键(int)→item.道具分类排序, #策划备注(str), 地块关卡类型(int)→vip.等级, 名称(str), icon(str)
- 关联: → skill_condition(地块关卡类型→值参数对比条件 @0.9), → item(地块关卡类型→道具分类排序 @0.82), → pve_pve_level(地块关卡类型→关卡显示等级 @0.81), → shop_shop_item(地块关卡类型→商店id @0.8), → shop_shop_item(主键→商店id @0.77), → item(主键→道具分类排序 @0.74), → data_constant(地块关卡类型→常量值 @0.72), → alliance_science(地块关卡类型→等级 @0.72), → key_new(地块关卡类型→facial @0.7), → activity(地块关卡类型→活动参数 @0.68), ...+17条出向, ← equip(装备位置→地块关卡类型 @0.76), ← recharge(档位(真实付费)→地块关卡类型 @0.76), ← alliance_building(建筑类型→地块关卡类型 @0.76), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→地块关卡类型 @0.76), ← hud_config(显示权重，越大显示越前面→地块关卡类型 @0.76), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→地块关卡类型 @0.73), ← panel_config(层级→地块关卡类型 @0.69), ← resource_ResRules(联盟资源田数量→地块关卡类型 @0.65), ← kvkSeason(默认投票结果→地块关卡类型 @0.62), ← draw_card(单次开启数量上限→地块关卡类型 @0.61)

## 表: army [battle]
- 文件: army.xlsx | sheet: army
- 行数: 15 | 列数: 27 | 主键: 士兵名称，
填写key_new表id
- 列: 主键，必须>100000(int), #策划备注(str), 士兵名称，
填写key_new表id(str), 士兵特点描述，
填写key_new表id(str)→key_new.facial, 兵种类型(int)→buff_attribute.类型, 兵种等级(int), 世界场景AI部队显示模型(str)→model.键值, 世界场景玩家部队显示模型(str)→model.键值, 城内显示模型(str)→model.键值, 部队图标，
路径：Assets/Game_Prefab/texture/army_icon(str), 部队形象
路径：Assets/Game_Prefab/texture/army_icon(str), 基础攻击(int), 基础防御(int), 基础生命(int), 基础行军速度(int)→building.幸存者等级上限, 基础负载(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 基础战力(int), 训练消耗资源(str), 训练消耗的时间(int)→hero_hero_level.等级, 治疗消耗资源(str), 治疗消耗时间(int)→item.参数1, 解锁科技等级需求(str), 士兵属性(str), 士兵特点(str), 优先级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, ...+2列
- 关联: → mail_bufftemplate(兵种类型→增益目标兵种类型枚举 @0.93), → pve_pve_level(优先级→关卡显示等级 @0.9), → city_node_type_cityNodeTypeConf(优先级→节点类型  参考CityNodeType @0.88), → activity(优先级→活动参数 @0.85), → pve_pve_level(基础负载→关卡显示等级 @0.84), → point_transform_pointTransform(兵种类型→参数类型 @0.83), → activity(基础负载→活动参数 @0.8), → rank_rank_reward(基础负载→排名组 @0.8), → key_new(士兵特点描述，
填写key_new表id→facial @0.8), → pve_pve_level(优先级→PVE关卡文件ID @0.79), ...+39条出向, ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→优先级 @0.76), ← activity(类型→优先级 @0.72), ← army_monster(基础负载→优先级 @0.7), ← equip(穿戴等级→优先级 @0.7), ← draw_card_discount(折扣组→优先级 @0.68), ← worldScene_monsterFresh(基础刷新等级→优先级 @0.68), ← alliance_building(排序数量→优先级 @0.68), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→优先级 @0.68), ← zombie_survivor(战斗力，显示值→优先级 @0.68), ← baseLevel(时代→优先级 @0.66), ...+14条入向

## 表: army_attribute [battle]
- 文件: army.xlsx | sheet: attribute
- 行数: 6 | 列数: 6 | 主键: 属性名称，索引key_new表id
- 列: 主键(int), #策划备注(str), 属性名称，索引key_new表id(str)→key_new.facial, 属性描述，索引key_new表id(str)→key_new.facial, 属性图标资源名
路径：Assets/Game_Prefab/texture/army_icon(str), 受哪种buff加成，第一个参数兵种Group id，紧接着buffid数组(str)
- 关联: → key_new(属性描述，索引key_new表id→facial @0.8), → key_new(属性名称，索引key_new表id→facial @0.6)

## 表: army_monster [battle]
- 文件: army.xlsx | sheet: monster
- 行数: 15 | 列数: 17 | 主键: 怪物名称，
填写key_new表id
- 列: 主键(int), #策划备注(str), 怪物名称，
填写key_new表id(str)→key_new.facial, 怪物特点描述，
填写key_new表id(str)→key_new.facial, 兵种类型(int)→mail_bufftemplate.增益目标兵种类型枚举, 兵种等级(int), 显示模型(str)→model.键值, 城内显示模型(str)→model.键值, 基础攻击(int), 基础防御(int), 基础生命(int), 基础行军速度(int)→building.幸存者等级上限, 基础负载(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 基础战力(int), 部队图标，
路径：Assets/Game_Prefab/texture/army_icon(str), 部队形象
路径：Assets/Game_Prefab/texture/army_icon(str), 普攻技能表现(int)→task.任务id
- 关联: → mail_bufftemplate(兵种类型→增益目标兵种类型枚举 @0.93), → pve_pve_level(基础负载→关卡显示等级 @0.84), → point_transform_pointTransform(兵种类型→参数类型 @0.83), → activity(基础负载→活动参数 @0.8), → rank_rank_reward(基础负载→排名组 @0.8), → key_new(怪物特点描述，
填写key_new表id→facial @0.8), → building(基础行军速度→幸存者等级上限 @0.78), → city_node_type_cityNodeTypeConf(基础负载→节点类型  参考CityNodeType @0.78), → pve_pve_level(基础负载→PVE关卡文件ID @0.76), → monsterTroop(基础负载→主键 @0.73), ...+23条出向

## 表: army_trait [battle]
- 文件: army.xlsx | sheet: trait
- 行数: 30 | 列数: 5 | 主键: 属性名称，索引key_new表id
- 列: 主键(int)→item.参数1, #策划备注(str), 属性名称，索引key_new表id(str)→key_new.facial, 属性描述，索引key_new表id(str)→key_new.facial, 属性图标资源名
路径：Assets/Game_Prefab/texture/army_icon(str)
- 关联: → pve_pve_level(主键→PVE关卡文件ID @0.93), → key_new(属性描述，索引key_new表id→facial @0.8), → item(主键→参数1 @0.77), → baseLevel(主键→大本等级 @0.73), → monsterTroop(主键→显示等级 @0.69), → monsterTroop(主键→主键 @0.68), → worldMonster(主键→部队配置ID @0.68), → unlock_functionSwitch(主键→主键（功能id） @0.61), → key_new(属性名称，索引key_new表id→facial @0.6), ← pve_pve_level(关卡显示等级→主键 @0.83), ← alliance_building(采集速度→主键 @0.74), ← material_merge_MaterialProduce(每次生产获得数量→主键 @0.74), ← material_merge_MaterialProduce(每次生产需要时间→主键 @0.74), ← building(缩放时隐藏次序，越大越不会被隐藏→主键 @0.73), ← soldier_consumption(重伤比例→主键 @0.73), ← entity_menu(缩放系数修正值→主键 @0.73), ← worldScene_monsterLevel(等级上限→主键 @0.71), ← item(物品类型→主键 @0.7), ← buff_attribute_buff_client(排序，小的在前→主键 @0.69), ...+13条入向

## 表: atlas_group [other]
- 文件: atlas_group.xlsx | sheet: atlas_group
- 行数: 3 | 列数: 5 | 主键: 图集宽度
- 列: 组名(str), 图集宽度(int), 图集高度(int), 图标宽度(int), 图标高度(int)
- 关联: 无

## 表: baseLevel [other]
- 文件: baseLevel.xlsx | sheet: baseLevel
- 行数: 40 | 列数: 5 | 主键: ID
- 列: ID(int)→pve_pve_level.PVE关卡文件ID, #策划备注(str), 大本等级(int)→hero_hero_level.等级, 时代(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 建造队列上限(int)
- 关联: → pve_pve_level(大本等级→PVE关卡文件ID @0.94), → item(时代→道具分类排序 @0.94), → shop_shop_item(时代→商店id @0.92), → pve_pve_level(时代→关卡显示等级 @0.81), → monsterTroop(大本等级→主键 @0.8), → pve_pve_level(ID→PVE关卡文件ID @0.79), → skill_condition(时代→值参数对比条件 @0.79), → activity(时代→活动参数 @0.78), → draw_card_discount(时代→折扣组 @0.77), → worldScene_monsterFresh(时代→基础刷新等级 @0.77), ...+34条出向, ← activity(活动参数→大本等级 @0.81), ← equip(装备位置→时代 @0.76), ← kvkSeason(默认投票结果→时代 @0.76), ← recharge(档位(真实付费)→时代 @0.76), ← alliance_building(建筑类型→时代 @0.76), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→时代 @0.76), ← hud_config(显示权重，越大显示越前面→时代 @0.76), ← task(任务类型→时代 @0.76), ← army(治疗消耗时间→大本等级 @0.74), ← army_trait(主键→大本等级 @0.73), ...+29条入向

## 表: battleAttribute [battle]
- 文件: battleAttribute.xlsx | sheet: battleAttribute
- 行数: 60 | 列数: 3 | 主键: 战斗实体属性枚举ID
- 列: 战斗实体属性枚举ID(int)→point_transform_pointTransform.ID, #属性名备注(str), #策划说明(str)
- 关联: → battle_system_event_conditionRelation(战斗实体属性枚举ID→战斗系统事件类型 @0.85), → monsterTroop(战斗实体属性枚举ID→主键 @0.69), → point_transform_pointTransform(战斗实体属性枚举ID→ID @0.61)

## 表: battleBehavior [battle]
- 文件: battleBehavior.xlsx | sheet: battleBehavior
- 行数: 1 | 列数: 2 | 主键: AI行为树配置方案ID
- 列: AI行为树配置方案ID(int), #策划说明(str)
- 关联: 无

## 表: battle_system_event_battleSystemEventType [battle]
- 文件: battle_system_event.xlsx | sheet: battleSystemEventType
- 行数: 35 | 列数: 5 | 主键: 战斗系统事件类型
- 列: 战斗系统事件类型(int)→pve_pve_level.PVE关卡文件ID, #战斗事件名(str), #备注(str), #特别说明(str), #抛出时机(str)
- 关联: → pve_pve_level(战斗系统事件类型→PVE关卡文件ID @0.69), ← pve_pve_level(关卡显示等级→战斗系统事件类型 @0.65), ← activity(活动参数→战斗系统事件类型 @0.64)

## 表: battle_system_event_conditionRelation [battle]
- 文件: battle_system_event.xlsx | sheet: conditionRelation
- 行数: 14 | 列数: 2 | 主键: 战斗系统事件类型
- 列: 战斗系统事件类型(int), 条件类型(str)
- 关联: ← battleAttribute(战斗实体属性枚举ID→战斗系统事件类型 @0.85)

## 表: buff [skill]
- 文件: buff.xlsx | sheet: buff
- 行数: 35 | 列数: 25 | 主键: 键值
- 列: 键值(int), 效果名称(str), #效果描述(str), 效果描述(str), #策划备注(str), 效果图标(str), 效果逻辑ID(int), 是否仅逻辑效果(str), 效果等级(int), 效果作用兵种类型(int), 效果目标选择区域类型(float), 效果目标选择数量、类型(str), 效果目标选择器筛选规则(int), 参数数值类型(int), 效果参数数值(str), 效果持续回合数(int), 效果CD回合数(int), 效果触发条件参数配置(str), 技能效果生效几率(int), 叠加规则(int), 是否可重置时间(int), 是否可驱散(int), 效果前端特效组(int), 效果文本显示类型(int), 效果tips文本(str)
- 关联: ← mail_bufftemplate(部队增益在buff表的逻辑ID→效果逻辑ID @0.91), ← hero(英雄主动技能ID→键值 @0.68), ← mail_bufftemplate(部队增益在buff表的逻辑ID→键值 @0.6)

## 表: buff_attribute [skill]
- 文件: buff_attribute.xlsx | sheet: buff_attribute
- 行数: 98 | 列数: 8 | 主键: 编号
- 列: 编号(int), #buff名称(str), 名字(str), 类型(int), 数值类型(int), 条件(str), 应用场景（1沙盘2副本3kvk）(str), 关联沙盘战斗效果配置(int)
- 关联: ← mail_bufftemplate(部队增益在buff表的逻辑ID→类型 @0.82), ← buff_attribute_buff_client(需要计算的buff_id，可能需要多个，如加步兵攻击力、加全体攻击力→编号 @0.75), ← alliance_buff_attribute(类型→类型 @0.72), ← army(兵种类型→类型 @0.72), ← army_monster(兵种类型→类型 @0.72), ← effect(触发的buff→编号 @0.68)

## 表: buff_attribute_buff_client [skill]
- 文件: buff_attribute.xlsx | sheet: buff_client
- 行数: 32 | 列数: 8 | 主键: 编号
- 列: 编号(int), #buff名称(str), 名字(str), 需要计算的buff_id，可能需要多个，如加步兵攻击力、加全体攻击力(int)→buff_attribute.编号, 图标(str), 页签(int), 排序，小的在前(int)→effect.组, 野外行军显示优先级(int)→key_new.facial
- 关联: → pve_pve_level(排序，小的在前→关卡显示等级 @0.96), → activity(排序，小的在前→活动参数 @0.88), → pve_pve_level(排序，小的在前→PVE关卡文件ID @0.82), → pve_pve_level(野外行军显示优先级→关卡显示等级 @0.82), → building(排序，小的在前→参数1 @0.76), → city_node_type_cityNodeTypeConf(野外行军显示优先级→节点类型  参考CityNodeType @0.76), → monsterTroop(排序，小的在前→主键 @0.75), → item(排序，小的在前→参数1 @0.75), → buff_attribute(需要计算的buff_id，可能需要多个，如加步兵攻击力、加全体攻击力→编号 @0.75), → building(排序，小的在前→等级 @0.73), ...+14条出向, ← army(优先级→排序，小的在前 @0.74), ← science(显示层级【只需配置第1级】→排序，小的在前 @0.74), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→排序，小的在前 @0.71), ← zombie_survivor(战斗力，显示值→排序，小的在前 @0.71), ← zombie(基础防御→排序，小的在前 @0.7), ← activity(类型→排序，小的在前 @0.67), ← explore_task_exploreTaskFresh(小队人数.1→野外行军显示优先级 @0.67), ← army(基础负载→排序，小的在前 @0.66), ← army_monster(基础负载→排序，小的在前 @0.66), ← equip(穿戴等级→排序，小的在前 @0.66), ...+20条入向

## 表: building [building]
- 文件: building.xlsx | sheet: building
- 行数: 424 | 列数: 47 | 主键: 先定一个9位数字作为id吧
- 列: 先定一个9位数字作为id吧(int), #策划备注(str), 建筑名，直接索引字典表(str), 描述，同样索引字典表(str), 描述，同样索引字典表.1(str), 组ID
(int)→building_buildingGroup.建筑组ID, 等级(int)→item.参数1, 最大等级(int), 战斗力(int), 繁荣度(int), 资源路径(str), 破损模型(str)→model.模型资源【Assets/Game_Prefab/prefab/model】, 建造图标(str), 点击音效(str), icon高度(str), icon宽度(str), 缩放时隐藏次序，越大越不会被隐藏(int)→item.参数1, 建筑高度（长度）(int)→monsterTroop.主键, 建筑宽度(int), 解锁等级(int), 是否开放(int), 是否可合成(str), 可删除，预留(int), 删除后奖励(int), 配置位于建造菜单的哪一页
配置0代表不可建造(str), ...+22列
- 关联: → activity(等级→活动参数 @0.94), → activity(缩放时隐藏次序，越大越不会被隐藏→活动参数 @0.89), → pve_pve_level(缩放时隐藏次序，越大越不会被隐藏→PVE关卡文件ID @0.87), → pve_pve_level(效果类型→关卡显示等级 @0.86), → activity(效果类型→活动参数 @0.82), → city_node_type_cityNodeTypeConf(效果类型→节点类型  参考CityNodeType @0.82), → monsterTroop(缩放时隐藏次序，越大越不会被隐藏→主键 @0.77), → item(等级→参数1 @0.76), → item(缩放时隐藏次序，越大越不会被隐藏→参数1 @0.74), → model(破损模型→键值 @0.74), ...+21条出向, ← city_area_gridEvent(奖励建筑id→先定一个9位数字作为id吧 @0.95), ← pve_pve_level(关卡显示等级→等级 @0.87), ← material_merge_MaterialProduce(每次生产获得数量→建筑高度（长度） @0.8), ← material_merge_MaterialProduce(每次生产需要时间→建筑高度（长度） @0.8), ← army(基础行军速度→幸存者等级上限 @0.78), ← army_monster(基础行军速度→幸存者等级上限 @0.78), ← soldier_consumption(重伤比例→建筑高度（长度） @0.78), ← worldScene_monsterLevel(等级上限→参数1 @0.77), ← buff_attribute_buff_client(排序，小的在前→参数1 @0.76), ← recharge(优先级→参数1 @0.76), ...+101条入向

## 表: building_buildingGroup [building]
- 文件: building.xlsx | sheet: buildingGroup
- 行数: 21 | 列数: 4 | 主键: 建筑组ID
- 列: 建筑组ID(int)→building.先定一个9位数字作为id吧, #策划备注(str), 建筑hud面板配置ID(str)→entity_menu_entity_menu_config.hud应用功能类型, 建造时是否使用地基(str)
- 关联: → entity_menu_entity_menu_config(建筑hud面板配置ID→hud应用功能类型 @0.62), → building(建筑组ID→先定一个9位数字作为id吧 @0.6), ← building(组ID
→建筑组ID @0.65)

## 表: building_npc [building]
- 文件: building_npc.xlsx | sheet: building_npc
- 行数: 3 | 列数: 6 | 主键: 建筑groupid
- 列: 自增id(str), 建筑groupid(int)→building.先定一个9位数字作为id吧, 休闲站位偏移值(str), 休闲y站位角度(str), 生产中站位偏移值(str), 生产中y站位角度(str)
- 关联: → building(建筑groupid→先定一个9位数字作为id吧 @0.6)

## 表: cinema_config [config]
- 文件: cinema_config.xlsx | sheet: cinema_config
- 行数: 1 | 列数: 3 | 主键: 步骤id
- 列: 步骤id(int), 剧情预制体名称(str), 是否启用自带相机(str)
- 关联: 无

## 表: city_area_areaUnlock [building]
- 文件: city_area.xlsx | sheet: areaUnlock
- 行数: 9 | 列数: 6 | 主键: 解锁地块id 关联grid表id
- 列: 主键(str)→key_new.facial, 解锁地块id 关联grid表id(str), 解锁前置条件(str), 必须解锁事件(str), 非必须解锁事件(str), 解锁地块id 关联grid表id.1(str)
- 关联: → rank(主键→排行数据源类型 @0.74), → pve_pve_level(主键→PVE关卡文件ID @0.72), → video_point_videoPoint(主键→主键 @0.71), → key_new(主键→facial @0.7), → world_building_worldBuilding(主键→id @0.62), → item(主键→编号 @0.61), ← client_rank_alliance_rank(排行榜类型→主键 @0.9), ← weapon(武器技能（pve_skill的技能组ID，复写）→主键 @0.88), ← sceneManager(场景LOD配置ID→主键 @0.85), ← world_building_worldBuilding(区分地图→主键 @0.8), ← default_sth_defaultSth(id→主键 @0.77), ← sceneManager(主键（唯一标识）→主键 @0.68), ← lodConfig(主键（唯一标识）→主键 @0.65), ← client_rank_alliance_rank(自增id→主键 @0.6)

## 表: city_area_grid [building]
- 文件: city_area.xlsx | sheet: grid
- 行数: 70 | 列数: 3 | 主键: 主键
不配置的ID为空地
- 列: 主键
不配置的ID为空地(str), 地表信息 areaBG(此列必须有值，取值范围参考gridBG表)(str), 绑定事件id gridEvent 
事件ideventTYpe(str)→city_area_gridEvent.主键
- 关联: → city_area_gridEvent(绑定事件id gridEvent 
事件ideventTYpe→主键 @0.85), ← activity(活动奖励显示→绑定事件id gridEvent 
事件ideventTYpe @0.73), ← city_area_gridEvent(绑定事件gridid→主键
不配置的ID为空地 @0.72)

## 表: city_area_gridBG [building]
- 文件: city_area.xlsx | sheet: gridBG
- 行数: 5 | 列数: 3 | 主键: 主键
- 列: 主键(str), #注释说明 地块属性 地表层(str), 自由城建标识(str)
- 关联: 无

## 表: city_area_gridBuilding [building]
- 文件: city_area.xlsx | sheet: gridBuilding
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: city_area_gridEvent [building]
- 文件: city_area.xlsx | sheet: gridEvent
- 行数: 55 | 列数: 12 | 主键: 主键
- 列: 主键(str), 前置条件(解锁条件判断填写gridId)(str), 关卡类型(int), 
事件奖励(str), 奖励建筑id(int)→building.先定一个9位数字作为id吧, 解锁后是否破损(int), pve关卡ID 地块战斗后没奖励(int), 外显形象配置（读取building表）
地块解锁时按钮位置、解锁阴影范围相关(str), 解锁时间(s)(str), 角度信息(str), 策划备注(str), 绑定事件gridid(str)→city_area_grid.主键
不配置的ID为空地
- 关联: → building(奖励建筑id→先定一个9位数字作为id吧 @0.95), → city_area_grid(绑定事件gridid→主键
不配置的ID为空地 @0.72), ← city_area_grid(绑定事件id gridEvent 
事件ideventTYpe→主键 @0.85)

## 表: city_area_gridFog [building]
- 文件: city_area.xlsx | sheet: gridFog
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: city_area_gridResource [item]
- 文件: city_area.xlsx | sheet: gridResource
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: city_area_navigate [building]
- 文件: city_area.xlsx | sheet: navigate
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: city_node_type_cityNodeTypeConf [building]
- 文件: city_node_type.xlsx | sheet: cityNodeTypeConf
- 行数: 18 | 列数: 4 | 主键: 自增id
- 列: 自增id(str)→pve_pve_level.PVE关卡文件ID, 节点类型  参考CityNodeType(str)→worldMonster.部队配置ID, #策划备注(str), 根节点名称(str)
- 关联: → worldMonster(节点类型  参考CityNodeType→部队配置ID @0.83), → monsterTroop(节点类型  参考CityNodeType→主键 @0.8), → rank_rank_reward(节点类型  参考CityNodeType→主键 @0.8), → hero_hero_level(节点类型  参考CityNodeType→等级 @0.75), → pve_pve_level(自增id→关卡显示等级 @0.75), → activity(自增id→活动参数 @0.67), → pve_pve_level(自增id→PVE关卡文件ID @0.66), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→节点类型  参考CityNodeType @0.89), ← army(优先级→节点类型  参考CityNodeType @0.88), ← science(显示层级【只需配置第1级】→节点类型  参考CityNodeType @0.88), ← zombie_survivor(战斗力，显示值→节点类型  参考CityNodeType @0.84), ← pve_skill_skill_target_action(筛选区域参数1→节点类型  参考CityNodeType @0.83), ← task(任务类型→节点类型  参考CityNodeType @0.82), ← building(效果类型→节点类型  参考CityNodeType @0.82), ← activity(类型→节点类型  参考CityNodeType @0.8), ← trigger_config(主键→节点类型  参考CityNodeType @0.8), ← army(基础负载→节点类型  参考CityNodeType @0.78), ...+34条入向

## 表: client_rank_alliance_rank [alliance]
- 文件: client_rank.xlsx | sheet: alliance_rank
- 行数: 6 | 列数: 7 | 主键: 自增id
- 列: 自增id(str)→city_area_areaUnlock.主键, 排行榜名字(str), 图标(str), 排行榜类型(str)→key_new.facial, 提示标题(str), 提示内容(str), 排行项文字(str)
- 关联: → activity_activity_param(排行榜类型→排行榜奖励发放 @0.9), → city_area_areaUnlock(排行榜类型→主键 @0.9), → video_point_videoPoint(排行榜类型→主键 @0.78), → pve_skill_skill_target_action(排行榜类型→执行逻辑 @0.77), → pve_pve_level(排行榜类型→PVE关卡文件ID @0.74), → rank(排行榜类型→排行数据源类型 @0.73), → worldMonster(排行榜类型→序号 @0.72), → world_building_worldBuilding(排行榜类型→id @0.71), → item(排行榜类型→编号 @0.71), → activity_activity_param(自增id→排行榜奖励发放 @0.7), ...+2条出向, ← default_sth_defaultSth(id→排行榜类型 @0.95), ← sceneManager(场景LOD配置ID→排行榜类型 @0.85), ← world_building_worldBuilding(区分地图→排行榜类型 @0.85), ← pve_skill_hit_effect(键值→排行榜类型 @0.75), ← sceneManager(主键（唯一标识）→排行榜类型 @0.7), ← sceneManager(场景LOD配置ID→自增id @0.7), ← default_sth_defaultSth(id→自增id @0.65), ← world_building_worldBuilding(区分地图→自增id @0.65), ← lodConfig(主键（唯一标识）→排行榜类型 @0.65), ← lodConfig(主键（唯一标识）→自增id @0.6)

## 表: client_show_client_bullet [other]
- 文件: client_show.xlsx | sheet: client_bullet
- 行数: 20 | 列数: 14 | 主键: 键值
- 列: 键值(str), #描述(str), 弹幕类型
0：Line直线飞行
1：抛物线
2：闪电链【暂未支持】
3：随机轨迹弹道
4：直接出现在目标位置，不移动
5：物理检测子弹(int), 飞行速度
默认15m/s(int)→building.参数1, 飞行距离【米】
目前fly_type==5起效(int), 水平移动模式
0：匀速
1：加速
2：减速
注意不影响命中总时长，命中总时长=实际距离/fly_speed(int), 命中目标后停留时间【ms】(int), 特效资源名
Assets/Game_Prefab/prefab/fx目录底下，不带后缀(str), 当flyType=1时起效，抛物线的幅度。(float), 当flyType=1时起效，目标影响抛物线实际幅度。
公式：height=parabolaHeight*dis/parabolaWidth(int), 发起者，从哪个骨点飞出
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部(int)→key_new.facial, 发起者，偏移位置
x|y|z(str), 命中，从哪个骨点飞出
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部(int), 命中，偏移位置
x|y|z(str)
- 关联: → pve_skill(飞行速度
默认15m/s→检索距离，即技能释放距离【float，米】 @0.79), → pve_pve_level(飞行速度
默认15m/s→PVE关卡文件ID @0.75), → pve_pve_level(发起者，从哪个骨点飞出
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部→关卡显示等级 @0.75), → data_constant(飞行速度
默认15m/s→常量值 @0.72), → monsterTroop(飞行速度
默认15m/s→主键 @0.72), → item(飞行速度
默认15m/s→参数1 @0.72), → data_constant(发起者，从哪个骨点飞出
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部→常量值 @0.71), → key_new(发起者，从哪个骨点飞出
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部→facial @0.7), → activity(飞行速度
默认15m/s→活动参数 @0.68), → building(飞行速度
默认15m/s→参数1 @0.64), ← material_merge_MaterialProduce(每次生产获得数量→飞行速度
默认15m/s @0.85), ← material_merge_MaterialProduce(每次生产需要时间→飞行速度
默认15m/s @0.85), ← alliance_building(采集速度→飞行速度
默认15m/s @0.85), ← soldier_consumption(重伤比例→飞行速度
默认15m/s @0.81), ← pve_skill_skill_target_action(弹幕配置，对应client_show.xlsx中client_bullet中配置，不是真正的弹幕
如果有弹幕，弹幕命中后才真正执行actionList→键值 @0.68)

## 表: client_show_client_effect [other]
- 文件: client_show.xlsx | sheet: client_effect
- 行数: 49 | 列数: 10 | 主键: 键值
- 列: 键值(int), #描述(str), 资源名(str), 特效类型：
0：实体
1：世界
2：UI
3：相机(int), 绑定方式
0：位置不跟随，脚底位置，初始朝向为绑定者朝向，偏移位置会起效。
1：不绑骨点，位置跟随，玩家骨点位置，不设置朝向，偏移位置会起效。
2：不绑骨点，位置不跟随，玩家骨点位置，不设置朝向，偏移位置会起效。
3：直接挂骨点上，偏移位置会起效。(int), 特效位置
0：头；2胸；
3：左手；4：右手；
5：左胳膊；6：右胳膊；
7：左腿；8：右腿；
9：左脚；10：右脚
11或者找不到：模型底部(int), 偏移位置
x|y|z(str), 缩放(float), 是否是循环特效(str), 持续时间【毫秒】(int)
- 关联: 无

## 表: combatStrength [battle]
- 文件: combatStrength.xlsx | sheet: combatStrength
- 行数: 10 | 列数: 2 | 主键: 索引
- 列: 索引(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 战斗力限制(str)
- 关联: → shop_shop_item(索引→商店id @0.72), → pve_pve_level(索引→关卡显示等级 @0.64), → city_node_type_cityNodeTypeConf(索引→节点类型  参考CityNodeType @0.63), → pve_pve_level(索引→PVE关卡文件ID @0.61), → activity(索引→活动参数 @0.6)

## 表: data_constant [config]
- 文件: data_constant.xlsx | sheet: data_constant
- 行数: 212 | 列数: 4 | 主键: 键值
- 列: 键值(str), 常量值(str), @类型(str), #策划备注(str)
- 关联: ← data_constant_battle_constant(@类型→@类型 @0.8), ← alliance_constant(@类型→@类型 @0.8), ← area_area_config(地块关卡类型→常量值 @0.72), ← activity(活动入口→常量值 @0.72), ← baseLevel(时代→常量值 @0.72), ← equip(装备位置→常量值 @0.72), ← kvkSeason(报名赛季标识组→常量值 @0.72), ← kvkSeason(默认投票结果→常量值 @0.72), ← recharge(档位(真实付费)→常量值 @0.72), ← alliance_building(建筑类型→常量值 @0.72), ...+52条入向

## 表: data_constant_battle_constant [battle]
- 文件: data_constant.xlsx | sheet: battle_constant
- 行数: 10 | 列数: 4 | 主键: 键值
- 列: 键值(str), 常量值(str)→data_constant.常量值, @类型(str)→data_constant.@类型, #策划备注(str)
- 关联: → data_constant(@类型→@类型 @0.8), → data_constant(常量值→常量值 @0.72)

## 表: default_sth_defaultSth [other]
- 文件: default_sth.xlsx | sheet: defaultSth
- 行数: 12 | 列数: 5 | 主键: -
- 列: id(int)→key_new.facial, #策划备注(str), 类型(str), 数据(str), #备注(str)
- 关联: → point_transform_pointTransform(id→积分类型 @0.95), → client_rank_alliance_rank(id→排行榜类型 @0.95), → activity_activity_param(id→排行榜奖励发放 @0.87), → pve_pve_level(id→PVE关卡文件ID @0.78), → city_area_areaUnlock(id→主键 @0.77), → pve_skill_skill_target_action(id→执行逻辑 @0.76), → rank(id→排行数据源类型 @0.72), → key_new(id→facial @0.7), → video_point_videoPoint(id→主键 @0.66), → client_rank_alliance_rank(id→自增id @0.65), ...+2条出向, ← sceneManager(场景LOD配置ID→id @0.93), ← world_building_worldBuilding(区分地图→id @0.88), ← sceneManager(主键（唯一标识）→id @0.79), ← lodConfig(主键（唯一标识）→id @0.73)

## 表: draw_card [other]
- 文件: draw_card.xlsx | sheet: draw_card
- 行数: 5 | 列数: 24 | 主键: 索引
- 列: 索引(int), #策划备注列(str), 卡池名称(str), 抽卡类型(int), 单抽消耗(str), 多次消耗(str), 消耗类型(int), 单抽出货次数(int), 单抽免费次数（活动）(int), 免费间隔时间(int), 奖励ID(int)→guide_config.主键, 是否有10连保底(int), 固定第N此奖励类型(int), 固定第N次奖励(str), M次未出次数(int), M次未出橙固定奖励(int), 终生限定次数(str), 每日抽取次数(int)→building.幸存者等级上限, 卡池美术资源(str), 单次开启数量上限(int)→key_new.facial, 前置建筑(str), 详情排序(int), 概率表id(int), 解锁条件(str)
- 关联: → reward(奖励ID→ID @0.95), → zombie(单次开启数量上限→装备武器（weapon表） @0.8), → item(单次开启数量上限→道具分类排序 @0.79), → shop_shop_item(单次开启数量上限→商店id @0.78), → skill_condition(单次开启数量上限→值参数对比条件 @0.78), → rank(单次开启数量上限→排行榜奖励 @0.76), → rank_rank_reward(单次开启数量上限→排名组 @0.76), → world_building_worldBuilding(奖励ID→id @0.76), → guide_config(奖励ID→主键 @0.76), → building(每日抽取次数→幸存者等级上限 @0.75), ...+34条出向

## 表: draw_card_discount [other]
- 文件: draw_card.xlsx | sheet: discount
- 行数: 13 | 列数: 7 | 主键: 索引
- 列: 索引(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 折扣组(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 折扣类型(int), 次数(int), 消耗类型(int), 价格(str), 折扣率(int)
- 关联: → shop_shop_item(折扣组→商店id @0.95), → item(折扣组→道具分类排序 @0.86), → pve_pve_level(折扣组→关卡显示等级 @0.82), → activity(折扣组→活动参数 @0.79), → equip(折扣组→穿戴等级 @0.77), → science(折扣组→等级 @0.77), → alliance_science_alliance_skill(折扣组→等级 @0.77), → pve_pve_level(折扣组→PVE关卡文件ID @0.76), → city_node_type_cityNodeTypeConf(折扣组→节点类型  参考CityNodeType @0.76), → activity(折扣组→类型 @0.75), ...+27条出向, ← activity(活动入口→折扣组 @0.77), ← baseLevel(时代→折扣组 @0.77), ← kvkSeason(报名赛季标识组→折扣组 @0.77), ← alliance_shop_alliance_shopItem(排序→折扣组 @0.77), ← zombie_survivor(兵种等级→折扣组 @0.77), ← equip(装备位置→折扣组 @0.73), ← kvkSeason(默认投票结果→折扣组 @0.73), ← recharge(档位(真实付费)→折扣组 @0.73), ← alliance_building(建筑类型→折扣组 @0.73), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→折扣组 @0.73), ...+8条入向

## 表: draw_card_probability [skill]
- 文件: draw_card.xlsx | sheet: probability
- 行数: 6 | 列数: 8 | 主键: Unnamed: 6
- 列: 索引(int), 总览(str), 详情(str), Unnamed: 6(str), Unnamed: 7(str), Unnamed: 8(float), Unnamed: 10(str), Unnamed: 14(str)
- 关联: 无

## 表: effect [other]
- 文件: effect.xlsx | sheet: effect
- 行数: 32 | 列数: 9 | 主键: 编号
- 列: 编号(int), 组(int)→item.参数1, 触发的buff(int)→buff_attribute.编号, 客户端是否要显示(int), 显示优先级(int), effect名称，key_new表字段(str), 图标(str), #策划备注1(str), 显示分组(int)
- 关联: → pve_pve_level(组→PVE关卡文件ID @0.89), → monsterTroop(组→主键 @0.78), → item(组→参数1 @0.78), → baseLevel(组→大本等级 @0.73), → monsterTroop(组→显示等级 @0.7), → buff_attribute(触发的buff→编号 @0.68), → pve_pve_level(组→主键 @0.66), → point_transform_pointTransform(组→ID @0.63), → worldMonster(组→部队配置ID @0.63), → skill_condition(组→键值 @0.62), ← pve_pve_level(关卡显示等级→组 @0.79), ← army(治疗消耗时间→组 @0.75), ← alliance_building(采集速度→组 @0.74), ← material_merge_MaterialProduce(每次生产获得数量→组 @0.74), ← material_merge_MaterialProduce(每次生产需要时间→组 @0.74), ← soldier_consumption(重伤比例→组 @0.73), ← entity_menu(缩放系数修正值→组 @0.73), ← worldScene_monsterLevel(等级上限→组 @0.7), ← building(等级→组 @0.7), ← building(缩放时隐藏次序，越大越不会被隐藏→组 @0.69), ...+9条入向

## 表: effect_autoEffect [other]
- 文件: effect.xlsx | sheet: autoEffect
- 行数: 4 | 列数: 7 | 主键: 编号
- 列: 编号(int), #注释(str), 开启条件(str), 关闭条件(str), 触发的effect(int)→world_building_worldBuilding.id, 持续时长(秒)(int), buffAttr值(int)→hero_hero_level.升下一级需要经验值
- 关联: → hero_hero_level(buffAttr值→升下一级需要经验值 @0.71), → world_building_worldBuilding(触发的effect→id @0.71), → effect(触发的effect→编号 @0.64)

## 表: effect_effectShowGroup [other]
- 文件: effect.xlsx | sheet: effectShowGroup
- 行数: 4 | 列数: 2 | 主键: 编号
- 列: 编号(int), 图标(str)
- 关联: 无

## 表: entity_menu [other]
- 文件: entity_menu.xlsx | sheet: entity_menu
- 行数: 34 | 列数: 11 | 主键: 菜单按钮，对应entity_menu_item中的key
- 列: 关键值【唯一】(str), #描述(str), 菜单按钮，对应entity_menu_item中的key(str), 基础信息对应ui节点名字，对应的脚本名：xxx_item，多个'_item', 如：
building_title_item(str), 底部菜单位置偏移
x,y,z(水平，垂直，前后)(str), 顶部菜单位置偏移
x,y,z(水平，垂直，前后)(str), 进度条位置偏移
x,y,z(水平，垂直，前后)(str), 基础信息ui偏移位置
x,y,z(水平，垂直，前后)(str), 缩放模式
[bottom, top, progress, info](str), 缩放系数修正值(int)→building.参数1, 是否是世界地图中的菜单
缩放算法不一样（废弃）(str)
- 关联: → point_transform_pointTransform(缩放系数修正值→等级区间最大值 @0.74), → worldScene_monsterLevel(缩放系数修正值→等级上限 @0.74), → item(缩放系数修正值→物品类型 @0.74), → building(缩放系数修正值→等级 @0.74), → activity(缩放系数修正值→活动参数 @0.73), → army_trait(缩放系数修正值→主键 @0.73), → effect(缩放系数修正值→组 @0.73), → science(缩放系数修正值→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.73), → building(缩放系数修正值→缩放时隐藏次序，越大越不会被隐藏 @0.73), → baseLevel(缩放系数修正值→大本等级 @0.72), ...+8条出向, ← entity_menu_entity_menu_config(默认加载配置→关键值【唯一】 @0.96)

## 表: entity_menu_entity_menu_config [config]
- 文件: entity_menu.xlsx | sheet: entity_menu_config
- 行数: 29 | 列数: 5 | 主键: hud应用功能类型
- 列: hud应用功能类型(str), #策划备注(str), 默认加载配置(str)→entity_menu.关键值【唯一】, GVG副本场景(str), 塞罗利副本场景(str)
- 关联: → entity_menu(默认加载配置→关键值【唯一】 @0.96), ← building_buildingGroup(建筑hud面板配置ID→hud应用功能类型 @0.62)

## 表: entity_menu_entity_menu_item [item]
- 文件: entity_menu.xlsx | sheet: entity_menu_item
- 行数: 90 | 列数: 16 | 主键: 关键值【唯一】
- 列: 关键值【唯一】(str), #描述(str), icon图标名，Assets/Arts/ui/bubble，细节看logic_lua实现细节(str), icon尺寸，如果不配置，就是SetNativeSize【图片实际尺寸】(str), icon图标名，Assets/Arts/ui/bubble，细节看logic_lua实现细节.1(str), 控制按钮显隐的数据脚本名字(str), 按钮显示时使用的ui资源名字，必须存放路径
Game_Prefab/prefab/panel/menu_item/(str), 菜单ui用的脚本名字，支持不同脚本使用相同ui(str), 是否是3DHud头顶(str), 显示状态：
0：选中才显示【默认】
1：常驻
2：选中、常驻都会显示(int), 显示部位
0：普通菜单位置【默认】
1：顶部位置
2：进度条位置
3：基础信息位置(int), 开启条件，也是显示条件(str), 正常点击执行逻辑(str), 点击按钮后，是否取消选中该实体(str), 沙盒地图LOD显示下限
最小值0
min_lod=max_lod都等于0，表示不限制(int), 沙盒地图LOD显示上限
最大值8(int)→key_new.facial
- 关联: → pve_pve_level(沙盒地图LOD显示上限
最大值8→关卡显示等级 @0.77), → data_constant(沙盒地图LOD显示上限
最大值8→常量值 @0.71), → key_new(沙盒地图LOD显示上限
最大值8→facial @0.7), → alliance_science(沙盒地图LOD显示上限
最大值8→等级 @0.64)

## 表: equip [item]
- 文件: equip.xlsx | sheet: equip
- 行数: 10 | 列数: 12 | 主键: 编号
- 列: 编号(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 名称(str), 品质(int), 穿戴等级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 装备位置(int)→alliance_science_alliance_skill.等级, 装备属性(str), 专属属性(str), 锻造需要材料（材料+图纸）(str), 锻造资源消耗(str), 精炼材料（图纸）消耗(str), 精炼资源消耗(str), 套装ID(int)
- 关联: → item(装备位置→道具分类排序 @0.91), → shop_shop_item(装备位置→商店id @0.89), → skill_condition(装备位置→值参数对比条件 @0.88), → shop_shop_item(穿戴等级→商店id @0.87), → pve_pve_level(穿戴等级→关卡显示等级 @0.84), → activity(穿戴等级→活动参数 @0.8), → pve_pve_level(装备位置→关卡显示等级 @0.8), → city_node_type_cityNodeTypeConf(穿戴等级→节点类型  参考CityNodeType @0.78), → activity(穿戴等级→类型 @0.77), → activity(装备位置→活动参数 @0.77), ...+52条出向, ← draw_card_discount(折扣组→穿戴等级 @0.77), ← worldScene_monsterFresh(基础刷新等级→穿戴等级 @0.77), ← alliance_building(排序数量→穿戴等级 @0.77), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→穿戴等级 @0.77), ← hud_config_personal_config(排序→穿戴等级 @0.77), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→装备位置 @0.76), ← baseLevel(时代→穿戴等级 @0.74), ← kvkSeason(报名赛季标识组→穿戴等级 @0.74), ← alliance_shop_alliance_shopItem(排序→穿戴等级 @0.74), ← zombie_survivor(兵种等级→穿戴等级 @0.74), ...+15条入向

## 表: equip_refine [item]
- 文件: equip.xlsx | sheet: refine
- 行数: 4 | 列数: 3 | 主键: 编号
- 列: 编号(int), 当前进度(int), 精炼增长进度及概率(str)
- 关联: 无

## 表: equip_suit [item]
- 文件: equip.xlsx | sheet: suit
- 行数: 2 | 列数: 5 | 主键: 编号
- 列: 编号(int), 名称(str), 套装组成(str), 套装属性件数(str), 套装属性，和上一条对应(str)
- 关联: 无

## 表: explore_task_exploreTask [quest]
- 文件: explore_task.xlsx | sheet: exploreTask
- 行数: 9 | 列数: 9 | 主键: ID
- 列: ID(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 任务类型(int), 品质(int), 任务名称(str), 说明文字(str), 任务奖励(int), 关联NPCID(int), 存在时间(int), 体力消耗(int)
- 关联: → shop_shop_item(ID→商店id @0.8), → item(ID→道具分类排序 @0.66), → pve_pve_level(ID→关卡显示等级 @0.62), → pve_pve_level(ID→PVE关卡文件ID @0.61), → city_node_type_cityNodeTypeConf(ID→节点类型  参考CityNodeType @0.61)

## 表: explore_task_exploreTaskFresh [quest]
- 文件: explore_task.xlsx | sheet: exploreTaskFresh
- 行数: 5 | 列数: 5 | 主键: ID
- 列: ID(int), 小队人数(str)→key_new.facial, 小队人数.1(str)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 出现任务数量(int), 任务几率(str)
- 关联: → city_node_type_cityNodeTypeConf(小队人数.1→节点类型  参考CityNodeType @0.78), → pve_pve_level(小队人数→关卡显示等级 @0.77), → pve_pve_level(小队人数.1→关卡显示等级 @0.77), → activity(小队人数→活动参数 @0.75), → activity(小队人数.1→活动参数 @0.75), → pve_pve_level(小队人数→PVE关卡文件ID @0.73), → building(小队人数→参数1 @0.72), → building(小队人数.1→参数1 @0.72), → data_constant(小队人数→常量值 @0.71), → monsterTroop(小队人数→主键 @0.71), ...+24条出向

## 表: gift_package [reward]
- 文件: gift_package.xlsx | sheet: gift_package
- 行数: 1 | 列数: 2 | 主键: 键值
- 列: 键值(int), #策划备注(str)
- 关联: ← recharge(礼包展示ID→键值 @0.8)

## 表: gift_package_gift_condition [reward]
- 文件: gift_package.xlsx | sheet: gift_condition
- 行数: 1 | 列数: 2 | 主键: 键值
- 列: 键值(int), #策划备注(str)
- 关联: 无

## 表: gift_package_gift_shoppage [reward]
- 文件: gift_package.xlsx | sheet: gift_shoppage
- 行数: 1 | 列数: 3 | 主键: 键值
- 列: 键值(int), #策划备注(str), 礼包标题名字(str)
- 关联: 无

## 表: guide_config [config]
- 文件: guide_config.xlsx | sheet: guide_config
- 行数: 128 | 列数: 24 | 主键: 主键
- 列: 主键(int), 步骤组ID
这个字段暂时没用(int), #策划备注(str), 引导类型
0,  -- 没有执行体
1,   -- UI 点击
2,  -- 内城场景实体 点击
3, -- 剧情对话
4,-- CG(int), 如果有小手指，是否隐藏手指(str), 是否是强制指引(str), 强引导蒙版透明度
【float】0~1，默认0(float), 步骤是否存档，force为false不会存档(str), 指引是否可整个跳过(str), 强制自动下一步时间，【秒float】(int), 自动关闭时间，【秒float】，一般用于非强制引导(int), guide_type=1：界面名字
guide_type=2：建筑GroupId
guide_type=3：剧情对话ID【guide_dialog】
guide_type=4：视频名字，xxx.mp4【目录:StreamingAssets/video】
guide_type=5：x,y,z,w,h，如："100,0.45,96,4,4"(str), 1.界面上按钮名字
2：Action函数，程序实现，返回 MapCityNodeView 及子类数据，优先于param1起效
3：配置id
4：wwise音频开始事件,wwise音频结束事件，如："Control_CGStart_kuafu,Control_CGEnd_kuafu"
5：当param_1无效时，Action函数形式返回 x,y,z,w,h(str), guide_type==1起效
是否缩放校准，目前实体上菜单按钮需要，其余不用勾(str), 是否移到屏幕中心(str), 是否打开boxCollider遮挡全屏【目前引导建造需要】
0：不需要（默认）
非0：需要(int), 下一步(int), 引导失败后执行的引导步骤，默认为0，即终止
用作实现分叉引导(int), 失败执行逻辑(str), 满足条件才能执行，否则失败处理，说明详见mos\策划文档\Words\Z_Condition_Action说明.xlsx(str), 满足条件执行下一步(str), 引导开始时执行行为(str), 引导结束执行行为，该引导条件成功才执行(str), 等待主城(int)
- 关联: ← draw_card(奖励ID→主键 @0.76), ← alliance_gift(奖励→主键 @0.71), ← alliance_buff_attribute(类型→主键 @0.71)

## 表: guide_config_guide_dialog [config]
- 文件: guide_config.xlsx | sheet: guide_dialog
- 行数: 32 | 列数: 10 | 主键: 主键
- 列: 主键(int), #说话人(str), #内容(str), 说话人位置
0：左侧，1：右侧2:插屏(int), 说话人头像路径
Game_Prefab/texture/xxx(str), 头像形象尺寸，不配置表示，NativeSize(str), 说话人名字
key_new.xlsx(str), 对话内容
key_new.xlsx(str), 说完之后是否移走，不移走，就半透明到后面去(str), 下一句对话(int)
- 关联: 无

## 表: gvgProcessConfig [config]
- 文件: gvgProcessConfig.xlsx | sheet: gvgProcessConfig
- 行数: 1 | 列数: 11 | 主键: gvg流程规则配置id
- 列: gvg流程规则配置id(int), #策划备注(str), 社交关系ID(int), 玩法活动ID(str), 预告阶段预留字段(int), 报名阶段-报名条件(str), 匹配阶段预留字段(int), 副本开启阶段-预告邮件时间(str), 副本开启阶段-进入条件(str), 副本开启阶段-原服主城获得状态(str), 副本关闭阶段-原服主城取消状态(str)
- 关联: 无

## 表: hero [hero]
- 文件: hero.xlsx | sheet: hero
- 行数: 17 | 列数: 37 | 主键: 键值
- 列: 键值(int)→pve_pve_level.关卡显示等级, #策划备注(str), 英雄名字(str), 英雄称号(str), 英雄描述(str), 英雄PVE介绍(str), 英雄头像(str), 英雄模型(str), 英雄展示场景(str), 英雄 timeline(str), 英雄品质(int), 英雄基础战斗力(int)→hero_hero_offices.解锁数值, 每级战力加成(str), 英雄每升级
增加部队容量(int), 英雄天赋(str), 英雄主动技能ID(int)→reward.ID, 英雄被动技能ID(int)→world_building_worldBuilding.id, 英雄技能升星与栏位配置(str), 英雄专属雕像物品ID(int)→item.编号, 英雄是否生效(int), 内城战斗显示模型(str), 内城战斗显示模型
(临时字段，敌人模型)(str), 内城战斗基础生命(int), 内城战斗基础攻击(int), 内城战斗基础防御(int), ...+12列
- 关联: → skill(英雄主动技能ID→键值 @0.95), → skill(英雄被动技能ID→键值 @0.95), → item(英雄专属雕像物品ID→编号 @0.95), → hero_hero_offices(英雄基础战斗力→解锁数值 @0.83), → world_building_worldBuilding(英雄被动技能ID→id @0.77), → world_building_worldBuilding(英雄主动技能ID→id @0.73), → hero_hero_level(英雄基础战斗力→升下一级需要经验值 @0.71), → alliance_building(英雄被动技能ID→id=10000*type+n @0.71), → buff(英雄主动技能ID→键值 @0.68), → activity(键值→活动参数 @0.66), ...+4条出向, ← monsterTroop_monsterHero(英雄ID→键值 @0.95), ← instanceTroop_instancePlayerHero(英雄ID→键值 @0.95), ← activity(活动额外参数→英雄主动技能ID @0.82), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→键值 @0.78), ← science(显示层级【只需配置第1级】→键值 @0.76), ← alliance_buff_attribute(类型→英雄主动技能ID @0.76), ← item_recycle(ID→英雄主动技能ID @0.73), ← activity(类型→键值 @0.69), ← army(基础负载→键值 @0.68), ← army_monster(基础负载→键值 @0.68), ...+22条入向

## 表: hero_hero_level [hero]
- 文件: hero.xlsx | sheet: hero_level
- 行数: 100 | 列数: 3 | 主键: 等级
- 列: 等级(int)→rank_rank_reward.主键, #策划备注(str), 升下一级需要经验值(int)
- 关联: → monsterTroop(等级→主键 @0.81), → rank_rank_reward(等级→主键 @0.63), ← city_node_type_cityNodeTypeConf(节点类型  参考CityNodeType→等级 @0.75), ← science(提供战斗力→升下一级需要经验值 @0.73), ← alliance_building(容纳士兵上限→升下一级需要经验值 @0.73), ← pve_pve_level(关卡显示等级→等级 @0.73), ← item(道具分类排序→等级 @0.73), ← shop_shop_item(周期内限购数量→等级 @0.73), ← army(基础行军速度→等级 @0.72), ← army_monster(基础行军速度→等级 @0.72), ← recharge_rechargeShow(分页→等级 @0.72), ← activity(显示优先级→等级 @0.71), ...+29条入向

## 表: hero_hero_offices [hero]
- 文件: hero.xlsx | sheet: hero_offices
- 行数: 7 | 列数: 5 | 主键: 键值
- 列: 键值(int)→item.道具分类排序, 官职名称(str), 官职buff(str), 解锁类型(int), 解锁数值(int)
- 关联: → shop_shop_item(键值→商店id @0.74), → item(键值→道具分类排序 @0.71), → skill_condition(键值→值参数对比条件 @0.68), → pve_pve_level(键值→关卡显示等级 @0.6), ← hero(英雄基础战斗力→解锁数值 @0.83), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→键值 @0.61)

## 表: hero_hero_star [hero]
- 文件: hero.xlsx | sheet: hero_star
- 行数: 20 | 列数: 6 | 主键: 键值
- 列: 键值(int)→pve_pve_level.PVE关卡文件ID, 稀有度(int), 星级(int), 单星级升阶次数(int), 升阶消耗(str), Unnamed: 5(int)
- 关联: → pve_pve_level(键值→关卡显示等级 @0.77), → activity(键值→活动参数 @0.69), → pve_pve_level(键值→PVE关卡文件ID @0.67)

## 表: hud_config [config]
- 文件: hud_config.xlsx | sheet: hud_config
- 行数: 8 | 列数: 7 | 主键: 按钮名字，key_new表key
- 列: 关键值【唯一】，暂时没有使用(str), 样式：要克隆的节点名，在main_panel.prefab中可以查找到。(str), 显示区域
0：底部菜单下
1：顶部菜单上(int), 显示权重，越大显示越前面(int)→key_new.facial, #按钮名字，key_new表key【注释】(str)→key_new_ui_key_new.中文, 按钮名字，key_new表key(str), icon图标名，Assets/Arts/ui/mainui(str)
- 关联: → item(显示权重，越大显示越前面→道具分类排序 @0.91), → shop_shop_item(显示权重，越大显示越前面→商店id @0.89), → skill_condition(显示权重，越大显示越前面→值参数对比条件 @0.88), → key_new_ui_key_new(#按钮名字，key_new表key【注释】→中文 @0.86), → pve_pve_level(显示权重，越大显示越前面→关卡显示等级 @0.8), → activity(显示权重，越大显示越前面→活动参数 @0.77), → area_area_config(显示权重，越大显示越前面→地块关卡类型 @0.76), → activity(显示权重，越大显示越前面→活动入口 @0.76), → baseLevel(显示权重，越大显示越前面→时代 @0.76), → kvkSeason(显示权重，越大显示越前面→报名赛季标识组 @0.76), ...+34条出向, ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→显示权重，越大显示越前面 @0.76), ← resource_ResRules(联盟资源田数量→显示权重，越大显示越前面 @0.67), ← draw_card(单次开启数量上限→显示权重，越大显示越前面 @0.63)

## 表: hud_config_bookmark_config [config]
- 文件: hud_config.xlsx | sheet: bookmark_config
- 行数: 13 | 列数: 5 | 主键: 标签名字，key_new表key
- 列: 关键值【唯一】，暂时没有使用(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 样式：
0：联盟菜单
1：个人书签
(int), 标签名字，key_new表key(str), icon图标名，Assets/Arts/ui/bookmark(str), 沙河地图上特效资源(str)
- 关联: → city_node_type_cityNodeTypeConf(关键值【唯一】，暂时没有使用→节点类型  参考CityNodeType @0.89), → pve_pve_level(关键值【唯一】，暂时没有使用→关卡显示等级 @0.88), → activity(关键值【唯一】，暂时没有使用→活动参数 @0.83), → pve_pve_level(关键值【唯一】，暂时没有使用→PVE关卡文件ID @0.83), → hero(关键值【唯一】，暂时没有使用→键值 @0.78), → monsterTroop(关键值【唯一】，暂时没有使用→主键 @0.78), → army(关键值【唯一】，暂时没有使用→优先级 @0.76), → science(关键值【唯一】，暂时没有使用→显示层级【只需配置第1级】 @0.76), → building(关键值【唯一】，暂时没有使用→参数1 @0.74), → item(关键值【唯一】，暂时没有使用→参数1 @0.73), ...+12条出向, ← activity(类型→关键值【唯一】，暂时没有使用 @0.75), ← equip(穿戴等级→关键值【唯一】，暂时没有使用 @0.73), ← science(等级→关键值【唯一】，暂时没有使用 @0.73), ← alliance_science_alliance_skill(等级→关键值【唯一】，暂时没有使用 @0.73), ← draw_card_discount(折扣组→关键值【唯一】，暂时没有使用 @0.71), ← kvkSeason_kvkScene(id→关键值【唯一】，暂时没有使用 @0.71), ← worldScene_monsterFresh(基础刷新等级→关键值【唯一】，暂时没有使用 @0.71), ← alliance_building(排序数量→关键值【唯一】，暂时没有使用 @0.71), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→关键值【唯一】，暂时没有使用 @0.71), ← hud_config_personal_config(排序→关键值【唯一】，暂时没有使用 @0.71), ...+22条入向

## 表: hud_config_personal_config [config]
- 文件: hud_config.xlsx | sheet: personal_config
- 行数: 9 | 列数: 9 | 主键: 关键值【唯一】
- 列: 关键值【唯一】(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, #按钮名字备注(str), 按钮名称key_new(str), 按钮icon
(没有正式资源，暂时使用buff文件夹下面的图标)(str), 类型(int), 排序(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 按钮解锁条件；未解锁按钮置灰，点击提示锁定原因(这个功能之后统筹到系统开启功能之中)(str), 点击触发客户端事件(str), 功能开关(关闭时不显示按钮)(str)
- 关联: → shop_shop_item(排序→商店id @0.95), → item(排序→道具分类排序 @0.86), → pve_pve_level(排序→关卡显示等级 @0.82), → shop_shop_item(关键值【唯一】→商店id @0.8), → activity(排序→活动参数 @0.79), → equip(排序→穿戴等级 @0.77), → pve_pve_level(排序→PVE关卡文件ID @0.76), → city_node_type_cityNodeTypeConf(排序→节点类型  参考CityNodeType @0.76), → activity(排序→类型 @0.75), → rank(排序→排行数据源类型 @0.74), ...+22条出向, ← activity(活动入口→排序 @0.77), ← baseLevel(时代→排序 @0.77), ← kvkSeason(报名赛季标识组→排序 @0.77), ← zombie_survivor(兵种等级→排序 @0.77), ← equip(装备位置→排序 @0.73), ← kvkSeason(默认投票结果→排序 @0.73), ← recharge(档位(真实付费)→排序 @0.73), ← alliance_building(建筑类型→排序 @0.73), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→排序 @0.73), ← hud_config(显示权重，越大显示越前面→排序 @0.73), ...+12条入向

## 表: instanceMonster [monster]
- 文件: instanceMonster.xlsx | sheet: instanceMonster
- 行数: 5 | 列数: 10 | 主键: 主键
- 列: 主键(int), 副本怪物名称(str), #策划备注(str), 类型(int), 击杀奖励(int), 奖励展示(str), 部队配置ID(int)→monsterTroop.主键, 半身像(str), AI行为树配置(str), 仇恨系统模式id(int)
- 关联: → monsterTroop(部队配置ID→主键 @0.76), ← sceneManager(场景LOD配置ID→主键 @0.73), ← sceneManager(主键（唯一标识）→主键 @0.69), ← world_building_worldBuilding(区分地图→主键 @0.68), ← lodConfig(主键（唯一标识）→主键 @0.63)

## 表: instanceReward [battle]
- 文件: instanceReward.xlsx | sheet: instanceReward
- 行数: 6 | 列数: 6 | 主键: 副本奖励主键
- 列: 副本奖励主键(int), #策划备注(str), PVP副本获胜方参与者奖励邮件(str), PVP副本战败方参与者奖励邮件(int), PVP副本战败方未参与者奖励邮件(int), PVP副本轮空奖励邮件(int)
- 关联: 无

## 表: instanceRule_instanceGameRule [other]
- 文件: instanceRule.xlsx | sheet: instanceGameRule
- 行数: 2 | 列数: 16 | 主键: 副本玩法规则ID
- 列: 副本玩法规则ID(int), #策划备注(str), 是否开启重置功能(int), 重置投票最大时间(int), 副本内可使用道具列表(str), 背包格子上限(int), 玩家断线重连时间(int), 副本内部统计数据类型集合(str), 副本可使用外部effect类型列表(str), 副本内UI可显示战斗buff列表(str), 对战积分功能(对战)(int), 是否开启副本内战报邮件(int), 玩家出生buff(str), 副本LOD层级最大与最小限制(str), 开启医院功能(int), 行军战斗是否消耗体力(int)
- 关联: 无

## 表: instanceRule_instanceStatistic [other]
- 文件: instanceRule.xlsx | sheet: instanceStatistic
- 行数: 28 | 列数: 8 | 主键: -
- 列: 统计数据项ID(int), #策划备注(str), 统计项名字(str), 统计项描述(str), 统计数据类型(int), 统计方式(int), 排序方式(int), 显示格式(str)
- 关联: 无

## 表: instanceRule_instanceTroopRule [other]
- 文件: instanceRule.xlsx | sheet: instanceTroopRule
- 行数: 7 | 列数: 8 | 主键: 副本玩家部队使用规则ID
- 列: 副本玩家部队使用规则ID(int)→item.道具分类排序, #策划备注(str), 部队来源类型(int), 部队创建方式(int), 可创建部队最大数量(int), 士兵来源(int), 英雄来源类型(int), 英雄来源(str)
- 关联: → shop_shop_item(副本玩家部队使用规则ID→商店id @0.74), → item(副本玩家部队使用规则ID→道具分类排序 @0.71), → skill_condition(副本玩家部队使用规则ID→值参数对比条件 @0.68), → kvkSeason_kvkScene(副本玩家部队使用规则ID→id @0.64), → weapon(副本玩家部队使用规则ID→主键 @0.61), → shop(副本玩家部队使用规则ID→ID @0.6), → pve_pve_level(副本玩家部队使用规则ID→关卡显示等级 @0.6), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→副本玩家部队使用规则ID @0.61)

## 表: instanceSkill [skill]
- 文件: instanceSkill.xlsx | sheet: instanceSkill
- 行数: 2 | 列数: 1 | 主键: -
- 列: #策划备注(str)
- 关联: 无

## 表: instanceTroop_instancePlayerHero [hero]
- 文件: instanceTroop.xlsx | sheet: instancePlayerHero
- 行数: 5 | 列数: 6 | 主键: 键值
- 列: 键值(int), #策划备注(str), 英雄ID(int)→hero.键值, 英雄等级(int)→rank_rank_reward.主键, 英雄星级(int), 英雄技能等级(str)
- 关联: → hero(英雄ID→键值 @0.95), → hero_hero_level(英雄等级→等级 @0.71), → monsterTroop(英雄等级→主键 @0.71), → rank_rank_reward(英雄等级→主键 @0.71)

## 表: instanceTroop_instancePlayerSoldier [other]
- 文件: instanceTroop.xlsx | sheet: instancePlayerSoldier
- 行数: 2 | 列数: 3 | 主键: 主键
- 列: 主键(int), #策划备注(str), 具体配置(str)
- 关联: 无

## 表: instanceTroop_instancePlayerTroop [other]
- 文件: instanceTroop.xlsx | sheet: instancePlayerTroop
- 行数: 2 | 列数: 7 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字(str), 部队显示等级(int), 主将(int), 副将(int), 具体配置(str)
- 关联: 无

## 表: instances [other]
- 文件: instances.xlsx | sheet: instances
- 行数: 30 | 列数: 14 | 主键: 主键
- 列: 主键(int)→pve_pve_level.PVE关卡文件ID, #策划备注(str), 副本名字(str), 副本描述(str), 副本显示等级(int), 推荐战力(int), json中显示怪物id(int), 玩家部队阵型类型(int), 是否Boss副本(int), 副本类型(int), 副本解锁条件(str), 副本首通奖励(int), 重复通关奖励(int), 副本关卡玩法JSON文件(str)
- 关联: → pve_pve_level(主键→PVE关卡文件ID @0.73), ← pve_pve_level(关卡显示等级→主键 @0.63)

## 表: instancesGroup [other]
- 文件: instancesGroup.xlsx | sheet: instancesGroup
- 行数: 6 | 列数: 15 | 主键: 副本奖励id
- 列: 主键(int), #策划备注(str), 副本tag(int), 关卡组id(str), 活动的开始时间(str), 最多可选活动时间个数(int), 副本难度排序(int), 副本组解锁条件(str), 匹配规则类型与ID(str), 副本部队使用规则ID(int), 副本玩法规则ID(int), 副本关联排行榜(str), gvg类多阶段副本流程规则(int), 副本奖励id(int)→reward.ID, 副本战损规则配置id(int)
- 关联: → reward(副本奖励id→ID @0.95)

## 表: instancesTag [other]
- 文件: instancesTag.xlsx | sheet: instancesTag
- 行数: 2 | 列数: 4 | 主键: 副本标签配置id
- 列: 副本标签配置id(int), #策划备注(str), 角色配置类型(int), 角色配置Id组(str)
- 关联: 无

## 表: instancesTag_gvgJob [other]
- 文件: instancesTag.xlsx | sheet: gvgJob
- 行数: 3 | 列数: 3 | 主键: 主键
- 列: 主键(int), 类型(int), 描述(str)
- 关联: 无

## 表: instancesTag_rpgRole [other]
- 文件: instancesTag.xlsx | sheet: rpgRole
- 行数: 3 | 列数: 13 | 主键: 主键
- 列: 主键(int), #策划备注(str), 玩家角色名字(str), 玩家角色icon(str), 玩家角色描述(str), 主动技能组1最大可选数量(int), 主动技能组2最大可选数量(int), 主动技能组3最大可选数量(int), 主动技能初始资源(int)→key_new.facial, 主动技能消耗资源上限(int)→key_new.facial, 主动技能资源恢复速率(str), 主动技能公共CD(int), 玩家角色专属Buff（配置技能来释放buff）(str)
- 关联: → zombie(主动技能初始资源→装备武器（weapon表） @0.8), → shop_shop_item(主动技能初始资源→商店id @0.78), → rank(主动技能初始资源→排行榜奖励 @0.76), → rank_rank_reward(主动技能初始资源→排名组 @0.76), → rank_rank_reward(主动技能消耗资源上限→排名组 @0.76), → city_node_type_cityNodeTypeConf(主动技能初始资源→节点类型  参考CityNodeType @0.75), → city_node_type_cityNodeTypeConf(主动技能消耗资源上限→节点类型  参考CityNodeType @0.75), → pve_pve_level(主动技能初始资源→关卡显示等级 @0.74), → pve_pve_level(主动技能消耗资源上限→关卡显示等级 @0.74), → activity(主动技能初始资源→活动参数 @0.73), ...+16条出向

## 表: item [item]
- 文件: item.xlsx | sheet: item
- 行数: 310 | 列数: 21 | 主键: 编号
- 列: 编号(int), 名字Key(str), #名字(str), 描述Key(str), #描述(str), 图标(str), 图标文本(str), 物品类型(int)→pve_pve_level.PVE关卡文件ID, 参数1(int), 参数2(str), 是否自动使用(int), 背包页分组(int), 道具分类排序(int)→rank_rank_reward.主键, 品质(int), 道具等级(int), 叠加规则(int), 是否能在背包里使用(int), 使用触发前端事件(str), #购买价格（钻石）(int), 使用等级下限(int), 道具消失时间（h）(int)
- 关联: → activity(物品类型→活动参数 @0.89), → pve_pve_level(物品类型→PVE关卡文件ID @0.81), → hero_hero_level(道具分类排序→等级 @0.73), → monsterTroop(道具分类排序→主键 @0.73), → monsterTroop(物品类型→主键 @0.73), → rank_rank_reward(道具分类排序→主键 @0.73), → army_trait(物品类型→主键 @0.7), → activity_activity_param(物品类型→ID @0.69), → monsterTroop(道具分类排序→显示等级 @0.69), → data_constant(道具分类排序→常量值 @0.65), ...+1条出向, ← hero(英雄专属雕像物品ID→编号 @0.95), ← material_merge_MaterialProduce(生产产物道具id→编号 @0.95), ← activity(活动入口→道具分类排序 @0.94), ← baseLevel(时代→道具分类排序 @0.94), ← kvkSeason(报名赛季标识组→道具分类排序 @0.94), ← alliance_shop_alliance_shopItem(排序→道具分类排序 @0.94), ← zombie_survivor(兵种等级→道具分类排序 @0.94), ← equip(装备位置→道具分类排序 @0.91), ← kvkSeason(默认投票结果→道具分类排序 @0.91), ← recharge(档位(真实付费)→道具分类排序 @0.91), ...+105条入向

## 表: item_recycle [item]
- 文件: item_recycle.xlsx | sheet: item_recycle
- 行数: 9 | 列数: 7 | 主键: ID
- 列: ID(int)→hero.英雄主动技能ID, #道具说明道具id详见后边[回收内容](str), 回收类型(int), 道具分类(int), 回收内容(int), 售出的货币类型(int), 售出价格(str)
- 关联: → hero(ID→英雄主动技能ID @0.73), ← activity(活动额外参数→ID @0.7), ← alliance_buff_attribute(类型→ID @0.6)

## 表: key_new [other]
- 文件: key_new.xlsx | sheet: key_new
- 行数: 4877 | 列数: 5 | 主键: facial
- 列: facial(str), 是否使用多语言字符串编译解析(str), 中文(str), 英文(str), 繁體(str)
- 关联: ← monsterTroop(名字，索引key_new表id→facial @0.81), ← army(士兵特点描述，
填写key_new表id→facial @0.8), ← army_monster(怪物特点描述，
填写key_new表id→facial @0.8), ← army_attribute(属性描述，索引key_new表id→facial @0.8), ← army_trait(属性描述，索引key_new表id→facial @0.8), ← area_area_config(地块关卡类型→facial @0.7), ← activity(活动入口→facial @0.7), ← activity(类型→facial @0.7), ← baseLevel(时代→facial @0.7), ← army(基础负载→facial @0.7), ...+62条入向

## 表: key_new_alliance_key_new [alliance]
- 文件: key_new_alliance.xlsx | sheet: key_new
- 行数: 89 | 列数: 2 | 主键: facial
- 列: facial(str), 中文(str)
- 关联: 无

## 表: key_new_instance_key_new [other]
- 文件: key_new_instance.xlsx | sheet: key_new
- 行数: 75 | 列数: 2 | 主键: facial
- 列: facial(str), 中文(str)
- 关联: 无

## 表: key_new_map_key_new [world]
- 文件: key_new_map.xlsx | sheet: key_new
- 行数: 13 | 列数: 3 | 主键: facial
- 列: facial(str), #说明描述(str), 中文(str)
- 关联: 无

## 表: key_new_task_key_new [quest]
- 文件: key_new_task.xlsx | sheet: key_new
- 行数: 29 | 列数: 2 | 主键: facial
- 列: facial(str), 中文(str)
- 关联: 无

## 表: key_new_ui_key_new [other]
- 文件: key_new_ui.xlsx | sheet: key_new
- 行数: 43 | 列数: 2 | 主键: facial
- 列: facial(str), 中文(str)
- 关联: ← hud_config(#按钮名字，key_new表key【注释】→中文 @0.86)

## 表: kingdomBuff [skill]
- 文件: kingdomBuff.xlsx | sheet: kingdomBuff
- 行数: 2 | 列数: 8 | 主键: id
- 列: id(int), 技能id(str), 持续时间（s）(int), 技能名称(str), 技能说明(str), 技能消耗（钻石）(int), 技能公用cd（s）(int), 头像(str)
- 关联: 无

## 表: kingdomGift [reward]
- 文件: kingdomGift.xlsx | sheet: kingdomGift
- 行数: 4 | 列数: 8 | 主键: 对应邮件id
- 列: 主键(int), #策划备注(str), 礼包名称(str), 礼包说明(str), 礼包数量(int), 对应邮件id(int)→mail.索引, 奖励内容预览(str), 礼包显示ICON(str)
- 关联: → mail(对应邮件id→索引 @0.95)

## 表: kingdomImmigration [other]
- 文件: kingdomImmigration.xlsx | sheet: kingdomImmigration
- 行数: 5 | 列数: 5 | 主键: 索引
- 列: 索引(int), 第几赛季(int), 赛季列表名称(str), 赛季名称(str), 赛季说明(str)
- 关联: 无

## 表: kingdomSkill [skill]
- 文件: kingdomSkill.xlsx | sheet: kingdomSkill
- 行数: 2 | 列数: 11 | 主键: 技能id
- 列: 技能id(int)→skill.键值, 技能名称(str), 技能说明(str), 技能图标(str), 技能消耗钻石数量(int), 技能cd（s）(int), 效果id列表(str), 效果持续时间（s）(int), 技能生效区域类型(int), 技能生效目标类型(int), 技能生效目标数量(int)
- 关联: → skill(技能id→键值 @0.95)

## 表: kingdom_official [other]
- 文件: kingdom_official.xlsx | sheet: kingdom_official
- 行数: 5 | 列数: 6 | 主键: id
- 列: id(int)→mail.模板, 官职名称(str), 头像(str), 官职buff(str), 分组(int), 权限(int)
- 关联: → mail(id→模板 @0.61)

## 表: kingspower [other]
- 文件: kingspower.xlsx | sheet: kingspower
- 行数: 5 | 列数: 7 | 主键: 组别
- 列: 组别(int), 国王官职(str), 王国buff(str), 分配礼包(str), 全服邮件(str), 王国技能(str), 移民调整(str)
- 关联: 无

## 表: kvkSeason [other]
- 文件: kvkSeason.xlsx | sheet: kvkSeason
- 行数: 8 | 列数: 7 | 主键: id
- 列: id(int)→item.道具分类排序, 报名赛季标识组(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 赛季名称(str), 是否可轮空配置(int), 默认投票结果(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 报名投票单位类型(int), 报名剧本组(str)
- 关联: → item(报名赛季标识组→道具分类排序 @0.94), → shop_shop_item(报名赛季标识组→商店id @0.92), → item(默认投票结果→道具分类排序 @0.91), → shop_shop_item(默认投票结果→商店id @0.89), → pve_pve_level(报名赛季标识组→关卡显示等级 @0.81), → pve_pve_level(默认投票结果→关卡显示等级 @0.8), → skill_condition(报名赛季标识组→值参数对比条件 @0.79), → activity(报名赛季标识组→活动参数 @0.78), → activity(默认投票结果→活动参数 @0.77), → draw_card_discount(报名赛季标识组→折扣组 @0.77), ...+59条出向, ← equip(装备位置→报名赛季标识组 @0.76), ← recharge(档位(真实付费)→报名赛季标识组 @0.76), ← alliance_building(建筑类型→报名赛季标识组 @0.76), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→报名赛季标识组 @0.76), ← hud_config(显示权重，越大显示越前面→报名赛季标识组 @0.76), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→默认投票结果 @0.76), ← task(任务类型→报名赛季标识组 @0.76), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→报名赛季标识组 @0.73), ← zombie_bt_ai(范围内不会跟随主将距离→默认投票结果 @0.71), ← zombie_bt_ai(范围内不会跟随主将距离→报名赛季标识组 @0.69), ...+5条入向

## 表: kvkSeason_kvkScene [other]
- 文件: kvkSeason.xlsx | sheet: kvkScene
- 行数: 11 | 列数: 6 | 主键: id
- 列: id(int)→zombie_survivor.战斗力，显示值, 地图(int), 里程碑(str), 剧本名称(str), 剧本介绍(str), 成就组(str)
- 关联: → hud_config_bookmark_config(id→关键值【唯一】，暂时没有使用 @0.71), → zombie_survivor(id→战斗力，显示值 @0.66), → science(id→显示层级【只需配置第1级】 @0.63), ← equip(穿戴等级→id @0.77), ← draw_card_discount(折扣组→id @0.75), ← worldScene_monsterFresh(基础刷新等级→id @0.75), ← alliance_building(排序数量→id @0.75), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→id @0.75), ← activity(活动入口→id @0.72), ← baseLevel(时代→id @0.72), ← kvkSeason(报名赛季标识组→id @0.72), ← zombie_survivor(兵种等级→id @0.72), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→id @0.71), ...+17条入向

## 表: lodConfig [config]
- 文件: lodConfig.xlsx | sheet: lodConfig
- 行数: 3 | 列数: 7 | 主键: 主键（唯一标识）
- 列: 主键（唯一标识）(int)→instanceMonster.主键, #策划备注(str), LOD应用层级范围(str), 高度(str), 相机FOV(str), 相机近处裁剪(str), 相机远处裁剪(str)
- 关联: → default_sth_defaultSth(主键（唯一标识）→id @0.73), → sceneManager(主键（唯一标识）→主键（唯一标识） @0.68), → city_area_areaUnlock(主键（唯一标识）→主键 @0.65), → point_transform_pointTransform(主键（唯一标识）→积分类型 @0.65), → client_rank_alliance_rank(主键（唯一标识）→排行榜类型 @0.65), → pve_skill_hit_effect(主键（唯一标识）→键值 @0.63), → instanceMonster(主键（唯一标识）→主键 @0.63), → resource_ResRefresh(主键（唯一标识）→资源类型 @0.61), → resource(主键（唯一标识）→资源转换类型(个人联盟之间转换关系) @0.61), → activity_activity_param(主键（唯一标识）→排行榜奖励发放 @0.6), ...+1条出向, ← sceneManager(场景LOD配置ID→主键（唯一标识） @0.65)

## 表: lord_exp_lordExp [other]
- 文件: lord_exp.xlsx | sheet: lordExp
- 行数: 40 | 列数: 2 | 主键: id
- 列: id(int)→pve_pve_level.PVE关卡文件ID, 经验值(int)
- 关联: → pve_pve_level(id→PVE关卡文件ID @0.79), ← alliance_gift_box(所需经验→经验值 @0.75), ← alliance_gift_box(所需钥匙→经验值 @0.75), ← alliance_building(资源田容量→经验值 @0.73), ← quality_quality_define(屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正→经验值 @0.73), ← resource_Resinfo(生成速度→经验值 @0.72), ← resource_Resinfo(兑换比例→经验值 @0.72), ← weapon(攻击速度（普攻技能CD，复写pve_skill字段）→经验值 @0.72), ← activity(活动参数→id @0.61)

## 表: mail [social]
- 文件: mail.xlsx | sheet: mail
- 行数: 61 | 列数: 18 | 主键: 索引
- 列: 索引(int), 类型(int), 模板(int)→worldMonster.部队配置ID, 标题(str), 副标题(str), #策划备注1(str), 内容(str), #策划备注2(str), 奖励(int)→reward.ID, 动态模板标题组件内容配置(str), 动态模板纯文本组件内容配置(str), 动态模板坐标组件内容配置(str), 动态模板用户列表组件内容配置(str), 动态模板奖励列表组件内容配置(str), 动态模板排行榜组件内容配置(str), 动态模板建筑组件内容配置(str), 动态模板按钮组件内容配置(str), 邮件sdk条件(str)
- 关联: → reward(奖励→ID @0.71), → rank_rank_reward(模板→主键 @0.69), → worldMonster(模板→部队配置ID @0.65), → monsterTroop(模板→主键 @0.63), ← activity_activity_param(奖励邮件ID→索引 @0.95), ← kingdomGift(对应邮件id→索引 @0.95), ← world_building_worldBuilding(建筑类型→模板 @0.81), ← alliance_buff_attribute(类型→奖励 @0.76), ← mail_mailTemplate(动态模板ID→模板 @0.67), ← alliance_gift(id→模板 @0.63), ← pve_pve_chapter(章节组ID→模板 @0.63), ← kingdom_official(id→模板 @0.61)

## 表: mail_bufftemplate [skill]
- 文件: mail.xlsx | sheet: bufftemplate
- 行数: 11 | 列数: 8 | 主键: 序号
- 列: 序号(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, #策划备注(str), 部队增益名字文本(str), 部队增益在buff表的逻辑ID(int)→buff_attribute.类型, 增益目标兵种类型枚举(float), 增益效果数值类型（显示用）(int), 显示优先级(int), 特定目标类型显示(str)
- 关联: → buff(部队增益在buff表的逻辑ID→效果逻辑ID @0.91), → buff_attribute(部队增益在buff表的逻辑ID→类型 @0.82), → worldMonster(部队增益在buff表的逻辑ID→序号 @0.71), → pve_pve_level(序号→关卡显示等级 @0.65), → activity(序号→活动参数 @0.61), → buff(部队增益在buff表的逻辑ID→键值 @0.6), → city_node_type_cityNodeTypeConf(序号→节点类型  参考CityNodeType @0.6), ← army(兵种类型→增益目标兵种类型枚举 @0.93), ← army_monster(兵种类型→增益目标兵种类型枚举 @0.93)

## 表: mail_dynamicbuff [skill]
- 文件: mail.xlsx | sheet: dynamicbuff
- 行数: 1 | 列数: 3 | 主键: 战斗日志左侧不需要显示的buff逻辑ID
- 列: 序号(int), #策划备注(str), 战斗日志左侧不需要显示的buff逻辑ID(str)
- 关联: 无

## 表: mail_mailTemplate [social]
- 文件: mail.xlsx | sheet: mailTemplate
- 行数: 8 | 列数: 3 | 主键: 动态模板ID
- 列: 动态模板ID(int)→mail.模板, #策划备注(str), 邮件动态模板样式配置(str)
- 关联: → mail(动态模板ID→模板 @0.67)

## 表: map_battle_battle_const [battle]
- 文件: map_battle.xlsx | sheet: battle_const
- 行数: 7 | 列数: 3 | 主键: 键值
- 列: 键值(str), #策划备注(str), 参数(str)
- 关联: 无

## 表: map_battle_battle_formation [battle]
- 文件: map_battle.xlsx | sheet: battle_formation
- 行数: 4 | 列数: 26 | 主键: 阵型模板id
- 列: 阵型模板id(int), #描述(str), 混兵排阵优先级(int)→building.缩放时隐藏次序，越大越不会被隐藏, 每行最大模型数量(int), 横向间隔（米）(float), 纵向间隔（米）(float), 模型换算区间(str), 模型换算区间.1(str), 模型换算区间.2(str), 模型换算区间.3(str), 模型换算区间.4(str), 模型换算区间.5(str), 模型换算区间.6(str), 模型换算区间.7(str), 模型换算区间.8(str), 模型换算区间.9(str), 模型换算区间.10(str), 模型换算区间.11(str), 模型换算区间.12(str), 模型换算区间.13(str), 模型换算区间.14(str), 模型换算区间.15(str), 模型换算区间.16(str), 模型换算区间.17(str), 模型换算区间.18(str), ...+1列
- 关联: → shop_shop_item(混兵排阵优先级→周期内限购数量 @0.83), → pve_skill(混兵排阵优先级→检索距离，即技能释放距离【float，米】 @0.8), → building(混兵排阵优先级→幸存者等级上限 @0.75), → science(混兵排阵优先级→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.74), → building(混兵排阵优先级→缩放时隐藏次序，越大越不会被隐藏 @0.74), → baseLevel(混兵排阵优先级→大本等级 @0.73), → monsterTroop(混兵排阵优先级→显示等级 @0.73), → worldMonster(混兵排阵优先级→部队配置ID @0.72), → pve_pve_level(混兵排阵优先级→PVE关卡文件ID @0.72), → data_constant(混兵排阵优先级→常量值 @0.71), ...+3条出向

## 表: map_item_popup [item]
- 文件: map_item_popup.xlsx | sheet: map_item_popup
- 行数: 5 | 列数: 8 | 主键: 关键值【唯一】
- 列: 关键值【唯一】(str), #描述(str), 子面板(str), 按钮状态   标记|分享(str), 面板类型icon(str), 面板类型文字(str), 跟随目标点(str), 面板类型底板(str)
- 关联: 无

## 表: matchingEntityConfig_matchingAllianceConfig [alliance]
- 文件: matchingEntityConfig.xlsx | sheet: matchingAllianceConfig
- 行数: 1 | 列数: 3 | 主键: 主键
- 列: 主键(int), #策划备注(str), 报名权限联盟位阶(int)
- 关联: 无

## 表: matchingEntityConfig_matchingTeamConfig [config]
- 文件: matchingEntityConfig.xlsx | sheet: matchingTeamConfig
- 行数: 1 | 列数: 6 | 主键: 主键
- 列: 主键(int), #策划备注(str), 是否可邀请队员(int), 邀请方式(int), 是否启用队长角色(int), 队长权限设置(int)
- 关联: 无

## 表: matchingEntityRule_matchAssess [other]
- 文件: matchingEntityRule.xlsx | sheet: matchAssess
- 行数: 2 | 列数: 4 | 主键: 对应的副本组id
- 列: 主键(int), 对应的副本组id(str), 判断权重类(int), 百分比(int)
- 关联: 无

## 表: matchingEntityRule_matchingAllianceRule [alliance]
- 文件: matchingEntityRule.xlsx | sheet: matchingAllianceRule
- 行数: 1 | 列数: 13 | 主键: 联盟匹配规则ID
- 列: 联盟匹配规则ID(int)→alliance_flag.索引, #策划备注(str), 联盟可报名最大人数(int), 联盟报名最少人数(int), 副本可容纳最多联盟数量(int), 匹配服务器的范围(int), 进入玩家的匹配规则matchAssess表的group(int), 匹配关键数据类型(int), 关键数据匹配范围(上下浮动)(str), 关键数据浮动变更时间(str), 玩家匹配区间调整(str), 玩家匹配区间调整时间(str), 轮空规则(int)
- 关联: → alliance_flag(联盟匹配规则ID→索引 @0.95)

## 表: matchingEntityRule_matchingTeamRule [other]
- 文件: matchingEntityRule.xlsx | sheet: matchingTeamRule
- 行数: 5 | 列数: 15 | 主键: 队伍匹配规则ID
- 列: 队伍匹配规则ID(int), #策划备注(str), 队伍最大人数(int), 可进入副本最小人数(int), 匹配时间满足最小人数的等待进入时间(int), 是否需要队伍确认就绪(int), 队伍确认就绪倒计时(int), 超时未就绪成员是否自动移除(int), 进入玩家的匹配规则matchAssess表的group(int), 匹配关键数据类型(int), 关键数据匹配范围(上下浮动)(str), 关键数据浮动变更时间(str), 匹配服务器的范围(int), 玩家匹配区间调整(str), 玩家匹配区间调整时间(str)
- 关联: 无

## 表: material_merge_MaterialMerge [item]
- 文件: material_merge.xlsx | sheet: MaterialMerge
- 行数: 30 | 列数: 4 | 主键: 编号
- 列: 编号(int), 分解后获得材料ID和数量(str), 分解需要消耗的资源(str), 合成目标的材料ID和当前消耗的数量(str)
- 关联: 无

## 表: material_merge_MaterialProduce [item]
- 文件: material_merge.xlsx | sheet: MaterialProduce
- 行数: 4 | 列数: 3 | 主键: 生产产物道具id
- 列: 生产产物道具id(int)→item.编号, 每次生产获得数量(int)→building.幸存者等级上限, 每次生产需要时间(int)→building.建筑高度（长度）
- 关联: → item(生产产物道具id→编号 @0.95), → zombie(每次生产获得数量→战斗力，显示值 @0.9), → zombie(每次生产需要时间→战斗力，显示值 @0.9), → client_show_client_bullet(每次生产获得数量→飞行速度
默认15m/s @0.85), → client_show_client_bullet(每次生产需要时间→飞行速度
默认15m/s @0.85), → pve_skill(每次生产获得数量→检索距离，即技能释放距离【float，米】 @0.8), → pve_skill(每次生产需要时间→检索距离，即技能释放距离【float，米】 @0.8), → building(每次生产获得数量→建筑高度（长度） @0.8), → building(每次生产需要时间→建筑高度（长度） @0.8), → worldScene_monsterLevel(每次生产获得数量→等级上限 @0.76), ...+30条出向

## 表: milestone [other]
- 文件: milestone.xlsx | sheet: milestone
- 行数: 19 | 列数: 20 | 主键: 编号
- 列: 编号(int), #策划备注(str), 名称(str), 背景图(str), 最小持续时间（小时）(int), 最大持续时间（小时）(int), 奖励领取时间限制(小时)(int), 任务id(int)→task.任务id, 奖励目标主体(str), 奖励未完成描述(str), 奖励(int), 功能解锁(int), 功能解锁图标(str), 功能解锁图标文字(str), 功能解锁tip标题(str), 功能解锁tip描述(str), 排行榜(str), 里程碑各阶段描述文本(str), action按钮名(str), 执行跳转(str)
- 关联: → task(任务id→任务id @0.95), ← weapon(武器技能（pve_skill的技能组ID，复写）→编号 @0.61), ← sceneManager(场景LOD配置ID→编号 @0.6)

## 表: model [other]
- 文件: model.xlsx | sheet: model
- 行数: 231 | 列数: 12 | 主键: 键值
- 列: 键值(str), #注释(str), 模型资源【Assets/Game_Prefab/prefab/model】(str), 模型缩放倍数(float), 模型城市内的偏移值(str), avatar_config.xlsx的ID，默认为1(int), 模型移动速度【run动作资源决定，跟美术约定5米/S【指不缩放的情况下】(float), 可选移动动画播放(str), 可选站立动动画播放(str), 资源优先级【性能优化用到】
<0，表示极可能快的加载，尽量少配置(int), 溶解颜色字段(str), 改模型是否是ecs(int)
- 关联: ← model_model_pve(#注释→#注释 @0.78), ← building(破损模型→键值 @0.74), ← building(破损模型→模型资源【Assets/Game_Prefab/prefab/model】 @0.73), ← army(世界场景AI部队显示模型→键值 @0.72), ← army(世界场景玩家部队显示模型→键值 @0.72), ← army_monster(显示模型→键值 @0.72), ← army_monster(城内显示模型→键值 @0.72), ← army(城内显示模型→键值 @0.71), ← zombie_trap_item(显示模型→键值 @0.61)

## 表: model_entity_attach [other]
- 文件: model.xlsx | sheet: entity_attach
- 行数: 1 | 列数: 9 | 主键: 挂点键值
- 列: 挂点键值(int), #挂点使用者模型参考(str), 挂载模型参考(str), #注释(str), 挂点位置(int), 位置(str), 角度(str), 缩放(int), 挂载后移动动画修改(str)
- 关联: 无

## 表: model_map_formation [world]
- 文件: model.xlsx | sheet: map_formation
- 行数: 32 | 列数: 3 | 主键: 键值
- 列: 键值(int), #策划备注(str), 参数(str)
- 关联: 无

## 表: model_model_pve [other]
- 文件: model.xlsx | sheet: model_pve
- 行数: 72 | 列数: 8 | 主键: 键值
- 列: 键值(str), #注释(str)→model.#注释, 模型碰撞体大小半径，单位：米（PVE）(float), 模型碰撞体高度，单位：米（PVE）(int), 可选休眠动画播放（PVE）(str), 可选起身动画播放（PVE）(str), 起身状态时间（PVE）(int), 死亡状态时间（尸体保留）（PVE）(int)
- 关联: → model(#注释→#注释 @0.78)

## 表: monsterTroop [monster]
- 文件: monsterTroop.xlsx | sheet: monsterTroop
- 行数: 117 | 列数: 10 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字，索引key_new表id(str)→key_new.facial, 显示等级(int)→pve_pve_level.主键, 主将(int), 敌人具体配置(str), 敌人部队的AI方案(str), 敌人部队阵型显示类型(int), 敌人部队体型半径(float), 战斗配置(int)
- 关联: → key_new(名字，索引key_new表id→facial @0.81), → worldMonster(显示等级→部队配置ID @0.68), → hero_hero_level(显示等级→等级 @0.64), → pve_pve_level(显示等级→主键 @0.6), ← worldMonster(部队配置ID→主键 @0.93), ← rank_rank_reward(主键→主键 @0.86), ← hero_hero_level(等级→主键 @0.81), ← baseLevel(大本等级→主键 @0.8), ← city_node_type_cityNodeTypeConf(节点类型  参考CityNodeType→主键 @0.8), ← activity(活动参数→显示等级 @0.78), ← effect(组→主键 @0.78), ← unlock_functionSwitch(条件解锁id→主键 @0.78), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→主键 @0.78), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→主键 @0.77), ...+105条入向

## 表: monsterTroop_monsterHero [hero]
- 文件: monsterTroop.xlsx | sheet: monsterHero
- 行数: 3 | 列数: 5 | 主键: 英雄ID
- 列: 键值(int), #策划备注(str), 英雄ID(int)→resource.资源转换类型(个人联盟之间转换关系), 英雄等级(int)→item.参数1, 英雄星级(int)
- 关联: → hero(英雄ID→键值 @0.95), → msg_config(英雄等级→最大同时显示数量 @0.88), → shop_shop_item(英雄等级→周期内限购数量 @0.8), → alliance_constant(英雄等级→值 @0.76), → monsterTroop(英雄等级→显示等级 @0.72), → data_constant(英雄等级→常量值 @0.71), → hero_hero_level(英雄等级→等级 @0.71), → monsterTroop(英雄等级→主键 @0.71), → rank_rank_reward(英雄等级→主键 @0.71), → item(英雄等级→参数1 @0.71), ...+2条出向

## 表: msg_config [config]
- 文件: msg_config.xlsx | sheet: msg_config
- 行数: 12 | 列数: 9 | 主键: 主键
- 列: 主键(int), #desc(str), 频道开关(int), 持续时间(float), 显示间隔(float), 最大排队数(int)→rank_rank_reward.主键, 最大同时显示数量(int)→item.参数1, 实体绑定模式(int), 绑定实体3D坐标偏移(str)
- 关联: → monsterTroop(最大同时显示数量→显示等级 @0.73), → data_constant(最大排队数→常量值 @0.72), → data_constant(最大同时显示数量→常量值 @0.71), → hero_hero_level(最大同时显示数量→等级 @0.71), → monsterTroop(最大同时显示数量→主键 @0.71), → rank_rank_reward(最大同时显示数量→主键 @0.71), → item(最大同时显示数量→参数1 @0.71), → hero_hero_level(最大排队数→等级 @0.62), → monsterTroop(最大排队数→主键 @0.62), → rank_rank_reward(最大排队数→主键 @0.62), ← monsterTroop_monsterHero(英雄等级→最大同时显示数量 @0.88), ← point_transform_pointTransform(参数类型→主键 @0.68)

## 表: normal_rank [other]
- 文件: normal_rank.xlsx | sheet: normal_rank
- 行数: 9 | 列数: 7 | 主键: 自增id
- 列: 自增id(str)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 排行榜名字(str), 图标(str), 提示标题(str), 提示内容(str), 排行项文字(str), 关联排行榜(str)
- 关联: → shop_shop_item(自增id→商店id @0.8), → item(自增id→道具分类排序 @0.66), → pve_pve_level(自增id→关卡显示等级 @0.62), → pve_pve_level(自增id→PVE关卡文件ID @0.61), → city_node_type_cityNodeTypeConf(自增id→节点类型  参考CityNodeType @0.61)

## 表: panel_config [config]
- 文件: panel_config.xlsx | sheet: panel_config
- 行数: 78 | 列数: 15 | 主键: 界面名称【与资源名一致】
- 列: 界面名称【与资源名一致】(str), #策划备注1(str), 层级(int)→key_new.facial, 互斥挡住同层级UI；挡住的其他UI会被挪开(str), 触发UI资源释放(str), 是否常驻(str), 是否调用转圈loading(str), 是否考虑刘海屏适配，弹出非全屏界面请选FALSE，绝大部分不要刘海适配(str), 关闭多久执行删除【秒】(int)→item.物品类型, 打开音效名(str), 关闭音效名(str), 是否没有LuaBehaviour(str), ui的sortingLayer是否自定义，不受PanelLayer影响(str), UI打开动画效果
1:由小到大(int), 是否关闭主界面(str)
- 关联: → recharge(关闭多久执行删除【秒】→关联活动Id @0.93), → skill_condition(层级→值参数对比条件 @0.82), → pve_pve_level(层级→关卡显示等级 @0.77), → vip(关闭多久执行删除【秒】→等级 @0.75), → pve_pve_level(关闭多久执行删除【秒】→关卡显示等级 @0.74), → item(关闭多久执行删除【秒】→物品类型 @0.74), → data_constant(层级→常量值 @0.71), → data_constant(关闭多久执行删除【秒】→常量值 @0.71), → key_new(层级→facial @0.7), → key_new(关闭多久执行删除【秒】→facial @0.7), ...+2条出向

## 表: player_info_head [other]
- 文件: player_info.xlsx | sheet: head
- 行数: 4 | 列数: 4 | 主键: 主键
- 列: 主键(int), #策划备注(str), 描述，获取途径(str), 图标，
路径：Assets/Arts/ui/player_head(str)
- 关联: 无

## 表: player_info_head_bg [other]
- 文件: player_info.xlsx | sheet: head_bg
- 行数: 6 | 列数: 6 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字(str), 描述，获取途径(str), 图标，
路径：Assets/Arts/ui/player_head(str), 品质(int)
- 关联: 无

## 表: point_transform_pointTransform [other]
- 文件: point_transform.xlsx | sheet: pointTransform
- 行数: 69 | 列数: 7 | 主键: ID
- 列: ID(int), 分组(int)→worldMonster.部队配置ID, 积分类型(int)→key_new.facial, 参数类型(int)→msg_config.主键, 等级区间最小值(int)→item.参数1, 等级区间最大值(int)→building.参数1, 积分(int)
- 关联: → pve_pve_level(等级区间最大值→PVE关卡文件ID @0.82), → pve_pve_level(等级区间最小值→PVE关卡文件ID @0.82), → activity(等级区间最小值→活动参数 @0.79), → activity(等级区间最大值→活动参数 @0.76), → monsterTroop(等级区间最大值→主键 @0.75), → monsterTroop(等级区间最小值→主键 @0.75), → item(等级区间最小值→参数1 @0.75), → worldMonster(分组→部队配置ID @0.74), → rank_rank_reward(分组→主键 @0.73), → monsterTroop(分组→主键 @0.72), ...+13条出向, ← default_sth_defaultSth(id→积分类型 @0.95), ← sceneManager(场景LOD配置ID→积分类型 @0.85), ← world_building_worldBuilding(区分地图→积分类型 @0.85), ← army(兵种类型→参数类型 @0.83), ← army_monster(兵种类型→参数类型 @0.83), ← activity(显示优先级→积分 @0.75), ← alliance_building(资源田容量→积分 @0.75), ← material_merge_MaterialProduce(每次生产获得数量→积分 @0.75), ← material_merge_MaterialProduce(每次生产需要时间→积分 @0.75), ← pve_skill_hit_effect(键值→积分类型 @0.75), ...+11条入向

## 表: powerconsume_powerConsume [other]
- 文件: powerconsume.xlsx | sheet: powerConsume
- 行数: 3 | 列数: 3 | 主键: 键值
- 列: 键值(int), #攻击目标(str), 消耗体力(int)
- 关联: 无

## 表: pre_load [other]
- 文件: pre_load.xlsx | sheet: pre_load
- 行数: 1 | 列数: 4 | 主键: 类型
PanelPrefab：界面
ModelPrefab：模型
Particle：特效
TimelineP：timeline预设体
详见客户端枚举：ResourceType
- 列: 类型
PanelPrefab：界面
ModelPrefab：模型
Particle：特效
TimelineP：timeline预设体
详见客户端枚举：ResourceType(str), 资源名字，务必不要重复预加载(str), 是否常驻(str), 是否需要实例化，model类起效(str)
- 关联: 无

## 表: pve_character [hero]
- 文件: pve_character.xlsx | sheet: pve_character
- 行数: 6 | 列数: 16 | 主键: 基础力量（物攻）
- 列: 主键(str), #策划备注(str), 名字(str), 图标(str), 显示模型(str), 等级(int), 基础生命(int)→key_new.facial, 基础魔力值(int), 基础移动速度(int), 基础旋转速度(int), 基础力量（物攻）(int), 基础体质（物抗）(int), 基础智力（魔攻）(int)→data_constant.常量值, 基础体质（魔抗）(int), 技能列表(str), AI行为树(str)
- 关联: → pve_pve_level(基础生命→PVE关卡文件ID @0.82), → city_node_type_cityNodeTypeConf(基础生命→节点类型  参考CityNodeType @0.77), → pve_pve_level(基础生命→关卡显示等级 @0.75), → activity(基础生命→活动参数 @0.74), → data_constant(基础智力（魔攻）→常量值 @0.72), → monsterTroop(基础生命→主键 @0.71), → item(基础生命→参数1 @0.71), → building(基础生命→参数1 @0.71), → key_new(基础生命→facial @0.7), → building(基础生命→效果类型 @0.6)

## 表: pve_config_pve_info_config [config]
- 文件: pve_config.xlsx | sheet: pve_info_config
- 行数: 1 | 列数: 5 | 主键: 主键
- 列: 主键(int), 相机高度(int), 相机初始化角度(str), 相机初始化FOV(int), 游戏FOV范围(str)
- 关联: 无

## 表: pve_config_zombie_config [config]
- 文件: pve_config.xlsx | sheet: zombie_config
- 行数: 5 | 列数: 3 | 主键: 键值
- 列: 键值(int), #策划备注(str), 参数(str)
- 关联: 无

## 表: pve_pve_chapter [quest]
- 文件: pve.xlsx | sheet: pve_chapter
- 行数: 6 | 列数: 14 | 主键: 章节组ID
- 列: 主键(int), #策划备注(str), 主标题文本key(str), 副标题文本key(str), 标题背景图资源(str), 关卡地图资源(str), 功能类型过滤(int), 章节难度(int), 章节组ID(int)→mail.模板, 普通关卡ids(str), 未解锁是否显示在章节列表(int), 章节解锁条件(str), 章节解锁条件描述(str), 关卡连线坐标数组(str)
- 关联: → mail(章节组ID→模板 @0.63)

## 表: pve_pve_diff [other]
- 文件: pve.xlsx | sheet: pve_diff
- 行数: 4 | 列数: 7 | 主键: 主标题文本key
- 列: 键值(难度)(int), #策划备注(str), 主标题文本key(str), 文本颜色(str), 按钮图标(str), boss图标(str), 锁定图标(str)
- 关联: 无

## 表: pve_pve_level [other]
- 文件: pve.xlsx | sheet: pve_level
- 行数: 59 | 列数: 20 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字，直接索引字典表(str), 描述，直接索引字典表(str), 关卡显示等级(int)→item.参数1, 敌人配置显示-UI用形象显示(str), 是否Boss关卡(int), 关卡解锁条件(str), 推荐战力(int), 资源消耗(int), 首通奖励(int)→reward.ID, 重复通关奖励(int)→reward.ID, PVE关卡文件ID(int), 关卡玩法类型(int), 通关主要条件（可选）(str), 额外条件(str), 星级关联条件(str), 昼夜(int), 临时点击玩法-点击次数(int), 临时点击玩法-暴击概率（千分比）(str)
- 关联: → building(关卡显示等级→等级 @0.87), → activity(关卡显示等级→活动参数 @0.83), → army_trait(关卡显示等级→主键 @0.83), → effect(关卡显示等级→组 @0.79), → monsterTroop(关卡显示等级→显示等级 @0.76), → worldMonster(关卡显示等级→部队配置ID @0.76), → hero_hero_level(关卡显示等级→等级 @0.73), → rank_rank_reward(关卡显示等级→主键 @0.73), → monsterTroop(关卡显示等级→主键 @0.72), → item(关卡显示等级→参数1 @0.72), ...+8条出向, ← buff_attribute_buff_client(排序，小的在前→关卡显示等级 @0.96), ← recharge(优先级→关卡显示等级 @0.96), ← vip(等级→关卡显示等级 @0.96), ← baseLevel(大本等级→PVE关卡文件ID @0.94), ← army_trait(主键→PVE关卡文件ID @0.93), ← army(优先级→关卡显示等级 @0.9), ← science(显示层级【只需配置第1级】→关卡显示等级 @0.9), ← activity(活动参数→PVE关卡文件ID @0.89), ← effect(组→PVE关卡文件ID @0.89), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→PVE关卡文件ID @0.89), ...+145条入向

## 表: pve_skill [skill]
- 文件: pve_skill.xlsx | sheet: pve_skill
- 行数: 33 | 列数: 17 | 主键: 键值
- 列: 键值(str), #备注说明(str), 技能类型
0：普攻
1：主动（可沉默）
2：被动
3：觉醒技能(int), 如果是被动技能，后面字段全部无效，映射pve_passive_effect中的内容(int), cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放）(int), 技能消耗怒气
（主动技能）
【int】(int), 技能总时长，动作总时长（优化timeline逻辑表现分离后可自动计算）
【int，毫秒】(int), 目标类型，【注：不是真正执行action的目标，只是后面筛选目标的输入依据】
0：自己
1：敌对【非死亡】
2：友方【非死亡】
3：敌对【死亡】
4：友方【死亡】(int), 【main_target_type == 0的时候】非战斗状态是否对自己自动释放技能(str), 检索距离，即技能释放距离【float，米】(float), 移动中是否可以释放技能（考虑到动作融合大部分技能都不可以移动释放，默认值false）(str), 技能开始时是否朝向跟随目标（立即旋转）(str), 技能过程中是否朝向跟随目标（有旋转速度）(str), timeline技能（接管后面的所有参数）
资源：Game_Prefab/prefab/timeline/raw/skill_XXX(str), delay,target_action|delay,target_action|…。从动作里获取
delay：【int，毫秒】
target_action：目标行为列表，对应skill_target_action种的配置
第三个参数为播放速度，不配则为1倍
支持数组配置(str), 过程动作
delay1,animName1|delay2,animName2|…
delay：【int，毫秒】
animName：【动作名】(str), 过程特效
delay1,effectID1|…
delay：【int，毫秒】
effect：对应client_show.xlsx中【client_effect中的配置(str)
- 关联: ← weapon(攻击速度（普攻技能CD，复写pve_skill字段）→cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放） @0.86), ← weapon(武器战斗力，显示值→检索距离，即技能释放距离【float，米】 @0.8), ← material_merge_MaterialProduce(每次生产获得数量→检索距离，即技能释放距离【float，米】 @0.8), ← material_merge_MaterialProduce(每次生产需要时间→检索距离，即技能释放距离【float，米】 @0.8), ← alliance_building(采集速度→检索距离，即技能释放距离【float，米】 @0.8), ← map_battle_battle_formation(混兵排阵优先级→检索距离，即技能释放距离【float，米】 @0.8), ← resource_Resinfo(兑换比例→技能总时长，动作总时长（优化timeline逻辑表现分离后可自动计算）
【int，毫秒】 @0.8), ← client_show_client_bullet(飞行速度
默认15m/s→检索距离，即技能释放距离【float，米】 @0.79), ← soldier_consumption(重伤比例→检索距离，即技能释放距离【float，米】 @0.78), ← resource_Resinfo(生成速度→cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放） @0.76), ...+3条入向

## 表: pve_skill_hit_effect [skill]
- 文件: pve_skill.xlsx | sheet: hit_effect
- 行数: 5 | 列数: 3 | 主键: 键值
- 列: 键值(int)→pve_pve_level.PVE关卡文件ID, #备注说明，可以播放特效、音效以及特效(str), 命中特效，对应client_show.xlsx中【client_effect中的配置(int)
- 关联: → point_transform_pointTransform(键值→积分类型 @0.75), → client_rank_alliance_rank(键值→排行榜类型 @0.75), → pve_pve_level(键值→PVE关卡文件ID @0.68), → activity_activity_param(键值→排行榜奖励发放 @0.67), ← sceneManager(场景LOD配置ID→键值 @0.73), ← sceneManager(主键（唯一标识）→键值 @0.69), ← world_building_worldBuilding(区分地图→键值 @0.68), ← lodConfig(主键（唯一标识）→键值 @0.63)

## 表: pve_skill_pve_passive_effect [skill]
- 文件: pve_skill.xlsx | sheet: pve_passive_effect
- 行数: 2 | 列数: 2 | 主键: 键值
- 列: 键值(int), #备注说明(str)
- 关联: 无

## 表: pve_skill_skill_action [skill]
- 文件: pve_skill.xlsx | sheet: skill_action
- 行数: 26 | 列数: 8 | 主键: 键值
- 列: 键值(int), #备注说明(str), 类型
type的具体逻辑见#说明分页(int)→key_new.facial, 参数1(str), 参数2(str), 参数3(str), 是否需要成功检测，true表示如果执行失败，后面的action将直接跳过，如用于伤害+眩晕(str), action作用时表现，对应sheet<hit_effect>的内容(str)
- 关联: → shop_shop_item(类型
type的具体逻辑见#说明分页→商店id @0.91), → pve_pve_level(类型
type的具体逻辑见#说明分页→PVE关卡文件ID @0.89), → item(类型
type的具体逻辑见#说明分页→道具分类排序 @0.88), → skill_condition(类型
type的具体逻辑见#说明分页→值参数对比条件 @0.85), → pve_pve_level(类型
type的具体逻辑见#说明分页→关卡显示等级 @0.78), → monsterTroop(类型
type的具体逻辑见#说明分页→主键 @0.77), → activity(类型
type的具体逻辑见#说明分页→活动参数 @0.76), → equip(类型
type的具体逻辑见#说明分页→装备位置 @0.76), → kvkSeason(类型
type的具体逻辑见#说明分页→默认投票结果 @0.76), → recharge(类型
type的具体逻辑见#说明分页→档位(真实付费) @0.76), ...+38条出向, ← resource_ResRules(联盟资源田数量→类型
type的具体逻辑见#说明分页 @0.7)

## 表: pve_skill_skill_buff [skill]
- 文件: pve_skill.xlsx | sheet: skill_buff
- 行数: 12 | 列数: 10 | 主键: 键值
- 列: 键值(int)→pve_pve_level.关卡显示等级, #备注说明(str), buff图标/battle_buff(str), buff类型
1.一段时间结算一次
2.属性修改
3.伤害护盾
4.薄葬
5.BUFF时间到移除时执行targetActions
6.嘲讽(int), 组ID
同组，权重>=就覆盖(int), buff重叠方式
0.时长不变
1.时长重置
2.时长累加(int), 最大叠加层数(int), 附加状态
1：眩晕
2：沉默
3：定身
4：无敌
5：失控
6：占据
7：不触发陷阱
8：免疫速度影响BUFF
如果附加效果被免疫，整个buff将移除(int), 属性修改列表
type1,changeV1|type2,changeV2|…
type:类型，见#说明的属性定义
changeV:变化值(str), 【间歇起效】每次起效执行的逻辑：目标行为列表，对应skill_target_action种的配置
因为有目标筛选，就可以做类似使周围目标受伤的效果
buff_type=1时起效(int)
- 关联: → pve_pve_level(键值→PVE关卡文件ID @0.72), → pve_pve_level(键值→关卡显示等级 @0.66), → activity(键值→活动参数 @0.62)

## 表: pve_skill_skill_target_action [skill]
- 文件: pve_skill.xlsx | sheet: skill_target_action
- 行数: 30 | 列数: 12 | 主键: 键值
- 列: 键值(int), #备注说明(str), 筛选区域类型
0.目标
1.自己
2.以自己为圆心
3.以目标为圆心
4.以自己为扇形
5.以目标为扇形
6.以自己为起点建立矩形
7.以目标为起点建立矩形
8.以自己与目标之间建立矩形(int), 筛选区域高度
(int), 筛选区域参数1(int)→key_new.facial, 筛选区域参数2(int)→building.升级时间(秒), 筛选数量限制，0无限制
技能等级决定用哪个，1级用第1个，2级用第2个，依次类推，对应等级找不到就算0，表示不限制数量(float), 敌对关系
0：友方
1：敌对
2：全体(int), 筛选生死限制
0：筛选存活单位
1：筛选死亡单位(int), 执行逻辑(str), 弹幕配置，对应client_show.xlsx中client_bullet中配置，不是真正的弹幕
如果有弹幕，弹幕命中后才真正执行actionList(str)→client_show_client_bullet.键值, 技能筛选目标
groupType(int)
- 关联: → pve_pve_level(筛选区域参数1→PVE关卡文件ID @0.85), → city_node_type_cityNodeTypeConf(筛选区域参数1→节点类型  参考CityNodeType @0.83), → pve_pve_level(筛选区域参数1→关卡显示等级 @0.81), → activity(筛选区域参数1→活动参数 @0.78), → data_constant(筛选区域参数1→常量值 @0.72), → monsterTroop(筛选区域参数1→主键 @0.72), → item(筛选区域参数1→参数1 @0.72), → building(筛选区域参数1→参数1 @0.72), → building(筛选区域参数2→升级时间(秒) @0.71), → key_new(筛选区域参数1→facial @0.7), ...+16条出向, ← client_rank_alliance_rank(排行榜类型→执行逻辑 @0.77), ← default_sth_defaultSth(id→执行逻辑 @0.76), ← sceneManager(场景LOD配置ID→执行逻辑 @0.74), ← world_building_worldBuilding(区分地图→执行逻辑 @0.74), ← task(任务类型→筛选区域参数1 @0.62)

## 表: quality_d_system_setting [config]
- 文件: quality.xlsx | sheet: d_system_setting
- 行数: 1 | 列数: 4 | 主键: 音乐开启
- 列: 音乐开启(str), 音乐音量(float), 音效开启(str), 音效音量(float)
- 关联: 无

## 表: quality_quality_check [other]
- 文件: quality.xlsx | sheet: quality_check
- 行数: 4 | 列数: 9 | 主键: 键值ID
- 列: 键值ID(int), #备注说明(str), Unnamed: 2(int), Unnamed: 3(int), Unnamed: 4(int), Unnamed: 5(int), Unnamed: 6(int), Unnamed: 7(int), Unnamed: 8(int)
- 关联: 无

## 表: quality_quality_define [other]
- 文件: quality.xlsx | sheet: quality_define
- 行数: 4 | 列数: 17 | 主键: 键值ID
- 列: 键值ID(int), #备注说明
前4个配置id不要修改，分别对应高、中、低、超低，后面可以随便拓展(str), Unnamed: 2(int), Unnamed: 3(int), Unnamed: 4(int), Unnamed: 5(int), Unnamed: 6(int), Unnamed: 7(int), LOD系数(int), shaderLOD(int), 多少分钟，自动清一次资源缓存(int), 是否开启场景特效(str), 相同特效最大缓存数(int), 屏幕适配尺寸，只影响Android，保底宽度(int), 屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正(int)→key_new.facial, 特效适配级别
2：高
1：中
0：低(int), 最多显示特效数量(int)
- 关联: → lord_exp_lordExp(屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正→经验值 @0.73), → item(屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正→参数1 @0.71), → building(屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正→参数2 @0.71), → key_new(屏幕分辨率修正系数，千分比，只影响Android，1000表示不修正→facial @0.7)

## 表: quality_quality_device [other]
- 文件: quality.xlsx | sheet: quality_device
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: rank [other]
- 文件: rank.xlsx | sheet: rank
- 行数: 66 | 列数: 11 | 主键: 主键
- 列: 主键(int), 排行数据源类型(int), #备注(str), 排名版显示名(str), 排行主体(int), 排行范围类型(单服、全服、K组等)(int), 排行榜奖励(int)→rank_rank_reward.排名组, 排行榜展示数量(int)→data_constant.常量值, 更新缓存时间(int), 显示信息格式化(str), 排序类型(int)
- 关联: → rank_rank_reward(排行榜奖励→排名组 @0.84), → monsterTroop(排行榜奖励→主键 @0.74), → data_constant(排行榜展示数量→常量值 @0.71), ← activity(活动额外参数→排行榜奖励 @0.82), ← video_point_videoPoint(主键→排行数据源类型 @0.78), ← draw_card(单次开启数量上限→排行榜奖励 @0.76), ← instancesTag_rpgRole(主动技能初始资源→排行榜奖励 @0.76), ← alliance_buff_attribute(类型→排行榜奖励 @0.76), ← activity(活动入口→排行数据源类型 @0.74), ← baseLevel(时代→排行数据源类型 @0.74), ← draw_card_discount(折扣组→排行数据源类型 @0.74), ← kvkSeason(报名赛季标识组→排行数据源类型 @0.74), ← worldScene_monsterFresh(基础刷新等级→排行数据源类型 @0.74), ...+32条入向

## 表: rank_rank_reward [battle]
- 文件: rank.xlsx | sheet: rank_reward
- 行数: 106 | 列数: 6 | 主键: 主键
- 列: 主键(int)→monsterTroop.主键, 排名组(int)→monsterTroop.主键, #排行说明(str), 排名区间下限(int)→building.参数1, 排名区间上限(int)→data_constant.常量值, 奖励id(int)→achievement.奖励
- 关联: → achievement(奖励id→奖励 @0.98), → reward(奖励id→ID @0.95), → monsterTroop(主键→主键 @0.86), → monsterTroop(排名组→主键 @0.74), → monsterTroop(排名区间下限→主键 @0.72), → item(排名区间上限→参数1 @0.64), → data_constant(排名区间上限→常量值 @0.64), → worldMonster(排名区间下限→部队配置ID @0.63), → hero_hero_level(排名区间下限→等级 @0.62), → building(排名区间下限→参数1 @0.62), ← rank(排行榜奖励→排名组 @0.84), ← activity(活动额外参数→排名组 @0.81), ← army(基础负载→排名组 @0.8), ← army_monster(基础负载→排名组 @0.8), ← city_node_type_cityNodeTypeConf(节点类型  参考CityNodeType→主键 @0.8), ← draw_card(单次开启数量上限→排名组 @0.76), ← trigger_config(主键→排名组 @0.76), ← instancesTag_rpgRole(主动技能初始资源→排名组 @0.76), ← instancesTag_rpgRole(主动技能消耗资源上限→排名组 @0.76), ← alliance_buff_attribute(类型→排名组 @0.76), ...+36条入向

## 表: recharge [other]
- 文件: recharge.xlsx | sheet: recharge
- 行数: 36 | 列数: 35 | 主键: ID
- 列: ID(int), #策划备注(str), 平台配置id(str), 渠道(str), 是否订阅(int), 试用天数(int), 是否开放(int), 分组(int), 分组规则(int), 优先级(int)→building.参数1, 礼包展示ID(int)→recharge_rechargeShow.ID, 档位(真实付费)(int)→key_new.facial, 折扣档位(str), 全局开启条件(str), 全局时间类型(str), 行为操作触发礼包(str), 礼包时间类型(str), 礼包获得条件(str), 关联活动Id(int)→key_new.facial, 奖励ID(int)→reward.ID, 赠送钻石数(int), 首次购买奖励(int), 扩展奖励(str), 非法购买保底奖励钻石数(int), 购买次数(int), ...+10列
- 关联: → pve_pve_level(优先级→关卡显示等级 @0.96), → activity(关联活动Id→ID @0.95), → reward(奖励ID→ID @0.95), → item(档位(真实付费)→道具分类排序 @0.91), → shop_shop_item(档位(真实付费)→商店id @0.89), → activity(优先级→活动参数 @0.88), → skill_condition(档位(真实付费)→值参数对比条件 @0.88), → pve_pve_level(优先级→PVE关卡文件ID @0.82), → gift_package(礼包展示ID→键值 @0.8), → pve_pve_level(档位(真实付费)→关卡显示等级 @0.8), ...+40条出向, ← panel_config(关闭多久执行删除【秒】→关联活动Id @0.93), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→档位(真实付费) @0.76), ← shop_shop_item(购买条件→玩家购买限制 @0.75), ← science(显示层级【只需配置第1级】→优先级 @0.74), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→优先级 @0.71), ← zombie_survivor(战斗力，显示值→优先级 @0.71), ← zombie(基础防御→优先级 @0.7), ← resource_ResRules(联盟资源田数量→档位(真实付费) @0.67), ← army(基础负载→优先级 @0.66), ← army_monster(基础负载→优先级 @0.66), ...+15条入向

## 表: recharge_rechargeProduct [other]
- 文件: recharge.xlsx | sheet: rechargeProduct
- 行数: 10 | 列数: 3 | 主键: ID
- 列: ID(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 人民币(int), 美元(int)
- 关联: → shop_shop_item(ID→商店id @0.72), → pve_pve_level(ID→关卡显示等级 @0.64), → city_node_type_cityNodeTypeConf(ID→节点类型  参考CityNodeType @0.63), → pve_pve_level(ID→PVE关卡文件ID @0.61), → activity(ID→活动参数 @0.6)

## 表: recharge_rechargeShow [other]
- 文件: recharge.xlsx | sheet: rechargeShow
- 行数: 10 | 列数: 11 | 主键: ID
- 列: ID(int), #策划备注(str), 宣传图(str)→activity.宣传图, 宣传图标题(str), 宣传图文字(str), 礼包说明(str), 界面名称(str), 分页(int)→rank_rank_reward.主键, 分页icon(str), 分页名称(str), 礼包入口(int)
- 关联: → activity(宣传图→宣传图 @0.88), → hero_hero_level(分页→等级 @0.72), → monsterTroop(分页→主键 @0.72), → rank_rank_reward(分页→主键 @0.72), ← recharge(礼包展示ID→ID @0.76)

## 表: recipe [other]
- 文件: recipe.xlsx | sheet: recipe
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: recipe_recipeIndex [other]
- 文件: recipe.xlsx | sheet: recipeIndex
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: recipe_recipeRule [other]
- 文件: recipe.xlsx | sheet: recipeRule
- 行数: 0 | 列数: 0 | 主键: -
- 列: 
- 关联: 无

## 表: resource [item]
- 文件: resource.xlsx | sheet: resource
- 行数: 23 | 列数: 24 | 主键: 编号 E_RESOURCE_TYPE
- 列: 编号 E_RESOURCE_TYPE(int), 名字Key(str), 描述Key(str), #描述，(str), 道具图标(str), 小图标(str), 品质（背景框）(int), SR ：是否有资源上限，默认值为0(int), 资源转换比例(int), 资源转换类型(个人联盟之间转换关系)(int)→rank.排行数据源类型, 显示优先级(越小越靠前)(int), 获取途径(str), 获取途径.1(str), 获取途径.2(str), 获取途径.3(str), 获取途径.4(str), 获取途径.5(str), 获取途径.6(str), 获取途径.7(str), 获取途径.8(str), 获取途径.9(str), 获取途径.10(str), 获取途径.11(str), 获取途径.12(str)
- 关联: → resource_ResRefresh(资源转换类型(个人联盟之间转换关系)→资源类型 @0.8), → activity(资源转换类型(个人联盟之间转换关系)→活动参数 @0.78), → pve_pve_level(资源转换类型(个人联盟之间转换关系)→PVE关卡文件ID @0.75), → key_new(资源转换类型(个人联盟之间转换关系)→facial @0.7), → rank(资源转换类型(个人联盟之间转换关系)→排行数据源类型 @0.65), → resource_Resinfo(资源转换类型(个人联盟之间转换关系)→主键 @0.6), ← sceneManager(场景LOD配置ID→资源转换类型(个人联盟之间转换关系) @0.81), ← resource_ResRefresh(资源类型→编号 E_RESOURCE_TYPE @0.7), ← resource_ResRules(联盟资源田数量→编号 E_RESOURCE_TYPE @0.65), ← resource_Resinfo(主键→编号 E_RESOURCE_TYPE @0.65), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→编号 E_RESOURCE_TYPE @0.63), ← monsterTroop_monsterHero(英雄ID→资源转换类型(个人联盟之间转换关系) @0.61), ← lodConfig(主键（唯一标识）→资源转换类型(个人联盟之间转换关系) @0.61), ← activity(活动入口→编号 E_RESOURCE_TYPE @0.6), ← baseLevel(时代→编号 E_RESOURCE_TYPE @0.6), ← kvkSeason(报名赛季标识组→编号 E_RESOURCE_TYPE @0.6), ...+2条入向

## 表: resource_ResRefresh [item]
- 文件: resource.xlsx | sheet: ResRefresh
- 行数: 28 | 列数: 5 | 主键: 主键
- 列: 主键(int)→pve_pve_level.PVE关卡文件ID, #策划备注(str), 资源类型(int)→rank.排行数据源类型, 资源等级(int), 最大采集(int)
- 关联: → activity(资源类型→活动参数 @0.78), → pve_pve_level(资源类型→PVE关卡文件ID @0.75), → activity(主键→活动参数 @0.73), → pve_pve_level(主键→PVE关卡文件ID @0.72), → resource(资源类型→编号 E_RESOURCE_TYPE @0.7), → key_new(资源类型→facial @0.7), → rank(资源类型→排行数据源类型 @0.65), → resource_Resinfo(资源类型→主键 @0.6), ← sceneManager(场景LOD配置ID→资源类型 @0.81), ← resource(资源转换类型(个人联盟之间转换关系)→资源类型 @0.8), ← pve_pve_level(关卡显示等级→主键 @0.65), ← monsterTroop_monsterHero(英雄ID→资源类型 @0.61), ← lodConfig(主键（唯一标识）→资源类型 @0.61)

## 表: resource_ResRules [item]
- 文件: resource.xlsx | sheet: ResRules
- 行数: 6 | 列数: 7 | 主键: 主键
- 列: 主键(int), #策划备注(str), 资源类型刷新权重(str), 资源等级刷新权重(str), 资源最大刷新数量(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 联盟资源田类型(str), 联盟资源田数量(int)→key_new.facial
- 关联: → item(联盟资源田数量→道具分类排序 @0.82), → shop_shop_item(联盟资源田数量→商店id @0.81), → skill_condition(联盟资源田数量→值参数对比条件 @0.8), → pve_pve_level(联盟资源田数量→关卡显示等级 @0.75), → city_node_type_cityNodeTypeConf(资源最大刷新数量→节点类型  参考CityNodeType @0.75), → activity(联盟资源田数量→活动参数 @0.74), → pve_pve_level(资源最大刷新数量→关卡显示等级 @0.74), → activity(资源最大刷新数量→活动参数 @0.73), → rank(联盟资源田数量→排行数据源类型 @0.72), → pve_pve_level(联盟资源田数量→PVE关卡文件ID @0.72), ...+34条出向

## 表: resource_Resinfo [item]
- 文件: resource.xlsx | sheet: Resinfo
- 行数: 8 | 列数: 13 | 主键: 主键
- 列: 主键(int)→resource.编号 E_RESOURCE_TYPE, #策划备注(str), 名称(str), 采集速度(int)→building.幸存者等级上限, 生成速度(int)→item.#购买价格（钻石）, 定时刷新(int), 残矿消失时间(int), 兑换比例(int)→item.参数1, 科技条件(str), 大地图资源模型(str), 大地图标志ICON(str), 采集资源界面icon(str), 优先展示buff(str)
- 关联: → alliance_gift_box(生成速度→所需经验 @0.85), → weapon(生成速度→攻击速度（普攻技能CD，复写pve_skill字段） @0.8), → pve_skill(兑换比例→技能总时长，动作总时长（优化timeline逻辑表现分离后可自动计算）
【int，毫秒】 @0.8), → pve_skill(生成速度→cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放） @0.76), → pve_skill(兑换比例→cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放） @0.76), → point_transform_pointTransform(采集速度→等级区间最大值 @0.74), → building(采集速度→幸存者等级上限 @0.74), → item(生成速度→#购买价格（钻石） @0.74), → science(采集速度→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.73), → baseLevel(采集速度→大本等级 @0.72), ...+16条出向, ← sceneManager(场景LOD配置ID→主键 @0.66), ← resource_ResRefresh(资源类型→主键 @0.6), ← resource(资源转换类型(个人联盟之间转换关系)→主键 @0.6)

## 表: resource_counter_resource [item]
- 文件: resource.xlsx | sheet: counter_resource
- 行数: 4 | 列数: 8 | 主键: 名字Key
- 列: 编号PBECounterType(int)→rank_rank_reward.主键, 名字Key(str), #名字(str), 描述Key(str), #描述，(str), 道具图标(str), 小图标(str), 品质（背景框）(int)
- 关联: → monsterTroop(编号PBECounterType→主键 @0.76), → rank_rank_reward(编号PBECounterType→主键 @0.76), → hero_hero_level(编号PBECounterType→等级 @0.71)

## 表: reward [battle]
- 文件: reward.xlsx | sheet: reward
- 行数: 593 | 列数: 11 | 主键: ID
- 列: ID(int), 备注（GM平台读取字段）(str), 直接给资源(str), 掉落类型(str), 道具必掉(str), 随机道具(str), 兵必掉落(str), 英雄必掉落(str), 英雄随机掉落(str), effect奖励(str), 奖励跳转(str)
- 关联: ← draw_card(奖励ID→ID @0.95), ← rank_rank_reward(奖励id→ID @0.95), ← recharge(奖励ID→ID @0.95), ← task(奖励ID→ID @0.95), ← task_daily_task_reward(奖励表id→ID @0.95), ← instancesGroup(副本奖励id→ID @0.95), ← video_gift_videoGift(奖励→ID @0.71), ← mail(奖励→ID @0.71), ← achievement(奖励→ID @0.71), ← alliance_gift(奖励→ID @0.7), ...+8条入向

## 表: sceneManager [other]
- 文件: sceneManager.xlsx | sheet: sceneManager
- 行数: 4 | 列数: 6 | 主键: 主键（唯一标识）
- 列: 主键（唯一标识）(int)→instanceMonster.主键, #策划备注(str), 场景名（必须小写）(str), 场景地图阻挡资源(str), 场景地图静态资源(str), 场景LOD配置ID(int)→resource_ResRefresh.资源类型
- 关联: → default_sth_defaultSth(场景LOD配置ID→id @0.93), → city_area_areaUnlock(场景LOD配置ID→主键 @0.85), → point_transform_pointTransform(场景LOD配置ID→积分类型 @0.85), → client_rank_alliance_rank(场景LOD配置ID→排行榜类型 @0.85), → resource(场景LOD配置ID→资源转换类型(个人联盟之间转换关系) @0.81), → resource_ResRefresh(场景LOD配置ID→资源类型 @0.81), → activity_activity_param(场景LOD配置ID→排行榜奖励发放 @0.8), → default_sth_defaultSth(主键（唯一标识）→id @0.79), → video_point_videoPoint(场景LOD配置ID→主键 @0.79), → pve_pve_level(场景LOD配置ID→PVE关卡文件ID @0.77), ...+20条出向, ← world_building_worldBuilding(区分地图→主键（唯一标识） @0.73), ← lodConfig(主键（唯一标识）→主键（唯一标识） @0.68)

## 表: science [other]
- 文件: science.xlsx | sheet: science
- 行数: 371 | 列数: 18 | 主键: ID，约定
group*1000+level
- 列: ID，约定
group*1000+level(int), #备注名称(str), 页签(int), 组名(int), 等级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 最高等级(int), 名称(str), 说明(str), 图标，Game_Prefab/texture/sciences(str), 显示层级【只需配置第1级】(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 显示Y轴坐标【只需配置第1级】0表示正中间(int), 科技前置解锁条件(str), 加成属性名【客户端】(str)→key_new.facial, 加成属性值【客户端】
正数表示百分比
负数表示直接数值(float)→item.参数1, @作用效果(str), 提供战斗力(int)→hero_hero_level.升下一级需要经验值, 升级消耗(str), 升级时间消耗（s）(int)
- 关联: → pve_pve_level(显示层级【只需配置第1级】→关卡显示等级 @0.9), → city_node_type_cityNodeTypeConf(显示层级【只需配置第1级】→节点类型  参考CityNodeType @0.88), → shop_shop_item(等级→商店id @0.87), → activity(显示层级【只需配置第1级】→活动参数 @0.85), → pve_pve_level(等级→关卡显示等级 @0.84), → activity(等级→活动参数 @0.8), → pve_pve_level(显示层级【只需配置第1级】→PVE关卡文件ID @0.79), → city_node_type_cityNodeTypeConf(等级→节点类型  参考CityNodeType @0.78), → activity(等级→类型 @0.77), → hero(显示层级【只需配置第1级】→键值 @0.76), ...+25条出向, ← draw_card_discount(折扣组→等级 @0.77), ← worldScene_monsterFresh(基础刷新等级→等级 @0.77), ← alliance_building(排序数量→等级 @0.77), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→等级 @0.77), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→显示层级【只需配置第1级】 @0.76), ← baseLevel(时代→等级 @0.74), ← kvkSeason(报名赛季标识组→等级 @0.74), ← alliance_building(采集速度→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.74), ← zombie_survivor(兵种等级→等级 @0.74), ← material_merge_MaterialProduce(每次生产获得数量→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.74), ...+51条入向

## 表: search [other]
- 文件: search.xlsx | sheet: search
- 行数: 5 | 列数: 8 | 主键: 主键
- 列: 主键(int), #策划备注(str), 搜索名称(str), 搜索tips显示(str)→key_new.facial, 搜索icon(str), 搜索类型(str), 是否显示(int), 显示顺序(int)
- 关联: → key_new(搜索tips显示→facial @0.7)

## 表: shop [other]
- 文件: shop.xlsx | sheet: shop
- 行数: 14 | 列数: 15 | 主键: ID
- 列: ID(int), #商店名称(str), key(str), 商店类型(int), 时间类型(int), 热更后是否强制刷新商品(int), 是否开放(int), 玩家条件(str), 商品最大显示数量(int), 商品定时刷新类型(int), 刷新参数(int)→data_constant.常量值, 是否是个人商店(int), 显示排序(int), 默认tab icon(str), 选中 icon(str)
- 关联: → data_constant(刷新参数→常量值 @0.71), ← shop_shop_item(商店id→ID @0.95), ← equip(穿戴等级→ID @0.71), ← draw_card_discount(折扣组→ID @0.69), ← worldScene_monsterFresh(基础刷新等级→ID @0.69), ← alliance_building(排序数量→ID @0.69), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→ID @0.69), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→ID @0.68), ← activity(活动入口→ID @0.67), ← baseLevel(时代→ID @0.67), ← kvkSeason(报名赛季标识组→ID @0.67), ...+13条入向

## 表: shop_shop_item [item]
- 文件: shop.xlsx | sheet: shop_item
- 行数: 89 | 列数: 14 | 主键: ID
- 列: ID(int), #道具所处商店(str), 商店id(int)→shop.ID, #道具名称(str), 出售内容(int), 数量(int), 限购类型(int), 周期内限购数量(int)→building.幸存者等级上限, 购买类型(int), 购买价格(str), 购买条件(str)→recharge.玩家购买限制, 折扣率(str), 是否上架(int), 出现权重(int)
- 关联: → shop(商店id→ID @0.95), → recharge(购买条件→玩家购买限制 @0.75), → hero_hero_level(周期内限购数量→等级 @0.73), → rank_rank_reward(周期内限购数量→主键 @0.73), → data_constant(周期内限购数量→常量值 @0.72), → monsterTroop(周期内限购数量→主键 @0.72), → building(周期内限购数量→幸存者等级上限 @0.72), ← draw_card_discount(折扣组→商店id @0.95), ← worldScene_monsterFresh(基础刷新等级→商店id @0.95), ← alliance_building(排序数量→商店id @0.95), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→商店id @0.95), ← hud_config_personal_config(排序→商店id @0.95), ← activity(活动入口→商店id @0.92), ← baseLevel(时代→商店id @0.92), ← kvkSeason(报名赛季标识组→商店id @0.92), ← alliance_shop_alliance_shopItem(排序→商店id @0.92), ← zombie_survivor(兵种等级→商店id @0.92), ...+30条入向

## 表: skill [skill]
- 文件: skill.xlsx | sheet: skill
- 行数: 25 | 列数: 19 | 主键: 键值
- 列: 键值(int), #策划备注(str), #技能说明(str), 技能名称(str), 技能描述(str), 技能图标(str), 技能类别(int), 技能模式(int), 技能解锁星级(int), 技能冷却时间(int), 技能限制回合数(int), 主动技能发动延迟回合数(int), 战斗状态条件(int), 技能触发条件(int), 技能触发几率(int), 客户端预警绘制方式(str), 技能效果等级数值配置(int), 技能前端特效组(int), 战斗公式技能修正系数(int)
- 关联: ← hero(英雄主动技能ID→键值 @0.95), ← hero(英雄被动技能ID→键值 @0.95), ← kingdomSkill(技能id→键值 @0.95)

## 表: skill_client_skill_show [skill]
- 文件: skill_client.xlsx | sheet: skill_show
- 行数: 23 | 列数: 10 | 主键: 键值
- 列: 键值(str), #备注说明(str), 释放技能时朝向目标(str), 技能自动释放表现cd【ms】
有的系统有效(int), 技能表现时间，现在先配置动作持续时间【ms】(int), 动作爆发点时间【ms】【动作人员告之】
近战：砍中的时间点
远程：释放技能的时间点(float), 技能动作名(str), 发起特效，对应client/skill_show.xlsx中【effect】中配置(int), 弹幕配置id，对应client_show.xlsx中client_bullet中配置(str), 命中特效，对应client_show.xlsx中【client_effect中的配置(int)
- 关联: 无

## 表: skill_condition [skill]
- 文件: skill_condition.xlsx | sheet: skill_condition
- 行数: 54 | 列数: 8 | 主键: 键值
- 列: 键值(int), #策划备注(str), 逻辑运算(str), 逻辑参数(str), 条件筛选类型(str), 值条件判定方法(str), 值参数对比条件(int), Unnamed: 7(str)
- 关联: ← area_area_config(地块关卡类型→值参数对比条件 @0.9), ← equip(装备位置→值参数对比条件 @0.88), ← recharge(档位(真实付费)→值参数对比条件 @0.88), ← alliance_building(建筑类型→值参数对比条件 @0.88), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→值参数对比条件 @0.88), ← hud_config(显示权重，越大显示越前面→值参数对比条件 @0.88), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→值参数对比条件 @0.85), ← panel_config(层级→值参数对比条件 @0.82), ← resource_ResRules(联盟资源田数量→值参数对比条件 @0.8), ← activity(活动入口→值参数对比条件 @0.79), ...+10条入向

## 表: skill_skill_level [skill]
- 文件: skill.xlsx | sheet: skill_level
- 行数: 24 | 列数: 6 | 主键: 键值
- 列: 键值(int), #策划备注(str), 技能图标(str), 技能升级消耗(int), 发动技能怒气消耗(int), 技能包含的所有效果列表(str)
- 关联: 无

## 表: socialRelation [other]
- 文件: socialRelation.xlsx | sheet: socialRelation
- 行数: 3 | 列数: 3 | 主键: 主键（社交关系id）
- 列: 主键（社交关系id）(int), #策划备注(str), 副本服匹配实体参数配置引用分页名(str)
- 关联: 无

## 表: soldier_consumption [other]
- 文件: soldier_consumption.xlsx | sheet: soldier_consumption
- 行数: 6 | 列数: 7 | 主键: 键值
- 列: 键值(int), #战斗类型描述(str), 轻伤比例(int)→building.幸存者等级上限, 重伤比例(int)→building.幸存者等级上限, 死亡比例(int), 关联玩法功能id组(int), 战斗目标 1是pve 2是pvp(int)
- 关联: → client_show_client_bullet(重伤比例→飞行速度
默认15m/s @0.81), → pve_skill(重伤比例→检索距离，即技能释放距离【float，米】 @0.78), → building(重伤比例→建筑高度（长度） @0.78), → alliance_constant(重伤比例→值 @0.76), → point_transform_pointTransform(重伤比例→等级区间最大值 @0.74), → building(重伤比例→幸存者等级上限 @0.74), → building(轻伤比例→幸存者等级上限 @0.74), → army_trait(重伤比例→主键 @0.73), → effect(重伤比例→组 @0.73), → science(重伤比例→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.73), ...+12条出向

## 表: task [quest]
- 文件: task.xlsx | sheet: task
- 行数: 340 | 列数: 15 | 主键: 任务id
- 列: 任务id(int), 任务类型(int)→key_new.facial, 分组(int), 前置条件(str), #备注(str), 任务条件(str), 扩展字段(int), 任务描述(str), #备注.1(str), 奖励ID(int)→reward.ID, 任务名称，key_new里的key(str), 任务品质，客户端用
  WHITE = 1,
  GREEN = 2,
  BLUE = 3,
  PURPLE = 4,
  ORANGE = 5,(int), 任务图标，texture\task(str), 任务显示优先级：数字越小优先级越高(int), 执行，任务跳转(str)
- 关联: → reward(奖励ID→ID @0.95), → item(任务类型→道具分类排序 @0.91), → shop_shop_item(任务类型→商店id @0.89), → city_node_type_cityNodeTypeConf(任务类型→节点类型  参考CityNodeType @0.82), → pve_pve_level(任务类型→关卡显示等级 @0.8), → activity(任务类型→活动参数 @0.77), → activity(任务类型→活动入口 @0.76), → baseLevel(任务类型→时代 @0.76), → kvkSeason(任务类型→报名赛季标识组 @0.76), → alliance_shop_alliance_shopItem(任务类型→排序 @0.76), ...+30条出向, ← achievement(任务索引→任务id @0.95), ← milestone(任务id→任务id @0.95), ← activity_activity_param(任务组→分组 @0.85), ← draw_card(奖励ID→任务id @0.75), ← zombie_bt_ai(范围内不会跟随主将距离→任务类型 @0.71), ← world_building_worldBuilding(建筑类型→任务显示优先级：数字越小优先级越高 @0.71), ← army(普攻技能表现→任务id @0.7), ← alliance_gift(奖励→任务id @0.7), ← alliance_buff_attribute(类型→任务id @0.7), ← army_monster(普攻技能表现→任务id @0.7), ...+1条入向

## 表: task_daily_task_group [quest]
- 文件: task.xlsx | sheet: daily_task_group
- 行数: 1 | 列数: 4 | 主键: id
- 列: id(int), 玩家最小等级(含)(int), 玩家最大等级(含)(int), 任务组(int)
- 关联: 无

## 表: task_daily_task_reward [battle]
- 文件: task.xlsx | sheet: daily_task_reward
- 行数: 5 | 列数: 3 | 主键: 奖励表id
- 列: id，唯一即可(int), 活跃度多少可领取(int)→building.幸存者等级上限, 奖励表id(int)→reward.ID
- 关联: → reward(奖励表id→ID @0.95), → building(活跃度多少可领取→幸存者等级上限 @0.76), → data_constant(活跃度多少可领取→常量值 @0.71), → hero_hero_level(活跃度多少可领取→等级 @0.71), → monsterTroop(活跃度多少可领取→主键 @0.71), → rank_rank_reward(活跃度多少可领取→主键 @0.71)

## 表: task_task_chapter [quest]
- 文件: task.xlsx | sheet: task_chapter
- 行数: 4 | 列数: 7 | 主键: 章节id
- 列: 章节id(int), 章节名称(str), 章节描述(str), 大本等级(int), 任务id(str), 章节奖励(int), 章节图标(str)
- 关联: 无

## 表: threatRule_threatEvents [other]
- 文件: threatRule.xlsx | sheet: threatEvents
- 行数: 5 | 列数: 5 | 主键: 事件id
- 列: 事件id(int), #策划备注(str), 触发仇恨事件类型(int), 服务器监听类名(str), 仇恨值计算公式系数配置id(int)
- 关联: 无

## 表: threatRule_threatFormula [other]
- 文件: threatRule.xlsx | sheet: threatFormula
- 行数: 1 | 列数: 5 | 主键: 公式系数配置id
- 列: 公式系数配置id(int), #策划备注(str), 伤害仇恨系数(int), 治疗仇恨系数(int), 进入战斗初始仇恨值(int)
- 关联: 无

## 表: threatRule_threatMode [other]
- 文件: threatRule.xlsx | sheet: threatMode
- 行数: 1 | 列数: 5 | 主键: 仇恨系统模式id
- 列: 仇恨系统模式id(int), #策划备注(str), 监听仇恨事件id列表(str), 仇恨递增/衰减时间间隔(int), 仇恨递增/衰减万分比(int)
- 关联: 无

## 表: trigger_config [config]
- 文件: trigger_config.xlsx | sheet: trigger_config
- 行数: 3 | 列数: 6 | 主键: 执行动作-> action表的ID
- 列: 主键(int)→key_new.facial, #描述(str), 步骤类型
等级条件：CondLv:等级，例：CondLv:1
科技解锁等级：CondScience:组Id,等级，例：CondScience:103,1
任务可领时：FinishTask:任务ID，例：FinishTask:2
建筑存在性：BuildingExist:组ID，例：BuildingExist:101(str), 执行动作-> action表的ID(str), 触发Times
0：满足条件就触发，不限次
>0：可触发的总次数(int), 每次游戏触发一次后是否移除，不再触发，断线重连次数会清掉(str)
- 关联: → city_node_type_cityNodeTypeConf(主键→节点类型  参考CityNodeType @0.8), → pve_pve_level(主键→PVE关卡文件ID @0.77), → rank_rank_reward(主键→排名组 @0.76), → pve_pve_level(主键→关卡显示等级 @0.74), → activity(主键→活动参数 @0.73), → data_constant(主键→常量值 @0.71), → item(主键→参数1 @0.71), → building(主键→战斗力 @0.71), → building(主键→繁荣度 @0.71), → building(主键→参数1 @0.71), ...+3条出向

## 表: unlock [other]
- 文件: unlock.xlsx | sheet: unlock
- 行数: 34 | 列数: 4 | 主键: 主键
- 列: 主键(int)→pve_pve_level.PVE关卡文件ID, #功能名称(str), #说明(str), 解锁条件(str)→building.建筑链需求多个时竖线"|"分割
- 关联: → pve_pve_level(主键→PVE关卡文件ID @0.76), → building(解锁条件→建筑链需求多个时竖线"|"分割 @0.72), ← activity(活动参数→主键 @0.64), ← pve_pve_level(关卡显示等级→主键 @0.61)

## 表: unlock_abtest [other]
- 文件: unlock.xlsx | sheet: abtest
- 行数: 2 | 列数: 4 | 主键: 索引
- 列: 索引(int), #备注(str), 下限（包含）(int), 上限（包含）(int)
- 关联: 无

## 表: unlock_functionSwitch [other]
- 文件: unlock.xlsx | sheet: functionSwitch
- 行数: 34 | 列数: 3 | 主键: 主键（功能id）
- 列: 主键（功能id）(int)→pve_pve_level.主键, #说明(str), 条件解锁id(int)→item.参数1
- 关联: → pve_pve_level(条件解锁id→PVE关卡文件ID @0.82), → monsterTroop(条件解锁id→主键 @0.78), → pve_pve_level(主键（功能id）→PVE关卡文件ID @0.76), → item(条件解锁id→参数1 @0.73), → monsterTroop(主键（功能id）→主键 @0.64), → pve_pve_level(主键（功能id）→主键 @0.62), → effect(条件解锁id→组 @0.61), → point_transform_pointTransform(主键（功能id）→ID @0.6), → point_transform_pointTransform(条件解锁id→ID @0.6), → worldMonster(条件解锁id→部队配置ID @0.6), ← activity(活动参数→主键（功能id） @0.64), ← army_trait(主键→主键（功能id） @0.61)

## 表: unlock_switch [other]
- 文件: unlock.xlsx | sheet: switch
- 行数: 2 | 列数: 6 | 主键: 索引
- 列: 索引(int), #策划备注(str), 正式服开关(str), 测试服开关(str), 客户端最低版本号(int), 客户端最高版本号(str)
- 关联: 无

## 表: video_gift_videoGift [reward]
- 文件: video_gift.xlsx | sheet: videoGift
- 行数: 30 | 列数: 6 | 主键: 主键
- 列: 主键(int), #备注(str), 持续时间（h）(int), 名称(str), 图片名称(str), 奖励(int)→world_building_worldBuilding.id
- 关联: → reward(奖励→ID @0.71), → world_building_worldBuilding(奖励→id @0.66), ← alliance_buff_attribute(类型→奖励 @0.78)

## 表: video_point_videoPoint [other]
- 文件: video_point.xlsx | sheet: videoPoint
- 行数: 24 | 列数: 9 | 主键: 礼包id
- 列: 主键(int)→rank.排行数据源类型, #策划备注(str), 类型(int), 大本等级限制(str), 参数(str), 间隔数值(str), 触发几率（%）(str), 礼包id(str), 奖励系数(str)
- 关联: → rank(主键→排行数据源类型 @0.78), ← weapon(武器技能（pve_skill的技能组ID，复写）→主键 @0.8), ← sceneManager(场景LOD配置ID→主键 @0.79), ← client_rank_alliance_rank(排行榜类型→主键 @0.78), ← world_building_worldBuilding(区分地图→主键 @0.74), ← city_area_areaUnlock(主键→主键 @0.71), ← default_sth_defaultSth(id→主键 @0.66), ← sceneManager(主键（唯一标识）→主键 @0.6)

## 表: vip [other]
- 文件: vip.xlsx | sheet: vip
- 行数: 19 | 列数: 5 | 主键: 编号
- 列: 编号(int)→pve_pve_level.关卡显示等级, 等级(int)→building.缩放时隐藏次序，越大越不会被隐藏, 需要点数(int), 头像框(str), vip特权(str)
- 关联: → pve_pve_level(等级→关卡显示等级 @0.96), → activity(等级→活动参数 @0.84), → pve_pve_level(等级→PVE关卡文件ID @0.77), → pve_pve_level(编号→关卡显示等级 @0.76), → building(等级→参数1 @0.72), → item(等级→参数1 @0.71), → activity(编号→活动参数 @0.68), → building(等级→缩放时隐藏次序，越大越不会被隐藏 @0.66), → science(等级→加成属性值【客户端】
正数表示百分比
负数表示直接数值 @0.61), → baseLevel(等级→大本等级 @0.6), ← panel_config(关闭多久执行删除【秒】→等级 @0.75), ← science(显示层级【只需配置第1级】→等级 @0.74), ← hud_config_bookmark_config(关键值【唯一】，暂时没有使用→等级 @0.71), ← zombie_survivor(战斗力，显示值→等级 @0.71), ← zombie(基础防御→等级 @0.7), ← building(效果类型→等级 @0.69), ← activity(类型→等级 @0.67), ← army(基础负载→等级 @0.66), ← army_monster(基础负载→等级 @0.66), ← equip(穿戴等级→等级 @0.66), ...+17条入向

## 表: weapon [other]
- 文件: weapon.xlsx | sheet: weapon
- 行数: 13 | 列数: 18 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字(str), 武器战斗力，显示值(int)→pve_skill.检索距离，即技能释放距离【float，米】, 是否投射武器(str), 持续靠近敌人距离(int), 敌人类型索敌优先级（值为类型的优先级，越小优先级越高）(str), 是否优先选择远距离目标(int), 武器技能（pve_skill的技能组ID，复写）(int)→key_new.facial, 攻击距离
（复写pve_skill字段）(float), 攻击速度（普攻技能CD，复写pve_skill字段）(int)→building.参数2, 攻击方式（替换pve_skill表的target_actions ID）(str), 攻击加成(int), 攻击等级成长值(int), 生命加成(int), 生命等级成长值(int), 防御加成(int), 防御等级成长值(int)
- 关联: → city_area_areaUnlock(武器技能（pve_skill的技能组ID，复写）→主键 @0.88), → pve_skill(攻击速度（普攻技能CD，复写pve_skill字段）→cd耗时
【int，毫秒】（注意：cd如果短于total_time则技能会加速播放） @0.86), → alliance_gift_box(攻击速度（普攻技能CD，复写pve_skill字段）→所需经验 @0.85), → pve_skill(武器战斗力，显示值→检索距离，即技能释放距离【float，米】 @0.8), → video_point_videoPoint(武器技能（pve_skill的技能组ID，复写）→主键 @0.8), → world_building_worldBuilding(武器技能（pve_skill的技能组ID，复写）→id @0.76), → item(武器技能（pve_skill的技能组ID，复写）→编号 @0.75), → item(攻击速度（普攻技能CD，复写pve_skill字段）→#购买价格（钻石） @0.74), → lord_exp_lordExp(攻击速度（普攻技能CD，复写pve_skill字段）→经验值 @0.72), → rank(武器技能（pve_skill的技能组ID，复写）→排行数据源类型 @0.72), ...+7条出向, ← zombie(装备武器（weapon表）→主键 @0.81), ← resource_Resinfo(生成速度→攻击速度（普攻技能CD，复写pve_skill字段） @0.8), ← activity(类型→主键 @0.75), ← equip(穿戴等级→主键 @0.73), ← draw_card_discount(折扣组→主键 @0.71), ← worldScene_monsterFresh(基础刷新等级→主键 @0.71), ← alliance_building(排序数量→主键 @0.71), ← alliance_science(显示X轴，横坐标
【只需配置第1级】→主键 @0.71), ← pve_skill_skill_action(类型
type的具体逻辑见#说明分页→主键 @0.69), ← activity(活动入口→主键 @0.68), ...+15条入向

## 表: worldMonster [monster]
- 文件: worldMonster.xlsx | sheet: worldMonster
- 行数: 106 | 列数: 12 | 主键: 序号
- 列: 序号(int), 名称，key_new表id(str), #策划备注(str), 类型(int), 胜利奖励(int), 奖励展示(str), 消失倒计时（秒）(int), 部队配置ID(int)→rank_rank_reward.主键, 大地图缩放icon(str), 战报图标(str), 半身像(str), 缩放(int)
- 关联: → monsterTroop(部队配置ID→主键 @0.93), → rank_rank_reward(部队配置ID→主键 @0.75), → hero_hero_level(部队配置ID→等级 @0.65), ← city_node_type_cityNodeTypeConf(节点类型  参考CityNodeType→部队配置ID @0.83), ← pve_pve_level(关卡显示等级→部队配置ID @0.76), ← point_transform_pointTransform(分组→部队配置ID @0.74), ← activity(活动参数→部队配置ID @0.73), ← activity(显示优先级→部队配置ID @0.72), ← army(治疗消耗时间→部队配置ID @0.72), ← point_transform_pointTransform(积分类型→序号 @0.72), ← alliance_building(采集速度→部队配置ID @0.72), ← zombie_bt_ai(脱战距离→部队配置ID @0.72), ← material_merge_MaterialProduce(每次生产获得数量→部队配置ID @0.72), ...+24条入向

## 表: worldMonster_monsterExtraDrop [monster]
- 文件: worldMonster.xlsx | sheet: monsterExtraDrop
- 行数: 1 | 列数: 8 | 主键: 活动掉落的id
- 列: 主键(int), #策划用(str), 怪物组(int), 怪物type(int), 怪物等级下限(包含)(int), 怪物等级上限(包含)(int), 掉落概率(万分比)(int), 活动掉落的id(int)→activity.ID
- 关联: → activity(活动掉落的id→ID @0.6)

## 表: worldScene_monsterFresh [monster]
- 文件: worldScene.xlsx | sheet: monsterFresh
- 行数: 18 | 列数: 11 | 主键: 主键
- 列: 主键(int), 刷新类型(int), 基础刷新等级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 成长系数(float), 等级上限(int)→worldScene_monsterLevel.等级上限, 资源带1刷新权重(int), 资源带2刷新权重(int), 资源带3刷新权重(int), 资源带4刷新权重(int), 资源带5刷新权重(int), 资源带6刷新权重(int)
- 关联: → shop_shop_item(基础刷新等级→商店id @0.95), → item(基础刷新等级→道具分类排序 @0.86), → pve_pve_level(基础刷新等级→关卡显示等级 @0.82), → activity(基础刷新等级→活动参数 @0.79), → activity(等级上限→活动参数 @0.79), → equip(基础刷新等级→穿戴等级 @0.77), → science(基础刷新等级→等级 @0.77), → alliance_science_alliance_skill(基础刷新等级→等级 @0.77), → pve_pve_level(基础刷新等级→PVE关卡文件ID @0.76), → pve_pve_level(等级上限→PVE关卡文件ID @0.76), ...+27条出向, ← activity(活动入口→基础刷新等级 @0.77), ← baseLevel(时代→基础刷新等级 @0.77), ← kvkSeason(报名赛季标识组→基础刷新等级 @0.77), ← zombie_survivor(兵种等级→基础刷新等级 @0.77), ← alliance_shop_alliance_shopItem(排序→基础刷新等级 @0.77), ← equip(装备位置→基础刷新等级 @0.73), ← kvkSeason(默认投票结果→基础刷新等级 @0.73), ← recharge(档位(真实付费)→基础刷新等级 @0.73), ← alliance_building(建筑类型→基础刷新等级 @0.73), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→基础刷新等级 @0.73), ...+9条入向

## 表: worldScene_monsterLevel [monster]
- 文件: worldScene.xlsx | sheet: monsterLevel
- 行数: 36 | 列数: 4 | 主键: 主键
- 列: 主键(int)→pve_pve_level.PVE关卡文件ID, 刷新类型(int), 开服天数(int)→rank_rank_reward.主键, 等级上限(int)→building.缩放时隐藏次序，越大越不会被隐藏
- 关联: → activity(等级上限→活动参数 @0.9), → pve_pve_level(等级上限→PVE关卡文件ID @0.83), → pve_pve_level(主键→PVE关卡文件ID @0.77), → building(等级上限→参数1 @0.77), → monsterTroop(等级上限→主键 @0.75), → item(等级上限→参数1 @0.75), → building(等级上限→等级 @0.75), → building(等级上限→缩放时隐藏次序，越大越不会被隐藏 @0.73), → army_trait(等级上限→主键 @0.71), → hero_hero_level(开服天数→等级 @0.71), ...+9条出向, ← alliance_building(采集速度→等级上限 @0.76), ← material_merge_MaterialProduce(每次生产获得数量→等级上限 @0.76), ← material_merge_MaterialProduce(每次生产需要时间→等级上限 @0.76), ← entity_menu(缩放系数修正值→等级上限 @0.74), ← activity(活动参数→主键 @0.63), ← worldScene_monsterFresh(等级上限→等级上限 @0.63)

## 表: worldScene_monsterWeights [monster]
- 文件: worldScene.xlsx | sheet: monsterWeights
- 行数: 12 | 列数: 5 | 主键: 主键
- 列: 主键(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 区域(int), 野怪类型(int), 野怪检索刷新时间(int), 野怪数量上限(int)
- 关联: → city_node_type_cityNodeTypeConf(主键→节点类型  参考CityNodeType @0.67), → pve_pve_level(主键→关卡显示等级 @0.66), → hud_config_bookmark_config(主键→关键值【唯一】，暂时没有使用 @0.63), → activity(主键→活动参数 @0.62), → pve_pve_level(主键→PVE关卡文件ID @0.62)

## 表: world_building_worldBuilding [building]
- 文件: world_building.xlsx | sheet: worldBuilding
- 行数: 174 | 列数: 25 | 主键: id
- 列: id(int), 区分地图(int)→key_new.facial, #策划备注(str), 建筑名称(str), 建筑说明(str), 详细描述，建筑描述(str), 建筑类型(int)→task.任务显示优先级：数字越小优先级越高, 图标(str), 模型资源名(str), 世界建筑等级(str), 携带buff(str), 领地范围(int), 容纳士兵上限(int), 资源带增加等级(int), 首次开放时间(s)(int), 英雄配置(str), npc士兵(str), 首胜奖励邮件(int), 占领奖励(int)→reward.ID, 胜利后需占领时间(h)(int), 开放后循环时间(h)(int), 是否存在失效状态(int), 不可迁城范围(int), 是否需要地块连接(int), 是否可被攻击(str)
- 关联: → default_sth_defaultSth(区分地图→id @0.88), → point_transform_pointTransform(区分地图→积分类型 @0.85), → client_rank_alliance_rank(区分地图→排行榜类型 @0.85), → mail(建筑类型→模板 @0.81), → activity_activity_param(区分地图→排行榜奖励发放 @0.8), → city_area_areaUnlock(区分地图→主键 @0.8), → video_point_videoPoint(区分地图→主键 @0.74), → pve_skill_skill_target_action(区分地图→执行逻辑 @0.74), → sceneManager(区分地图→主键（唯一标识） @0.73), → pve_pve_level(区分地图→PVE关卡文件ID @0.72), ...+9条出向, ← hero(英雄被动技能ID→id @0.77), ← draw_card(奖励ID→id @0.76), ← sceneManager(场景LOD配置ID→id @0.76), ← weapon(武器技能（pve_skill的技能组ID，复写）→id @0.76), ← hero(英雄主动技能ID→id @0.73), ← alliance_gift(奖励→id @0.71), ← activity(活动额外参数→id @0.71), ← alliance_buff_attribute(类型→id @0.71), ← client_rank_alliance_rank(排行榜类型→id @0.71), ← effect_autoEffect(触发的effect→id @0.71), ...+3条入向

## 表: zombie [other]
- 文件: zombie.xlsx | sheet: zombie
- 行数: 13 | 列数: 21 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字(str), 特点描述(str), 部队图标，
路径：Assets/Game_Prefab/texture/army_icon(str), 兵种类型(int), 是否是boss(int), 能力组别
1 - 防御型
2 - 近战输出
3 - 远程输出
4 - 辅助型(int), 兵种等级(int), 兵种品质(int), 显示星级(int), 战斗力，显示值(int), 装备武器（weapon表）(int)→weapon.主键, 显示模型(str), 拥有技能列表(到了CD就放)(int)→pve_pve_level.PVE关卡文件ID, 基础移动速度(float), 基础生命(int), 基础攻击(int)→hero_hero_level.等级, 基础防御(int)→building.参数1, AI行为（bt_ai页签）(int), RVO优先级（0~1）（>1锁定RVO）(float)
- 关联: → weapon(装备武器（weapon表）→主键 @0.81), → pve_pve_level(拥有技能列表(到了CD就放)→PVE关卡文件ID @0.73), → buff_attribute_buff_client(基础防御→排序，小的在前 @0.7), → recharge(基础防御→优先级 @0.7), → vip(基础防御→等级 @0.7), → monsterTroop(基础攻击→显示等级 @0.69), → pve_pve_level(基础防御→关卡显示等级 @0.68), → item(基础防御→物品类型 @0.68), → worldMonster(基础攻击→部队配置ID @0.67), → building(基础防御→缩放时隐藏次序，越大越不会被隐藏 @0.67), ...+17条出向, ← material_merge_MaterialProduce(每次生产获得数量→战斗力，显示值 @0.9), ← material_merge_MaterialProduce(每次生产需要时间→战斗力，显示值 @0.9), ← draw_card(单次开启数量上限→装备武器（weapon表） @0.8), ← instancesTag_rpgRole(主动技能初始资源→装备武器（weapon表） @0.8)

## 表: zombie_bt_ai [other]
- 文件: zombie.xlsx | sheet: bt_ai
- 行数: 14 | 列数: 9 | 主键: 主键
- 列: 主键(int), #描述(str), 名字(str), 行为树资源名字(str), 范围内不会跟随主将距离(int)→key_new.facial, 随机巡逻（失控）半径(int), 警戒距离(int), 脱战距离(int)→building.缩放时隐藏次序，越大越不会被隐藏, ap怒气值获取倍率（负数为关闭怒气获取）(int)
- 关联: → item(范围内不会跟随主将距离→道具分类排序 @0.85), → shop_shop_item(范围内不会跟随主将距离→商店id @0.84), → city_node_type_cityNodeTypeConf(范围内不会跟随主将距离→节点类型  参考CityNodeType @0.78), → pve_pve_level(范围内不会跟随主将距离→关卡显示等级 @0.77), → activity(范围内不会跟随主将距离→活动参数 @0.75), → building(脱战距离→缩放时隐藏次序，越大越不会被隐藏 @0.74), → baseLevel(脱战距离→大本等级 @0.73), → monsterTroop(脱战距离→显示等级 @0.73), → pve_pve_level(范围内不会跟随主将距离→PVE关卡文件ID @0.73), → rank(范围内不会跟随主将距离→排行数据源类型 @0.72), ...+35条出向, ← zombie_survivor(AI行为（bt_ai页签）→主键 @0.61)

## 表: zombie_survivor [other]
- 文件: zombie.xlsx | sheet: survivor
- 行数: 22 | 列数: 23 | 主键: 主键
- 列: 主键(int), #策划备注(str), 名字(str), 部队图标，
路径：Assets/Game_Prefab/texture/army_icon(str), 兵种类型(int), 能力组别
1 - 防御型
2 - 近战输出
3 - 远程输出
4 - 辅助型(int), 兵种等级(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 兵种品质(int), 显示星级(int), 战斗力，显示值(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 显示模型(str), 激活后模型显示颜色（临时方案）
填写RGB值(str), 显示模型(临时字段，敌人模型)(str), 装备武器（weapon表）(int), 幸存者主动与被动技能列表（pve_skill）(int)→pve_skill.键值, 基础移动速度(int), 基础生命(int), 基础攻击(int)→monsterTroop.主键, 基础防御(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, 最大san值(int), 队形站位优先级（玩家控制友军）(int), AI行为（bt_ai页签）(int)→zombie_bt_ai.主键, RVO优先级（0~1）（>1锁定RVO）(float)
- 关联: → item(兵种等级→道具分类排序 @0.94), → shop_shop_item(兵种等级→商店id @0.92), → pve_pve_level(战斗力，显示值→关卡显示等级 @0.88), → city_node_type_cityNodeTypeConf(战斗力，显示值→节点类型  参考CityNodeType @0.84), → activity(战斗力，显示值→活动参数 @0.83), → pve_pve_level(幸存者主动与被动技能列表（pve_skill）→PVE关卡文件ID @0.83), → pve_pve_level(兵种等级→关卡显示等级 @0.81), → skill_condition(兵种等级→值参数对比条件 @0.79), → activity(兵种等级→活动参数 @0.78), → draw_card_discount(兵种等级→折扣组 @0.77), ...+44条出向, ← equip(装备位置→兵种等级 @0.76), ← kvkSeason(默认投票结果→兵种等级 @0.76), ← recharge(档位(真实付费)→兵种等级 @0.76), ← alliance_building(建筑类型→兵种等级 @0.76), ← alliance_science(显示Y轴坐标，纵坐标
(分为7层,最上面为第1层）
【只需配置第一级】
→兵种等级 @0.76), ← hud_config(显示权重，越大显示越前面→兵种等级 @0.76), ← task(任务类型→兵种等级 @0.76), ← activity(类型→战斗力，显示值 @0.75), ← equip(穿戴等级→战斗力，显示值 @0.73), ← science(等级→战斗力，显示值 @0.73), ...+24条入向

## 表: zombie_trap_item [item]
- 文件: zombie.xlsx | sheet: trap_item
- 行数: 9 | 列数: 7 | 主键: 主键
- 列: 主键(int)→city_node_type_cityNodeTypeConf.节点类型  参考CityNodeType, #策划备注(str), 名字(str), 类型
1 - 一次性增益
2 - 持续增益
3 - 一次性陷阱
4 - 持续陷阱(int), 显示模型(str)→model.键值, 拥有技能列表（都是只能对自己放的技能）(float)→key_new.facial, 基础数值(int)→data_constant.常量值
- 关联: → shop_shop_item(主键→商店id @0.8), → data_constant(基础数值→常量值 @0.71), → item(主键→道具分类排序 @0.66), → worldMonster(拥有技能列表（都是只能对自己放的技能）→序号 @0.65), → pve_pve_level(主键→关卡显示等级 @0.62), → key_new(拥有技能列表（都是只能对自己放的技能）→facial @0.62), → pve_pve_level(主键→PVE关卡文件ID @0.61), → city_node_type_cityNodeTypeConf(主键→节点类型  参考CityNodeType @0.61), → model(显示模型→键值 @0.61)

