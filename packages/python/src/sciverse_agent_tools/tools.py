"""Auto-generated. Do not edit. Run scripts/build.sh."""
TOOLS_VERSION = "0.2.0"
OPENAI_TOOLS = [
  {
    "type": "function",
    "function": {
      "name": "search_papers",
      "description": "按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。\n适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。\n不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。\n返回：论文元数据列表，每条含 doc_id、title、author、abstract、publication_venue_name、publication_published_year 等。",
      "parameters": {
        "type": "object",
        "properties": {
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
            "description": "期刊名（任一命中即可）。SDK 内部映射到后端 `publication_venue_name` 字段（FILTER_OP_IN）。"
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
            "description": "高级过滤逃生舱（仅当上述字段不够用时使用）。",
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
                  "enum": [
                    "FILTER_OP_EQ",
                    "FILTER_OP_NE",
                    "FILTER_OP_GT",
                    "FILTER_OP_GTE",
                    "FILTER_OP_LT",
                    "FILTER_OP_LTE",
                    "FILTER_OP_IN",
                    "FILTER_OP_NIN",
                    "FILTER_OP_CONTAINS"
                  ],
                  "default": "FILTER_OP_EQ"
                },
                "value": {}
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
            "maximum": 30
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
  }
]
ANTHROPIC_TOOLS = [
  {
    "name": "search_papers",
    "description": "按结构化条件检索学术文献元数据（标题、作者、期刊、年份、摘要等）。\n适用：「查找 Hinton 在 2020-2023 年发表的论文」「找 Nature 上关于 CRISPR 的近期文献」。\n不适用：自然语言问答检索 → 用 semantic_search；查全文片段 → 用 read_content。\n返回：论文元数据列表，每条含 doc_id、title、author、abstract、publication_venue_name、publication_published_year 等。",
    "input_schema": {
      "type": "object",
      "properties": {
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
          "description": "期刊名（任一命中即可）。SDK 内部映射到后端 `publication_venue_name` 字段（FILTER_OP_IN）。"
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
          "description": "高级过滤逃生舱（仅当上述字段不够用时使用）。",
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
                "enum": [
                  "FILTER_OP_EQ",
                  "FILTER_OP_NE",
                  "FILTER_OP_GT",
                  "FILTER_OP_GTE",
                  "FILTER_OP_LT",
                  "FILTER_OP_LTE",
                  "FILTER_OP_IN",
                  "FILTER_OP_NIN",
                  "FILTER_OP_CONTAINS"
                ],
                "default": "FILTER_OP_EQ"
              },
              "value": {}
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
          "maximum": 30
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
  }
]
