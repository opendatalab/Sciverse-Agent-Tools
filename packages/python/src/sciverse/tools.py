"""Auto-generated. Do not edit. Run scripts/build.sh."""
import json

TOOLS_VERSION = "0.11.2"

OPENAI_TOOLS = json.loads(r"""
[
  {
    "type": "function",
    "function": {
      "name": "search_papers",
      "description": "按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。\n适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。\n不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。\n返回：论文元数据列表，每条含 unique_id（始终存在）、doc_id（仅当有全文）、title、author、abstract、publication_venue_name_unified、publication_published_year 等。",
      "parameters": {
        "type": "object",
        "properties": {
          "collection": {
            "type": "string",
            "enum": [
              "papers",
              "authors",
              "sources"
            ],
            "default": "papers",
            "description": "检索的实体集合。papers（默认，论文）/ authors（作者）/ sources（来源期刊）。 各 collection 字段集不同，用 list_catalog（collection=<name>）学习对应 schema。 注意：本工具的便捷字段（authors/journals/year_from/subjects 等）只对 papers 有意义； 查 authors/sources 时改用 filters_advanced + 该 collection 的字段名（如 authors 的 summary_stats.h_index / orcid，sources 的 issn / is_oa）。authors 用 orcid、 sources 用 issn 与论文检索结果关联。",
            "x-en-description": "Entity collection to search. papers (default) / authors / sources. Each collection has its own field schema — call list_catalog(collection=<name>). The convenience fields (authors/journals/year_from/subjects) apply to papers only; for authors/sources use filters_advanced with that collection's field names."
          },
          "query": {
            "type": "string",
            "description": "BM25 全文关键词，匹配标题/摘要/期刊名/关键词字段。留空则纯靠结构化过滤。"
          },
          "title_contains": {
            "type": "string",
            "description": "标题中必须包含的词（仅匹配 title 字段）。"
          },
          "abstract_contains": {
            "type": "string",
            "description": "摘要中必须包含的词（仅匹配 abstract 字段）。"
          },
          "authors": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "description": "作者名（任一命中即可）。SDK 内部映射到后端 `author` 字段（FILTER_OP_IN）。"
          },
          "year_from": {
            "type": "integer",
            "description": "起始发表年（含）。"
          },
          "year_to": {
            "type": "integer",
            "description": "结束发表年（含）。"
          },
          "journals": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "description": "期刊名（任一命中即可）。SDK 内部映射到后端 `publication_venue_name_unified` 字段（FILTER_OP_IN，规范化后的载体名）。"
          },
          "subjects": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "description": "学科分类，如 \"computer science\"、\"biology\"。"
          },
          "filters_advanced": {
            "type": "array",
            "description": "高级过滤逃生舱（仅当上述字段不够用时使用）。可用字段见 get_field_catalog。\n\n引文反查（常用）：field=\"references_unique_id\" 查「谁引用了某篇论文」，\nvalue 填目标论文的 unique_id。相比 list_paper_relations 的 CITATIONS，\n它支持深翻页与任意排序，适合超高被引论文。可叠加条件，\n例如「引用了 ResNet 且 2023 年后发表」：\n  [{\"field\":\"references_unique_id\",\"value\":\"paper:10.1109/cvpr.2016.90\"},\n   {\"field\":\"publication_published_year\",\"operator\":\"FILTER_OP_GTE\",\"value\":2023}]\n该字段仅支持过滤，不能排序/聚合，也不能放进 fields 返回。\n",
            "items": {
              "type": "object",
              "required": [
                "field",
                "value"
              ],
              "properties": {
                "field": {
                  "type": "string"
                },
                "operator": {
                  "type": "string",
                  "description": "过滤操作符。MATCH（分词模糊）适用于 author、keywords（输入 \"Hinton\" 命中 \"Geoffrey Hinton\"）； MATCH_PHRASE（短语模糊）适用于 publication_venue_name_unified，整词连续匹配（\"Nature\" 命中 \"Nature Communications\"；非前缀匹配，\"Nature Comm\" 不会命中）； doi 用 EQ，服务端归一化（去 doi.org 前缀+转小写）后精确匹配。MATCH/MATCH_PHRASE 仅对配了 text 子字段的字段有效。",
                  "enum": [
                    "FILTER_OP_EQ",
                    "FILTER_OP_NE",
                    "FILTER_OP_GT",
                    "FILTER_OP_GTE",
                    "FILTER_OP_LT",
                    "FILTER_OP_LTE",
                    "FILTER_OP_IN",
                    "FILTER_OP_NIN",
                    "FILTER_OP_CONTAINS",
                    "FILTER_OP_MATCH",
                    "FILTER_OP_MATCH_PHRASE"
                  ],
                  "default": "FILTER_OP_EQ"
                },
                "value": {}
              }
            }
          },
          "sort_advanced": {
            "type": "array",
            "description": "高级排序逃生舱（按任意可排序字段）。papers 用 sort_by_year 即可； authors/sources 想按 h-index / 被引 / works_count 排序时用本字段。 与 query 互斥（query 走相关性排序）。",
            "items": {
              "type": "object",
              "required": [
                "field",
                "order"
              ],
              "properties": {
                "field": {
                  "type": "string"
                },
                "order": {
                  "type": "string",
                  "enum": [
                    "SORT_ORDER_DESC",
                    "SORT_ORDER_ASC"
                  ],
                  "default": "SORT_ORDER_DESC"
                }
              }
            }
          },
          "sort_by_year": {
            "type": "string",
            "enum": [
              "desc",
              "asc",
              "none"
            ],
            "default": "desc"
          },
          "freshness_boost": {
            "type": "string",
            "enum": [
              "NONE",
              "MILD",
              "STRONG"
            ],
            "default": "NONE",
            "description": "模糊搜索新鲜度加权（仅 query 非空时生效；与 sort_by_year 互斥）。\nMILD: 近 10 年加权，适合日常查文献；STRONG: 近 3 年加权，适合跟踪\n研究方向 / 追最新进展。底层为 function_score + gauss decay over\npublication_published_date。\n"
          },
          "page": {
            "type": "integer",
            "default": 1,
            "minimum": 1
          },
          "page_size": {
            "type": "integer",
            "default": 10,
            "minimum": 1,
            "maximum": 50
          }
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "semantic_search",
      "description": "自然语言语义检索，返回相关文献片段（chunk）用于 RAG 回答。\n适用：「Transformer 注意力机制如何工作？」「最新的蛋白质折叠预测方法有哪些？」\n不适用：精确字段过滤 → search_papers；取完整原文 → read_content。\n返回：相关 chunk 列表，每条含 chunk_id/doc_id/abstract/chunk/score/title/offset。\n典型链路：semantic_search → 选取 chunk → read_content(doc_id, offset)。",
      "parameters": {
        "type": "object",
        "required": [
          "query"
        ],
        "properties": {
          "query": {
            "type": "string",
            "minLength": 1,
            "maxLength": 4096,
            "description": "自然语言查询，1-200 字最佳。"
          },
          "top_k": {
            "type": "integer",
            "default": 10,
            "minimum": 1,
            "maximum": 100,
            "description": "返回命中条数上限，合法 1-100（服务端校验，超出报 400）。\n实际条数还受 mode 影响：balanced 单路混合召回在服务端固定截到约 50 条，\ntop_k 超过 50 时多出的部分不会返回；fast 与 quality 可取到 top_k。\n另外同一篇论文最多返回约 3 个 chunk，因此高 top_k 需要命中足够多的不同论文。\n"
          },
          "source_types": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": [
                "web",
                "pdf"
              ]
            }
          },
          "mode": {
            "type": "string",
            "enum": [
              "fast",
              "balanced",
              "quality"
            ],
            "default": "balanced",
            "description": "fast = 仅关键词召回 (~200ms)；balanced = 混合检索 (~600ms)；quality = LLM 改写 + 混合 (~2-4s)。\n"
          }
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "list_catalog",
      "description": "返回 search_papers 所有可用字段的 catalog：字段名、类型、能否过滤/排序、\n是否默认返回、字段说明、FilterOperator 清单等。\n适用：「我该用哪个字段过滤 DOI?」「access_oa_status 有哪些可能值？」\n「`metadata_type` 的合法取值是？」\n不适用：实际查询文献，那是 search_papers / semantic_search 的事。\n典型用法：Agent 第一次接触 Sciverse 或碰到模糊字段需求时先调一次本接口，\n把 schema 装进 working memory，后续精确构造 search_papers 的 filters。\ninclude_sample_values=true 时返回枚举值样本（OpenSearch terms agg，缓存 24h）。",
      "parameters": {
        "type": "object",
        "properties": {
          "collection": {
            "type": "string",
            "enum": [
              "papers",
              "authors",
              "sources"
            ],
            "default": "papers",
            "description": "字段 catalog 所属实体集合。papers（默认）/ authors / sources，各 collection 字段不同。"
          },
          "include_sample_values": {
            "type": "boolean",
            "default": false,
            "description": "是否拉取 enum-like 字段的取值样本。false 仅返回静态 schema（毫秒级）；true 触发 OpenSearch terms agg（首次几百毫秒，之后 24h 走缓存）。"
          },
          "include_field_stats": {
            "type": "boolean",
            "default": false,
            "description": "是否返回字段统计（keyword 字段基数 + 数值字段 min/max/avg/p50/p95）。触发 OpenSearch 聚合，缓存 24h。"
          }
        },
        "required": []
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "list_paper_relations",
      "description": "分页返回某篇论文的引用关系完整列表。citations/references/related_works 是无界数组\n（单篇最大 34 万条），在 search_papers 中**不可投影**，取这些列表只能用本接口。\n适用：「论文 X 引用了哪些文献」（relation=REFERENCES）、「哪些文献引用了论文 X」\n（relation=CITATIONS）、「与论文 X 相关的工作」（relation=RELATED_WORKS）。\n注意：CITATIONS（被引：谁引用了我）与 REFERENCES（参考文献：我引用了谁）方向相反。\n典型链路：先 search_papers / semantic_search 拿到 unique_id，再用本接口按 relation 分页。\n两个上限（仅 CITATIONS 可能触发；REFERENCES/RELATED_WORKS 实测最大 11833/20 条）：\n关系数超 10000 返回 429；page×page_size 超 10000 返回 400。两种情况都改用\nsearch_papers 的 filters_advanced 传 references_unique_id 反查——可深翻页并任意排序。\ntotal_count 为库内命中数（不含指向库外论文的边），与论文自身 citation_count 可能有 ±1% 差异。",
      "parameters": {
        "type": "object",
        "required": [
          "unique_id",
          "relation"
        ],
        "properties": {
          "unique_id": {
            "type": "string",
            "description": "目标论文 unique_id（如 paper:10.1038/xxx），来自 search_papers / semantic_search；勿传 doc_id。"
          },
          "relation": {
            "type": "string",
            "enum": [
              "CITATIONS",
              "REFERENCES",
              "RELATED_WORKS"
            ],
            "description": "关系类型。CITATIONS=被引（谁引用了我）；REFERENCES=参考文献（我引用了谁）；RELATED_WORKS=相关工作。"
          },
          "page": {
            "type": "integer",
            "default": 1,
            "minimum": 1
          },
          "page_size": {
            "type": "integer",
            "default": 25,
            "minimum": 1,
            "maximum": 200
          }
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "read_content",
      "description": "按字节区间读取文献原文片段。通常配合 semantic_search 返回的 doc_id/offset 使用，\n用于扩展上下文（往前/往后读更多字节）。\n返回：UTF-8 文本片段、bytes_returned、next_offset、是否还有后续。",
      "parameters": {
        "type": "object",
        "properties": {
          "doc_id": {
            "type": "string",
            "description": "文献 ID（来自 search_papers / semantic_search）。"
          },
          "offset": {
            "type": "integer",
            "format": "int64",
            "default": 0
          },
          "limit": {
            "type": "integer",
            "format": "int64",
            "default": 4096,
            "maximum": 16384
          }
        },
        "required": [
          "doc_id"
        ]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_resource",
      "description": "按文件名取文献中嵌入的图片字节流（PNG / JPG 等）。\n触发场景：read_content 返回的 Markdown 中含 `![alt](file_name)` 形式的图片占位，\nagent 需要把图给用户看时调本接口。\n入参 file_name 来自 markdown 内的 url 段（相对路径，禁止 `\\\\` 或 `..`）。\n返回：HTTP 二进制流 + image/* Content-Type。\nSDK / MCP server 包装层会做 base64 + mime 转换以便 agent 多模态使用。",
      "parameters": {
        "type": "object",
        "properties": {
          "file_name": {
            "type": "string",
            "description": "图片相对路径，来自 read_content Markdown 中的 `![alt](file_name)` 占位。禁止 `\\\\` 与 `..`，不能以 `/` 开头。"
          }
        },
        "required": [
          "file_name"
        ]
      }
    }
  }
]
""")

ANTHROPIC_TOOLS = json.loads(r"""
[
  {
    "name": "search_papers",
    "description": "按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。\n适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。\n不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。\n返回：论文元数据列表，每条含 unique_id（始终存在）、doc_id（仅当有全文）、title、author、abstract、publication_venue_name_unified、publication_published_year 等。",
    "input_schema": {
      "type": "object",
      "properties": {
        "collection": {
          "type": "string",
          "enum": [
            "papers",
            "authors",
            "sources"
          ],
          "default": "papers",
          "description": "检索的实体集合。papers（默认，论文）/ authors（作者）/ sources（来源期刊）。 各 collection 字段集不同，用 list_catalog（collection=<name>）学习对应 schema。 注意：本工具的便捷字段（authors/journals/year_from/subjects 等）只对 papers 有意义； 查 authors/sources 时改用 filters_advanced + 该 collection 的字段名（如 authors 的 summary_stats.h_index / orcid，sources 的 issn / is_oa）。authors 用 orcid、 sources 用 issn 与论文检索结果关联。",
          "x-en-description": "Entity collection to search. papers (default) / authors / sources. Each collection has its own field schema — call list_catalog(collection=<name>). The convenience fields (authors/journals/year_from/subjects) apply to papers only; for authors/sources use filters_advanced with that collection's field names."
        },
        "query": {
          "type": "string",
          "description": "BM25 全文关键词，匹配标题/摘要/期刊名/关键词字段。留空则纯靠结构化过滤。"
        },
        "title_contains": {
          "type": "string",
          "description": "标题中必须包含的词（仅匹配 title 字段）。"
        },
        "abstract_contains": {
          "type": "string",
          "description": "摘要中必须包含的词（仅匹配 abstract 字段）。"
        },
        "authors": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "作者名（任一命中即可）。SDK 内部映射到后端 `author` 字段（FILTER_OP_IN）。"
        },
        "year_from": {
          "type": "integer",
          "description": "起始发表年（含）。"
        },
        "year_to": {
          "type": "integer",
          "description": "结束发表年（含）。"
        },
        "journals": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "期刊名（任一命中即可）。SDK 内部映射到后端 `publication_venue_name_unified` 字段（FILTER_OP_IN，规范化后的载体名）。"
        },
        "subjects": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "学科分类，如 \"computer science\"、\"biology\"。"
        },
        "filters_advanced": {
          "type": "array",
          "description": "高级过滤逃生舱（仅当上述字段不够用时使用）。可用字段见 get_field_catalog。\n\n引文反查（常用）：field=\"references_unique_id\" 查「谁引用了某篇论文」，\nvalue 填目标论文的 unique_id。相比 list_paper_relations 的 CITATIONS，\n它支持深翻页与任意排序，适合超高被引论文。可叠加条件，\n例如「引用了 ResNet 且 2023 年后发表」：\n  [{\"field\":\"references_unique_id\",\"value\":\"paper:10.1109/cvpr.2016.90\"},\n   {\"field\":\"publication_published_year\",\"operator\":\"FILTER_OP_GTE\",\"value\":2023}]\n该字段仅支持过滤，不能排序/聚合，也不能放进 fields 返回。\n",
          "items": {
            "type": "object",
            "required": [
              "field",
              "value"
            ],
            "properties": {
              "field": {
                "type": "string"
              },
              "operator": {
                "type": "string",
                "description": "过滤操作符。MATCH（分词模糊）适用于 author、keywords（输入 \"Hinton\" 命中 \"Geoffrey Hinton\"）； MATCH_PHRASE（短语模糊）适用于 publication_venue_name_unified，整词连续匹配（\"Nature\" 命中 \"Nature Communications\"；非前缀匹配，\"Nature Comm\" 不会命中）； doi 用 EQ，服务端归一化（去 doi.org 前缀+转小写）后精确匹配。MATCH/MATCH_PHRASE 仅对配了 text 子字段的字段有效。",
                "enum": [
                  "FILTER_OP_EQ",
                  "FILTER_OP_NE",
                  "FILTER_OP_GT",
                  "FILTER_OP_GTE",
                  "FILTER_OP_LT",
                  "FILTER_OP_LTE",
                  "FILTER_OP_IN",
                  "FILTER_OP_NIN",
                  "FILTER_OP_CONTAINS",
                  "FILTER_OP_MATCH",
                  "FILTER_OP_MATCH_PHRASE"
                ],
                "default": "FILTER_OP_EQ"
              },
              "value": {}
            }
          }
        },
        "sort_advanced": {
          "type": "array",
          "description": "高级排序逃生舱（按任意可排序字段）。papers 用 sort_by_year 即可； authors/sources 想按 h-index / 被引 / works_count 排序时用本字段。 与 query 互斥（query 走相关性排序）。",
          "items": {
            "type": "object",
            "required": [
              "field",
              "order"
            ],
            "properties": {
              "field": {
                "type": "string"
              },
              "order": {
                "type": "string",
                "enum": [
                  "SORT_ORDER_DESC",
                  "SORT_ORDER_ASC"
                ],
                "default": "SORT_ORDER_DESC"
              }
            }
          }
        },
        "sort_by_year": {
          "type": "string",
          "enum": [
            "desc",
            "asc",
            "none"
          ],
          "default": "desc"
        },
        "freshness_boost": {
          "type": "string",
          "enum": [
            "NONE",
            "MILD",
            "STRONG"
          ],
          "default": "NONE",
          "description": "模糊搜索新鲜度加权（仅 query 非空时生效；与 sort_by_year 互斥）。\nMILD: 近 10 年加权，适合日常查文献；STRONG: 近 3 年加权，适合跟踪\n研究方向 / 追最新进展。底层为 function_score + gauss decay over\npublication_published_date。\n"
        },
        "page": {
          "type": "integer",
          "default": 1,
          "minimum": 1
        },
        "page_size": {
          "type": "integer",
          "default": 10,
          "minimum": 1,
          "maximum": 50
        }
      }
    }
  },
  {
    "name": "semantic_search",
    "description": "自然语言语义检索，返回相关文献片段（chunk）用于 RAG 回答。\n适用：「Transformer 注意力机制如何工作？」「最新的蛋白质折叠预测方法有哪些？」\n不适用：精确字段过滤 → search_papers；取完整原文 → read_content。\n返回：相关 chunk 列表，每条含 chunk_id/doc_id/abstract/chunk/score/title/offset。\n典型链路：semantic_search → 选取 chunk → read_content(doc_id, offset)。",
    "input_schema": {
      "type": "object",
      "required": [
        "query"
      ],
      "properties": {
        "query": {
          "type": "string",
          "minLength": 1,
          "maxLength": 4096,
          "description": "自然语言查询，1-200 字最佳。"
        },
        "top_k": {
          "type": "integer",
          "default": 10,
          "minimum": 1,
          "maximum": 100,
          "description": "返回命中条数上限，合法 1-100（服务端校验，超出报 400）。\n实际条数还受 mode 影响：balanced 单路混合召回在服务端固定截到约 50 条，\ntop_k 超过 50 时多出的部分不会返回；fast 与 quality 可取到 top_k。\n另外同一篇论文最多返回约 3 个 chunk，因此高 top_k 需要命中足够多的不同论文。\n"
        },
        "source_types": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "web",
              "pdf"
            ]
          }
        },
        "mode": {
          "type": "string",
          "enum": [
            "fast",
            "balanced",
            "quality"
          ],
          "default": "balanced",
          "description": "fast = 仅关键词召回 (~200ms)；balanced = 混合检索 (~600ms)；quality = LLM 改写 + 混合 (~2-4s)。\n"
        }
      }
    }
  },
  {
    "name": "list_catalog",
    "description": "返回 search_papers 所有可用字段的 catalog：字段名、类型、能否过滤/排序、\n是否默认返回、字段说明、FilterOperator 清单等。\n适用：「我该用哪个字段过滤 DOI?」「access_oa_status 有哪些可能值？」\n「`metadata_type` 的合法取值是？」\n不适用：实际查询文献，那是 search_papers / semantic_search 的事。\n典型用法：Agent 第一次接触 Sciverse 或碰到模糊字段需求时先调一次本接口，\n把 schema 装进 working memory，后续精确构造 search_papers 的 filters。\ninclude_sample_values=true 时返回枚举值样本（OpenSearch terms agg，缓存 24h）。",
    "input_schema": {
      "type": "object",
      "properties": {
        "collection": {
          "type": "string",
          "enum": [
            "papers",
            "authors",
            "sources"
          ],
          "default": "papers",
          "description": "字段 catalog 所属实体集合。papers（默认）/ authors / sources，各 collection 字段不同。"
        },
        "include_sample_values": {
          "type": "boolean",
          "default": false,
          "description": "是否拉取 enum-like 字段的取值样本。false 仅返回静态 schema（毫秒级）；true 触发 OpenSearch terms agg（首次几百毫秒，之后 24h 走缓存）。"
        },
        "include_field_stats": {
          "type": "boolean",
          "default": false,
          "description": "是否返回字段统计（keyword 字段基数 + 数值字段 min/max/avg/p50/p95）。触发 OpenSearch 聚合，缓存 24h。"
        }
      },
      "required": []
    }
  },
  {
    "name": "list_paper_relations",
    "description": "分页返回某篇论文的引用关系完整列表。citations/references/related_works 是无界数组\n（单篇最大 34 万条），在 search_papers 中**不可投影**，取这些列表只能用本接口。\n适用：「论文 X 引用了哪些文献」（relation=REFERENCES）、「哪些文献引用了论文 X」\n（relation=CITATIONS）、「与论文 X 相关的工作」（relation=RELATED_WORKS）。\n注意：CITATIONS（被引：谁引用了我）与 REFERENCES（参考文献：我引用了谁）方向相反。\n典型链路：先 search_papers / semantic_search 拿到 unique_id，再用本接口按 relation 分页。\n两个上限（仅 CITATIONS 可能触发；REFERENCES/RELATED_WORKS 实测最大 11833/20 条）：\n关系数超 10000 返回 429；page×page_size 超 10000 返回 400。两种情况都改用\nsearch_papers 的 filters_advanced 传 references_unique_id 反查——可深翻页并任意排序。\ntotal_count 为库内命中数（不含指向库外论文的边），与论文自身 citation_count 可能有 ±1% 差异。",
    "input_schema": {
      "type": "object",
      "required": [
        "unique_id",
        "relation"
      ],
      "properties": {
        "unique_id": {
          "type": "string",
          "description": "目标论文 unique_id（如 paper:10.1038/xxx），来自 search_papers / semantic_search；勿传 doc_id。"
        },
        "relation": {
          "type": "string",
          "enum": [
            "CITATIONS",
            "REFERENCES",
            "RELATED_WORKS"
          ],
          "description": "关系类型。CITATIONS=被引（谁引用了我）；REFERENCES=参考文献（我引用了谁）；RELATED_WORKS=相关工作。"
        },
        "page": {
          "type": "integer",
          "default": 1,
          "minimum": 1
        },
        "page_size": {
          "type": "integer",
          "default": 25,
          "minimum": 1,
          "maximum": 200
        }
      }
    }
  },
  {
    "name": "read_content",
    "description": "按字节区间读取文献原文片段。通常配合 semantic_search 返回的 doc_id/offset 使用，\n用于扩展上下文（往前/往后读更多字节）。\n返回：UTF-8 文本片段、bytes_returned、next_offset、是否还有后续。",
    "input_schema": {
      "type": "object",
      "properties": {
        "doc_id": {
          "type": "string",
          "description": "文献 ID（来自 search_papers / semantic_search）。"
        },
        "offset": {
          "type": "integer",
          "format": "int64",
          "default": 0
        },
        "limit": {
          "type": "integer",
          "format": "int64",
          "default": 4096,
          "maximum": 16384
        }
      },
      "required": [
        "doc_id"
      ]
    }
  },
  {
    "name": "get_resource",
    "description": "按文件名取文献中嵌入的图片字节流（PNG / JPG 等）。\n触发场景：read_content 返回的 Markdown 中含 `![alt](file_name)` 形式的图片占位，\nagent 需要把图给用户看时调本接口。\n入参 file_name 来自 markdown 内的 url 段（相对路径，禁止 `\\\\` 或 `..`）。\n返回：HTTP 二进制流 + image/* Content-Type。\nSDK / MCP server 包装层会做 base64 + mime 转换以便 agent 多模态使用。",
    "input_schema": {
      "type": "object",
      "properties": {
        "file_name": {
          "type": "string",
          "description": "图片相对路径，来自 read_content Markdown 中的 `![alt](file_name)` 占位。禁止 `\\\\` 与 `..`，不能以 `/` 开头。"
        }
      },
      "required": [
        "file_name"
      ]
    }
  }
]
""")
