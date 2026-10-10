# 班级管理测试数据与 NL2SQL 样例问题

业务库 `backend/data/analytics.db` 在应用启动时会执行 `seed_analytics.py`：若 `classes` 表为空，会自动写入下列演示数据（不影响已有 `sales` 表数据）。

## 表结构摘要

| 表名 | 说明 |
|------|------|
| `classes` | 班级：`class_code`、`class_name`、`grade`、`head_teacher`、`room_no`、`max_capacity` |
| `students` | 学生：`student_no`、`name`、`gender`、`class_id`（关联 `classes.id`）、`math_score`、`english_score` |

## 演示班级与学生规模

- **三年级一班**（G301）：5 名学生  
- **三年级二班**（G302）：6 名学生  
- **四年级一班**（G401）：4 名学生  

## 建议测试问题（自然语言 → 期望涉及 SQL 思路）

1. **三年级一共有几个班？每个班各有多少名学生？**  
   - 涉及：`classes` 与 `students` 按年级筛选、`COUNT`、按班分组。

2. **哪个班的数学平均分最高？**  
   - 涉及：`students` 按 `class_id` 分组、`AVG(math_score)`，可与 `classes` 联查班级名称。

3. **四年级一班所有学生的数学和英语平均分分别是多少？**  
   - 涉及：联表或子查询定位 G401 / 四年级一班，`AVG(math_score)`、`AVG(english_score)`。

登录测试：先访问前端登录页，使用后端 `AUTH_DEMO_MODE=true` 时任意账号密码即可；再进入工作区用上述问题验证 NL2SQL（需配置 `DASHSCOPE_API_KEY`）。
