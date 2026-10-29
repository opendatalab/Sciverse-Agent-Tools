# 多实体检索迁移指南（breaking 1.0 计划）

本次升级按 breaking 1.0 计划组织：默认工具名、参数契约及工具发现结果有变化。
最终发布版本号由 release 流程自动确定；本指南不手工指定或修改最终版本号。

## 新入口

| 入口 | 新调用 |
| --- | --- |
| MCP / Function calling | `search_metadata` |
| Python SDK | `await client.search_metadata(...)` |
| TypeScript SDK | `await client.searchMetadata({...})` |
| Python CLI | `sciverse search-metadata` |
| Skills 脚本 | `node scripts/search_metadata.mjs '<JSON>'` |

`collection` 支持 `papers`、`authors`、`sources`、`patents`，省略时为 `papers`。
先用相同 collection 调用 `list_catalog`，再按该实体的字段构造查询；论文的年份、作者字段不能直接套在专利、作者或来源集合上。

## 参数迁移：不能只改工具名

新入口使用 canonical `filters` 和 `sort`，不接受 `filters_advanced`、`sort_advanced` 或论文便捷参数。新脚本会拒绝未知顶层参数，避免参数被后端静默忽略。

| 旧参数 | 新调用迁移方式 |
| --- | --- |
| `authors=["Hinton"]` | `{"field":"author","operator":"FILTER_OP_IN","value":["Hinton"]}` |
| `year_from=2020` | `{"field":"publication_published_year","operator":"FILTER_OP_GTE","value":2020}` |
| `year_to=2024` | `{"field":"publication_published_year","operator":"FILTER_OP_LTE","value":2024}` |
| `journals=[...]` | `publication_venue_name_unified` + `FILTER_OP_IN` |
| `subjects=[...]` | `subjects` + `FILTER_OP_IN` |
| `title_contains` | 先用 `list_catalog` 确认 `title` 可过滤及支持的算子；仅在支持时使用相应过滤器，否则使用 `query` 检索可检索字段 |
| `abstract_contains` | 当前服务 `abstract` 为 `filterable=false`，不能直接转成 `abstract` + `FILTER_OP_CONTAINS`；使用 `query` 检索可检索字段，并按 `list_catalog` 确认字段能力，不能保证摘要单字段过滤 |

旧 `filters_advanced` 缺省的 operator 需明确补为 `FILTER_OP_EQ`；旧 `sort_advanced` 缺省的 order 需补为 `SORT_ORDER_DESC`。保留原有值的类型，例如布尔字段用 `true`，数值字段用数值。

旧调用：

```python
await client.search_papers(authors=["Hinton"], year_from=2020, sort_by_year="desc")
```

新调用（保留原先显式年份降序语义）：

```python
await client.search_metadata(
    collection="papers",
    filters=[
        {"field": "author", "operator": "FILTER_OP_IN", "value": ["Hinton"]},
        {"field": "publication_published_year", "operator": "FILTER_OP_GTE", "value": 2020},
    ],
    sort=[{"field": "publication_published_year", "order": "SORT_ORDER_DESC"}],
)
```

新入口不会自动加年份排序。旧 `sort_by_year="asc"/"desc"` 应转为显式 sort；`none` 应省略 sort。旧 `auto` 在有 query 时保持相关性，纯论文过滤时默认年份降序；若要保留后一行为，必须显式加 sort。显式排序会禁用相关性软加权，论文相关性与时效兼顾时用 `freshness_boost`。

```bash
sciverse search-metadata --collection authors --filters '[{"field":"summary_stats.h_index","operator":"FILTER_OP_GTE","value":50}]' --sort '[{"field":"cited_by_count","order":"SORT_ORDER_DESC"}]'
node scripts/search_metadata.mjs '{"collection":"patents","query":"CRISPR","page_size":5}'
```

## 正文与能力边界

`read_content` 支持 `collection="papers"` 或 `"patents"`，默认 `papers`、`offset=0`、`limit=4096`。offset/limit 按 Unicode 码点计数，不是字节。传入检索返回的 doc_id，不要拼接或猜测 ID；后续分页沿用同一 collection 和返回的 next_offset。

```bash
node scripts/read_content.mjs '{"collection":"patents","doc_id":"<检索返回的doc_id>","offset":0,"limit":4096}'
```

`semantic_search` 仍只检索论文，不能用专利关键词把它变成专利检索。`list_paper_relations` 仍为论文引用关系工具。`get_resource` 主要读取论文图表图片，不新增 ZIP 下载能力。

## 兼容旧调用

按宿主保留 `search_papers.mjs` 的原语义：

- **ClawHub**：旧脚本原样透传 canonical 参数，不添加默认 collection 或年份排序，不转换便捷参数；filters、sort 和 cursor 保持调用方原值。
- **Web skill（以及使用同一便捷转换脚本的 Claude fallback）**：既有论文便捷参数及 advanced 参数仍按旧规则翻译。

以下便捷参数兼容规则适用于 Web 旧脚本，不改变 ClawHub 的透传行为。非 papers 集合不再自动添加论文年份排序，并拒绝 `authors`、`journals`、`subjects`、`year_from`、`year_to`、`title_contains`、`abstract_contains`。旧 `sort_by_year="none"` 或 `"auto"` 仍允许，均不添加年份排序；仅 `"asc"` / `"desc"` 因要求论文年份排序而拒绝。这与 Python / TypeScript SDK 的兼容语义一致。显式 canonical sort 或旧 sort_advanced 保持原排序，不会被自动年份排序抢占。

MCP 默认发现新工具列表。旧客户端仍需要原工具列表时，在 **MCP 服务进程** 环境中设置：

```bash
export SCIVERSE_ENABLE_LEGACY_TOOLS=true
```

重启 MCP 服务并刷新客户端工具列表。桌面客户端可在 MCP 配置的 `env` 中设为字符串 `"true"`。这是旧工具发现列表的兼容开关，不会让论文语义检索支持专利，也不会关闭集合参数校验。新集成应直接使用新入口。
