from pathlib import Path
from generators._common import load_openapi, get_request_schema

SPEC = Path(__file__).resolve().parents[1] / 'openapi.yaml'

def test_multi_entity_search_contract():
    spec = load_openapi(SPEC)
    op = spec['paths']['/meta-search']['post']
    assert op['operationId'] == 'search_metadata'
    schema = get_request_schema(op, spec)
    assert schema['additionalProperties'] is False
    assert schema['properties']['collection']['enum'] == ['papers', 'authors', 'sources', 'patents']
    assert {'filters', 'sort', 'cursor', 'facets', 'fields'} <= schema['properties'].keys()
    assert 'sort_by_year' not in schema['properties']
    assert op['x-legacy-operation']['operationId'] == 'search_papers'
    legacy = get_request_schema(op['x-legacy-operation'], spec)
    assert 'filters_advanced' in legacy['properties']

def test_patent_content_and_catalog_contract():
    spec = load_openapi(SPEC)
    for path, collections in [('/content', ['papers', 'patents']), ('/meta-catalog', ['papers', 'authors', 'sources', 'patents'])]:
        schema = get_request_schema(spec['paths'][path]['get'], spec)
        assert schema['properties']['collection']['enum'] == collections

def test_metadata_response_does_not_require_paper_fields():
    from generators._common import inline_refs
    from jsonschema import validate
    spec = load_openapi(SPEC)
    response = spec['paths']['/meta-search']['post']['responses']['200']['content']['application/json']['schema']
    schema = inline_refs(response, spec)
    for record in [{'invention_title': '示例', 'doc_id': 'abc'}, {'display_name': 'Author'}, {'id': 'S1'}]:
        validate({'results': [record], 'total_count': '1', 'page': 1, 'page_size': 1,
                  'facets': [{'field': 'type', 'buckets': [{'key': 'journal', 'doc_count': '1'}]}]}, schema)

def test_default_generated_tools_use_only_new_name():
    from generators.to_openai import generate
    names = {t['function']['name'] for t in generate(SPEC)['tools']}
    assert 'search_metadata' in names
    assert 'search_papers' not in names

def test_script_artifacts_are_in_release_and_drift_checks():
    root = SPEC.parent
    for path in ['clawhub/scripts', 'skill-claude-code/skills/sciverse/scripts']:
        assert path in (root / '.releaserc.yaml').read_text()
        assert path in (root / '.github/workflows/test.yml').read_text()
